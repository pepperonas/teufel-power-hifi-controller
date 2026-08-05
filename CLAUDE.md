# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This project provides comprehensive infrared (IR) remote control for Teufel Power HiFi systems through multiple platforms and interfaces. Originally reverse-engineered from the official remote control, it now offers web-based control, REST API, command-line tools, and Arduino implementation.

## Repository Structure

```
powerhifi-controller/
├── arduino/              # Arduino IR reverse-engineering tools
│   ├── *.ino            # IR receiver/transmitter sketches
│   └── *.csv            # Command mapping
├── docs/                # Technical documentation
│   ├── API.md           # REST API reference
│   ├── ARCHITECTURE.md  # System architecture
│   └── HARDWARE.md      # Hardware specifications
├── images/              # Visual assets
├── public/              # Web interface (HTML/CSS/JS)
├── logs/                # Application logs
├── server.js            # Express.js web server
└── teufel-power-hifi-controller.py  # Python IR controller
```

## Key Technologies

- **Node.js/Express**: Web server and REST API
- **Python/pigpio**: Hardware PWM control for IR transmission
- **Arduino/IRremote**: IR protocol reverse-engineering
- **HTML/CSS/JS**: Responsive web interface

## Hardware Requirements

- **Raspberry Pi**: GPIO 12 (Pin 32) for hardware PWM
- **IR LED**: 940nm wavelength
- **NPN Transistor**: Signal amplification (2N2222 or similar)
- **Resistors**: 47Ω and 1kΩ

## Running the Controllers

### Web Interface (Recommended)
```bash
npm install
npm start
# Access via http://localhost:5002 or http://[pi-ip]:5002
```

### Command Line
```bash
# Direct Python execution
python3 teufel-power-hifi-controller.py --command CMD_POWER

# With pigpio daemon for best performance
sudo pigpiod
sudo python3 teufel-power-hifi-controller.py --command CMD_VOL_UP
```

### Process Management
```bash
# PM2 (recommended)
pm2 start ecosystem.config.js
pm2 save
pm2 startup

# Check status
pm2 status powerhifi-controller
```

## IR Protocol Details

- **Protocol**: NEC (38kHz carrier, 33% duty cycle)
- **Address**: 0x5780 (16-bit)
- **Frame Structure**: LSB first transmission
  - Address_Low | Address_High | Command | ~Command
- **Hardware**: GPIO 12 required for hardware PWM

## Command Mapping

All IR codes are defined in `arduino/teufel-power-hifi-ir-mapping.csv`:

| Function | Hex Code | Python Constant | API Endpoint |
|----------|----------|-----------------|--------------|
| Power | 0x48 | CMD_POWER | POST /api/power |
| Mute | 0x28 | CMD_MUTE | POST /api/mute |
| Volume Up | 0xB0 | CMD_VOL_UP | POST /api/volume |
| Volume Down | 0x30 | CMD_VOL_DOWN | POST /api/volume |
| Bluetooth | 0x40 | CMD_BT | POST /api/input |
| Bass Up/Down | 0x58/0x41 | CMD_BASS_UP/DOWN | POST /api/eq |
| Mid Up/Down | 0x68/0x42 | CMD_MID_UP/DOWN | POST /api/eq |
| Treble Up/Down | 0xB8/0x43 | CMD_TREBLE_UP/DOWN | POST /api/eq |
| AUX/Line/Optical/USB | 0x44/0x45/0x3F/0xDF | CMD_AUX/LINE/OPT/USB | POST /api/input |

> **Mute (`0x28`) mutes nothing.** Power and volume work, so the IR path is fine and the NEC address 0x5780 is right — the byte is simply mislabelled in the original capture. Unresolved; the remaining candidates are the 22 unused values whose low three bits are zero (every confirmed code is in that family).
>
> **Extra Bass is `Auto`/`Off`, not `On`/`Off`** (Yamaha side, see yahama-controller). The RX-V577 answers `On` with `RC=3`, and a rejected command still returns HTTP 200 — check the return code or the UI will report success.

## API Endpoints

See `docs/API.md` for complete reference. Key endpoints:

- `GET /api/health` - Health check
- `GET /api/status` - Current status
- `POST /api/power` - Toggle power
- `POST /api/volume` - Volume control (rate-limited)
- `POST /api/mute` - Toggle mute
- `POST /api/input` - Select input source
- `POST /api/eq` - EQ adjustments

## Common Issues and Solutions

### Path Configuration Issues
- **Problem**: 500 Internal Server Error
- **Solution**: Check `controller-config.json` for correct Python script path

