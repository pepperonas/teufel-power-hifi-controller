# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This project provides IR remote control for Teufel Power HiFi systems using both Arduino and Raspberry Pi platforms. The system uses NEC protocol with address 0x5780 and specific command codes for all HiFi functions.

## Hardware Platforms

### Arduino (reverse-engineering/ directory)
- **teufel-power-hifi-ir-rx.ino**: IR receiver for scanning original remote codes
- **teufel-power-hifi-ir-tx.ino**: IR transmitter for sending commands
- **teufel-power-hifi-ir-rx-ts.ino**: Combined receiver/transmitter for testing

### Raspberry Pi (root directory)
- **teufel-power-hifi-controller.py**: Main Python controller using pigpio for hardware PWM

## Running the Controllers

### Arduino
1. Install IRremote library (version 4.x) in Arduino IDE
2. Flash appropriate .ino file to Arduino
3. Open Serial Monitor at 9600 baud
4. Use interactive commands (p=power, m=mute, +=volume up, etc.)

### Raspberry Pi
```bash
# Start pigpio daemon first
sudo pigpiod

# Run the controller (requires root for GPIO access)
sudo python3 teufel-power-hifi-controller.py
```

## IR Protocol Details

- **Protocol**: NEC
- **Address**: 0x5780 (16-bit)
- **Frame Structure**: LSB first, Address_Low | Address_High | Command | ~Command
- **Hardware**: GPIO 12 (Pin 32) for hardware PWM on RPi

## Command Mapping

All IR codes are defined in `teufel-power-hifi-ir-mapping.csv` and implemented in both Arduino and Python versions:

- Power: 0x48
- Mute: 0x28
- Bluetooth: 0x40
- Volume Up/Down: 0xB0/0x30
- Bass/Mid/Treble controls: 0x58/0x41, 0x68/0x42, 0xB8/0x43
- Input selection: AUX (0x44), Line (0x45), Optical (0x3F), USB (0xDF)

## Architecture Notes

### NEC Frame Calculation
The Python implementation uses correct NEC frame structure:
- 16-bit address split into low/high bytes
- LSB-first bit transmission
- Proper byte ordering in 32-bit frame

### Hardware PWM
The Raspberry Pi version uses hardware PWM on GPIO 12 for precise 38kHz carrier generation, which is critical for reliable IR transmission.

## Development Requirements

- **Arduino**: IRremote library 4.x, VS1838B receiver, IR LED
- **Raspberry Pi**: pigpio library, GPIO 12 hardware PWM capability
- **Testing**: IR receiver module for signal verification