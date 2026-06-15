#!/usr/bin/env python3
"""
Teufel Power HiFi IR Remote Control für Raspberry Pi
Hardware: IR LED an GPIO 12 (Pin 32) - Hardware PWM!
Protokoll: NEC
Adresse: 0x5780
"""

import pigpio
import time
import sys
import os
import argparse

# Setze Prozesspriorität auf Maximum
try:
    os.nice(-20)
except:
    print("Hinweis: Für beste Performance als root ausführen (sudo)")

# GPIO Pin (Hardware PWM!)
IR_PIN = 12

# Teufel Power HiFi IR-Codes (NEC Protocol)
TEUFEL_ADDR = 0x5780

# Befehle
COMMANDS = {
    # Basis-Funktionen
    'CMD_POWER': 0x48,
    'CMD_BLUETOOTH': 0x40,
    'CMD_MUTE': 0x28,
    
    # Lautstärke
    'CMD_VOLUME_UP': 0xB0,
    'CMD_VOLUME_DOWN': 0x30,
    
    # Navigation
    'CMD_LEFT': 0x78,
    'CMD_RIGHT': 0xF8,
    
    # Sound Einstellungen
    'CMD_BASS_UP': 0x58,
    'CMD_BASS_DOWN': 0x41,
    'CMD_MID_UP': 0x68,
    'CMD_MID_DOWN': 0x42,
    'CMD_TREBLE_UP': 0xB8,
    'CMD_TREBLE_DOWN': 0x43,
    
    # Eingänge
    'CMD_AUX': 0x44,
    'CMD_LINE': 0x45,
    'CMD_OPT': 0x3F,
    'CMD_USB': 0xDF,
    
    # Balance
    'CMD_BAL_LEFT': 0xBF,
    'CMD_BAL_RIGHT': 0x5F
}

class TeufelIRRemote:
    def __init__(self):
        # Starte pigpio mit maximaler Performance
        self.pi = pigpio.pi()
        if not self.pi.connected:
            raise Exception("pigpio daemon nicht gestartet! Starte mit: sudo pigpiod")
        
        # Setze GPIO Mode
        self.pi.set_mode(IR_PIN, pigpio.OUTPUT)
        self.pi.write(IR_PIN, 0)
        
        # NEC Timing in Mikrosekunden
        self.NEC_HDR_MARK = 9000
        self.NEC_HDR_SPACE = 4500
        self.NEC_BIT_MARK = 560
        self.NEC_ONE_SPACE = 1690
        self.NEC_ZERO_SPACE = 560
        
        # Carrier Frequenz
        self.FREQ = 38000
        self.period = 1000000 // self.FREQ  # ~26 µs
        
    def __del__(self):
        if hasattr(self, 'pi'):
            self.pi.set_mode(IR_PIN, pigpio.INPUT)
            self.pi.stop()
    
    def send_carrier(self, duration_us):
        """Sendet 38kHz Carrier für duration_us Mikrosekunden"""
        # Hardware PWM für perfektes Timing
        self.pi.hardware_PWM(IR_PIN, self.FREQ, 333333)  # 33% duty cycle
        time.sleep(duration_us / 1000000.0)
        self.pi.hardware_PWM(IR_PIN, 0, 0)  # PWM aus
    
    def send_space(self, duration_us):
        """Pause für duration_us Mikrosekunden"""
        time.sleep(duration_us / 1000000.0)
    
    def send_nec(self, address, command):
        """Sendet NEC IR-Signal mit Hardware PWM"""
        # Berechne NEC Frame für 16-bit Adresse
        # LSB first: Address_Low, Address_High, Command, ~Command
        addr_low = address & 0xFF
        addr_high = (address >> 8) & 0xFF
        frame = addr_low | (addr_high << 8) | (command << 16) | ((~command & 0xFF) << 24)
        
        # Header
        self.send_carrier(self.NEC_HDR_MARK)
        self.send_space(self.NEC_HDR_SPACE)
        
        # 32 Bits senden (LSB first)
        for i in range(32):
            self.send_carrier(self.NEC_BIT_MARK)
            if frame & (1 << i):
                self.send_space(self.NEC_ONE_SPACE)
            else:
                self.send_space(self.NEC_ZERO_SPACE)
        
        # Stop bit
        self.send_carrier(self.NEC_BIT_MARK)
        self.send_space(100000)  # 100ms Pause
    
    def send_nec_wave(self, address, command):
        """Alternative: Sendet NEC mit pigpio wave (noch präziser)"""
        self.pi.wave_clear()
        
        # Berechne Pulslängen
        carrier_pulses = []
        
        # Helper: Füge Carrier-Burst hinzu
        def add_carrier(duration_us):
            cycles = int(duration_us * self.FREQ / 1000000)
            on_time = int(self.period * 0.33)  # 33% duty
            off_time = self.period - on_time
            
            for _ in range(cycles):
                carrier_pulses.append(pigpio.pulse(1<<IR_PIN, 0, on_time))
                carrier_pulses.append(pigpio.pulse(0, 1<<IR_PIN, off_time))
        
        # Helper: Füge Space hinzu
        def add_space(duration_us):
            carrier_pulses.append(pigpio.pulse(0, 1<<IR_PIN, duration_us))
        
        # Header
        add_carrier(self.NEC_HDR_MARK)
        add_space(self.NEC_HDR_SPACE)
        
        # Frame berechnen für 16-bit Adresse
        # LSB first: Address_Low, Address_High, Command, ~Command
        addr_low = address & 0xFF
        addr_high = (address >> 8) & 0xFF
        frame = addr_low | (addr_high << 8) | (command << 16) | ((~command & 0xFF) << 24)
        
        # 32 Bits (LSB first)
        for i in range(32):
            add_carrier(self.NEC_BIT_MARK)
            if frame & (1 << i):
                add_space(self.NEC_ONE_SPACE)
            else:
                add_space(self.NEC_ZERO_SPACE)
        
        # Stop bit
        add_carrier(self.NEC_BIT_MARK)
        
        # Wave erstellen und senden
        self.pi.wave_add_generic(carrier_pulses)
        wave_id = self.pi.wave_create()
        
        if wave_id >= 0:
            self.pi.wave_send_once(wave_id)
            while self.pi.wave_tx_busy():
                time.sleep(0.001)
            self.pi.wave_delete(wave_id)
        else:
            print(f"Wave Fehler: {wave_id}")
    
    def send_command(self, cmd_name, use_wave=True):
        """Sendet Befehl (Wave-Methode ist präziser)"""
        if cmd_name not in COMMANDS:
            print(f"Unbekannter Befehl: {cmd_name}")
            return
        
        command = COMMANDS[cmd_name]
        print(f"Sende: {cmd_name} (0x{command:02X}) an GPIO {IR_PIN}")
        
        # Test GPIO vor dem Senden
        print(f"GPIO {IR_PIN} Mode: {self.pi.get_mode(IR_PIN)}")
        
        if use_wave:
            self.send_nec_wave(TEUFEL_ADDR, command)
        else:
            self.send_nec(TEUFEL_ADDR, command)
        
        print(f"IR Signal gesendet!")
    
    def send_repeating(self, cmd_name, repeats=3, delay=0.05):
        """Sendet Befehl mehrfach (für Volume etc.)"""
        for _ in range(repeats):
            self.send_command(cmd_name)
            time.sleep(delay)

