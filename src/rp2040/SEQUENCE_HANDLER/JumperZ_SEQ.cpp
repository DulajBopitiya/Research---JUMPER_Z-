#include "JumperZ_SEQ.h"

/// in here the main sequnce is need to implemented
// 1.what needed to do when power on the device / led sequnce and system check
//

namespace JumperZ_SEQUENCE
{


    void JumperZ_Setup()
    {
        USB_CDC_Config::USB_CDC_setup();
        UARTMainBridge::begin(115200);
        LedMatrix::begin(50);
        rgbPatterns::startup(LedMatrix::strip());
        initCH446Q();
        JsonBridge::clearFrame();
        JsonBridge::begin(LedMatrix::strip());
        NanoHeader::setup();
    }

    void JumperZ_Loop()
    {

       
        // main sequence loop
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
        NanoHeader::loop();
        UARTMainBridge::loop();
    }
}