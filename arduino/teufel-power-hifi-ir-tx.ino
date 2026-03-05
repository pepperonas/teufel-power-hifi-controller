/*
 * Teufel Power HiFi IR Remote Control
 * 
 * Hardware:
 * - Arduino Uno/Nano
 * - IR LED an Pin 3 (ohne Widerstand)
 * - Optional: Transistor für mehr Reichweite
 * 
 * Protokoll: NEC
 * Adresse: 0x5780
 */

#include <IRremote.hpp>

#define IR_SEND_PIN 3  // IR-LED an Pin 3

// Teufel Power HiFi IR-Codes (NEC Protocol)
#define TEUFEL_ADDR          0x5780

// Basis-Funktionen (korrigiertes Mapping)
#define CMD_POWER            0x48
#define CMD_BLUETOOTH        0x40
#define CMD_MUTE             0x28

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

void setup() {
  Serial.begin(9600);
  IrSender.begin(IR_SEND_PIN);
  
  Serial.println("=== Teufel Power HiFi IR Controller ===");
  Serial.println("Befehle:");
  Serial.println("p - Power ON/OFF");
  Serial.println("m - Mute");
  Serial.println("l - bLuetooth");
  Serial.println("+ - Lautstärke +");
  Serial.println("- - Lautstärke -");
  Serial.println("← - Links (a)");
  Serial.println("→ - Rechts (d)");
  Serial.println("B/b - Bass +/-");
  Serial.println("M/n - Mid +/-");
  Serial.println("T/t - Treble +/-");
  Serial.println("1 - AUX");
  Serial.println("2 - Line");
  Serial.println("3 - Optical");
  Serial.println("4 - USB");
  Serial.println("< - Balance Links");
  Serial.println("> - Balance Rechts");
  Serial.println();
}

void sendTeufelCommand(uint8_t command) {
  Serial.print("Sende: 0x");
  Serial.print(command, HEX);
  
  // Sende NEC Befehl
  IrSender.sendNEC(TEUFEL_ADDR, command, 0);
  
  // Beschreibung ausgeben
  switch(command) {
    case CMD_POWER:       Serial.println(" - Power"); break;
    case CMD_BLUETOOTH:   Serial.println(" - Bluetooth"); break;
    case CMD_MUTE:        Serial.println(" - Mute"); break;
    case CMD_VOLUME_UP:   Serial.println(" - Volume +"); break;
    case CMD_VOLUME_DOWN: Serial.println(" - Volume -"); break;
    case CMD_LEFT:        Serial.println(" - Links"); break;
    case CMD_RIGHT:       Serial.println(" - Rechts"); break;
    case CMD_BASS_UP:     Serial.println(" - Bass +"); break;
    case CMD_BASS_DOWN:   Serial.println(" - Bass -"); break;
    case CMD_MID_UP:      Serial.println(" - Mid +"); break;
    case CMD_MID_DOWN:    Serial.println(" - Mid -"); break;
    case CMD_TREBLE_UP:   Serial.println(" - Treble +"); break;
    case CMD_TREBLE_DOWN: Serial.println(" - Treble -"); break;
    case CMD_AUX:         Serial.println(" - AUX"); break;
    case CMD_LINE:        Serial.println(" - Line"); break;
    case CMD_OPT:         Serial.println(" - Optical"); break;
    case CMD_USB:         Serial.println(" - USB"); break;
    case CMD_BAL_LEFT:    Serial.println(" - Balance Links"); break;
    case CMD_BAL_RIGHT:   Serial.println(" - Balance Rechts"); break;
    default:              Serial.println(" - Unbekannt"); break;
  }
  
  delay(100); // Kurze Pause zwischen Befehlen
}

// Für kontinuierliche Befehle (Volume, Bass, etc.)
void sendRepeatingCommand(uint8_t command, int repeats = 3) {
  for (int i = 0; i < repeats; i++) {
    sendTeufelCommand(command);
    delay(50); // Kürzere Pause für Wiederholungen
  }
}

