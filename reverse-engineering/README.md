# Teufel Power HiFi IR Controller

Arduino-basierte Infrarot-Fernbedienung für Teufel Power HiFi Systeme.

## 📋 Übersicht

Dieses Projekt ermöglicht die Steuerung einer Teufel Power HiFi Anlage via Arduino und Infrarot. Es
besteht aus drei Komponenten:

1. **IR-Scanner** - Liest IR-Codes von der Original-Fernbedienung
2. **IR-Controller** - Sendet Befehle an die Anlage
3. **IR-Tester** - Kombiniert Senden und Empfangen zum Debugging

## 🛠️ Hardware-Anforderungen

- Arduino Uno oder Nano
- VS1838B IR-Empfänger
- IR-LED (940nm)
- Optional: 100Ω Widerstand (nicht erforderlich)
- Optional: 2N2222 Transistor für mehr Reichweite

## 📐 Schaltung

### IR-Empfänger (VS1838B)

```
VS1838B          Arduino
-------          -------
OUT (Pin 1)  →   D2
GND (Pin 2)  →   GND  
VCC (Pin 3)  →   5V
```

### IR-Sender (LED)

```
Arduino Pin 3 ──┬── IR-LED Anode (+)
                        │
                       GND ── IR-LED Kathode (-)
```

### Verstärkte Sender-Schaltung (optional)

```
               +5V
                │
               [10kΩ]
                │
Pin 3 ──┤ 2N2222
                │E
               GND
                
              C │
                ├── IR-LED (-)
               +5V ── IR-LED (+)
```

## 📦 Installation

1. Arduino IDE installieren
2. IRremote Library hinzufügen:
    - Tools → Manage Libraries
    - Suche nach "IRremote"
    - Version 4.x installieren

## 🚀 Verwendung

### 1. IR-Codes scannen (`teufel-ir-receiver.ino`)

Liest die Codes deiner Original-Fernbedienung:

```bash
1. Code auf Arduino laden
2. Serial Monitor öffnen (9600 Baud)
3. Fernbedienung auf VS1838B richten
4. Tasten drücken und Codes notieren
```

**Ausgabe-Beispiel:**

```
NEC      | 0x5780  | 0x48    | Power
NEC      | 0x5780  | 0x28    | Mute
```

### 2. Anlage steuern (`teufel-ir-controller-fixed.ino`)

Sendet IR-Befehle an die Anlage:

```bash
1. Code auf Arduino laden
2. Serial Monitor öffnen
3. Befehle eingeben:
   p = Power
   m = Mute
   + = Lauter
   - = Leiser
   ...
```

### 3. Verbindung testen (`teufel-ir-send-receive.ino`)

Testet ob gesendete Signale korrekt empfangen werden:

```bash
Modi:
- t = Test-Modus (prüft Empfang)
- r = Nur lesen
- A = Alle Codes automatisch testen
```

## 📟 IR-Code Referenz

| Funktion      | Code | Taste |
|---------------|------|-------|
| Power         | 0x48 | p     |
| Bluetooth     | 0x40 | l     |
| Mute          | 0x28 | m     |
| Volume Up     | 0xB0 | +     |
| Volume Down   | 0x30 | -     |
| Left          | 0x78 | a     |
| Right         | 0xF8 | d     |
| Bass Up       | 0x58 | B     |
| Bass Down     | 0x41 | b     |
| Mid Up        | 0x68 | M     |
| Mid Down      | 0x42 | n     |
| Treble Up     | 0xB8 | T     |
| Treble Down   | 0x43 | t     |
| AUX           | 0x44 | 1     |
| Line          | 0x45 | 2     |
| Optical       | 0x3F | 3     |
| USB           | 0xDF | 4     |
| Balance Left  | 0xBF | <     |
| Balance Right | 0x5F | >     |

**Protokoll:** NEC  
**Adresse:** 0x5780

## 🔧 Troubleshooting

### LED sendet, aber Anlage reagiert nicht

- Abstand verringern (10-20cm)
- LED-Polung prüfen (langes Bein = +)
- Transistor-Verstärker verwenden
- Widerstand ist optional und kann weggelassen werden

### Keine IR-Codes empfangen

- VS1838B Verkabelung prüfen
- Richtigen Arduino-Pin verwenden (D2)
- Batterien der Fernbedienung prüfen

### Falsche Codes empfangen

- Störquellen entfernen (Leuchtstoffröhren)
- Abschirmung zwischen Sender und Empfänger

## 🔮 Erweiterungen

### ESP8266/ESP32 WiFi-Steuerung

```cpp
// Webhook für Smart Home Integration
server.on("/power", [](){
  sendTeufelCommand(CMD_POWER);
  server.send(200, "text/plain", "OK");
});
```

### Alexa Integration

- Fauxmo Library für ESP8266
- Emuliert Philips Hue
- "Alexa, schalte HiFi ein"

### Home Assistant

```yaml
switch:
  - platform: rest
    name: Teufel HiFi
    resource: http://esp8266.local/power
```

## 📄 Lizenz

MIT License

Copyright (c) 2025 Martin Pfeffer

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

## 🙏 Danksagung

- IRremote Library von Arduino-IRremote
- Teufel für die großartige Power HiFi Anlage
- Arduino Community für die Unterstützung