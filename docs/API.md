# API Documentation

## Base URL
```
http://localhost:5002/api
```

## Authentication
Currently, no authentication is required. The API is designed for local network use only.

## Rate Limiting
Volume endpoints implement rate limiting:
- Maximum 20 changes per 10 seconds
- 30-second cooldown period when limit is reached

## Endpoints

### Health Check
Check server status and configuration.

```http
GET /api/health
```

#### Response
```json
{
  "status": "ok",
  "timestamp": 1643836800000,
  "config": {
    "pythonScript": "/path/to/controller.py",
    "port": 5002,
    "rateLimit": {
      "maxChanges": 20,
      "timeWindow": 10000,
      "cooldown": 30000
    }
  },
  "uptime": 3600
}
```

### System Status
Get current system status.

```http
GET /api/status
```

#### Response
```json
{
  "power": true,
  "muted": false,
  "volume": 50,
  "input": "aux",
  "lastCommand": "CMD_POWER",
  "timestamp": 1643836800000
}
```

### Power Control
Toggle power on/off.

```http
POST /api/power
```

#### Request Body
No body required.

#### Response
```json
{
  "success": true,
  "command": "CMD_POWER",
  "state": "on",
  "timestamp": 1643836800000
}
```

### Volume Control
Adjust volume up or down.

```http
POST /api/volume
```

#### Request Body
```json
{
  "action": "up" | "down"
}
```

#### Response
```json
{
  "success": true,
  "command": "CMD_VOL_UP",
  "action": "up",
  "rateLimit": {
    "remaining": 15,
    "resetIn": 8000
  }
}
```

#### Rate Limit Response (when exceeded)
```json
{
  "success": false,
  "error": "Rate limit exceeded",
  "retryAfter": 30000,
  "message": "Too many volume changes. Please wait 30 seconds."
}
```

### Mute Control
Toggle mute on/off.

```http
POST /api/mute
```

#### Request Body
No body required.

#### Response
```json
{
  "success": true,
  "command": "CMD_MUTE",
  "muted": true
}
```

### Input Selection
Select audio input source.

```http
POST /api/input
```

#### Request Body
```json
{
  "source": "aux" | "line" | "optical" | "usb" | "bluetooth"
}
```

#### Response
```json
{
  "success": true,
  "command": "CMD_AUX",
  "input": "aux"
}
```

### EQ Control
Adjust equalizer settings.

```http
POST /api/eq
```

#### Request Body
```json
{
  "type": "bass" | "mid" | "treble",
  "action": "up" | "down"
}
```

#### Response
```json
{
  "success": true,
  "command": "CMD_BASS_UP",
  "type": "bass",
  "action": "up"
}
```

### Balance Control
Adjust left/right balance.

```http
POST /api/balance
```

#### Request Body
```json
{
  "direction": "left" | "right"
}
```

#### Response
```json
{
  "success": true,
  "command": "CMD_BAL_L",
  "direction": "left"
}
```

### Navigation Control
Navigate menu system.

```http
POST /api/navigation
```

#### Request Body
```json
{
  "direction": "left" | "right"
}
```

#### Response
```json
{
  "success": true,
  "command": "CMD_LEFT",
  "direction": "left"
}
```

## Error Responses

### 400 Bad Request
Invalid request parameters.

```json
{
  "success": false,
  "error": "Invalid input source",
  "validSources": ["aux", "line", "optical", "usb", "bluetooth"]
}
```

### 429 Too Many Requests
Rate limit exceeded.

```json
{
  "success": false,
  "error": "Rate limit exceeded",
  "retryAfter": 30000
}
```

### 500 Internal Server Error
Server or hardware error.

```json
{
  "success": false,
  "error": "Failed to execute command",
  "details": "pigpio daemon not running"
}
```

## WebSocket Events (Future)

### Connection
```javascript
const ws = new WebSocket('ws://localhost:5002');
```

### Events
```javascript
// Status update
{
  "type": "status",
  "data": {
    "power": true,
    "volume": 50,
    "input": "aux"
  }
}

// Command executed
{
  "type": "command",
  "data": {
    "command": "CMD_POWER",
    "success": true
  }
}

// Error
{
  "type": "error",
  "data": {
    "message": "Command failed",
    "code": "HARDWARE_ERROR"
  }
}
```

## Command Reference

| Command | Description | API Endpoint |
|---------|-------------|--------------|
| `CMD_POWER` | Toggle power | `POST /api/power` |
| `CMD_MUTE` | Toggle mute | `POST /api/mute` |
| `CMD_VOL_UP` | Volume up | `POST /api/volume` |
| `CMD_VOL_DOWN` | Volume down | `POST /api/volume` |
| `CMD_BASS_UP` | Bass up | `POST /api/eq` |
| `CMD_BASS_DOWN` | Bass down | `POST /api/eq` |
| `CMD_MID_UP` | Midrange up | `POST /api/eq` |
| `CMD_MID_DOWN` | Midrange down | `POST /api/eq` |
| `CMD_TREBLE_UP` | Treble up | `POST /api/eq` |
| `CMD_TREBLE_DOWN` | Treble down | `POST /api/eq` |
| `CMD_AUX` | Select AUX | `POST /api/input` |
| `CMD_LINE` | Select Line | `POST /api/input` |
| `CMD_OPT` | Select Optical | `POST /api/input` |
| `CMD_USB` | Select USB | `POST /api/input` |
| `CMD_BT` | Select Bluetooth | `POST /api/input` |
| `CMD_BAL_L` | Balance left | `POST /api/balance` |
| `CMD_BAL_R` | Balance right | `POST /api/balance` |
| `CMD_LEFT` | Navigate left | `POST /api/navigation` |
| `CMD_RIGHT` | Navigate right | `POST /api/navigation` |

## Usage Examples

### cURL
```bash
# Power on/off
curl -X POST http://localhost:5002/api/power

# Volume up
curl -X POST http://localhost:5002/api/volume \
  -H "Content-Type: application/json" \
  -d '{"action":"up"}'

# Select AUX input
curl -X POST http://localhost:5002/api/input \
  -H "Content-Type: application/json" \
  -d '{"source":"aux"}'
```

### JavaScript (Fetch)
```javascript
// Power toggle
fetch('http://localhost:5002/api/power', { method: 'POST' })
  .then(res => res.json())
  .then(data => console.log(data));

// Volume control
fetch('http://localhost:5002/api/volume', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ action: 'up' })
})
  .then(res => res.json())
  .then(data => console.log(data));
```

### Python (requests)
```python
import requests

# Power toggle
response = requests.post('http://localhost:5002/api/power')
print(response.json())

# Volume control
response = requests.post(
  'http://localhost:5002/api/volume',
  json={'action': 'up'}
)
print(response.json())

# Select input
response = requests.post(
  'http://localhost:5002/api/input',
  json={'source': 'bluetooth'}
)
print(response.json())
```

### Node.js (axios)
```javascript
const axios = require('axios');

// Power toggle
axios.post('http://localhost:5002/api/power')
  .then(res => console.log(res.data));

// Volume control
axios.post('http://localhost:5002/api/volume', { action: 'up' })
  .then(res => console.log(res.data));

// Select input
axios.post('http://localhost:5002/api/input', { source: 'optical' })
  .then(res => console.log(res.data));
```