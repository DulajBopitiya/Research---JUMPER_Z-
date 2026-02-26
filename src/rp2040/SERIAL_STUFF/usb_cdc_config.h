#pragma once
#include <Arduino.h>
#include <Adafruit_TinyUSB.h>

namespace USB_CDC_Config
{
  extern Adafruit_USBD_CDC USBSer1;
  extern Adafruit_USBD_CDC USBSer2;
  extern Adafruit_USBD_CDC USBSer3;

  void USB_CDC_setup(uint32_t baud = 115200);
  void USB_CDC_loop(); // optional (can stay empty)
}