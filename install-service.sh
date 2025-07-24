#!/bin/bash

# Installation Script für Teufel Power HiFi Controller Service

echo "=== Teufel Power HiFi Controller Service Installation ==="

# 1. Prüfe ob PM2 installiert ist
if ! command -v pm2 &> /dev/null; then
    echo "PM2 wird installiert..."
    npm install pm2 -g
fi

# 2. Prüfe ob pigpio daemon läuft
if ! pgrep -x "pigpiod" > /dev/null; then
    echo "⚠️  pigpiod läuft nicht - starte pigpiod..."
    sudo pigpiod
fi

# 3. Installiere systemd Service
echo "Installiere systemd Service..."
sudo cp teufel-controller.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable teufel-controller.service

# 4. Starte Service
echo "Starte Teufel Controller Service..."
sudo systemctl start teufel-controller.service

# 5. Status anzeigen
echo "Service Status:"
sudo systemctl status teufel-controller.service

echo ""
echo "✅ Installation abgeschlossen!"
echo ""
echo "Service-Befehle:"
echo "sudo systemctl start teufel-controller     - Service starten"
echo "sudo systemctl stop teufel-controller      - Service stoppen"
echo "sudo systemctl restart teufel-controller   - Service neustarten"
echo "sudo systemctl status teufel-controller    - Service Status"
echo "sudo systemctl disable teufel-controller   - Auto-Start deaktivieren"
echo "sudo journalctl -u teufel-controller -f    - Live-Logs anzeigen"
echo ""
echo "Der Service startet automatisch nach jedem Boot!"
echo "Webinterface: http://localhost:5002"