#include "uart_main_bridge.h"

// SerialPIO(TX_pin, RX_pin)
SerialPIO UARTMainBridge::E_EspUart(ESP32_RP_COM_TX, ESP32_RP_COM_RX);

void UARTMainBridge::begin(uint32_t baud) {
    E_EspUart.begin(baud);
}

void UARTMainBridge::sendLine(const char* msg) {
    E_EspUart.println(msg);
}

int UARTMainBridge::available() {
    return E_EspUart.available();
}

int UARTMainBridge::read() {
    return E_EspUart.read();
}

void UARTMainBridge::loop() {
    while (E_EspUart.available()) {
        String line = E_EspUart.readStringUntil('\n');
        line.trim();
        if (line.length() == 0) continue;

        // Print to debug serial so we can see ESP32 messages
        Serial.print("[ESP32] ");
        Serial.println(line);

        // TODO: parse ESP32 status messages here (e.g. "WIFI_READY", "IP:x.x.x.x")
    }
}