### Permission Issues
- **Problem**: GPIO access denied
- **Solution**: 
  1. Add user to gpio group: `sudo usermod -a -G gpio $USER`
  2. Or run with pigpio daemon: `sudo pigpiod`

### pigpio Daemon Issues
- **Problem**: Performance warnings
- **Solution**: Script works without daemon but with warnings. For best performance: `sudo pigpiod`

### Node.js Server Issues
- **Problem**: Server not responding on port 5002
- **Solution**: 
  1. Check with `pm2 status`
  2. Restart: `pm2 restart powerhifi-controller`
  3. Check logs: `pm2 logs`

### IR Transmission Issues
- **Problem**: HiFi system not responding
- **Solution**:
  1. Verify IR LED orientation (point at receiver)
  2. Test at close range (10-20cm)
  3. Check LED with phone camera (should see purple glow)
  4. Ensure GPIO 12 is used (hardware PWM required)

## Development Guidelines

### Code Style
- Use existing code patterns and conventions
- Follow security best practices
- Never expose or log secrets
- Add appropriate error handling

### Testing Commands
```bash
# Test Python controller
python3 teufel-power-hifi-controller.py --list
python3 teufel-power-hifi-controller.py --command CMD_POWER

# Test API
curl -X POST http://localhost:5002/api/power
curl -X GET http://localhost:5002/api/health

# Debug mode
DEBUG=1 python3 teufel-power-hifi-controller.py --command CMD_POWER
DEBUG=* node server.js
```

### Arduino Development
1. Use sketches in `arduino/` for IR reverse-engineering
2. Capture new codes with `teufel-power-hifi-ir-rx.ino`
3. Test transmission with `teufel-power-hifi-ir-tx.ino`
4. Update `arduino/teufel-power-hifi-ir-mapping.csv` with new codes

## Rate Limiting

Volume control implements intelligent rate limiting:
- Max 20 changes per 10 seconds
- 30-second cooldown when exceeded
- Prevents hardware damage and abuse

## Architecture Notes

### System Layers
1. **User Interface**: Web dashboard, REST API, CLI
2. **Control Layer**: Node.js server, Python controller
3. **Hardware Abstraction**: pigpio library
4. **Physical Layer**: GPIO 12 → IR LED → HiFi System

### NEC Frame Calculation
```python
def calculate_nec_frame(address, command):
    addr_low = address & 0xFF
    addr_high = (address >> 8) & 0xFF
    frame = (addr_low << 24) | (addr_high << 16) | (command << 8) | (~command & 0xFF)
    return frame
```

## Documentation

- **README.md**: Main documentation and setup guide
- **docs/API.md**: Complete API reference with examples
- **docs/ARCHITECTURE.md**: System design and data flow
- **docs/HARDWARE.md**: Circuit diagrams and specifications
- **arduino/README.md**: Arduino tools documentation

## Useful Commands

```bash
# Check GPIO status
gpio readall

# Monitor server logs
pm2 logs powerhifi-controller --lines 100

# Test IR LED with camera
# Point phone camera at LED while sending command

# Check Python dependencies
python3 -c "import pigpio; print('pigpio OK')"

# Restart all services
pm2 restart all
sudo systemctl restart pigpiod
```

## R4 LED matrix (raspi5 / teufel-ir-bridge)

Shared firmware lives in gartenklima/raumklima `arduino/r4-firmware/` (not this repo’s `arduino/`).

| Mode name | Firmware `mN` | Notes |
|-----------|---------------|--------|
| `clock` / Uhr | 12 | Digital HH:MM (`FONT2`), blink colon, corner pips — **no** seconds bar |
| `analog` / Wanduhr | 13 | Analog face: cardinal ticks, hour/minute hands, second rim tip |
| (both) | `vHHMMSS` | Packed local time from `ir_bridge.clock_value()` ~4×/s |

Serial: plain ACM open + `m0` probe; **avoid** 1200-baud touch and `stty` ExecStartPre on `/dev/ttyACM0` (wedges USB-CDC). Drop-in on raspi5: `/etc/systemd/system/teufel-ir-bridge.service.d/no-stty.conf`.

## Der Deadlock, der die Selbstheilung lahmlegte (2026-08-04)

Das Watchdog-Konstrukt von 2026-08-02 konnte in genau dem Fall nicht feuern, für
den es geschrieben wurde. **pyserial hat `write_timeout=None` als Default** — ein
unbegrenztes Warten darauf, dass der Port Daten annimmt. Wenn der R4 aufhört,
seinen USB-Endpunkt zu leeren, parkt `ser.write()` **für immer in `pselect6()`,
und zwar mit gehaltenem `ser_lock`**. Alles, was den Port braucht, staut sich
dahinter: IR-Befehle, Matrix-Pushes — und der Nudge des Watchdogs selbst.

