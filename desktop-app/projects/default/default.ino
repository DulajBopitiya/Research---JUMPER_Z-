// The built-in LED on Arduino Nano is on pin 13
void setup() {
  // Initialize digital pin LED_BUILTIN as an output.
  pinMode(LED_BUILTIN, OUTPUT);
}

void loop() {
  digitalWrite(LED_BUILTIN, HIGH);  // Turn the LED on
  delay(100);                      // Wait for a second
  digitalWrite(LED_BUILTIN, LOW);   // Turn the LED off
  delay(100);                      // Wait for a second
}
