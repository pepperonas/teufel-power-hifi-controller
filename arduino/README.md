# Arduino IR Tools

This directory contains Arduino sketches for reverse engineering and testing the Teufel Power HiFi IR remote control protocol.

## Available Sketches

### 1. IR Receiver (`teufel-power-hifi-ir-rx.ino`)
Captures and decodes IR signals from the original Teufel remote control.

**Usage:**
1. Upload sketch to Arduino
2. Open Serial Monitor (9600 baud)
3. Point original remote at VS1838B sensor
4. Press buttons to see decoded values

**Output Format:**
```
Protocol | Address | Command | Function
NEC      | 0x5780  | 0x48    | Power
NEC      | 0x5780  | 0x28    | Mute
```

### 2. IR Transmitter (`teufel-power-hifi-ir-tx.ino`)
Sends IR commands to control the Teufel Power HiFi system.

**Serial Commands:**
```
p = Power toggle
m = Mute toggle
+ = Volume up
- = Volume down
b/B = Bass down/up
n/M = Midrange down/up  
t/T = Treble down/up
1 = AUX input
2 = Line input
3 = Optical input
4 = USB input
l = Bluetooth input
< = Balance left
> = Balance right
a = Navigate left
d = Navigate right
```

### 3. IR Transceiver (`teufel-power-hifi-ir-rx-ts.ino`)
Combined transmitter and receiver for testing and verification.

**Operating Modes:**
- `t` = Test mode (sends signal and verifies reception)
- `r` = Read only mode (passive IR monitoring)
- `A` = Auto-test all commands sequentially

## Hardware Requirements

### Components
- Arduino Uno/Nano/Mega
- VS1838B IR Receiver Module
- 940nm IR LED
- Jumper wires
- Optional: 100Ω resistor for LED current limiting

### Wiring

#### IR Receiver (VS1838B)
```
VS1838B Pin    Arduino Pin
-----------    -----------
OUT (1)        D2
GND (2)        GND
VCC (3)        5V
```

#### IR Transmitter (LED)
```
Arduino Pin    Component
-----------    ---------
D3             IR LED Anode (+)
GND            IR LED Cathode (-)
```

## Software Requirements

### Arduino IDE Setup
1. Install Arduino IDE (1.8.x or 2.x)
2. Install IRremote library:
   - Open Library Manager: `Tools → Manage Libraries`
   - Search for "IRremote"
   - Install version 4.x or later

### Library Configuration
The sketches use IRremote library v4.x with the following settings:
- Protocol: NEC
- Carrier: 38kHz
- Address: 0x5780

## Command Mapping

The complete IR command mapping is available in `teufel-power-hifi-ir-mapping.csv`:

```csv
0x48;Power
0x40;Bluetooth
0x28;Mute
0xB0;Vol_Up
0x30;Vol_Down
0x78;Left
0xF8;Right
0x58;Bass_Up
0x41;Bass_Down
0x68;Mid_Up
0x42;Mid_Down
0xB8;Treble_Up
0x43;Treble_Down
0x44;Aux
0x45;Line
0x3F;Opt
0xDF;USB
0xBF;Bal_Left
0x5F;Bal_Right
```

## Protocol Details

### NEC Protocol Specification
- **Carrier Frequency**: 38kHz
- **Duty Cycle**: 33%
- **Address**: 0x5780 (16-bit)
- **Data Format**: 32-bit (Address_Low, Address_High, Command, ~Command)
- **Timing**:
  - Leader: 9ms pulse + 4.5ms space
  - Bit 0: 562.5µs pulse + 562.5µs space  
  - Bit 1: 562.5µs pulse + 1687.5µs space
  - Stop bit: 562.5µs pulse

### Frame Structure
```
[Leader][Addr_L][Addr_H][Command][~Command][Stop]
  13.5ms   8bit    8bit     8bit      8bit   562µs
```

## Troubleshooting

### Common Issues

#### No IR codes received
- Check VS1838B connections
- Verify 5V power to receiver
- Test with TV remote first
- Remove fluorescent light interference

#### LED not transmitting
- Verify LED polarity (long leg = positive)
- Check with phone camera (should see purple glow)
- Test LED with multimeter (1.2-1.4V drop)
- Try different Arduino pin if D3 fails

#### Weak transmission range
- Add transistor amplifier circuit
- Use multiple IR LEDs in parallel
- Reduce ambient light interference
- Ensure direct line of sight

### Debug Mode
Enable debug output by uncommenting:
```cpp
#define DEBUG 1
```

This will show detailed protocol information in Serial Monitor.

## Usage Examples

### Basic Testing
```cpp
// Send power command
irsend.sendNEC(0x57800048, 32);

// Send with repeats
irsend.sendNEC(0x578000B0, 32, 3); // Volume up x3
```

### Custom Integration
```cpp
// Define commands
const uint32_t CMD_POWER = 0x57800048;
const uint32_t CMD_MUTE  = 0x57800028;

// Send command function
void sendCommand(uint32_t cmd) {
    irsend.sendNEC(cmd, 32);
    delay(100);
}
```

## Contributing

To add new commands or improve the sketches:

1. Use the receiver sketch to capture new codes
2. Add them to the mapping CSV file
3. Update the transmitter sketch with new commands
4. Test with the transceiver sketch
5. Submit a pull request with your changes

## License

These Arduino sketches are part of the Teufel Power HiFi Controller project and are licensed under the MIT License.