# Hardware Documentation

## Required Components

### Raspberry Pi Setup
- **Board**: Raspberry Pi 3/4/5 or Zero W
- **OS**: Raspbian Bullseye or newer
- **GPIO**: Access to GPIO 12 (Pin 32) for hardware PWM

### IR Transmitter Components
| Component | Specification | Quantity | Purpose |
|-----------|--------------|----------|---------|
| IR LED | 940nm wavelength | 1 | Infrared transmission |
| NPN Transistor | 2N2222, BC547, or similar | 1 | Signal amplification |
| Resistor | 47Ω ±5% | 1 | LED current limiting |
| Resistor | 1kΩ ±5% | 1 | Transistor base current |
| Jumper Wires | Male-to-Female | 4 | Connections |
| Breadboard | Any size | 1 | Prototyping (optional) |

### Arduino Setup (for reverse engineering)
| Component | Specification | Quantity | Purpose |
|-----------|--------------|----------|---------|
| Arduino | Uno, Nano, or Mega | 1 | Microcontroller |
| VS1838B | IR Receiver Module | 1 | Signal reception |
| IR LED | 940nm | 1 | Signal transmission |
| Resistor | 100Ω (optional) | 1 | Current limiting |
| Jumper Wires | Male-to-Male | 6 | Connections |

## Circuit Diagrams

### Raspberry Pi IR Transmitter Circuit

```
                         Raspberry Pi GPIO Header
    ┌────────────────────────────────────────────────────┐
    │                                                    │
    │  Pin 1 (3.3V) ●─────────────────────┐            │
    │                                      │            │
    │                                     47Ω           │
    │                                      │            │
    │                                      ▼            │
    │                                   IR LED          │
    │                                    (+)            │
    │                                     │             │
    │                                     │             │
    │                                     ▼ C           │
    │                                  ┌──┴──┐         │
    │  Pin 32 (GPIO12) ●────[1kΩ]────▶│ NPN │         │
    │                                  └──┬──┘         │
    │                                     │ E          │
    │                                     │            │
    │  Pin 34 (GND) ●─────────────────────┘            │
    │                                                   │
    └───────────────────────────────────────────────────┘

    NPN Transistor Pinout (2N2222):
         C
         │
      ┌──┴──┐
    B─┤     ├─E
      └─────┘
```

### Detailed Connection Table

| From | To | Wire Color (suggested) |
|------|-----|------------------------|
| Pi Pin 1 (3.3V) | 47Ω Resistor | Red |
| 47Ω Resistor | IR LED Anode (+) | Red |
| IR LED Cathode (-) | Transistor Collector | Black |
| Pi Pin 32 (GPIO12) | 1kΩ Resistor | Yellow |
| 1kΩ Resistor | Transistor Base | Yellow |
| Transistor Emitter | Pi Pin 34 (GND) | Black |

### Arduino IR Receiver Circuit

```
    VS1838B IR Receiver              Arduino
    ┌─────────────────┐             
    │                 │             
    │ OUT  GND  VCC   │             
    │  1    2    3    │             
    └──┼────┼────┼────┘             
       │    │    │                  
       │    │    └────────●  5V (Power)
       │    │                       
       │    └─────────────●  GND (Ground)
       │                           
       └──────────────────●  Pin D2 (Data)
```

### Arduino IR Transmitter Circuit

```
    Arduino                   IR LED
                              
    Pin D3 ●─────────────────▶ Anode (+)
                              
    GND    ●─────────────────▶ Cathode (-)
```

## Pin Mappings

### Raspberry Pi 40-Pin Header

```
           3.3V ● ● 5V        ← Power Rails
         GPIO2 ● ● 5V
         GPIO3 ● ● GND
         GPIO4 ● ● GPIO14
           GND ● ● GPIO15
        GPIO17 ● ● GPIO18
        GPIO27 ● ● GND
        GPIO22 ● ● GPIO23
          3.3V ● ● GPIO24
        GPIO10 ● ● GND
         GPIO9 ● ● GPIO25
        GPIO11 ● ● GPIO8
           GND ● ● GPIO7
         GPIO0 ● ● GPIO1
         GPIO5 ● ● GND
         GPIO6 ● ● GPIO12    ← Pin 32 (PWM)
        GPIO13 ● ● GND       ← Pin 34
        GPIO19 ● ● GPIO16
        GPIO26 ● ● GPIO20
           GND ● ● GPIO21
```

### Important GPIO Notes

#### Why GPIO 12?
GPIO 12 supports hardware PWM (PWM0), which is essential for generating the precise 38kHz carrier frequency required by the NEC protocol. Software PWM would introduce timing jitter that could cause unreliable IR transmission.

#### Alternative PWM Pins
If GPIO 12 is unavailable, you can use:
- GPIO 18 (Pin 12) - PWM0
- GPIO 13 (Pin 33) - PWM1
- GPIO 19 (Pin 35) - PWM1

