#include "path_mapping_algo.h"

// the way the breadboard is connected to the chips, we can easily map each node to a chip. This is used for pathfinding and mapping the LEDs to the breadboard nodes.
const int bbNodesToChip[62] = {
    -1,CHIP_L, // 0,1
    CHIP_A,CHIP_A,CHIP_A,CHIP_A,CHIP_A,CHIP_A,CHIP_A, // 2, 3, 4, 5, 6, 7, 8
    CHIP_B,CHIP_B,CHIP_B,CHIP_B,CHIP_B,CHIP_B,CHIP_B, // 9,10,11,12,13,14,15
    CHIP_C,CHIP_C,CHIP_C,CHIP_C,CHIP_C,CHIP_C,CHIP_C, // 16,17,18,19,20,21,22
    CHIP_D,CHIP_D,CHIP_D,CHIP_D,CHIP_D,CHIP_D,CHIP_D, // 23,24,25,26,27,28,29
    CHIP_L,CHIP_L,CHIP_L, // 30,31,32 (TOP_30=BBL, BOTTOM_1=BBL, BOTTOM_2=BBL via Chip L)
    CHIP_E,CHIP_E,CHIP_E,CHIP_E,CHIP_E,CHIP_E,CHIP_E, // 33,34,35,36,37,38,39 (BOTTOM_3..BOTTOM_9)
    CHIP_F,CHIP_F,CHIP_F,CHIP_F,CHIP_F,CHIP_F,CHIP_F, // 40,41,42,43,44,45,46 (BOTTOM_10..BOTTOM_16)
    CHIP_G,CHIP_G,CHIP_G,CHIP_G,CHIP_G,CHIP_G,CHIP_G, // 47,48,49,50,51,52,53 (BOTTOM_17..BOTTOM_23)
    CHIP_H,CHIP_H,CHIP_H,CHIP_H,CHIP_H,CHIP_H,CHIP_H, // 54,55,56,57,58,59,60 (BOTTOM_24..BOTTOM_30)
};



struct netStruct net[MAX_NETS] = { //these are the special function nets that will always be made
//netNumber,       ,netName          ,memberNodes[]         ,memberBridges[][2]     ,specialFunction        ,intsctNet[] ,doNotIntersectNodes[]                 ,priority (unused)
    {     127      ,"Empty Net"      ,{EMPTY_NET}           ,{{}}                   ,EMPTY_NET              ,{}          ,{EMPTY_NET,EMPTY_NET,EMPTY_NET,EMPTY_NET,EMPTY_NET,EMPTY_NET,EMPTY_NET} , 0},     
    {     1        ,"GND"            ,{GND}                 ,{{}}                   ,GND                    ,{}          ,{SUPPLY_3V3,SUPPLY_5V,DAC0,DAC1}    , 1},
    {     2        ,"+5V"            ,{SUPPLY_5V}           ,{{}}                   ,SUPPLY_5V              ,{}          ,{GND,SUPPLY_3V3,DAC0,DAC1}          , 1},
    {     3        ,"+3.3V"          ,{SUPPLY_3V3}          ,{{}}                   ,SUPPLY_3V3             ,{}          ,{GND,SUPPLY_5V,DAC0,DAC1}           , 1},
    {     4        ,"DAC 0"          ,{DAC0}                ,{{}}                   ,DAC0                   ,{}          ,{GND,SUPPLY_5V,SUPPLY_3V3,DAC1}     , 1},
    {     5        ,"DAC 1"          ,{DAC1}                ,{{}}                   ,DAC1                   ,{}          ,{GND,SUPPLY_5V,SUPPLY_3V3,DAC0}     , 1},
    {     6        ,"I Sense +"      ,{ISENSE_PLUS}         ,{{}}                   ,ISENSE_PLUS            ,{}          ,{ISENSE_MINUS}                      , 2},
    {     7        ,"I Sense -"      ,{ISENSE_MINUS}        ,{{}}                   ,ISENSE_MINUS           ,{}          ,{ISENSE_PLUS}                       , 2},
};


