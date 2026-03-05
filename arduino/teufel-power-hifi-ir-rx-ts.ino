/*
 * Teufel Power HiFi IR Sender + Empfänger Test
 * 
 * Hardware:
 * - IR LED an Pin 3 (ohne Widerstand)
 * - VS1838B IR-Empfänger an Pin 2
 * 
 * Testet ob gesendete Signale korrekt empfangen werden
 */

#include <IRremote.hpp>

#define IR_SEND_PIN     3
#define IR_RECEIVE_PIN  2

// Teufel Power HiFi IR-Codes (NEC Protocol)
#define TEUFEL_ADDR          0x5780

// Basis-Funktionen (aus deinem Mapping)
#define CMD_POWER            0x48
#define CMD_MUTE             0x28
#define CMD_BLUETOOTH        0x40

// Lautstärke
#define CMD_VOLUME_UP        0xB0
#define CMD_VOLUME_DOWN      0x30

// Navigation
#define CMD_LEFT             0x78
#define CMD_RIGHT            0xF8

// Sound Einstellungen  
#define CMD_BASS_UP          0x58
#define CMD_BASS_DOWN        0x41
#define CMD_MID_UP           0x68
#define CMD_MID_DOWN         0x42
#define CMD_TREBLE_UP        0xB8
#define CMD_TREBLE_DOWN      0x43

// Eingänge
#define CMD_AUX              0x44
#define CMD_LINE             0x45
#define CMD_OPT              0x3F
#define CMD_USB              0xDF

// Balance
#define CMD_BAL_LEFT         0xBF
#define CMD_BAL_RIGHT        0x5F

// Test-Modus Variablen
bool testMode = true;
unsigned long lastSentCommand = 0;
unsigned long sendTime = 0;

void setup() {
  Serial.begin(9600);
  
  // Sender initialisieren
  IrSender.begin(IR_SEND_PIN);
  
  // Empfänger initialisieren
  IrReceiver.begin(IR_RECEIVE_PIN, ENABLE_LED_FEEDBACK);
  
  Serial.println("=== Teufel IR Test-System ===");
  Serial.println("Mode: SENDEN + EMPFANGEN");
  Serial.println();
  Serial.println("Befehle:");
  Serial.println("t - Test-Modus AN/AUS (aktuell: AN)");
  Serial.println("r - Nur Empfangen (Read-Only Modus)");
  Serial.println("A - Alle Codes automatisch testen");
  Serial.println();
  Serial.println("Sende-Befehle:");
  Serial.println("p=Power, m=Mute, l=bLuetooth");
  Serial.println("+/-=Volume, a/d=Links/Rechts");
  Serial.println("B/b=Bass, M/n=Mid, T/y=Treble");
  Serial.println("1=AUX, 2=Line, 3=Optical, 4=USB");
  Serial.println("<>=Balance Links/Rechts");
  Serial.println();
  Serial.println("HINWEIS: Richte die IR-LED auf den Empfänger!");
  Serial.println();
}

void sendAndVerify(uint8_t command, const char* name) {
  Serial.print("SENDE: 0x");
  Serial.print(command, HEX);
  Serial.print(" (");
  Serial.print(name);
  Serial.print(") ... ");
  
  // Merke was gesendet wurde
  lastSentCommand = (TEUFEL_ADDR << 8) | command;
  sendTime = millis();
  
  // Sende Befehl
  IrSender.sendNEC(TEUFEL_ADDR, command, 0);
  
  // Warte auf Empfang (max 200ms)
  unsigned long timeout = millis() + 200;
  bool received = false;
  
  while (millis() < timeout && !received) {
    if (IrReceiver.decode()) {
      if (IrReceiver.decodedIRData.protocol == NEC &&
          IrReceiver.decodedIRData.address == TEUFEL_ADDR &&
          IrReceiver.decodedIRData.command == command) {
        
        unsigned long responseTime = millis() - sendTime;
        Serial.print("✓ EMPFANGEN");
        Serial.print(" (");
        Serial.print(responseTime);
        Serial.println("ms)");
        received = true;
        
      } else if (IrReceiver.decodedIRData.decodedRawData != 0x0) {
        // Falsches Signal empfangen
        Serial.print("✗ FEHLER: Empfangen 0x");
        Serial.print(IrReceiver.decodedIRData.command, HEX);
        Serial.print(" statt 0x");
        Serial.println(command, HEX);
        received = true;
      }
      IrReceiver.resume();
    }
  }
  
  if (!received) {
    Serial.println("✗ KEIN SIGNAL EMPFANGEN!");
    Serial.println("   → Prüfe Verkabelung und Ausrichtung");
  }
  
  delay(100);
}