Note: Requires code modification to change the pin number.

## Component Specifications

### IR LED Details
- **Wavelength**: 940nm (invisible to human eye)
- **Forward Voltage**: 1.2-1.4V typical
- **Forward Current**: 20mA typical, 100mA peak
- **Viewing Angle**: 20-40° typical
- **Power Dissipation**: 100mW max

### Transistor Selection
Any general-purpose NPN transistor will work:
- **2N2222**: 600mA collector current, 40V
- **BC547**: 100mA collector current, 45V
- **2N3904**: 200mA collector current, 40V
- **BC337**: 800mA collector current, 45V

### VS1838B IR Receiver
- **Carrier Frequency**: 38kHz
- **Supply Voltage**: 2.7-5.5V
- **Reception Distance**: 18m typical
- **Reception Angle**: ±45°
- **Output**: Active low, TTL level

## Testing & Troubleshooting

### LED Testing
1. **Visual Test**: IR LEDs are invisible to the naked eye
2. **Camera Test**: Use smartphone camera to see purple glow
3. **Multimeter Test**: Check forward voltage drop (1.2-1.4V)

### Circuit Verification
```bash
# Test GPIO access
gpio -v
gpio readall

# Test PWM functionality
gpio -g mode 12 pwm
gpio -g pwm 12 512

# Check with Python
python3 -c "import RPi.GPIO as GPIO; GPIO.setmode(GPIO.BCM); print('GPIO OK')"
```

### Common Issues

#### No IR Signal
- Check LED polarity (long leg = positive)
- Verify transistor orientation
- Measure voltages with multimeter
- Test with phone camera for IR emission

#### Weak Signal
- Reduce distance to target (test at 10-20cm)
- Check resistor values
- Ensure good connections
- Consider adding lens for focusing

#### Intermittent Operation
- Check for loose connections
- Verify power supply stability
- Ensure proper grounding
- Add capacitor (100nF) across power rails

## Range Optimization

### Factors Affecting Range
1. **LED Power**: Higher current = longer range
2. **Lens/Reflector**: Focuses IR beam
3. **Alignment**: Direct line of sight
4. **Ambient Light**: Minimize interference

### Improving Range
```
Standard Circuit: ~2-3 meters
With Lens: ~5-7 meters
Multiple LEDs: ~5-10 meters
High-Power LED + Driver: ~10-15 meters
```

### Multiple LED Configuration
```
    3.3V ●────┬────[47Ω]────LED1────┐
              │                      │
              ├────[47Ω]────LED2────┤
              │                      │
              └────[47Ω]────LED3────┤
                                     │
                                     ▼ C
                                  ┌──┴──┐
    GPIO12 ●────[1kΩ]──────────▶│ NPN │
                                  └──┬──┘
                                     │ E
                                     │
    GND ●────────────────────────────┘
```

## Power Calculations

### Single LED Circuit
```
LED Current = (VCC - VF - VCE_sat) / R
            = (3.3V - 1.3V - 0.2V) / 47Ω
            = 38mA

Power Dissipation:
- LED: 1.3V × 38mA = 49mW
- Resistor: 1.8V × 38mA = 68mW
- Transistor: 0.2V × 38mA = 8mW
```

### Safety Margins
- LED rated for 100mA peak (38mA is safe)
- 47Ω resistor should be 1/4W rated minimum
- Transistor barely warm (8mW << 500mW max)

## Bill of Materials (BOM)

### Basic Setup (~$5)
| Item | Quantity | Unit Price | Total |
|------|----------|------------|--------|
| IR LED 940nm | 1 | $0.50 | $0.50 |
| 2N2222 Transistor | 1 | $0.30 | $0.30 |
| 47Ω Resistor | 1 | $0.10 | $0.10 |
| 1kΩ Resistor | 1 | $0.10 | $0.10 |
| Jumper Wires | 4 | $0.25 | $1.00 |
| **Total** | | | **$2.00** |

### Professional Setup (~$20)
| Item | Quantity | Unit Price | Total |
|------|----------|------------|--------|
| High-Power IR LED | 3 | $1.00 | $3.00 |
| MOSFET Driver | 1 | $2.00 | $2.00 |
| PCB | 1 | $5.00 | $5.00 |
| Enclosure | 1 | $5.00 | $5.00 |
| Connectors | 1 set | $3.00 | $3.00 |
| **Total** | | | **$18.00** |

## PCB Design Considerations

### Layout Guidelines
1. Keep traces short for high-frequency signals
2. Use ground plane for better performance
3. Place bypass capacitors close to power pins
4. Consider thermal relief for power components

### Suggested PCB Size
- Minimum: 30mm × 20mm
- Recommended: 40mm × 30mm
- With mounting holes: 50mm × 40mm