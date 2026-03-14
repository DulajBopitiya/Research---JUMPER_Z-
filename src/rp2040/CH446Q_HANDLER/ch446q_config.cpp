#include "ch446q_config.h"

// ---------------------------------------------------------------------------
// PIO state machine handle (PIO0, SM0)
// ---------------------------------------------------------------------------
static uint _progOffset = 0;
static PIO  _pio        = pio0;
static uint _sm         = 0;

// ---------------------------------------------------------------------------
// initCH446Q
// ---------------------------------------------------------------------------
void initCH446Q()
{
    // ── 1. Hardware reset all chips (active HIGH, hold ≥100 ns) ─────────────
    pinMode(CH_RST, OUTPUT);
    digitalWrite(CH_RST, HIGH);
    delayMicroseconds(1);
    digitalWrite(CH_RST, LOW);

    // ── 2. Load PIO program and start state machine ──────────────────────────
    _progOffset = pio_add_program(_pio, &spi_ch446_multi_cs_program);

    // clkdiv = 2.0 → bit clock ≈ 125 MHz / (2 × 2 × ~7 cycles/bit) ≈ 4.5 MHz
    // Well within the CH446Q 40 MHz serial clock limit.
    pio_spi_ch446_multi_cs_init(_pio, _sm, _progOffset,
                                /*n_bits=*/8, /*clkdiv=*/2.0f,
                                /*pin_sck=*/CH_CLK, /*pin_mosi=*/CH_DATA);

    // ── 3. We use polling (not ISR) to wait for the PIO IRQ flag. ───────────
    //    The pio_spi_ch446_multi_cs_init call enables PIO0_IRQ_0 at the NVIC,
    //    so disable it — we will poll pio_interrupt_get() in sendXYraw instead.
    irq_set_enabled(PIO0_IRQ_0, false);
    pio_interrupt_clear(_pio, _sm);

    // ── 4. Clear software status mirrors ─────────────────────────────────────
    for (int c = 0; c < 12; c++) {
        for (int x = 0; x < 16; x++) ch[c].xStatus[x] = -1;
        for (int y = 0; y < 8;  y++) ch[c].yStatus[y] = -1;
    }
}

// ---------------------------------------------------------------------------
// sendXYraw  (time-critical — runs from SRAM to avoid flash wait states)
//
// Flow:
//   1. Build 8-bit CH446Q command byte
//   2. Push it into PIO TX FIFO (8-bit alias → hardware byte-replicates for
//      MSB-first autopull)
//   3. Spin until PIO fires IRQ0 after the last bit is shifted out
//   4. Pulse STB for this chip  →  CH446Q latches the switch state
//   5. Clear PIO IRQ so the state machine can process the next word
//   6. Update software xStatus mirror
// ---------------------------------------------------------------------------
void __time_critical_func(sendXYraw)(int chip, int x, int y, int setOrClear)
{
    if (chip < CHIP_A || chip > CHIP_L) return;
    if (x < 0 || x > 15 || y < 0 || y > 7)  return;

    // [ AY2 AY1 AY0 | AX3 AX2 AX1 AX0 | DS ]  — Y in upper 3 bits, X in next 4, DS last
    uint8_t cmd = (uint8_t)(((y & 0x07) << 5) | ((x & 0x0F) << 1) | (setOrClear & 1));

    // Write via 8-bit FIFO alias.
    // Hardware byte-replicates the value so the MSB contains our data,
    // which is what the MSB-first PIO shift-out expects.
    io_rw_8 *txfifo = (io_rw_8 *)&_pio->txf[_sm];
    while (pio_sm_is_tx_fifo_full(_pio, _sm)) tight_loop_contents();
    *txfifo = cmd;

    // Wait for PIO to finish shifting and signal IRQ (after last bit)
    while (!pio_interrupt_get(_pio, _sm)) tight_loop_contents();

    // Pulse STB for the target chip and clear the PIO IRQ flag
    ch446_stb_pulse(_pio, _sm, (uint)chip);

    // Update software status mirror
    ch[chip].xStatus[x] = setOrClear ? (int16_t)1 : (int16_t)-1;
}

// ---------------------------------------------------------------------------
// sendPath
// Iterate up to 4 chip hops in path[i] and send each switch command.
// ---------------------------------------------------------------------------
void sendPath(int i, int setOrClear)
{
    if (i < 0 || i >= numberOfPaths) return;
    if (path[i].skip) return;

    for (int hop = 0; hop < 6; hop++) {
        int c = path[i].chip[hop];
        int x = path[i].x[hop];
        int y = path[i].y[hop];

        if (c == -1) break;           // no more hops
        if (x == -1 || y == -1) continue; // hop not yet committed (skip for now)

        sendXYraw(c, x, y, setOrClear);
    }
}

// ---------------------------------------------------------------------------
// sendAllPaths
// ---------------------------------------------------------------------------
void sendAllPaths(int setOrClear)
{
    for (int i = 0; i < numberOfPaths; i++) {
        sendPath(i, setOrClear);
    }
}

// ---------------------------------------------------------------------------
// clearAllChips
// Hardware RST pulse clears every switch on all 12 chips simultaneously.
// Also resets the software status mirrors.
// ---------------------------------------------------------------------------
void clearAllChips()
{
    digitalWrite(CH_RST, HIGH);
    delayMicroseconds(1);
    digitalWrite(CH_RST, LOW);

    for (int c = 0; c < 12; c++) {
        for (int x = 0; x < 16; x++) ch[c].xStatus[x] = -1;
        for (int y = 0; y < 8;  y++) ch[c].yStatus[y] = -1;
    }

    numberOfPaths = 0;
}