def main():
    """Interaktive Steuerung"""
    remote = TeufelIRRemote()
    
    print("=== Teufel Power HiFi IR Controller (Raspberry Pi) ===")
    print("GPIO 12 (Hardware PWM)")
    print("\nBefehle:")
    print("p - Power ON/OFF")
    print("m - Mute")
    print("l - Bluetooth")
    print("+ - Lautstärke +")
    print("- - Lautstärke -")
    print("← - Links (a)")
    print("→ - Rechts (d)")
    print("B/b - Bass +/-")
    print("M/n - Mid +/-")
    print("T/t - Treble +/-")
    print("1 - AUX")
    print("2 - Line")
    print("3 - Optical")
    print("4 - USB")
    print("< - Balance Links")
    print("> - Balance Rechts")
    print("q - Beenden")
    print()
    
    command_map = {
        'p': 'CMD_POWER',
        'm': 'CMD_MUTE',
        'l': 'CMD_BLUETOOTH',
        '+': 'CMD_VOLUME_UP',
        '=': 'CMD_VOLUME_UP',
        '-': 'CMD_VOLUME_DOWN',
        '_': 'CMD_VOLUME_DOWN',
        'a': 'CMD_LEFT',
        'd': 'CMD_RIGHT',
        'B': 'CMD_BASS_UP',
        'b': 'CMD_BASS_DOWN',
        'M': 'CMD_MID_UP',
        'n': 'CMD_MID_DOWN',
        'T': 'CMD_TREBLE_UP',
        't': 'CMD_TREBLE_DOWN',
        '1': 'CMD_AUX',
        '2': 'CMD_LINE',
        '3': 'CMD_OPT',
        '4': 'CMD_USB',
        '<': 'CMD_BAL_LEFT',
        ',': 'CMD_BAL_LEFT',
        '>': 'CMD_BAL_RIGHT',
        '.': 'CMD_BAL_RIGHT'
    }
    
    try:
        while True:
            try:
                cmd = input("Befehl: ").strip()
                if cmd == 'q':
                    break
                elif cmd in command_map:
                    # Volume-Befehle mit Wiederholung
                    if cmd in ['+', '=', '-', '_']:
                        remote.send_repeating(command_map[cmd], 3)
                    else:
                        remote.send_command(command_map[cmd])
                elif cmd == 'h' or cmd == '?':
                    print("\n=== Hilfe ===")
                    print("p=Power, m=Mute, l=Bluetooth")
                    print("+/-=Volume, a/d=Links/Rechts")
                    print("B/b=Bass+/-, M/n=Mid+/-, T/t=Treble+/-")
                    print("1=AUX, 2=Line, 3=Opt, 4=USB")
                    print("<>=Balance L/R")
                    print("q=Beenden")
                else:
                    print(f"Unbekannter Befehl: {cmd}")
            except KeyboardInterrupt:
                print("\nUnterbrochen")
                break
            except EOFError:
                print("\nBefehl fehlgeschlagen")
                break
    finally:
        del remote

