/*
 * Teufel Power HiFi - IR Serial Bridge (Raspberry-Pi-Anbindung)
 * Liest pro Zeile einen HEX-Command-Code und sendet ihn als NEC (Adresse 0x5780).
 * IR-Emitter an Pin D3. Baud 115200.  Beispiel:  48\n = Power,  30\n = Volume Down
 */
#include <IRremote.hpp>
#define IR_SEND_PIN 3
#define TEUFEL_ADDR 0x5780

void setup() {
  Serial.begin(115200);
  IrSender.begin(IR_SEND_PIN);
  Serial.println(F("Teufel IR Serial Bridge bereit (NEC 0x5780, HEX/Zeile)"));
}

String buf;
void loop() {
  while (Serial.available()) {
    char c = Serial.read();
    if (c == 13 || c == 10) {            // CR/LF = Zeilenende
      buf.trim();
      if (buf.length() > 0) {
        long v = strtol(buf.c_str(), NULL, 16);
        IrSender.sendNEC(TEUFEL_ADDR, (uint8_t)v, 0);
        Serial.print(F("TX 0x")); Serial.println((uint8_t)v, HEX);
      }
      buf = "";
    } else if (buf.length() < 8) {
      buf += c;
    }
  }
}
