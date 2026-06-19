#!/usr/bin/env python3
"""
Teufel IR Serial Bridge
=======================
Haelt den seriellen Port zum Arduino Nano (IRremote-Sketch) dauerhaft offen und
nimmt Befehle ueber einen lokalen TCP-Socket entgegen. So entsteht KEIN
Nano-Reset (und damit keine ~2s Verzoegerung) pro Tastendruck.

Protokoll (TCP 127.0.0.1:8799, eine Zeile):
    CMD_POWER            -> sendet 1x
    CMD_VOLUME_DOWN 5    -> sendet 5x
Antwort: "OK\\n" oder "ERR <grund>\\n".

Der Nano sendet den NEC-Frame (Adresse 0x5780). Quelle des Sketches:
arduino/teufel-ir-serial-bridge/  (HEX-pro-Zeile).
"""
import serial, socket, threading, time, glob, os

BAUD = 115200
HOST, TCP_PORT = "127.0.0.1", 8799

# CMD-Name -> NEC Command-Code (identisch zum Original-Mapping / arduino/*-mapping.csv)
CODES = {
    "CMD_POWER": 0x48, "CMD_BLUETOOTH": 0x40, "CMD_MUTE": 0x28,
    "CMD_VOLUME_UP": 0xB0, "CMD_VOLUME_DOWN": 0x30,
    "CMD_LEFT": 0x78, "CMD_RIGHT": 0xF8,
    "CMD_BASS_UP": 0x58, "CMD_BASS_DOWN": 0x41,
    "CMD_MID_UP": 0x68, "CMD_MID_DOWN": 0x42,
    "CMD_TREBLE_UP": 0xB8, "CMD_TREBLE_DOWN": 0x43,
    "CMD_AUX": 0x44, "CMD_LINE": 0x45, "CMD_OPT": 0x3F, "CMD_USB": 0xDF,
    "CMD_BAL_LEFT": 0xBF, "CMD_BAL_RIGHT": 0x5F,
}

ser = None
ser_lock = threading.Lock()

def find_port():
    for link in ("/dev/teufel-ir", "/dev/teufel-nano"):
        if os.path.exists(link):
            return os.path.realpath(link)
    cands = sorted(glob.glob("/dev/ttyACM*")) + sorted(glob.glob("/dev/ttyUSB*"))
    return cands[0] if cands else "/dev/ttyACM0"

def open_serial():
    global ser
    while True:
        port = find_port()
        try:
            ser = serial.Serial(port, BAUD, timeout=1)
            time.sleep(2.0)            # Nano-Reset/Boot abwarten
            ser.reset_input_buffer()
            print("Serial offen:", port, flush=True)
            return
        except Exception as e:
            print("Serial-Fehler (%s), retry 3s: %s" % (port, e), flush=True)
            time.sleep(3)

def send_code(code, repeats):
    global ser
    with ser_lock:
        for _ in range(max(1, repeats)):
            try:
                ser.write(("%02X\n" % code).encode())
                ser.flush()
            except Exception as e:
                print("Write-Fehler, reopen:", e, flush=True)
                try: ser.close()
                except Exception: pass
                open_serial()
                ser.write(("%02X\n" % code).encode()); ser.flush()
            time.sleep(0.06)

def handle(conn):
    try:
        data = conn.recv(256).decode(errors="replace").strip()
        if not data:
            conn.sendall(b"ERR empty\n"); return
        parts = data.split()
        cmd = parts[0].upper()
        repeats = int(parts[1]) if len(parts) > 1 else 1
        if cmd not in CODES:
            conn.sendall(b"ERR unknown\n"); return
        send_code(CODES[cmd], repeats)
        conn.sendall(b"OK\n")
    except Exception as e:
        try: conn.sendall(("ERR %s\n" % e).encode())
        except Exception: pass
    finally:
        conn.close()

def main():
    open_serial()
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((HOST, TCP_PORT)); srv.listen(8)
    print("IR-Bridge lauscht auf %s:%d" % (HOST, TCP_PORT), flush=True)
    while True:
        conn, _ = srv.accept()
        threading.Thread(target=handle, args=(conn,), daemon=True).start()

if __name__ == "__main__":
    main()
