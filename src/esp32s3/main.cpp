#include <Arduino.h>

#define TOGGLE_PIN 40

// Create an explicit handle to UART0
HardwareSerial RP(0);   // UART0

bool pinState = false;

void setup() {
  Serial.begin(115200);           // USB CDC (your monitor)
  RP.begin(115200);               // UART0 on default U0TXD/U0RXD pins

  pinMode(TOGGLE_PIN, OUTPUT);
  digitalWrite(TOGGLE_PIN, LOW);

  Serial.println("ESP32-S3 ready (UART0)");
  RP.println("READY");            // handshake (optional but recommended)
}

void loop() {
  if (RP.available()) {
    String msg = RP.readStringUntil('\n');
    msg.trim();

    if (msg == "TOGGLE") {
      pinState = !pinState;
      digitalWrite(TOGGLE_PIN, pinState);
      RP.println("OK");
    }
  }
    // digitalWrite(TOGGLE_PIN, HIGH);
    // delay(1000);
    // digitalWrite(TOGGLE_PIN, LOW);
    // delay(1000);
}