# Zusätzliche Funktionen (wie im Arduino)
class TeufelMacros(TeufelIRRemote):
    """Erweiterte Funktionen"""
    
    def power_on_with_bluetooth(self):
        """Einschalten und Bluetooth aktivieren"""
        self.send_command('CMD_POWER')
        time.sleep(2)
        self.send_command('CMD_BLUETOOTH')
    
    def set_volume_level(self, level):
        """Setzt Lautstärke auf bestimmten Level (0-50)"""
        # Erst auf Minimum
        print("Setze Lautstärke auf Minimum...")
        for _ in range(50):
            self.send_command('CMD_VOLUME_DOWN')
            time.sleep(0.05)
        
        # Dann auf gewünschten Level
        print(f"Setze Lautstärke auf Level {level}...")
        for _ in range(level):
            self.send_command('CMD_VOLUME_UP')
            time.sleep(0.05)
    
    def switch_to_input(self, input_type):
        """Schnell auf Eingang wechseln"""
        inputs = {
            'A': 'CMD_AUX',
            'L': 'CMD_LINE',
            'O': 'CMD_OPT',
            'U': 'CMD_USB',
            'B': 'CMD_BLUETOOTH'
        }
        if input_type in inputs:
            self.send_command(inputs[input_type])
    
    def set_flat_eq(self):
        """Reset Bass, Mid, Treble auf neutral"""
        print("Setze EQ auf Flat...")
        for _ in range(10):
            self.send_command('CMD_BASS_DOWN')
            self.send_command('CMD_MID_DOWN')
            self.send_command('CMD_TREBLE_DOWN')
            time.sleep(0.05)

def execute_command(command_name, repeats=1):
    """Führt einen einzelnen Befehl aus"""
    try:
        remote = TeufelIRRemote()
        
        if command_name in COMMANDS:
            if repeats > 1:
                remote.send_repeating(command_name, repeats)
            else:
                remote.send_command(command_name)
            print(f"Command {command_name} sent successfully (repeats: {repeats})")
            return True
        else:
            print(f"Unknown command: {command_name}")
            print("Available commands:", list(COMMANDS.keys()))
            return False
    except Exception as e:
        print(f"Error executing command: {e}")
        return False
    finally:
        if 'remote' in locals():
            del remote

if __name__ == "__main__":
    # Argument parser für Command-Line-Interface
    parser = argparse.ArgumentParser(description='Teufel Power HiFi IR Controller')
    parser.add_argument('--command', '-c', help='Command to execute')
    parser.add_argument('--repeats', '-r', type=int, default=1, help='Number of repeats (default: 1)')
    parser.add_argument('--list', '-l', action='store_true', help='List available commands')
    parser.add_argument('--interactive', '-i', action='store_true', help='Interactive mode')
    
    args = parser.parse_args()
    
    # Prüfe ob als root
    if os.geteuid() != 0:
        print("WARNUNG: Für beste Performance als root ausführen!")
        print("sudo python3 teufel-power-hifi-controller.py\n")
    
    # Prüfe pigpio daemon
    try:
        test = pigpio.pi()
        if not test.connected:
            print("FEHLER: pigpio daemon läuft nicht!")
            print("Starte mit: sudo pigpiod")
            sys.exit(1)
        test.stop()
    except:
        print("FEHLER: pigpio nicht installiert!")
        print("Installation: sudo apt-get install pigpio python3-pigpio")
        sys.exit(1)
    
    # Command-Line-Modus
    if args.list:
        print("Available commands:")
        for cmd in COMMANDS.keys():
            print(f"  {cmd}")
        sys.exit(0)
    
    if args.command:
        success = execute_command(args.command, args.repeats)
        sys.exit(0 if success else 1)
    
    # Interactive-Modus oder Fallback
    if args.interactive or len(sys.argv) == 1:
        main()
    else:
        parser.print_help()