char *netNameConstants[MAX_NETS] = {(char *)"Net 0", (char *)"Net 1", (char *)"Net 2", (char *)"Net 3", (char *)"Net 4", (char *)"Net 5", (char *)"Net 6", (char *)"Net 7", (char *)"Net 8", (char *)"Net 9", (char *)"Net 10", (char *)"Net 11", (char *)"Net 12", (char *)"Net 13", (char *)"Net 14", (char *)"Net 15", (char *)"Net 16", (char *)"Net 17", (char *)"Net 18", (char *)"Net 19", (char *)"Net 20", (char *)"Net 21", (char *)"Net 22", (char *)"Net 23", (char *)"Net 24", (char *)"Net 25", (char *)"Net 26", (char *)"Net 27", (char *)"Net 28", (char *)"Net 29", (char *)"Net 30", (char *)"Net 31", (char *)"Net 32", (char *)"Net 33", (char *)"Net 34", (char *)"Net 35", (char *)"Net 36", (char *)"Net 37", (char *)"Net 38", (char *)"Net 39", (char *)"Net 40", (char *)"Net 41", (char *)"Net 42", (char *)"Net 43", (char *)"Net 44", (char *)"Net 45", (char *)"Net 46", (char *)"Net 47", (char *)"Net 48", (char *)"Net 49", (char *)"Net 50", (char *)"Net 51", (char *)"Net 52", (char *)"Net 53", (char *)"Net 54", (char *)"Net 55", (char *)"Net 56", (char *)"Net 57", (char *)"Net 58", (char *)"Net 59", (char *)"Net 60", (char *)"Net 61", (char *)"Net 62"};



/// @brief // This struct holds the status of the nano connections, and the mapping from nano pins to chips and breadboard nodes. This is used for pathfinding and mapping the LEDs to the nano pins.
struct chipStatus_BB_NANO ch[12] = {
    {0, 'A', {-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1},                                                         // x status
     {-1, -1, -1, -1, -1, -1, -1, -1},                                                                                                 // y status
     {CHIP_I, CHIP_J, CHIP_B, CHIP_B, CHIP_C, CHIP_C, CHIP_D, CHIP_D, CHIP_E, CHIP_K, CHIP_F, CHIP_F, CHIP_G, CHIP_G, CHIP_H, CHIP_H}, // X MAP constant
     {CHIP_L, TOP_2, TOP_3, TOP_4, TOP_5, TOP_6, TOP_7, TOP_8}},                                                                       // Y MAP constant

    {1, 'B', {-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1}, // x status
     {-1, -1, -1, -1, -1, -1, -1, -1},                                         // y status
     {CHIP_A, CHIP_A, CHIP_I, CHIP_J, CHIP_C, CHIP_C, CHIP_D, CHIP_D, CHIP_E, CHIP_E, CHIP_F, CHIP_K, CHIP_G, CHIP_G, CHIP_H, CHIP_H},
     {CHIP_L, TOP_9, TOP_10, TOP_11, TOP_12, TOP_13, TOP_14, TOP_15}}, // yMap

    {2, 'C', {-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1}, // x status
     {-1, -1, -1, -1, -1, -1, -1, -1},                                         // y status
     {CHIP_A, CHIP_A, CHIP_B, CHIP_B, CHIP_I, CHIP_J, CHIP_D, CHIP_D, CHIP_E, CHIP_E, CHIP_F, CHIP_F, CHIP_G, CHIP_K, CHIP_H, CHIP_H},
     {CHIP_L, TOP_16, TOP_17, TOP_18, TOP_19, TOP_20, TOP_21, TOP_22}},

    {3, 'D', {-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1}, // x status
     {-1, -1, -1, -1, -1, -1, -1, -1},                                         // y status
     {CHIP_A, CHIP_A, CHIP_B, CHIP_B, CHIP_C, CHIP_C, CHIP_I, CHIP_J, CHIP_E, CHIP_E, CHIP_F, CHIP_F, CHIP_G, CHIP_G, CHIP_H, CHIP_K},
     {CHIP_L, TOP_23, TOP_24, TOP_25, TOP_26, TOP_27, TOP_28, TOP_29}},

