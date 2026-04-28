#pragma once

#include <Arduino.h>
#include "Led_Matrix.h"
#include "pin_map.h"


struct netStruct{ 

uint8_t number; //nets are uint8_t, nodes are int8_t

const char *name; // human readable "Net 3"

int16_t nodes[MAX_NODES] = {}; // int16_t: node numbers can reach 169 (EXT pins) — int8_t overflows above 127

int16_t bridges[MAX_NODES][2]; // pairs of node numbers; must match nodes[] width

int8_t specialFunction = -1; // store #defined number for that special function -1 for regular net

uint8_t intersections[8]; //if this net shares a node with another net, store this here. If it's a regular net, we'll need a function to just merge them into one new net. special functions can intersect though (except Power and Ground), 0x7f is a reserved empty net that nothing and intersect

int16_t doNotIntersectNodes[8]; // node numbers — must match nodes[] width

uint8_t priority = 0; //this isn't implemented - priority = 1 means it will move connections to take the most direct path, priority = 2 means connections will be doubled up when possible, priority = 3 means both

LedMatrix::RGB_t color; //color of the net in hex

uint32_t rawColor; //color of the net in hex (for the machine)

char *colorName; //name of the color

bool machine = false; //whether this net was created by the machine or by the user

int duplicatePaths[MAX_DUPLICATE] = {-1, -1, -1, -1,-1, -1, -1, -1,-1,-1}; // if the paths are redundant (for lower resistance) this is the pathNumber of the other one(s)

int numberOfDuplicates = 0; // if the paths are redundant (for lower resistance) this is the number of duplicates

};

extern struct netStruct net[MAX_NETS];

extern char *netNameConstants[MAX_NETS];

struct nanoStatus
{ // there's only one of these so ill declare and initalize together unlike above

    // all these arrays should line up (both by index and visually) so one index will give you all this data

