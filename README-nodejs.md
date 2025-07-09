# Teufel Power HiFi Controller - Node.js Web Interface

Modern web-based controller for Teufel Power HiFi systems via Raspberry Pi using IR remote control.

## Features

- **Web Interface**: Modern, responsive dark theme interface
- **Full Remote Control**: Power, volume, input selection, EQ controls
- **Real-time Status**: Live updates of system status
- **PM2 Management**: Process management for reliability
- **Raspberry Pi Integration**: Direct GPIO control for IR transmission

## Installation

1. Install Node.js dependencies:
```bash
npm install
```

2. Ensure the Python script is executable and pigpio is running:
```bash
sudo pigpiod
```

3. Start the server:
```bash
# Development mode
npm run dev

# Production mode with PM2
npm run pm2:start

# Auto-start nach Boot einrichten (Option 1 - PM2)
npm run pm2:setup

# Auto-start nach Boot einrichten (Option 2 - systemd)
./install-service.sh
```

## Auto-Start nach Boot

**Option 1: PM2 Startup (Empfohlen)**
```bash
npm run pm2:setup
```

**Option 2: systemd Service**
```bash
./install-service.sh
```

## Usage

1. Open your browser and go to `http://localhost:5002`
2. Use the web interface to control your Teufel Power HiFi system
3. All controls work via IR signals sent through the Raspberry Pi

## API Endpoints

- `GET /api/health` - Health check and configuration
- `GET /api/status` - Current system status
- `POST /api/power` - Toggle power
- `POST /api/volume` - Volume control
- `POST /api/mute` - Toggle mute
- `POST /api/input` - Select input source
- `POST /api/eq` - EQ adjustments
- `POST /api/balance` - Balance control
- `POST /api/navigation` - Navigation controls

## PM2 Commands

```bash
npm run pm2:start    # Start the service
npm run pm2:stop     # Stop the service
npm run pm2:restart  # Restart the service
npm run pm2:delete   # Delete the service
```

## Requirements

- Node.js 14+
- Raspberry Pi with GPIO access
- pigpio library
- IR LED connected to GPIO 12 (Pin 32)
- Teufel Power HiFi system

## Technical Details

- **Port**: 5002
- **Protocol**: HTTP/JSON API
- **IR Protocol**: NEC (Address: 0x5780)
- **Hardware**: Hardware PWM on GPIO 12 for precise IR timing

## Files

- `server.js` - Main Express server
- `public/index.html` - Web interface
- `ecosystem.config.js` - PM2 configuration
- `teufel-power-hifi-controller.py` - Python IR controller script