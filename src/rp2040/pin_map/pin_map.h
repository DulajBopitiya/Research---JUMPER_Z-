#pragma once

#include <Arduino.h>

#define ESP32_RP_COM_TX 19
#define ESP32_RP_COM_RX 18

#define RGB_LED_PIN 25


#define MAX_NETS 64

// Your pins
#define CH_DATA 14   // DAT
#define CH_CLK  15   // CS/CK (serial clock)
#define CH_RST  24   // RST (ACTIVE HIGH reset)


//BRead board numbers not how they are placed
#define CHIP_A 0
#define CHIP_B 1
#define CHIP_C 2
#define CHIP_D 3
#define CHIP_E 4
#define CHIP_F 5
#define CHIP_G 6
#define CHIP_H 7
#define CHIP_I 8
#define CHIP_J 9
#define CHIP_K 10
#define CHIP_L 11



//Breadboard connected CH STB pinmapping
#define STB_A 6
#define STB_B 7
#define STB_C 8
#define STB_D 9
#define STB_E 10
#define STB_F 11
#define STB_G 12
#define STB_H 13


//Special function ch chips STB pins
#define STB_I 20
#define STB_J 21
#define STB_K 22
#define STB_L 23


//Cross and mux uart // form mux this connected to nano header and external headers

//this is temporaray
// GPIO 1: Nano reset line (active LOW pulse triggers bootloader entry)
#define NANO_RST_PIN  1
#define MUX_SWITCH 0



//definetions for pathfinding algo stuff
//not the pin definitions only defines for algo stuff

#define MAX_BRIDGES 255
#define MAX_NODES 64
#define MAX_DUPLICATE 12


#define TOP_1  1
#define TOP_2  2
#define TOP_3  3
#define TOP_4  4
#define TOP_5  5
#define TOP_6  6
#define TOP_7  7
#define TOP_8  8
#define TOP_9  9
#define TOP_10 10
#define TOP_11 11
#define TOP_12 12
#define TOP_13 13
#define TOP_14 14
#define TOP_15 15
#define TOP_16 16
#define TOP_17 17
#define TOP_18 18
#define TOP_19 19
#define TOP_20 20
#define TOP_21 21
#define TOP_22 22
#define TOP_23 23
#define TOP_24 24
#define TOP_25 25
#define TOP_26 26
#define TOP_27 27
#define TOP_28 28
#define TOP_29 29
#define TOP_30 30


#define BOTTOM_1 31
#define BOTTOM_2 32
#define BOTTOM_3 33
#define BOTTOM_4 34
#define BOTTOM_5 35
#define BOTTOM_6 36
#define BOTTOM_7 37
#define BOTTOM_8 38
#define BOTTOM_9 39
#define BOTTOM_10 40
#define BOTTOM_11 41
#define BOTTOM_12 42
#define BOTTOM_13 43
#define BOTTOM_14 44
#define BOTTOM_15 45
#define BOTTOM_16 46
#define BOTTOM_17 47
#define BOTTOM_18 48
#define BOTTOM_19 49
#define BOTTOM_20 50
#define BOTTOM_21 51
#define BOTTOM_22 52
#define BOTTOM_23 53
#define BOTTOM_24 54
#define BOTTOM_25 55
#define BOTTOM_26 56
#define BOTTOM_27 57
#define BOTTOM_28 58
#define BOTTOM_29 59
#define BOTTOM_30 60

#define NANO_D0  70 //these are completely arbitrary but they should come in handy
#define NANO_D1  71 
#define NANO_D2  72 
#define NANO_D3  73 
#define NANO_D4  74 
#define NANO_D5  75 
#define NANO_D6  76 
#define NANO_D7  77 
#define NANO_D8  78 
#define NANO_D9  79 
#define NANO_D10  80 
#define NANO_D11  81 
#define NANO_D12  82 
#define NANO_D13  83 
#define NANO_RESET  84 
#define NANO_AREF  85 
#define NANO_A0  86 
#define NANO_A1  87 
#define NANO_A2  88 
#define NANO_A3  89 
#define NANO_A4  90 
#define NANO_A5  91 
#define NANO_A6  92 
#define NANO_A7  93


