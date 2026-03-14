#pragma once

#include <Arduino.h>
#include "hardware/pio.h"
#include "pin_map.h"
#include "spi.pio.h"                  // PIO program + ch446_stb_pin/pulse helpers
#include "path_mapping_algo.h"        // ch[], path[], netStruct
#include "nets_to_chip_connections.h" // numberOfPaths, netsToChipConnections()

// ---------------------------------------------------------------------------
// ch446q_config — CH446Q crosspoint switch controller
//
// Hardware: 12× CH446Q analog matrix switches (8Y × 16X per chip)
//   Chips A-H (0-7) : breadboard rows
//   Chips I-J (8-9) : Nano header + external 40-pin header
//   Chips K-L (10-11): special function + bridge
//
// Serial protocol (shared bus):
//   DAT  = GPIO 14   (CH_DATA, shared MOSI to all chips)
//   CLK  = GPIO 15   (CH_CLK,  shared clock)
//   STBx = per-chip  (STB_A..STB_L, active HIGH latch pulse)
//   RST  = GPIO 24   (CH_RST,  active HIGH resets all chips)
//
// 8-bit command format sent MSB first:
//   [ AX3 AX2 AX1 AX0 | AY2 AY1 AY0 | DS ]
//   AX = X address (0-15), AY = Y address (0-7), DS = 1 connect / 0 disconnect
// ---------------------------------------------------------------------------

// Initialise PIO-SPI bus and all 12 CH446Q chips.
// Must be called once before any sendXYraw / sendAllPaths.
void initCH446Q();

// Send a single switch command to one chip.
//   chip       : CHIP_A..CHIP_L (0-11)
//   x          : X address 0-15
//   y          : Y address 0-7
//   setOrClear : 1 = close switch, 0 = open switch
void sendXYraw(int chip, int x, int y, int setOrClear);

// Send all committed X/Y hops for path[i].
void sendPath(int i, int setOrClear);

// Send every path in path[0..numberOfPaths-1].
void sendAllPaths(int setOrClear);

// Hardware-reset all 12 chips via CH_RST pulse. Clears every connection
// instantly and resets the software xStatus/yStatus mirrors.
void clearAllChips();
