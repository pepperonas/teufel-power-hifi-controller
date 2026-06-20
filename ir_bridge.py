#!/usr/bin/env python3
"""
Teufel IR Serial Bridge (+ LED-Matrix-Anzeige)
==============================================
Haelt den seriellen Port zum Arduino (UNO R4 / Nano, IRremote-Sketch) dauerhaft
offen und nimmt IR-Befehle ueber einen lokalen TCP-Socket entgegen (kein
Arduino-Reset pro Tastendruck).

Zusaetzlich (2026-06-20): die R4-LED-Matrix zeigt wahlweise den **dB-Pegel (0-100)**
oder die **BPM** vom disco-controller (:5007). Es ist immer nur EIN Wert sichtbar;
ein kleiner Indikator auf der Matrix zeigt den Modus. Umschaltung kommt aus dem
Smart-Home-Dashboard via powerhifi-controller -> "MATRIX <off|db|bpm>".

TCP 127.0.0.1:8799 (eine Zeile):
    CMD_POWER            -> IR 1x
    CMD_VOLUME_DOWN 5    -> IR 5x
    MATRIX db            -> Matrix-Modus setzen (off|db|bpm), persistent
    MATRIX?              -> aktuellen Modus abfragen -> "OK <mode>"
Serielles Protokoll zum Arduino: IR=<HEX>, Matrix-Modus=m<0|1|2>, Wert=v<int>.
"""
import serial, socket, threading, time, glob, os, json, urllib.request

BAUD = 115200
HOST, TCP_PORT = "127.0.0.1", 8799
DISCO_URL = "http://127.0.0.1:5007/api/status"
MATRIX_FILE = "/home/pi/apps/powerhifi-controller/matrix_mode.txt"
MODE_NUM = {"off": 0, "db": 1, "bpm": 2}

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
matrix_mode = "off"
_last_value = None
_last_beats = None
IDLE_LEVEL = 0.03          # Pegel darunter = Stille -> Matrix zeigt "--"

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
            time.sleep(2.0)            # Arduino-Reset/Boot abwarten
            ser.reset_input_buffer()
            print("Serial offen:", port, flush=True)
            return
        except Exception as e:
            print("Serial-Fehler (%s), retry 3s: %s" % (port, e), flush=True)
            time.sleep(3)

def _write_line(line):
    """Eine Zeile an den Arduino schreiben (mit Reconnect). Lock muss gehalten werden."""
    global ser
    data = (line + "\n").encode()
    try:
        ser.write(data); ser.flush()
    except Exception as e:
        print("Write-Fehler, reopen:", e, flush=True)
        try: ser.close()
        except Exception: pass
        open_serial()
        ser.write(data); ser.flush()

def send_code(code, repeats):
    with ser_lock:
        for _ in range(max(1, repeats)):
            _write_line("%02X" % code)
            time.sleep(0.06)

def push_matrix(line):
    with ser_lock:
        _write_line(line)

# ---- Matrix-Modus -----------------------------------------------------------
def load_mode():
    global matrix_mode
    try:
        m = open(MATRIX_FILE).read().strip().lower()
        if m in MODE_NUM:
            matrix_mode = m
    except Exception:
        pass

def save_mode():
    try:
        with open(MATRIX_FILE, "w") as f:
            f.write(matrix_mode)
    except Exception as e:
        print("Mode-Save-Fehler:", e, flush=True)

def set_matrix_mode(mode):
    global matrix_mode, _last_value
    mode = mode.lower()
    if mode not in MODE_NUM:
        return False
    matrix_mode = mode
    save_mode()
    _last_value = None                       # erzwingt sofortiges Neu-Senden des Werts
    push_matrix("m%d" % MODE_NUM[mode])      # Indikator/Clear sofort aktualisieren
    return True

def poll_disco():
    try:
        with urllib.request.urlopen(DISCO_URL, timeout=2) as r:
            return json.loads(r.read().decode())
    except Exception:
        return None

def poller():
    """Schiebt periodisch Wert/Beat auf die Matrix, wenn ein Modus aktiv ist.
       Idle (Stille) -> "--"; im BPM-Modus zusaetzlich Beat-Flash + schnelleres Polling."""
    global _last_value, _last_beats
    while True:
        if matrix_mode == "off":
            _last_beats = None
            time.sleep(0.6); continue
        interval = 0.12 if matrix_mode == "bpm" else 0.25
        st = poll_disco()
        if st is not None:
            level = st.get("level", 0.0) or 0.0
            idle = level < IDLE_LEVEL
            if matrix_mode == "db":
                _last_beats = None
                val = -1 if idle else max(0, min(100, int(round(level * 100))))
            else:  # bpm
                bpm = int(round(st.get("bpm", 0) or 0))
                val = -1 if (idle or bpm <= 0) else bpm
                beats = st.get("beats")
                if (not idle) and beats is not None and _last_beats is not None and beats > _last_beats:
                    push_matrix("f")                 # Beat-Flash (Rahmenpuls)
                _last_beats = beats
            if val != _last_value:
                _last_value = val
                push_matrix("v%d" % val)
        time.sleep(interval)

# ---- TCP --------------------------------------------------------------------
def handle(conn):
    try:
        data = conn.recv(256).decode(errors="replace").strip()
        if not data:
            conn.sendall(b"ERR empty\n"); return
        parts = data.split()
        cmd = parts[0].upper()
        if cmd == "MATRIX?":
            conn.sendall(("OK %s\n" % matrix_mode).encode()); return
        if cmd == "MATRIX":
            mode = parts[1] if len(parts) > 1 else ""
            if set_matrix_mode(mode):
                conn.sendall(("OK %s\n" % matrix_mode).encode())
            else:
                conn.sendall(b"ERR mode\n")
            return
        # sonst: IR-Befehl
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
    load_mode()
    open_serial()
    # aktuellen Modus an den Arduino spiegeln
    push_matrix("m%d" % MODE_NUM[matrix_mode])
    threading.Thread(target=poller, daemon=True).start()
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((HOST, TCP_PORT)); srv.listen(8)
    print("IR-Bridge lauscht auf %s:%d (Matrix-Modus: %s)" % (HOST, TCP_PORT, matrix_mode), flush=True)
    while True:
        conn, _ = srv.accept()
        threading.Thread(target=handle, args=(conn,), daemon=True).start()

if __name__ == "__main__":
    main()
