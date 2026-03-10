#pragma once

#include <Arduino.h>
#include "pin_map.h"
#include "usb_cdc_config.h"



// Note: MAIN__UART_Rx/MAIN_UART_Tx labels in pin_map.h are inverted.
// Tested working assignment: Serial1 TX = GPIO 16, RX = GPIO 17.
#define NANO_UART_TX  16
#define NANO_UART_RX  17

namespace NanoHeader
{
    void setup();
    void loop();
}