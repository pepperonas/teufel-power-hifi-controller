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
- **Reverse Engineered** — Custom IR protocol analysis for full system control

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
- **Hardware** — IR LED transmitter, LIRC
- **Process Manager** — PM2

## Author

**Martin Pfeffer** — [celox.io](https://celox.io)

## License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