    // bottom breadboard chips
    {4, 'E', {-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1}, // x status
     {-1, -1, -1, -1, -1, -1, -1, -1},                                         // y status
     {CHIP_A, CHIP_I, CHIP_B, CHIP_B, CHIP_C, CHIP_C, CHIP_D, CHIP_D, CHIP_J, CHIP_K, CHIP_F, CHIP_F, CHIP_G, CHIP_G, CHIP_H, CHIP_H},
     {CHIP_L, BOTTOM_3, BOTTOM_4, BOTTOM_5, BOTTOM_6, BOTTOM_7, BOTTOM_8, BOTTOM_9}},

    {5, 'F', {-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1}, // x status
     {-1, -1, -1, -1, -1, -1, -1, -1},                                         // y status
     {CHIP_A, CHIP_A, CHIP_B, CHIP_I, CHIP_C, CHIP_C, CHIP_D, CHIP_D, CHIP_E, CHIP_E, CHIP_J, CHIP_K, CHIP_G, CHIP_G, CHIP_H, CHIP_H},
     {CHIP_L, BOTTOM_10, BOTTOM_11, BOTTOM_12, BOTTOM_13, BOTTOM_14, BOTTOM_15, BOTTOM_16}},

    {6, 'G', {-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1}, // x status
     {-1, -1, -1, -1, -1, -1, -1, -1},                                         // y status
     {CHIP_A, CHIP_A, CHIP_B, CHIP_B, CHIP_C, CHIP_I, CHIP_D, CHIP_D, CHIP_E, CHIP_E, CHIP_F, CHIP_F, CHIP_J, CHIP_K, CHIP_H, CHIP_H},
     {CHIP_L, BOTTOM_17, BOTTOM_18, BOTTOM_19, BOTTOM_20, BOTTOM_21, BOTTOM_22, BOTTOM_23}},

    {7, 'H', {-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1}, // x status
     {-1, -1, -1, -1, -1, -1, -1, -1},                                         // y status
     {CHIP_A, CHIP_A, CHIP_B, CHIP_B, CHIP_C, CHIP_C, CHIP_D, CHIP_I, CHIP_E, CHIP_E, CHIP_F, CHIP_F, CHIP_G, CHIP_G, CHIP_J, CHIP_K},
     {CHIP_L, BOTTOM_24, BOTTOM_25, BOTTOM_26, BOTTOM_27, BOTTOM_28, BOTTOM_29, BOTTOM_30}},

    // special function chips
    {8, 'I', {-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1}, // x status
     {-1, -1, -1, -1, -1, -1, -1, -1},                                         // y status
     {NANO_A0, NANO_D1                                                         // NANO Tx
      ,
      NANO_A2, NANO_D3, NANO_A4, NANO_D5, NANO_A6, NANO_D7, NANO_D11, NANO_D9, NANO_D13, ESP_REST, DAC0, ADC0, SUPPLY_3V3, GND},
     {CHIP_A, CHIP_B, CHIP_C, CHIP_D, CHIP_E, CHIP_F, CHIP_G, CHIP_H}},

    {9, 'J', {-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1}, // x status
     {-1, -1, -1, -1, -1, -1, -1, -1},                                         // y status
     {NANO_D0                                                                  // NANO Rx
      ,
      NANO_A1, NANO_D2, NANO_A3, NANO_D4, NANO_A5, NANO_D6, NANO_A7, NANO_D8, NANO_D10, NANO_D12, NANO_AREF, NANO_RESET, ADC1, SUPPLY_5V, GND},
     {CHIP_A, CHIP_B, CHIP_C, CHIP_D, CHIP_E, CHIP_F, CHIP_G, CHIP_H}},

    {10, 'K', {-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1}, // x status
     {-1, -1, -1, -1, -1, -1, -1, -1},                                          // y status
     {EXT_PIN_15, EXT_PIN_13, EXT_PIN_9, EXT_PIN_3,esp32_STM32_Bridge_Rx ,esp32_STM32_Bridge_Tx, EXT_PIN_DEV_BOOT, ESP_REST, OSC_PROBE, EXT_GND, SQUARE_WAVE_FUN, SINE_TRANG_FUN, EXTRA_1, EXTRA_2, EXTRA_3,ADC2},
     {CHIP_A, CHIP_B, CHIP_C, CHIP_D, CHIP_E, CHIP_F, CHIP_G, CHIP_H}},

