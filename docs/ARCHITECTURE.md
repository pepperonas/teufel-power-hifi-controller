# Architecture Documentation

## System Overview

The Teufel Power HiFi Controller is a multi-layered system that provides infrared remote control through various interfaces:

```
┌─────────────────────────────────────────────────────────────┐
│                         User Interfaces                      │
├─────────────┬──────────────┬──────────────┬────────────────┤
│  Web UI     │   REST API   │   CLI        │   Arduino      │
│  (Browser)  │   (HTTP)     │   (Python)   │   (Serial)     │
├─────────────┴──────────────┴──────────────┴────────────────┤
│                      Control Layer                          │
├─────────────────────────────────────────────────────────────┤
│   Node.js   │            Python Controller                  │
│   Server    │         (teufel-power-hifi-controller.py)    │
├─────────────┴────────────────────────────────────────────────┤
│                    Hardware Abstraction                      │
├─────────────────────────────────────────────────────────────┤
│            pigpio Library (Hardware PWM)                     │
├─────────────────────────────────────────────────────────────┤
│                    Physical Layer                            │
├─────────────────────────────────────────────────────────────┤
│   GPIO 12   →   IR LED   →   Teufel Power HiFi System      │
└─────────────────────────────────────────────────────────────┘
```

## Component Details

### 1. Web Interface (`public/`)
- **Technology**: Vanilla JavaScript, HTML5, CSS3
- **Features**: Dark theme, responsive design, real-time updates
- **Communication**: REST API via fetch()

### 2. Node.js Server (`server.js`)
- **Framework**: Express.js
- **Port**: 5002
- **Features**: 
  - REST API endpoints
  - Static file serving
  - Rate limiting for volume control
  - Process spawning for Python scripts

### 3. Python Controller (`teufel-power-hifi-controller.py`)
- **Purpose**: Hardware-level IR signal generation
- **Library**: pigpio for precise timing
- **Modes**:
  - CLI with arguments
  - Interactive mode
  - Single command execution

### 4. Arduino Tools (`arduino/`)
- **Purpose**: Reverse engineering and testing
- **Components**:
  - IR receiver for scanning codes
  - IR transmitter for sending codes
  - Combined transceiver for testing

## Data Flow

### Web UI → HiFi System
```
1. User clicks button in browser
2. JavaScript sends POST to /api/[endpoint]
3. Express server validates request
4. Server spawns Python process with command
5. Python generates NEC IR protocol frames
6. pigpio sends PWM signals to GPIO 12
7. IR LED transmits to HiFi system
```

### CLI → HiFi System
```
1. User runs: python3 controller.py --command CMD_POWER
2. Python directly generates IR signals
3. pigpio handles hardware PWM
4. IR LED transmits to HiFi system
```

## IR Protocol Implementation

### NEC Protocol Structure
```
[9ms pulse][4.5ms space][Address Low][Address High][Command][~Command][stop bit]
```

### Frame Calculation (Python)
```python
def calculate_nec_frame(address, command):
    addr_low = address & 0xFF
    addr_high = (address >> 8) & 0xFF
    frame = (addr_low << 24) | (addr_high << 16) | (command << 8) | (~command & 0xFF)
    return frame
```

## Rate Limiting Strategy

Volume control implements intelligent rate limiting to prevent damage:

```javascript
// Configuration
const RATE_LIMIT = {
    maxChanges: 20,      // Maximum volume changes
    timeWindow: 10000,   // Within 10 seconds
    cooldown: 30000      // 30 second cooldown period
}

// Implementation
1. Track volume changes with timestamps
2. Count changes within time window
3. Enforce cooldown when limit reached
4. Auto-reset after cooldown period
```

## Process Management

### PM2 Configuration
```javascript
module.exports = {
    apps: [{
        name: 'teufel-controller',
        script: 'server.js',
        instances: 1,
        autorestart: true,
        watch: false,
        max_memory_restart: '100M'
    }]
}
```

### Systemd Service
```ini
[Service]
Type=simple
ExecStart=/usr/bin/node /path/to/server.js
Restart=always
User=pi
Environment=NODE_ENV=production
```

## Security Considerations

1. **GPIO Access**: Requires appropriate permissions
2. **Rate Limiting**: Prevents abuse and hardware damage
3. **Input Validation**: All API inputs are validated
4. **Error Handling**: Graceful degradation on failures

## Performance Optimizations

1. **Hardware PWM**: Uses GPIO 12 for precise 38kHz carrier
2. **Process Caching**: Reuses Python processes where possible
3. **Static Asset Caching**: Browser caching for UI resources
4. **Efficient Protocol**: Minimal overhead in IR transmission

## Debugging

### Enable Debug Mode
```bash
# Node.js server
DEBUG=* node server.js

# Python controller
DEBUG=1 python3 teufel-power-hifi-controller.py --command CMD_POWER
```

### Common Debug Points
1. Check pigpio daemon: `sudo pigpiod`
2. Verify GPIO permissions: `ls -l /dev/gpio*`
3. Test Python script directly
4. Monitor server logs: `pm2 logs`
5. Check IR LED with phone camera