    //                            |        |        |        |        |        |        |        |        |        |        |         |         |          |         |           |          |        |        |        |        |        |        |        |        |
    const char *pinNames[24]; //=  {   " D0",   " D1",   " D2",   " D3",   " D4",   " D5",   " D6",   " D7",   " D8",   " D9",    "D10",    "D11",     "D12",    "D13",      "RST",     "REF",   " A0",   " A1",   " A2",   " A3",   " A4",   " A5",   " A6",   " A7"};// String with readable name //padded to 3 chars (space comes before chars)
    //                            |        |        |        |        |        |        |        |        |        |        |         |         |          |         |           |          |        |        |        |        |        |        |        |        |
    const int16_t pinMap[24]; // =  { NANO_D0, NANO_D1, NANO_D2, NANO_D3, NANO_D4, NANO_D5, NANO_D6, NANO_D7, NANO_D8, NANO_D9, NANO_D10, NANO_D11,  NANO_D12, NANO_D13, NANO_RESET, NANO_AREF, NANO_A0, NANO_A1, NANO_A2, NANO_A3, NANO_A4, NANO_A5, NANO_A6, NANO_A7};//Array index to internal arbitrary #defined number
    //                            |        |        |        |        |        |        |        |        |        |        |         |         |          |         |           |          |        |        |        |        |        |        |        |        |
    const int16_t numConns[24]; //= {  1     , 1      , 2      , 2      , 2      , 2      , 2      , 2      , 2      , 2      , 2       , 2       ,  2       , 2       , 1         , 1        , 2      , 2      , 2      , 2      , 2      , 2      , 1      , 1      };//Whether this pin has 1 or 2 connections to special function chips    (OR maybe have it be a map like i = 2  j = 3  k = 4  l = 5 if there's 2 it's the product of them ij = 6  ik = 8  il = 10 jk = 12 jl = 15 kl = 20 we're trading minuscule amounts of CPU for RAM)
    //                            |        |        |        |        |        |        |        |        |        |        |         |         |          |         |           |          |        |        |        |        |        |        |        |        |
    const int16_t mapIJ[24]; // =  { CHIP_J , CHIP_I , CHIP_J , CHIP_I , CHIP_J , CHIP_I , CHIP_J , CHIP_I , CHIP_J , CHIP_I , CHIP_J  , CHIP_I  ,  CHIP_J  , CHIP_I  , CHIP_I    ,  CHIP_J  , CHIP_I , CHIP_J , CHIP_I , CHIP_J , CHIP_I , CHIP_J , CHIP_I , CHIP_J };//Since there's no overlapping connections between Chip I and J, this holds which of those 2 chips has a connection at that index, if numConns is 1, you only need to check this one
    const int16_t mapKL[24]; // =  { -1     , -1     , CHIP_K , CHIP_K , CHIP_K , CHIP_K , CHIP_K , CHIP_K , CHIP_K , CHIP_K , CHIP_K  , CHIP_K  ,  CHIP_K  , -1      , -1        , -1       , CHIP_K , CHIP_K , CHIP_K , CHIP_K , CHIP_L , CHIP_L , -1     , -1     };//Since there's no overlapping connections between Chip K and L, this holds which of those 2 chips has a connection at that index, -1 for no connection
    //                            |        |        |        |        |        |        |        |        |        |        |         |         |          |         |           |          |        |        |        |        |        |        |        |        |
    const int16_t xMapI[24]; //  =  { -1     , 1      , -1     , 3      , -1     , 5      , -1     , 7      , -1     , 9      , -1      , 8       ,  -1      , 10      , 11        , -1       , 0      , -1     , 2      , -1     , 4      , -1     , 6      , -1     };//holds which X pin is connected to the index on Chip I, -1 for none
    int8_t xStatusI[24];    //  =  { -1     , 0      , -1     , 0      , -1     , 0      , -1     , 0      , -1     , 0      , -1      , 0       ,  -1      , 0       , 0         , -1       , 0      , -1     , 0      , -1     , 0      , -1     , 0      , -1     };//-1 for not connected to that chip, 0 for available, >0 means it's connected and the netNumber is stored here
    //                            |        |        |        |        |        |        |        |        |        |        |         |         |          |         |           |          |        |        |        |        |        |        |        |        |
    const int16_t xMapJ[24]; //  =  { 0      , -1     , 2      , -1     , 4      , -1     , 6      , -1     , 8      , -1     , 9       , -1      ,  10      , -1      , -1        , 11       , -1     , 1      , -1     , 3      , -1     , 5      , -1     , 7      };//holds which X pin is connected to the index on Chip J, -1 for none
    int16_t xStatusJ[24];    //  =  { 0      , -1     , 0      , -1     , 0      , -1     , 0      , -1     , 0      , -1     , 0       , -1      , 0        , 0       , -1        , 0        , -1     , 0      , -1     , 0      , -1     , 0      , -1     , 0      };//-1 for not connected to that chip, 0 for available, >0 means it's connected and the netNumber is stored here
    //                            |        |        |        |        |        |        |        |        |        |        |         |         |          |         |           |          |        |        |        |        |        |        |        |        |
    const int16_t xMapK[24]; //  =  { -1     , -1     , 4      , 5      , 6      , 7      , 8      , 9      , 10     , 11     , 12      , 13      ,  14      , -1      , -1        , -1       , 0      , 1      , 2      , 3      , -1     , -1     , -1     , -1     };//holds which X pin is connected to the index on Chip K, -1 for none
    int16_t xStatusK[24];    //  =  { -1     , -1     , 0      , 0      , 0      , 0      , 0      , 0      , 0      , 0      , 0       , 0       ,  0       , -1      , -1        , -1       , 0      , 0      , 0      , 0      ,-1     ,-1     ,-1     ,-1     };//-1 for not connected to that chip, 0 for available, >0 means it's connected and the netNumber is stored here
    //                            |        |        |        |        |        |        |        |        |        |        |         |         |          |         |           |          |        |        |        |        |        |        |        |        |
    const int16_t xMapL[24]; //  =  { -1     , -1     , -1     , -1     , -1     , -1     , -1     , -1     , -1     , -1     , -1      , -1      ,  -1      , -1      , -1        , -1       , -1     , -1     , -1     , -1     , 12     , 13     , -1     , -1     };//holds which X pin is connected to the index on Chip L, -1 for none
    int16_t xStatusL[24];    //  =  { -1     , -1     , -1     , -1     , -1     , -1     , -1     , -1     , -1     , -1     , -1      , -1      ,  -1      , -1      , -1        , -1       , -1     , -1     , -1     , -1     , 0      , 0      , -1     , -1     };//-1 for not connected to that chip, 0 for available, >0 means it's connected and the netNumber is stored here