#define GND  100 
#define SUPPLY_3V3  103
#define SUPPLY_5V  105

#define DAC0  106 
#define DAC1  107

#define ISENSE_PLUS  108
#define ISENSE_MINUS  109

#define ADC0 110
#define ADC1 111
#define ADC2 112
#define ADC3 113


#define RP_GPIO_0 114

#define RP_UART_TX 116  //also GPIO_16
#define RP_GPIO_16 116  //these are the same as the UART pins

#define RP_UART_RX 117  //also GPIO_17
#define RP_GPIO_17 117  //but if we want to use them as GPIO we should use these names



#define RP_GPIO_18 118  //these aren't actually connected to anything
#define RP_GPIO_19 119  //but we might as well define names for them

#define SUPPLY_8V_P 120   //not actually connected to anything
#define SUPPLY_8V_N 121   //not actually connected to anything
#define ESP_REST 122 



#define EMPTY_NET 127

///external pin configuration note: the defined no is only for refference in thje code not represent the actual gpio or some shit like that.

#define EXT_RESET 128
#define EXT_PIN_1 129
#define EXT_PIN_2 130 //connected via nano header A0
#define EXT_PIN_3 131
#define EXT_PIN_4 132 //connected via nano header D1
#define EXT_PIN_Tx 168 // not connected to ep32 mini, connected from rp side along from mux
#define EXT_PIN_6 133 //connected via nano header A2
#define EXT_PIN_Rx 169 // not connected to ep32 mini, connected from rp side along from mux
#define EXT_PIN_8 134 //connected via nano header D3
#define EXT_PIN_9 135
#define EXT_PIN_10 136 //connected via nano header A4
#define EXT_PIN_11 100 // conneced to GND
#define EXT_PIN_12 137 //connnected via nano header D5
#define EXT_PIN_13 138 
#define EXT_PIN_14 139 //connected via nano header A6
#define EXT_PIN_15 140
#define EXT_PIN_16 141 // connected via nano header D7
#define EXT_PIN_17 142
#define EXT_PIN_18 143  // conneced via nano header D11
#define EXT_PIN_19 144 // also connected via a nano heade AREF
#define EXT_PIN_20 145 // connected via nano header D9
#define EXT_PIN_21 146 //connected via nano header D12
#define EXT_PIN_22 147 // connected via nano header D13
#define EXT_PIN_23 148 // connected via nano header D10
#define EXT_PIN_24 100 // connected to GND
#define EXT_PIN_DEV_BOOT 149 
#define EXT_PIN_26 150 //connnect via nano header D0
#define EXT_PIN_27 151 //connected via nano header D8
#define EXT_PIN_28 152 // connected via nano header A1
#define EXT_PIN_29 153 // connected via nano header A7
#define EXT_PIN_30 154 // connected via nano header D2
#define EXT_PIN_31 155 // connected via nano header D6
#define EXT_PIN_32 156 // connected via nano header D13 , some fucks going on here, his also connected to D13
#define EXT_PIN_33 157 // connected via nano header A5
#define EXT_PIN_34 105 // connected to analog 5v
#define EXT_PIN_35 158 // connected via nano header D4


#define ESP_RST 168 //inbuild esp reset

//this is connected to esp32s3 mini so when communicating path finding will not intersect with this
//DO NOT USE THESE PINS IN PATH FINDING ALGO UNLESS YOU KNOW WHAT YOU ARE DOING
#define esp32_STM32_Bridge_Tx 159
#define esp32_STM32_Bridge_Rx 160

///Oscillascope and function gen pin stuff
#define OSC_PROBE 161
#define EXT_GND 162
#define SQUARE_WAVE_FUN 163
#define SINE_TRANG_FUN 164
#define EXTRA_1 165
#define EXTRA_2 166
#define EXTRA_3 167