void testAllCodes() {
  Serial.println("\n=== AUTOMATISCHER TEST ALLER CODES ===");
  Serial.println("Teste alle bekannten Teufel-Codes...\n");
  
  int erfolg = 0;
  int gesamt = 0;
  
  // Test Array mit allen Codes
  struct {
    uint8_t code;
    const char* name;
  } testCodes[] = {
    {CMD_POWER, "Power"},
    {CMD_MUTE, "Mute"},
    {CMD_BLUETOOTH, "Bluetooth"},
    {CMD_VOLUME_UP, "Volume+"},
    {CMD_VOLUME_DOWN, "Volume-"},
    {CMD_LEFT, "Left"},
    {CMD_RIGHT, "Right"},
    {CMD_BASS_UP, "Bass+"},
    {CMD_BASS_DOWN, "Bass-"},
    {CMD_MID_UP, "Mid+"},
    {CMD_MID_DOWN, "Mid-"},
    {CMD_TREBLE_UP, "Treble+"},
    {CMD_TREBLE_DOWN, "Treble-"},
    {CMD_AUX, "AUX"},
    {CMD_LINE, "Line"},
    {CMD_OPT, "Optical"},
    {CMD_USB, "USB"},
    {CMD_BAL_LEFT, "Balance Left"},
    {CMD_BAL_RIGHT, "Balance Right"}
  };
  
  for (auto& test : testCodes) {
    gesamt++;
    
    // Sende und prüfe
    Serial.print(gesamt);
    Serial.print(". ");
    sendAndVerify(test.code, test.name);
    
    delay(200); // Pause zwischen Tests
  }
  
  Serial.println("\n=== TEST ZUSAMMENFASSUNG ===");
  Serial.print("Getestet: ");
  Serial.println(gesamt);
  Serial.print("Erfolgsrate: ");
  Serial.print((erfolg * 100) / gesamt);
  Serial.println("%");
  Serial.println();
}

void readOnlyMode() {
  Serial.println("\n=== NUR-LESEN MODUS ===");
  Serial.println("Empfange IR-Signale... (q zum Beenden)");
  
  while (true) {
    // Check für Beenden
    if (Serial.available() && Serial.read() == 'q') {
      Serial.println("Nur-Lesen Modus beendet.\n");
      break;
    }
    
    if (IrReceiver.decode()) {
      // Ignoriere Repeats
      if (IrReceiver.decodedIRData.decodedRawData != 0x0) {
        Serial.print("EMPFANGEN: ");
        Serial.print("Protokoll=");
        Serial.print(getProtocolString(IrReceiver.decodedIRData.protocol));
        Serial.print(", Adresse=0x");
        Serial.print(IrReceiver.decodedIRData.address, HEX);
        Serial.print(", Command=0x");
        Serial.print(IrReceiver.decodedIRData.command, HEX);
        
        // Prüfe ob es ein Teufel-Signal ist
        if (IrReceiver.decodedIRData.protocol == NEC && 
            IrReceiver.decodedIRData.address == TEUFEL_ADDR) {
          Serial.print(" ✓ TEUFEL");
        }
        
        Serial.println();
      }
      IrReceiver.resume();
    }
  }
}

