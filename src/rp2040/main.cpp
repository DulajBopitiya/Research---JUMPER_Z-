#include <Arduino.h>

// Your pins
#define CH_DATA 14   // DAT
#define CH_CLK  15   // CS/CK (serial clock)
#define CH_RST  24   // RST (ACTIVE HIGH reset)
#define STB_A   6    // STB (execute/latch)  <-- your "CS_A" likely behaves as STB

// pulse helpers
static inline void clkPulse() {
  digitalWrite(CH_CLK, HIGH);
  delayMicroseconds(2);
  digitalWrite(CH_CLK, LOW);
  delayMicroseconds(2);
}

static inline void stbPulse() {
  digitalWrite(STB_A, HIGH);
  delayMicroseconds(5);
  digitalWrite(STB_A, LOW);
  delayMicroseconds(5);
}

// Shift 7-bit address MSB->LSB on DAT, clocked by CH_CLK rising edges
static void ch_shiftAddress7(uint8_t addr7)
{
  for (int i = 6; i >= 0; i--) {
    digitalWrite(CH_DATA, (addr7 >> i) & 0x01);
    // datasheet says rising edge is valid in serial mode
    clkPulse();
  }
}

// Write one crosspoint (X0..15, Y0..7), on=true/false
static void ch_writeSwitch(uint8_t x, uint8_t y, bool on)
{
  if (x > 15 || y > 7) return;

  uint8_t addr = (y << 4) | x; // addressing table in datasheet

  // 1) shift address
  ch_shiftAddress7(addr);

  // 2) put data bit on DAT (1=ON, 0=OFF)
  digitalWrite(CH_DATA, on ? HIGH : LOW);
  delayMicroseconds(2);

  // 3) STB high pulse to execute/latch
  stbPulse();

  // leave DAT low
  digitalWrite(CH_DATA, LOW);
}

static void ch_reset()
{
  // RST is ACTIVE HIGH: high clears all latches (all switches open)
  digitalWrite(CH_RST, HIGH);
  delay(10);
  digitalWrite(CH_RST, LOW);
  delay(10);
}

void setup()
{
  Serial.begin(115200);

  pinMode(CH_DATA, OUTPUT);
  pinMode(CH_CLK, OUTPUT);
  pinMode(CH_RST, OUTPUT);
  pinMode(STB_A, OUTPUT);

  digitalWrite(CH_DATA, LOW);
  digitalWrite(CH_CLK, LOW);
  digitalWrite(STB_A, LOW);
  digitalWrite(CH_RST, LOW);

  Serial.println("CH446Q SERIAL MODE TEST");

  ch_reset();
  delay(500);


}

void loop() {

    // Turn ON: X2 <-> Y1  (address 0x12)
  // Serial.println("ON  : Y1-X2 (0x12)");
  // 

  // 

  // Turn OFF: same switch
  Serial.println("OFF : Y1-X2 (0x12)");
  ch_writeSwitch(2, 1, false);

  delay(1000);

  ch_writeSwitch(2, 1, true);
  delay(1000);
}