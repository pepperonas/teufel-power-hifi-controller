/*
 * Teufel Power HiFi IR-Code Scanner
 * 
 * Dieses Programm liest IR-Codes von beliebigen Fernbedienungen
 * und zeigt sie im Serial Monitor an.
 * 
 * Hardware:
 * - Arduino Uno/Nano
 * - VS1838B IR-Empfänger an Pin 2
 * 
 * === SCHALTUNG VS1838B ===
 * 
 * VS1838B Pinbelegung (von vorne betrachtet):
 * 
 *      ╭─────╮
 *      │ ╱╲  │  <- Empfänger-Linse
 *      │╱  ╲ │
 *      ╰─────╯
 *       │ │ │
 *       1 2 3
 * 
 * Pin 1: OUT (Signal)     → Arduino Pin 2
 * Pin 2: GND (Minus)      → Arduino GND
 * Pin 3: VCC (Plus)       → Arduino 5V
 * 
 * Verdrahtung:
 * 
 *     Arduino             VS1838B
 *   ╔═════════╗         ╔═══════╗
 *   ║      5V ╟─────────╢ VCC   ║
 *   ║     GND ╟─────────╢ GND   ║
 *   ║   Pin 2 ╟─────────╢ OUT   ║
 *   ╚═════════╝         ╚═══════╝
 * 
 * WICHTIG:
 * - Keine zusätzlichen Bauteile nötig!
 * - VS1838B hat bereits Filter integriert
 * - Arbeitet mit 38 kHz Trägerfrequenz
 * - Reichweite: ca. 8-10 Meter
 */

#include <IRremote.hpp>

#define IR_RECEIVE_PIN 2

void setup() {
  Serial.begin(9600);
  IrReceiver.begin(IR_RECEIVE_PIN, ENABLE_LED_FEEDBACK);
  
  Serial.println("╔════════════════════════════════════════╗");
  Serial.println("║   Teufel Power HiFi IR-Code Scanner    ║");
  Serial.println("╠════════════════════════════════════════╣");
  Serial.println("║ 1. Richte die Fernbedienung auf den    ║");
  Serial.println("║    VS1838B Empfänger                   ║");
  Serial.println("║ 2. Drücke nacheinander alle Tasten     ║");
  Serial.println("║ 3. Notiere dir die angezeigten Codes   ║");
  Serial.println("╚════════════════════════════════════════╝");
  Serial.println();
  Serial.println("Protokoll | Adresse | Command | Beschreibung");
  Serial.println("----------|---------|---------|-------------");
}

void loop() {
  if (IrReceiver.decode()) {
    // Nur neue Codes anzeigen (keine Repeats)
    if (IrReceiver.decodedIRData.decodedRawData != 0x0) {
      
      // Protokoll
      Serial.print(getProtocolString(IrReceiver.decodedIRData.protocol));
      Serial.print("      | ");
      
      // Adresse
      Serial.print("0x");
      if (IrReceiver.decodedIRData.address < 0x10) Serial.print("0");
      Serial.print(IrReceiver.decodedIRData.address, HEX);
      Serial.print("  | ");
      
      // Command
      Serial.print("0x");
      if (IrReceiver.decodedIRData.command < 0x10) Serial.print("0");
      Serial.print(IrReceiver.decodedIRData.command, HEX);
      Serial.print("    | ");
      
      // Platz für Beschreibung
      Serial.println("?");
    }
    IrReceiver.resume();
  }
}

/*
 * === FEHLERSUCHE ===
 * 
 * Problem: Keine Codes werden angezeigt
 * - Prüfe Verkabelung (besonders VCC und GND)
 * - VS1838B richtig herum? (Linse nach vorne)
 * - Richtiger Pin? (Pin 2)
 * - Serial Monitor auf 9600 Baud?
 * 
 * Problem: Falsche/zufällige Codes
 * - Störquellen entfernen (Leuchtstoffröhren, LEDs)
 * - Abstand zur Fernbedienung verringern
 * - Batterien der Fernbedienung prüfen
 * 
 * === ERWEITERTE ANALYSE ===
 * 
 * Für detaillierte Timing-Analyse, ersetze den Code in loop() mit:
 * 
 * if (IrReceiver.decode()) {
 *   Serial.println();
 *   IrReceiver.printIRResultRawFormatted(&Serial, true);
 *   IrReceiver.printIRSendUsage(&Serial);
 *   IrReceiver.resume();
 * }
 */