    {11, 'L', {-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1}, // x status
     {-1, -1, -1, -1, -1, -1, -1, -1},                                          // y status
     {ISENSE_MINUS, ISENSE_PLUS, ADC0, ADC1, ADC2, ADC3, DAC1, DAC0, TOP_1, TOP_30, BOTTOM_2, BOTTOM_1, RP_UART_TX, RP_UART_RX, SUPPLY_5V, RP_GPIO_0},
     {CHIP_A, CHIP_B, CHIP_C, CHIP_D, CHIP_E, CHIP_F, CHIP_G, CHIP_H}}};


///from special chips some of them are connected through external 40pin heders , so there are defined bellow // Note from these two chips some nano pins are also conneted, means the nano pins and external both are c0nnected through this chips
struct chipStatus_BB_EXT chExt[2]{

        // special function chips
    {8, 'I', {-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1}, // x status
     {-1, -1, -1, -1, -1, -1, -1, -1},                                         // y status
     {EXT_PIN_2, EXT_PIN_4// NANO Tx also connected to this pin EXT_PIN_4
      ,
      EXT_PIN_6 , EXT_PIN_8, EXT_PIN_10, EXT_PIN_12, EXT_PIN_14 , EXT_PIN_16, EXT_PIN_18 , EXT_PIN_20, EXT_PIN_22, ESP_REST, DAC0, ADC0, SUPPLY_3V3, GND},
     {CHIP_A, CHIP_B, CHIP_C, CHIP_D, CHIP_E, CHIP_F, CHIP_G, CHIP_H}},

    {9, 'J', {-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1}, // x status
     {-1, -1, -1, -1, -1, -1, -1, -1},                                         // y status
     {EXT_PIN_32  // NANO Rx also connected to this pin EXT_PIN_32                                                               // NANO Rx
      ,
      EXT_PIN_28, EXT_PIN_30, -1, EXT_PIN_35, EXT_PIN_33, EXT_PIN_31, EXT_PIN_29, EXT_PIN_27 , EXT_PIN_23, EXT_PIN_21, EXT_PIN_19, EXT_PIN_17, ADC1, SUPPLY_5V, GND},
     {CHIP_A, CHIP_B, CHIP_C, CHIP_D, CHIP_E, CHIP_F, CHIP_G, CHIP_H}},

};

enum nanoPinsToIndex
{
    NANO_PIN_D0,
    NANO_PIN_D1,
    NANO_PIN_D2,
    NANO_PIN_D3,
    NANO_PIN_D4,
    NANO_PIN_D5,
    NANO_PIN_D6,
    NANO_PIN_D7,
    NANO_PIN_D8,
    NANO_PIN_D9,
    NANO_PIN_D10,
    NANO_PIN_D11,
    NANO_PIN_D12,
    NANO_PIN_D13,
    NANO_PIN_RST,
    NANO_PIN_REF,
    NANO_PIN_A0,
    NANO_PIN_A1,
    NANO_PIN_A2,
    NANO_PIN_A3,
    NANO_PIN_A4,
    NANO_PIN_A5,
    NANO_PIN_A6,
    NANO_PIN_A7
};





struct nanoStatus nano = { // there's only one of these so ill declare and initalize together unlike above

    // all these arrays should line up (both by index and visually) so one index will give you all this data

