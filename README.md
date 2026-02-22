# Teufel Power HiFi Controller

<div align="center">

![License](https://img.shields.io/badge/License-MIT-blue.svg)
![Node.js](https://img.shields.io/badge/Node.js-18+-339933.svg?logo=nodedotjs&logoColor=white)
![Platform](https://img.shields.io/badge/Platform-Raspberry%20Pi-C51A4A.svg?logo=raspberrypi&logoColor=white)

Web-based IR remote controller for Teufel Power HiFi systems via Raspberry Pi, featuring power, volume, and mute control through a modern web interface.

</div>

## Features

- **IR Remote Control** — Send infrared commands to Teufel Power HiFi system
- **Web Dashboard** — Control power, volume, and mute from any device on the network
- **REST API** — Programmatic access for home automation integration
- **Responsive UI** — Mobile-friendly interface for quick access
- **Reverse Engineered** — Custom NEC protocol analysis for full system control

## Wiring Diagram

```
    Raspberry Pi                     IR LED Circuit
    ┌──────────────┐                 ┌─────────────────────┐
    │              │                 │                     │
    │   GPIO 12 ●──┼───────┐        │   ┌───►│──┐        │
    │   (Pin 32)   │       │        │   │  IR LED │        │
    │   HW PWM     │       │        │   │        │        │
    │              │    ┌───┴───┐    │   │   R    │        │
    │              │    │  NPN  │    │   │  (47Ω) │        │
    │              │    │  BCE  │────┼───┘        │        │
    │              │    └───┬───┘    │            │        │
    │      GND ●───┼────────┘       │            │        │
    │   (Pin 34)   │                │      GND ──┘        │
    │              │                │                     │
    │      3.3V ●──┼────────────────┤──► VCC               │
    │   (Pin 1)    │                │                     │
    └──────────────┘                └─────────────────────┘

    Pin Mapping:
    ┌──────────┬──────────┬─────────────────────────────────┐
    │ Pi Pin   │ GPIO     │ Connection                      │
    ├──────────┼──────────┼─────────────────────────────────┤
    │ Pin 32   │ GPIO 12  │ IR LED (via NPN, Hardware PWM)  │
    │ Pin 34   │ GND      │ Common ground                   │
    └──────────┴──────────┴─────────────────────────────────┘

    IR Protocol: NEC, 38kHz carrier, 33% duty cycle
    Library: pigpio (hardware PWM for precise timing)
```

> **Note:** GPIO 12 is used because it supports hardware PWM, which is required for the precise 38kHz IR carrier frequency. Uses pigpio daemon for GPIO access.

## Quick Start

```bash
# Clone the repository
git clone https://github.com/pepperonas/teufel-power-hifi-controller.git
cd teufel-power-hifi-controller

# Install dependencies
npm install

# Start the server
npm start
```

## API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | Health check |
| `/api/status` | GET | Current device status |
| `/api/power` | POST | Toggle power on/off |
| `/api/volume` | POST | Adjust volume (`{ "action": "up" \| "down" }`) |
| `/api/mute` | POST | Toggle mute |

## Tech Stack

- **Backend** — Node.js, Express
- **Frontend** — HTML5, CSS3, JavaScript
- **Hardware** — IR LED, NPN transistor, pigpio
- **Process Manager** — PM2

## Author

**Martin Pfeffer** — [celox.io](https://celox.io)

## License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
