#!/bin/bash

# PM2 Setup Script für Teufel Power HiFi Controller
# Automatisches Starten nach Boot

echo "=== PM2 Setup für Teufel Power HiFi Controller ==="

# 1. PM2 startup als Service einrichten
echo "1. PM2 Startup-Service einrichten..."
pm2 startup

echo ""
echo "⚠️  WICHTIG: Führe den oben angezeigten 'sudo env PATH=...' Befehl manuell aus!"
echo ""
read -p "Drücke Enter nachdem du den sudo-Befehl ausgeführt hast..."

# 2. In das Projektverzeichnis wechseln
cd /home/martin/teufel-power-hifi-controller

# 3. PM2 App starten
echo "2. Teufel Controller mit PM2 starten..."
pm2 start ecosystem.config.js

# 4. PM2 Konfiguration speichern
echo "3. PM2 Konfiguration speichern..."
pm2 save

# 5. Status anzeigen
echo "4. PM2 Status:"
pm2 status

echo ""
echo "✅ Setup abgeschlossen!"
echo ""
echo "Nützliche Befehle:"
echo "pm2 status          - Status anzeigen"
echo "pm2 logs            - Logs anzeigen"
echo "pm2 restart all     - Neustart"
echo "pm2 stop all        - Stoppen"
echo "pm2 delete all      - Löschen"
echo ""
echo "Der Service startet jetzt automatisch nach jedem Boot!"