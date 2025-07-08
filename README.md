# Teufel Power HiFi IR Controller

🎵 Arduino und Raspberry Pi Infrarot-Fernbedienung für Teufel Power HiFi Systeme

## Übersicht

Dieses Projekt ermöglicht die Infrarot-Fernsteuerung von Teufel Power HiFi Systemen mit Arduino und Raspberry Pi. Es implementiert das NEC Protocol mit korrektem Timing und Frame-Struktur für zuverlässige Kommunikation.

## Features

- ✅ Vollständiger IR Command Set (Power, Volume, EQ, Inputs)
- ✅ Arduino Implementierung mit IRremote Library
- ✅ Raspberry Pi Implementierung mit Hardware PWM
- ✅ Interaktive Befehlsoberfläche
- ✅ Signal-Verifikation und Test-Tools

## Hardware Anforderungen

### Arduino Setup
- Arduino Uno/Nano
- VS1838B IR Receiver
- IR LED (940nm)
- Optional: 2N2222 Transistor für erweiterte Reichweite

### Raspberry Pi Setup
- Raspberry Pi (beliebiges Modell mit GPIO)
- IR LED angeschlossen an GPIO 12 (Pin 32)
- pigpio Library für Hardware PWM

## Schnellstart

### Arduino
```bash
# IRremote Library (Version 4.x) in Arduino IDE installieren
# teufel-power-hifi-ir-tx.ino auf Arduino flashen
# Serial Monitor bei 9600 Baud öffnen
# Befehle verwenden: p=power, m=mute, +=volume up, etc.
```

### Raspberry Pi
```bash
# pigpio installieren
sudo apt-get install pigpio python3-pigpio

# pigpio daemon starten
sudo pigpiod

# Controller ausführen
sudo python3 teufel-power-hifi-controller.py
```

## Befehlsreferenz

| Funktion | Code | Taste |
|----------|------|-------|
| Power | 0x48 | p |
| Mute | 0x28 | m |
| Bluetooth | 0x40 | l |
| Volume Up | 0xB0 | + |
| Volume Down | 0x30 | - |
| Bass Up/Down | 0x58/0x41 | B/b |
| Mid Up/Down | 0x68/0x42 | M/n |
| Treble Up/Down | 0xB8/0x43 | T/t |
| AUX | 0x44 | 1 |
| Line | 0x45 | 2 |
| Optical | 0x3F | 3 |
| USB | 0xDF | 4 |

## Technische Details

- **Protocol**: NEC
- **Address**: 0x5780 (16-bit)
- **Carrier**: 38kHz
- **Frame**: LSB first transmission

## Projektstruktur

```
├── teufel-power-hifi-controller.py    # Raspberry Pi Controller
├── reverse-engineering/
│   ├── teufel-power-hifi-ir-tx.ino   # Arduino Transmitter
│   ├── teufel-power-hifi-ir-rx.ino   # Arduino Receiver
│   ├── teufel-power-hifi-ir-rx-ts.ino # Kombiniertes Test-Tool
│   └── teufel-power-hifi-ir-mapping.csv # IR Code Mapping
└── CLAUDE.md                          # Entwicklungshandbuch
```

## Schaltpläne

### Arduino IR Transmitter
```
Arduino Pin 3 ──── IR LED (+)
GND ──────────────── IR LED (-)
```

### Raspberry Pi IR Transmitter
```
GPIO 12 (Pin 32) ── IR LED (+)
GND ────────────────── IR LED (-)
```

## Fehlerbehebung

- **Keine Reaktion**: LED-Polarität und Abstand prüfen (10-20cm)
- **Schwaches Signal**: 2N2222 Transistor-Verstärker hinzufügen
- **Falsche Codes**: NEC Protocol und Address 0x5780 verifizieren

## Lizenz

MIT License

Copyright (c) 2025 Martin Pfeffer, Berlin

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

## Mitwirkung

Issues und Pull Requests für Verbesserungen sind willkommen!