Live vorgefunden: **17 Handler-Threads in `futex_wait`**, der Watchdog mitten
darunter, ein Thread in `pselect6` mit gesetztem Write-Set und **NULL-Timeout**.
`MATRIX?` antwortete weiter (beantwortet aus dem Cache, ohne Lock) und `FRAME?`
lieferte ein eingefrorenes Bild — von außen sah die Bridge gesund aus, während
node im Sekundentakt `IR bridge timeout` loggte.

Drei Korrekturen:

1. **`write_timeout=SER_WRITE_TIMEOUT` (1 s)** beim Öffnen. Der Write scheitert
   jetzt, `_write_line` verwirft den Port, `serial_loop` öffnet neu.
2. **Jedes Warten auf den Port ist begrenzt.** `send_code` scheitert nach
   `LOCK_WAIT_S` mit einem Fehler (ein Tastendruck, der Minuten später ankommt,
   ist schlimmer als keiner), `push_matrix` überspringt still.
3. **Der Watchdog wartet nicht mehr auf das Lock.** Das Lock nicht zu bekommen,
   während seit `RX_STALE_S` nichts zurückkommt, ist **kein Grund zu warten —
   es ist die Diagnose**. Er setzt dann direkt zurück, bewusst ohne Lock: wer es
   hält, ist der feststeckende Writer, und die Re-Enumeration ist genau das, was
   ihn befreit.

Nebenbei: `_write_line` setzte `_serial_booted` ohne `global` — die Zuweisung war
wirkungslos, entgegen dem Docstring. Und der Reconnect-Loop (alle 3 s) hat bei
physisch abwesendem R4 ~2400 Zeilen/h produziert; `_log_once(tag, msg)`
unterdrückt das jetzt **pro Bedingung** (eine Dedupe nur über den Text griff
nicht, weil sich zwei Meldungen abwechselten).

`tests/test_ir_bridge_deadlock.py` hält alle vier Eigenschaften fest.

## Wenn der R4 gar nicht mehr enumeriert (2026-08-05)

Am 2026-08-04 um 05:33 fiel der R4 aus und war **18,6 Stunden weg**. Der
Ausfall lief nach dem bekannten Muster (`error -110` → `error -62` →
`attempt power cycle` → `unable to enumerate`), aber mit einer entscheidenden
Zeile mittendrin: um 05:35:55 flog **auch das Mikrofon** vom selben Hub-Ast.
Das ist kein R4-Problem — das ist der ganze Ast.

**Warum nichts Alarm schlug:** der R4 lief die ganze Zeit weiter. Er postet
Klima-Daten über **WLAN**, nicht über USB; die Messreihen von raumklima und
gartenklima haben im Ausfallfenster **keine Lücke**. Jeder überwachte
Datenstrom war gesund, während Matrix und IR ins Leere liefen. Wer hier nach
einem Ausfall sucht, darf sich nicht auf die Klima-Feeds verlassen.

**Was gefehlt hat:** `usb_reset_r4()` braucht ein Gerät. Ist der R4 gar nicht
mehr am Bus, meldet die Bridge korrekt „nicht am Bus" — und konnte nichts
weiter tun. Bisher hieß das: physisch umstecken.

⚠️ **Der `authorized`-Toggle muss am ELTERN-Hub passieren.** Am Hub des Geräts
(`1-2.1`) bewirkte er nichts; eine Ebene höher (`1-2`) kam der R4 nach acht
Sekunden zurück. Das widerlegt die frühere Notiz, physisches Umstecken sei der
einzige Weg — sie hatte die falsche Ebene erwischt.

`usb_hub_recover()` macht das jetzt automatisch: nach `HUB_RECOVER_AFTER`=6
erfolglosen Öffnungsversuchen, mit 10 min Abkühlzeit (der Hub trägt auch das
Mikrofon, das binnen einer Sekunde zurückkommt). Der Hub-Pfad wird gemerkt,
solange der R4 da ist — hinterher lässt er sich nicht mehr erfragen.
**End-to-end nachgestellt: Ausfall → 50 s → wieder online.**

⚠️ **`authorized` ist ein sysfs-Attribut, kein Geräteknoten** — udevs `MODE`
und `GROUP` erreichen es nicht, und der Dienst läuft als `pi`. Statt die Rechte
auf jedem Hub aufzuweichen, geht genau ein Kommando über sudo:
`system/r4-hub-recover` + `system/teufel-ir-bridge.sudoers`. Das Skript prüft
sein Argument streng (Bus-Port-Name, sonst nichts) — es entscheidet über eine
sudo-Grenze hinweg, welche Datei als root geschrieben wird — und weigert sich
bei allem, was kein Hub ist.

