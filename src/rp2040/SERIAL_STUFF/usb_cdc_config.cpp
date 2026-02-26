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
    USBDevice.setID(0x1D51, 0xACAB);
    USBDevice.addStringDescriptor("Jumper ZERO");
    USBDevice.addStringDescriptor("FabVolt");

    USBSer1.setStringDescriptor("Jumper_Z USB Serial");
    USBSer2.setStringDescriptor("JZ Oscilloscope");
    USBSer3.setStringDescriptor("JZ FunctionGen");

    // IMPORTANT for multiple CDCs on TinyUSB:
    TinyUSBDevice.addInterface(USBSer1);
    TinyUSBDevice.addInterface(USBSer2);
    TinyUSBDevice.addInterface(USBSer3);

    Serial.begin(baud);
    USBSer1.begin(baud);
    USBSer2.begin(baud);
    USBSer3.begin(baud);
  }

  void USB_CDC_loop()
  {
    // optional: nothing needed
  }
}