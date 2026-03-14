#include "usb_cdc_config.h"

namespace USB_CDC_Config
{
  Adafruit_USBD_CDC USBSer1;
  Adafruit_USBD_CDC USBSer2;
  Adafruit_USBD_CDC USBSer3;

  void USB_CDC_setup(uint32_t baud)
  {
    USBDevice.setProductDescriptor("Jumper_Z");
    USBDevice.setManufacturerDescriptor("FabVolt");
    USBDevice.setSerialDescriptor("0");
    USBDevice.setID(0x1D51, 0xACAB); // changed from 0xACAB to bust Windows descriptor cache
    USBDevice.addStringDescriptor("Jumper ZERO");
    USBDevice.addStringDescriptor("FabVolt");

    // CDC 0 = Serial "JZ Serial"  — added automatically by framework before setup()
    // CDC 1 = USBSer1 "JZ NETSH"
    // CDC 2 = USBSer3 "JZ TTL"   ← Nano bridge (TTL_CDC_IDX = 2)
    // CDC 3 = USBSer2 "JZ Oscilloscope"
    //
    // Set string BEFORE begin() so the patched begin() keeps it instead of
    // overriding with "JZ Serial". Do NOT call TinyUSBDevice.addInterface()
    // directly — begin() handles that. Calling both causes duplicate descriptors.
    USBSer1.setStringDescriptor("JZ NETSH");
    USBSer1.begin(baud);

    USBSer3.setStringDescriptor("JZ TTL");
    USBSer3.begin(baud);

    USBSer2.setStringDescriptor("JZ Oscilloscope");
    USBSer2.begin(baud);

    Serial.begin(baud); // no-op: framework already called Serial.begin() before setup()
  }

  void USB_CDC_loop()
  {
    // optional: nothing needed
  }
}