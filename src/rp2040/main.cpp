#include "configuration.h"
// ==========================================================
// ======================== SETUP ============================
// ==========================================================

void setup()
{

  USB_CDC_Config::USB_CDC_setup();
  // EspUart.begin(115200);
  LedMatrix::begin(20);   
  JsonBridge::clearFrame();
  JsonBridge::begin(LedMatrix::strip());
}

// ==========================================================
// ========================= LOOP ============================
// ==========================================================

void loop()
{

  if (USB_CDC_Config::USBSer1.available())
  {
    JsonDocument req;
    DeserializationError err = deserializeJson(req, USB_CDC_Config::USBSer1);

    if (!err)
    {
      JsonBridge::handle(USB_CDC_Config::USBSer1, req);
    }
  }

  JsonBridge::tick();
}