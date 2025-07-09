# Teufel Power HiFi Controller - Node.js Web-Interface

🔊 Moderne Web-basierte Fernbedienung für Teufel Power HiFi Systeme via Raspberry Pi mit Infrarot-Steuerung.

## Features

- **Web-Interface**: Moderne, responsive Dark Theme Benutzeroberfläche
- **Vollständige Fernbedienung**: Power, Lautstärke, Eingangswahl, EQ-Regler
- **Echtzeit-Status**: Live-Updates des Systemstatus
- **PM2-Verwaltung**: Prozess-Management für Zuverlässigkeit
- **Raspberry Pi Integration**: Direkte GPIO-Steuerung für IR-Übertragung
- **Lautstärke-Rate-Limiting**: Intelligente Begrenzung von Lautstärke-Änderungen

## Installation

1. Node.js Abhängigkeiten installieren:
```bash
npm install
```

2. Python-Script ausführbar machen und pigpio starten:
```bash
sudo pigpiod
```

3. Server starten:
```bash
# Entwicklungsmodus
npm run dev

# Produktionsmodus mit PM2
npm run pm2:start

# Auto-Start nach Boot einrichten (Option 1 - PM2)
npm run pm2:setup

# Auto-Start nach Boot einrichten (Option 2 - systemd)
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

## Verwendung

1. Browser öffnen und zu `http://localhost:5002` navigieren
2. Web-Interface zur Steuerung des Teufel Power HiFi Systems verwenden
3. Alle Steuerungen funktionieren über IR-Signale, die über den Raspberry Pi gesendet werden

## API-Endpunkte

- `GET /api/health` - Gesundheitscheck und Konfiguration
- `GET /api/status` - Aktueller Systemstatus
- `POST /api/power` - Power Ein/Aus
- `POST /api/volume` - Lautstärke-Steuerung
- `POST /api/mute` - Stumm Ein/Aus
- `POST /api/input` - Eingangsquelle auswählen
- `POST /api/eq` - EQ-Anpassungen
- `POST /api/balance` - Balance-Steuerung
- `POST /api/navigation` - Navigations-Steuerung

## PM2-Befehle

```bash
npm run pm2:start    # Service starten
npm run pm2:stop     # Service stoppen
npm run pm2:restart  # Service neu starten
npm run pm2:delete   # Service löschen
```

## Anforderungen

- Node.js 14+
- Raspberry Pi mit GPIO-Zugriff
- pigpio Library
- IR-LED angeschlossen an GPIO 12 (Pin 32)
- Teufel Power HiFi System

## Technische Details

- **Port**: 5002
- **Protokoll**: HTTP/JSON API
- **IR-Protokoll**: NEC (Adresse: 0x5780)
- **Hardware**: Hardware PWM auf GPIO 12 für präzises IR-Timing
- **Rate-Limiting**: Max. 20 Lautstärke-Schritte in 10s, dann 30s Cooldown

## Dateien

- `server.js` - Haupt-Express-Server
- `public/index.html` - Web-Interface
- `ecosystem.config.js` - PM2-Konfiguration
- `teufel-power-hifi-controller.py` - Python IR-Controller-Script