void loop() {
  // Prüfe eingehende IR-Signale (wenn nicht gerade gesendet wird)
  if (millis() - sendTime > 250) {  // 250ms nach Senden
    if (IrReceiver.decode()) {
      if (IrReceiver.decodedIRData.decodedRawData != 0x0) {
        Serial.print("[EMPFANG] ");
        if (IrReceiver.decodedIRData.address == TEUFEL_ADDR) {
          Serial.print("Teufel ");
        }
        Serial.print("0x");
        Serial.println(IrReceiver.decodedIRData.command, HEX);
      }
      IrReceiver.resume();
    }
  }
  
  // Prüfe Serien-Eingabe
  if (Serial.available()) {
    char input = Serial.read();
    
    // Spezial-Modi
    if (input == 't') {
      testMode = !testMode;
      Serial.print("Test-Modus: ");
      Serial.println(testMode ? "AN" : "AUS");
      return;
    }
    
    if (input == 'r') {
      readOnlyMode();
      return;
    }
    
    if (input == 'A') {
      testAllCodes();
      return;
    }
    
    // Normale Befehle
    uint8_t cmdToSend = 0;
    const char* cmdName = "";
    
    switch(input) {
      case 'p': cmdToSend = CMD_POWER; cmdName = "Power"; break;
      case 'm': cmdToSend = CMD_MUTE; cmdName = "Mute"; break;
      case 'l': cmdToSend = CMD_BLUETOOTH; cmdName = "Bluetooth"; break;
      case '+': 
      case '=': cmdToSend = CMD_VOLUME_UP; cmdName = "Volume+"; break;
      case '-': 
      case '_': cmdToSend = CMD_VOLUME_DOWN; cmdName = "Volume-"; break;
      case 'a': cmdToSend = CMD_LEFT; cmdName = "Left"; break;
      case 'd': cmdToSend = CMD_RIGHT; cmdName = "Right"; break;
      case 'B': cmdToSend = CMD_BASS_UP; cmdName = "Bass+"; break;
      case 'b': cmdToSend = CMD_BASS_DOWN; cmdName = "Bass-"; break;
      case 'M': cmdToSend = CMD_MID_UP; cmdName = "Mid+"; break;
      case 'n': cmdToSend = CMD_MID_DOWN; cmdName = "Mid-"; break;
      case 'T': cmdToSend = CMD_TREBLE_UP; cmdName = "Treble+"; break;
      case 'y': cmdToSend = CMD_TREBLE_DOWN; cmdName = "Treble-"; break;
      case '1': cmdToSend = CMD_AUX; cmdName = "AUX"; break;
      case '2': cmdToSend = CMD_LINE; cmdName = "Line"; break;
      case '3': cmdToSend = CMD_OPT; cmdName = "Optical"; break;
      case '4': cmdToSend = CMD_USB; cmdName = "USB"; break;
      case '<': cmdToSend = CMD_BAL_LEFT; cmdName = "Balance Left"; break;
      case '>': cmdToSend = CMD_BAL_RIGHT; cmdName = "Balance Right"; break;
      
      case 'h':
      case '?':
        Serial.println("\n=== HILFE ===");
        Serial.println("Modi: t=Test An/Aus, r=Nur Lesen, A=Auto-Test");
        Serial.println("Senden: p=Power, m=Mute, +/-=Volume, l=Bluetooth");
        Serial.println("Sound: B/b=Bass, M/n=Mid, T/y=Treble");
        Serial.println("Input: 1=AUX, 2=Line, 3=Opt, 4=USB");
        Serial.println("Balance: <>=Links/Rechts");
        break;
    }
    
    if (cmdToSend != 0) {
      if (testMode) {
        sendAndVerify(cmdToSend, cmdName);
      } else {
        // Normales Senden ohne Verifikation
        Serial.print("Sende: ");
        Serial.println(cmdName);
        IrSender.sendNEC(TEUFEL_ADDR, cmdToSend, 0);
        delay(100);
      }
    }
  }
}

/*
 * === VERKABELUNG ===
 * 
 * IR-LED Sender (Pin 3):
 * Pin 3 ──┬── IR-LED Anode (+)
 *                 │
 *                GND ── IR-LED Kathode (-)
 * 
 * VS1838B Empfänger (Pin 2):
 * OUT (Pin 1) → Arduino Pin 2
 * GND (Pin 2) → Arduino GND  
 * VCC (Pin 3) → Arduino 5V
 * 
 * TIPP: Positioniere LED und Empfänger so, dass 
 *       das IR-Licht reflektiert werden kann!
 */