    //                         |        |        |        |        |        |        |        |        |        |        |         |         |          |         |           |          |        |        |        |        |        |        |        |        |
    {" D0", " D1", " D2", " D3", " D4", " D5", " D6", " D7", " D8", " D9", "D10", "D11", "D12", "D13", "RST", "REF", " A0", " A1", " A2", " A3", " A4", " A5", " A6", " A7"},                                                          // String with readable name //padded to 3 chars (space comes before chars)
                                                                                                                                                                                                                                       //                         |        |        |        |        |        |        |        |        |        |        |         |         |          |         |           |          |        |        |        |        |        |        |        |        |
    {NANO_D0, NANO_D1, NANO_D2, NANO_D3, NANO_D4, NANO_D5, NANO_D6, NANO_D7, NANO_D8, NANO_D9, NANO_D10, NANO_D11, NANO_D12, NANO_D13, NANO_RESET, NANO_AREF, NANO_A0, NANO_A1, NANO_A2, NANO_A3, NANO_A4, NANO_A5, NANO_A6, NANO_A7}, // Array index to internal arbitrary #defined number
    //                         |        |        |        |        |        |        |        |        |        |        |         |         |          |         |           |          |        |        |        |        |        |        |        |        |
    {1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1}, // Whether this pin has 1 or 2 connections to special function chips    (OR maybe have it be a map like i = 2  j = 3  k = 4  l = 5 if there's 2 it's the product of them ij = 6  ik = 8  il = 10 jk = 12 jl = 15 kl = 20 we're trading minuscule amounts of CPU for RAM)
    //                         |        |        |        |        |        |        |        |        |        |        |         |         |          |         |           |          |        |        |        |        |        |        |        |        |
    {CHIP_J, CHIP_I, CHIP_J, CHIP_I, CHIP_J, CHIP_I, CHIP_J, CHIP_I, CHIP_J, CHIP_I, CHIP_J, CHIP_I, CHIP_J, CHIP_I, CHIP_I, CHIP_J, CHIP_I, CHIP_J, CHIP_I, CHIP_J, CHIP_I, CHIP_J, CHIP_I, CHIP_J}, // Since there's no overlapping connections between Chip I and J, this holds which of those 2 chips has a connection at that index, if numConns is 1, you only need to check this one
    {-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1},                                     // Since there's no overlapping connections between Chip K and L, this holds which of those 2 chips has a connection at that index, -1 for no connection
    //                         |        |        |        |        |        |        |        |        |        |        |         |         |          |         |           |          |        |        |        |        |        |        |        |        |
    {-1, 1, -1, 3, -1, 5, -1, 7, -1, 9, -1, 8, -1, 10, 11, -1, 0, -1, 2, -1, 4, -1, 6, -1},           // holds which X pin is connected to the index on Chip I, -1 for none
    {-1, 0, -1, 0, -1, 0, -1, 0, -1, 0, -1, 0, -1, 0, 0, -1, 0, -1, 0, -1, 0, -1, 0, -1},             //-1 for not connected to that chip, 0 for available, >0 means it's connected and the netNumber is stored here
                                                                                                      //                         |        |        |        |        |        |        |        |        |        |        |         |         |          |         |           |          |        |        |        |        |        |        |        |        |
    {0, -1, 2, -1, 4, -1, 6, -1, 8, -1, 9, -1, 10, -1, -1, 11, -1, 1, -1, 3, -1, 5, -1, 7},           // holds which X pin is connected to the index on Chip J, -1 for none
    {0, -1, 0, -1, 0, -1, 0, -1, 0, -1, 0, -1, 0, 0, -1, 0, -1, 0, -1, 0, -1, 0, -1, 0},              //-1 for not connected to that chip, 0 for available, >0 means it's connected and the netNumber is stored here
                                                                                                      //                         |        |        |        |        |        |        |        |        |        |        |         |         |          |         |           |          |        |        |        |        |        |        |        |        |
    {-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1},           // holds which X pin is connected to the index on Chip K, -1 for none
    {-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1},                //-1 for not connected to that chip, 0 for available, >0 means it's connected and the netNumber is stored here
                                                                                                      //                         |        |        |        |        |        |        |        |        |        |        |         |         |          |         |           |          |        |        |        |        |        |        |        |        |
    {-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1}, // holds which X pin is connected to the index on Chip L, -1 for none
    {-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1},   //-1 for not connected to that chip, 0 for available, >0 means it's connected and the netNumber is stored here