**Stromlage am 2026-08-05:** `usb_max_current_enable` weiterhin **nicht**
gesetzt (600-mA-Deckel), EXT5V bei **4,90 V** im Leerlauf, **2471
Unterspannungs-Ereignisse in 3,2 Tagen** — durchgehend 30–49 pro 10 Minuten,
nicht an ein Ereignis gekoppelt. ⚠️ **`usb_max_current_enable=1` wäre hier
falsch:** die 5-V-Schiene sackt schon ohne R4 ab, ein höherer Deckel ließe die
Peripherie mehr ziehen und verschlimmerte den Einbruch. Der Ausweg bleibt
Hardware — **aktiver** USB-Hub (nimmt R4 und Mikro ganz von der Pi-Schiene)
und/oder 5 V/5 A.

## ⚠️ Die eigentliche Ursache ist Strom, nicht Software

Der Deadlock-Fix macht die Bridge robust — er behebt **nicht**, warum der R4
überhaupt wegbricht. Am 2026-08-04 gemessen:

- **1318 `Undervoltage detected` in 2 d 9,7 h** Uptime (~23/h, alle 2,5 min eins)
- **`usb_max_current_enable` steht NICHT in `/boot/firmware/config.txt`** → der
  Pi 5 deckelt den gesamten USB-Strom auf **600 mA**. Daran hängen der R4 (bis
  500 mA), das USB-Mikrofon und zwei Genesys-Hubs.
- Im `dmesg` fallen Enumeration und Brownout **ins selbe Sekundenfenster**:
  `new full-speed USB device number 11` → `Undervoltage detected!` →
  `device descriptor read/64, error -110` → `device not accepting address, error -62`.

Das ist derselbe Befund wie damals auf raspi3 (Memory `raspi3-usb-power-crashes`).
**Wenn der R4 in diesem Zustand ist, hilft keine Software mehr:** `USBDEVFS_RESET`,
`authorized`-Toggle und ein Reset des Elternhubs sind alle durchprobiert — das
Gerät nimmt die Adresse nicht an. Dann bleibt nur physisches Aus- und Einstecken,
besser an einem **aktiven** USB-Hub. Dauerhaft: 5 V/5 A (27 W USB-C PD) und/oder
`usb_max_current_enable=1` (braucht Reboot; nur sinnvoll, wenn das Netzteil den
Strom auch liefern kann — sonst erkauft man sich mehr Brownouts statt weniger).

Die Bridge versucht derweil alle 3 s neu und greift den R4 automatisch, sobald er
wieder am Bus ist — nach dem Replug ist kein Eingriff nötig.

## R4 wedges — and how the bridge gets out of it

raspi5 browns out constantly (hundreds of `Undervoltage detected` per day), and a glitched USB link leaves the R4 **accepting writes while it stops answering anything**. From the Pi that is indistinguishable from healthy hardware: the port is open, writes succeed, and matrix updates plus IR codes vanish into the void while every layer above reports success. A service restart does not help — the wedge sits in the device, not in the handle. Only re-enumeration clears it.

- `liveness_watchdog` checks every 5 s how long ago *any* line arrived. After `RX_STALE_S` (25 s) of silence it first nudges the board (a mode command, which the firmware always answers with `M<n>` — necessary because in mode `off` the R4 streams nothing on its own) and only then calls `usb_reset_r4()`.
- `try_open_serial` also resets when `open()` itself fails with EIO, otherwise the bridge retries a dead node forever.
- The reset needs write access to the bus node and the service runs as `pi`, hence `system/99-arduino-r4-usbreset.rules` (`MODE=0660`, `GROUP=plugdev`). Install with `sudo cp system/*.rules /etc/udev/rules.d/ && sudo udevadm control --reload-rules && sudo udevadm trigger --subsystem-match=usb --action=change`.

**Do not add a per-command acknowledgement.** It was tried: the firmware echoes `TX 0x<hex>` after `IrSender` emits, but in the streaming matrix modes the R4 floods the port with frames, the reader falls behind the ack window, and *every working button* gets reported as broken. Freshness of any line is the robust signal; a reply to one specific command is not.

## Contributing

1. Test changes thoroughly with actual hardware
2. Update documentation when adding features
3. Follow existing code structure
4. Test all API endpoints after changes
5. Verify IR transmission with oscilloscope if available