    // mapIJKL[]     will tell you whethher there's a connection from that nano pin to the corresponding special function chip
    // xMapIJKL[]    will tell you the X pin that it's connected to on that sf chip
    // xStatusIJKL[] says whether that x pin is being used (this should be the same as mt[8-10].xMap[] if theyre all stacked on top of each other)
    //              I haven't decided whether to make this just a flag, or store that signal's destination
    const int16_t reversePinMap[110]; // = {NANO_D0, NANO_D1, NANO_D2, NANO_D3, NANO_D4, NANO_D5, NANO_D6, NANO_D7, NANO_D8, NANO_D9, NANO_D10, NANO_D11, NANO_D12, NANO_D13, NANO_RESET, NANO_AREF, NANO_A0, NANO_A1, NANO_A2, NANO_A3, NANO_A4, NANO_A5, NANO_A6, NANO_A7,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
    //  1      , 2      , 3      , 4      , 5      , 6      , 7      , 8      , 9      , 10     , 11     , 12     , 13     , 14     , 15     , 16     , 17     , 18     , 19     , 20     , 21     , 22     , 23     , 24     };
};
extern struct nanoStatus nano;

struct chipStatus_BB_NANO
{

    int chipNumber;

    char chipChar;

    int16_t xStatus[16]; // store the bb row or nano conn this is eventually connected to so they can be stacked if conns are redundant

    int16_t yStatus[8]; // store the row/nano it's connected to

    const int16_t xMap[16];

    const int16_t yMap[8];
};

struct chipStatus_BB_EXT
{

    int chipNumber;

    char chipChar;

    int16_t xStatus[16]; // store the bb row or nano conn this is eventually connected to so they can be stacked if conns are redundant

    int16_t yStatus[8]; // store the row/nano it's connected to

    const int16_t xMap[16];

    const int16_t yMap[8];
};
/// Mapping from breadboard nodes to CH446Q chips. Indexed by bb node number (0-60).
extern const int bbNodesToChip[61];

enum pathType
{
    BBtoBB,
    BBtoNANO,
    NANOtoNANO,
    BBtoSF,
    NANOtoSF,
    BBtoBBL,
    NANOtoBBL,
    SFtoSF,
    SFtoBBL,
    BBLtoBBL,
    // External 40-pin header path types
    BBtoEXT,
    NANOtoEXT,
    EXTtoSF,
    EXTtoEXT,
    EXTtoBBL
};

enum nodeType
{
    BB,
    NANO,
    EXT,
    SF,
    BBL
};
struct pathStruct
{

    int node1; // these are the rows or nano header pins to connect
    int node2;
    int net;

    int chip[6];
    int x[6];
    int y[6];
    int candidates[3][3]; //[node][candidate]
    int altPathNeeded;
    enum pathType pathType;
    enum nodeType nodeType[3];
    bool sameChip;
    bool Lchip;
    bool skip = false;

    int duplicate = 0; // the "parent" path if 1, the "child" path if 2, 0 if not a duplicate
};

extern struct pathStruct path[MAX_BRIDGES]; // this is the array of paths
struct SFmapPair
{
    const char *name;
    int replacement;
};

extern struct SFmapPair sfMappings[200];

extern struct chipStatus_BB_NANO ch[12];
extern struct chipStatus_BB_EXT chExt[2];