void loop() {
  if (Serial.available()) {
    char input = Serial.read();
    
    switch(input) {
      // Basis-Funktionen
      case 'p': sendTeufelCommand(CMD_POWER); break;
      case 'm': sendTeufelCommand(CMD_MUTE); break;
      case 'l': sendTeufelCommand(CMD_BLUETOOTH); break;
      
      // Lautstärke (mit Wiederholung für smooth control)
      case '+': 
      case '=': sendRepeatingCommand(CMD_VOLUME_UP, 3); break;
      case '-': 
      case '_': sendRepeatingCommand(CMD_VOLUME_DOWN, 3); break;
      
      // Navigation
      case 'a': sendTeufelCommand(CMD_LEFT); break;
      case 'd': sendTeufelCommand(CMD_RIGHT); break;
      
      // Sound Einstellungen
      case 'B': sendTeufelCommand(CMD_BASS_UP); break;
      case 'b': sendTeufelCommand(CMD_BASS_DOWN); break;
      case 'M': sendTeufelCommand(CMD_MID_UP); break;
      case 'n': sendTeufelCommand(CMD_MID_DOWN); break;
      case 'T': sendTeufelCommand(CMD_TREBLE_UP); break;
      case 't': sendTeufelCommand(CMD_TREBLE_DOWN); break;
      
      // Eingänge
      case '1': sendTeufelCommand(CMD_AUX); break;
      case '2': sendTeufelCommand(CMD_LINE); break;
      case '3': sendTeufelCommand(CMD_OPT); break;
      case '4': sendTeufelCommand(CMD_USB); break;
      
      // Balance
      case '<': 
      case ',': sendTeufelCommand(CMD_BAL_LEFT); break;
      case '>': 
      case '.': sendTeufelCommand(CMD_BAL_RIGHT); break;
      
      // Hilfe
      case 'h':
      case '?':
        Serial.println("\n=== Hilfe ===");
        Serial.println("p=Power, m=Mute, l=bLuetooth");
        Serial.println("+/-=Volume, a/d=Links/Rechts");
        Serial.println("B/b=Bass+/-, M/n=Mid+/-, T/t=Treble+/-");
        Serial.println("1=AUX, 2=Line, 3=Opt, 4=USB");
        Serial.println("<>=Balance L/R");
        break;
        
      case '\n':
      case '\r':
        // Ignoriere Zeilenumbrüche
        break;
        
      default:
        Serial.print("Unbekannter Befehl: ");
        Serial.println(input);
    }
  }
}

/* 
 * === Erweiterte Funktionen ===
 * 
 * 1. Makros für häufige Aktionen:
 */
void powerOnWithBluetooth() {
  sendTeufelCommand(CMD_POWER);      // 0x48
  delay(2000); // Warte auf Einschalten
  sendTeufelCommand(CMD_BLUETOOTH);  // 0x40
}

void setVolumeLevel(int level) {
  // Erst auf Minimum
  for(int i = 0; i < 50; i++) {
    sendTeufelCommand(CMD_VOLUME_DOWN);  // 0x30
    delay(50);
  }
  
  // Dann auf gewünschten Level
  for(int i = 0; i < level; i++) {
    sendTeufelCommand(CMD_VOLUME_UP);    // 0xB0
    delay(50);
  }
}

// Schnell auf einen bestimmten Eingang wechseln
void switchToInput(char inputType) {
  switch(inputType) {
    case 'A': sendTeufelCommand(CMD_AUX); break;      // 0x44
    case 'L': sendTeufelCommand(CMD_LINE); break;     // 0x45
    case 'O': sendTeufelCommand(CMD_OPT); break;      // 0x3F
    case 'U': sendTeufelCommand(CMD_USB); break;      // 0xDF
    case 'B': sendTeufelCommand(CMD_BLUETOOTH); break; // 0x40
  }
}

// Sound-Preset
void setFlatEQ() {
  // Reset Bass, Mid, Treble auf neutral
  for(int i = 0; i < 10; i++) {
    sendTeufelCommand(CMD_BASS_DOWN);    // 0x41
    sendTeufelCommand(CMD_MID_DOWN);     // 0x42
    sendTeufelCommand(CMD_TREBLE_DOWN);  // 0x43
    delay(50);
  }
}

/*
 * 2. Hardware-Erweiterung für mehr Reichweite:
 * 
 *                +5V
 *                 |
 *                 R1 (10k)
 *                 |
 * Pin 3 ---+--- Base (2N2222)
 *                         |
 *                         Emitter
 *                         |
 *                        GND
 *                         
 *                     Collector
 *                         |
 *                         +--- IR-LED Kathode
 *                         |
 *                        +5V --- IR-LED Anode
 * 
 * Für noch mehr Power: Mehrere IR-LEDs parallel
 * 
 * === ALLE TEUFEL POWER HIFI CODES ===
 * 
 * 0x48 - Power
 * 0x40 - Bluetooth
 * 0x28 - Mute
 * 0xB0 - Volume Up
 * 0x30 - Volume Down
 * 0x78 - Left
 * 0xF8 - Right
 * 0x58 - Bass Up
 * 0x41 - Bass Down
 * 0x68 - Mid Up
 * 0x42 - Mid Down
 * 0xB8 - Treble Up
 * 0x43 - Treble Down
 * 0x44 - AUX
 * 0x45 - Line
 * 0x3F - Optical
 * 0xDF - USB
 * 0xBF - Balance Left
 * 0x5F - Balance Right
 */