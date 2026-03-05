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

## Contributing

1. Test changes thoroughly with actual hardware
2. Update documentation when adding features
3. Follow existing code structure
4. Test all API endpoints after changes
5. Verify IR transmission with oscilloscope if available