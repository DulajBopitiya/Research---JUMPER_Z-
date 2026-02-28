
#pragma once


#include <Arduino.h>


#define esp32_STM32_Bridge_Tx 46
#define esp32_STM32_Bridge_Rx 45


///External connections (40 pin header)
// 
#define EXT_RESET 48
#define EXT_PIN_1 45
#define EXT_PIN_2 1 //connected via nano header A0
#define EXT_PIN_3 42
#define EXT_PIN_4 2 //connected via nano header D1
#define EXT_PIN_Tx NULL // not connected to ep32 mini, connected from rp side along from mux
#define EXT_PIN_6 3 //connected via nano header A2
#define EXT_PIN_Rx NULL // not connected to ep32 mini, connected from rp side along from mux
#define EXT_PIN_8 4 //connected via nano header D3
#define EXT_PIN_9 41
#define EXT_PIN_10 5 //connected via nano header A4
#define EXT_PIN_11 NULL // conneced to GND
#define EXT_PIN_12 6 //connnected via nano header D5
#define EXT_PIN_13 40 
#define EXT_PIN_14 7 //connected via nano header A6
#define EXT_PIN_15 39
#define EXT_PIN_16 8  // connected via nano header D7
#define EXT_PIN_17 38
#define EXT_PIN_18 9  // conneced via nano header D11
#define EXT_PIN_19 37 // also connected via a nano heade AREF
#define EXT_PIN_20 10 // connected via nano header D9
#define EXT_PIN_21 36 //connected via nano header D12
#define EXT_PIN_22 11 // connected via nano header D13
#define EXT_PIN_23 35 // connected via nano header D10
#define EXT_PIN_24 NULL // connected to GND
#define EXT_PIN_DEV_BOOT 47 
#define EXT_PIN_26 12 //connnect via nano header D0
#define EXT_PIN_27 34 //connected via nano header D8
#define EXT_PIN_28 13 // connected via nano header A1
#define EXT_PIN_29 33 // connected via nano header A7
#define EXT_PIN_30 14 // connected via nano header D2
#define EXT_PIN_31 26 // connected via nano header D6
#define EXT_PIN_32 12 // connected via nano header D13 , some fucks going on here, his also connected to D13
#define EXT_PIN_33 21 // connected via nano header A5
#define EXT_PIN_34 NULL // connected to analog 5v
#define EXT_PIN_35 18 // connected via nano header D4