    // mapIJKL[]     will tell you whethher there's a connection from that nano pin to the corresponding special function chip
    // xMapIJKL[]    will tell you the X pin that it's connected to on that sf chip
    // xStatusIJKL[] says whether that x pin is being used (this should be the same as mt[8-10].xMap[] if theyre all stacked on top of each other)
    //              I haven't decided whether to make this just a flag, or store that signal's destination
    {NANO_D0, NANO_D1, NANO_D2, NANO_D3, NANO_D4, NANO_D5, NANO_D6, NANO_D7, NANO_D8, NANO_D9, NANO_D10, NANO_D11, NANO_D12, NANO_D13, NANO_RESET, NANO_AREF, NANO_A0, NANO_A1, NANO_A2, NANO_A3, NANO_A4, NANO_A5, NANO_A6, NANO_A7, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, GND, 101, 102, SUPPLY_3V3, 104, SUPPLY_5V, DAC0, DAC1, ISENSE_PLUS, ISENSE_MINUS}

};


///neeeded to write similar code to the above but for the external header pins,

struct pathStruct path[MAX_BRIDGES]; // node1, node2, net, chip[3], x[3], y[3]


SFmapPair sfMappings[200] = {

        {"GND", 100},
        {"GROUND", 100},
        {"SUPPLY_5V", 105},
        {"SUPPLY_3V3", 103},
        {"DAC0_5V", 106},
        {"DAC1_8V", 107},
        {"DAC0", 106},
        {"DAC1", 107},
        {"INA_N", 109},
        {"INA_P", 108},
        {"I_N", 109},
        {"I_P", 108},
        {"ISENSE_MINUS", 109},
        {"ISENSE_PLUS", 108},
        {"CURRENT_SENSE_MINUS", 109},
        {"CURRENT_SENSE_PLUS", 108},
        {"EMPTY_NET", 127},
        {"ADC0_5V", 110},
        {"ADC1_5V", 111},
        {"ADC2_5V", 112},
        {"ADC3_8V", 113},
        {"ADC0", 110},
        {"ADC1", 111},
        {"ADC2", 112},
        {"ADC3", 113},
        {"+5V", 105},
        {"5V", 105},
        {"3.3V", 103},
        {"3V3", 103},
        {"RP_GPIO_0", 114},
        {"RP_UART_TX", 116},
        {"RP_UART_RX", 117},
        {"GPIO_0", 114},
        {"UART_TX", 116},
        {"UART_RX", 117},
        {"NANO_RESET", 84},
        {"NANO_AREF", 85},
        {"NANO_D0", 70},
        {"NANO_D1", 71},
        {"NANO_D2", 72},
        {"NANO_D3", 73},
        {"NANO_D4", 74},
        {"NANO_D5", 75},
        {"NANO_D6", 76},
        {"NANO_D7", 77},
        {"NANO_D8", 78},
        {"NANO_D9", 79},
        {"NANO_D10", 80},
        {"NANO_D11", 81},
        {"NANO_D12", 82},
        {"NANO_D13", 83},
        {"NANO_A0", 86},
        {"NANO_A1", 87},
        {"NANO_A2", 88},
        {"NANO_A3", 89},
        {"NANO_A4", 90},
        {"NANO_A5", 91},
        {"NANO_A6", 92},
        {"NANO_A7", 93},
        {"RESET", 84},
        {"AREF", 85},
        {"D0", 70},
        {"D1", 71},
        {"D2", 72},
        {"D3", 73},
        {"D4", 74},
        {"D5", 75},
        {"D6", 76},
        {"D7", 77},
        {"D8", 78},
        {"D9", 79},
        {"D10", 80},
        {"D11", 81},
        {"D12", 82},
        {"D13", 83},
        {"A0", 86},
        {"A1", 87},
        {"A2", 88},
        {"A3", 89},
        {"A4", 90},
        {"A5", 91},
        {"A6", 92},
        {"A7", 93},

        //Externa pin debug deffintions
        {"EXT_RESET" , 128},
        {"EXT_PIN_1" , 129},
        {"EXT_PIN_2" , 130},
        {"EXT_PIN_3" , 131},
        {"EXT_PIN_4" , 132},
        {"EXT_PIN_Tx" , 168},
        {"EXT_PIN_6" , 133,},
        {"EXT_PIN_Rx" , 169},
        {"EXT_PIN_8" , 134},
        {"EXT_PIN_9" , 135},
        {"EXT_PIN_10", 136},
        {"EXT_PIN_11", 100},
        {"EXT_PIN_12", 137},
        {"EXT_PIN_13", 138},
        {"EXT_PIN_14", 139},
        {"EXT_PIN_15", 140},
        {"EXT_PIN_16", 141},
        {"EXT_PIN_17", 142},
        {"EXT_PIN_18", 143},
        {"EXT_PIN_19", 144},
        {"EXT_PIN_20", 145},
        {"EXT_PIN_21", 146},
        {"EXT_PIN_22", 147},
        {"EXT_PIN_23", 148},
        {"EXT_PIN_24", 100},
        {"EXT_PIN_DEV_BOOT", 149},
        {"EXT_PIN_26", 150},
        {"EXT_PIN_27", 151},
        {"EXT_PIN_28", 152},
        {"EXT_PIN_29", 153},
        {"EXT_PIN_30", 154},
        {"EXT_PIN_31", 155},
        {"EXT_PIN_32", 156},
        {"EXT_PIN_33", 157},
        {"EXT_PIN_34", 105},
        {"EXT_PIN_35", 158},

        //osciallscope and function generator debug definitions
        {"ESP_REST", 160},
        {"OSC_PROBE", 161},
        {"SQUARE_WAVE_FUN", 162},
        {"SINE_TRANG_FUN", 164},
        {"EXTRA_1", 165,},
        {"EXTRA_2", 166},
        {"EXTRA_3", 167},

        {"ESP_REST" , 168},

        // Breadboard top rows: "TOP_1".."TOP_30" → node numbers 1..30
        {"TOP_1",  1},  {"TOP_2",  2},  {"TOP_3",  3},  {"TOP_4",  4},  {"TOP_5",  5},
        {"TOP_6",  6},  {"TOP_7",  7},  {"TOP_8",  8},  {"TOP_9",  9},  {"TOP_10", 10},
        {"TOP_11", 11}, {"TOP_12", 12}, {"TOP_13", 13}, {"TOP_14", 14}, {"TOP_15", 15},
        {"TOP_16", 16}, {"TOP_17", 17}, {"TOP_18", 18}, {"TOP_19", 19}, {"TOP_20", 20},
        {"TOP_21", 21}, {"TOP_22", 22}, {"TOP_23", 23}, {"TOP_24", 24}, {"TOP_25", 25},
        {"TOP_26", 26}, {"TOP_27", 27}, {"TOP_28", 28}, {"TOP_29", 29}, {"TOP_30", 30},

        // Breadboard bottom rows: "BOTTOM_1".."BOTTOM_30" → node numbers 31..60
        {"BOTTOM_1",  31}, {"BOTTOM_2",  32}, {"BOTTOM_3",  33}, {"BOTTOM_4",  34}, {"BOTTOM_5",  35},
        {"BOTTOM_6",  36}, {"BOTTOM_7",  37}, {"BOTTOM_8",  38}, {"BOTTOM_9",  39}, {"BOTTOM_10", 40},
        {"BOTTOM_11", 41}, {"BOTTOM_12", 42}, {"BOTTOM_13", 43}, {"BOTTOM_14", 44}, {"BOTTOM_15", 45},
        {"BOTTOM_16", 46}, {"BOTTOM_17", 47}, {"BOTTOM_18", 48}, {"BOTTOM_19", 49}, {"BOTTOM_20", 50},
        {"BOTTOM_21", 51}, {"BOTTOM_22", 52}, {"BOTTOM_23", 53}, {"BOTTOM_24", 54}, {"BOTTOM_25", 55},
        {"BOTTOM_26", 56}, {"BOTTOM_27", 57}, {"BOTTOM_28", 58}, {"BOTTOM_29", 59}, {"BOTTOM_30", 60},
};