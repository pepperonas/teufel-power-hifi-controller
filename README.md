# Teufel Power HiFi Controller

<div align="center">

![License](https://img.shields.io/badge/License-MIT-blue.svg)
![Version](https://img.shields.io/badge/version-1.0.0-orange.svg)
![Node.js](https://img.shields.io/badge/Node.js-18+-339933.svg?logo=nodedotjs&logoColor=white)
![Platform](https://img.shields.io/badge/Platform-Raspberry%20Pi-C51A4A.svg?logo=raspberrypi&logoColor=white)
![Hardware PWM](https://img.shields.io/badge/Hardware_PWM-GPIO_12-purple.svg)
![Express](https://img.shields.io/badge/Express-4.x-000000.svg?logo=express&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.9+-3776AB.svg?logo=python&logoColor=white)

![IR Protocol](https://img.shields.io/badge/IR_Protocol-NEC-red.svg)
![Frequency](https://img.shields.io/badge/Carrier-38kHz-brightgreen.svg)
![Code Quality](https://img.shields.io/badge/code_style-standard-brightgreen.svg)
![Maintenance](https://img.shields.io/badge/Maintained%3F-yes-green.svg)
![GitHub Issues](https://img.shields.io/github/issues/pepperonas/teufel-power-hifi-controller.svg)
![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)

![pigpio](https://img.shields.io/badge/pigpio-hardware_PWM-FF6600.svg)
![PM2](https://img.shields.io/badge/PM2-production_ready-2B037A?logo=pm2&logoColor=white)
![REST API](https://img.shields.io/badge/REST_API-5_endpoints-blue.svg)
![Mobile Ready](https://img.shields.io/badge/mobile-responsive-purple?logo=smartphone&logoColor=white)
![Lines of Code](https://img.shields.io/badge/LOC-1.5k+-informational)

Web-based IR remote controller for Teufel Power HiFi systems via Raspberry Pi, featuring power, volume, and mute control through a modern web interface.

<br>

<a href="https://www.paypal.com/donate/?business=martinpaush@gmail.com&currency_code=EUR">
  <img src="https://img.shields.io/badge/Sponsor_this_project-PayPal-00457C?style=for-the-badge&logo=paypal&logoColor=white" alt="Donate via PayPal">
</a>

</div>

## Features

- **IR Remote Control** — Send infrared commands to Teufel Power HiFi system
- **Web Dashboard** — Control power, volume, and mute from any device on the network
- **REST API** — Programmatic access for home automation integration
- **Responsive UI** — Mobile-friendly interface for quick access
- **Reverse Engineered** — Custom NEC protocol analysis for full system control

## Wiring Diagram

```
    Raspberry Pi                         IR Transmitter Circuit
    ┌──────────────┐
    │              │                     ┌──[47Ω]──[IR LED]──┐
    │   3.3V  (1) ─┼─────────────────────┘                    │ C
    │              │                                       ┌──┴──┐
    │  GPIO12(32) ─┼──────────[1kΩ]─────────────────── B ──┤ NPN │
    │   (HW PWM)   │                                       └──┬──┘
    │              │                                          │ E
    │   GND  (34) ─┼──────────────────────────────────────────┘
    │              │
    └──────────────┘

    NEC Protocol · 38kHz carrier · 33% duty cycle
    Library: pigpio (hardware PWM for precise carrier timing)

    ┌──────────┬──────────┬──────────────────────────────────┐
    │ Pi Pin   │ GPIO     │ Connection                       │
    ├──────────┼──────────┼──────────────────────────────────┤
    │ Pin 1    │ 3.3V     │ IR LED anode (via 47Ω resistor)  │
    │ Pin 32   │ GPIO 12  │ NPN base (via 1kΩ resistor)      │
    │ Pin 34   │ GND      │ NPN emitter                      │
    └──────────┴──────────┴──────────────────────────────────┘
```

> **Note:** GPIO 12 is required because it supports hardware PWM for the precise 38kHz IR carrier frequency. The NPN transistor amplifies the signal for sufficient IR range.

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
