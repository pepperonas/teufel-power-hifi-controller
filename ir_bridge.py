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
MODE_NUM = {"off": 0, "db": 1, "pegel": 1, "bpm": 2, "smiley": 3,
            "vu": 4, "heart": 5, "spektrum": 6, "welle": 7}

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
latest_frame = ""          # last 12x8 frame streamed by the R4 ('F'+24 hex), for the 1:1 viewer
_last_value = None
_last_beats = None
IDLE_LEVEL = 0.03          # Pegel darunter = Stille -> Matrix zeigt "--"
FLASH_MIN_GAP = 0.30       # max ~3 Beat-Flashes/s -> ruhigere BPM-/Beat-Anzeige
_last_flash_ts = 0.0
_last_spectrum = None

def _needs_beat(m):   return m in ("bpm", "smiley", "heart", "welle")
def _needs_level(m):  return m in ("db", "pegel", "vu", "smiley", "heart")
def _downsample12(bands):
    out = []
    for i in range(12):
        a = bands[2*i] if 2*i < len(bands) else 0.0
        b = bands[2*i+1] if 2*i+1 < len(bands) else 0.0
        out.append(max(0, min(8, int(round((a + b) / 2.0 * 8)))))
    return out

def find_port():
    for link in ("/dev/teufel-ir", "/dev/teufel-nano"):
        if os.path.exists(link):
            return os.path.realpath(link)
    cands = sorted(glob.glob("/dev/ttyACM*")) + sorted(glob.glob("/dev/ttyUSB*"))
    return cands[0] if cands else "/dev/ttyACM0"

def try_open_serial():
    """Ein einzelner Verbindungsversuch zum R4. Setzt `ser` bei Erfolg, sonst None."""
    global ser
    port = find_port()
    try:
        s = serial.Serial(port, BAUD, timeout=1)
        time.sleep(2.0)            # Arduino-Reset/Boot abwarten
        s.reset_input_buffer()
        ser = s
        print("Serial offen:", port, flush=True)
        return True
    except Exception as e:
        ser = None
        return False

def serial_loop():
    """Hält die R4-Verbindung am Leben; (re)öffnet sobald der Arduino auftaucht.
       Läuft im Hintergrund, damit der TCP-Server auch OHNE R4 lauscht."""
    while True:
        if ser is None:
            if try_open_serial():
                try: push_matrix("m%d" % MODE_NUM[matrix_mode])   # Modus spiegeln
                except Exception: pass
            else:
                time.sleep(3); continue
        time.sleep(2)

def _write_line(line):
    """Eine Zeile an den Arduino schreiben. Lock muss gehalten werden.
       Ohne/defektem R4: `ser=None` setzen (serial_loop öffnet neu) + Fehler werfen."""
    global ser
    if ser is None:
        raise RuntimeError("R4 nicht verbunden")
    try:
        ser.write((line + "\n").encode()); ser.flush()
    except Exception as e:
        print("Write-Fehler, markiere R4 als getrennt:", e, flush=True)
        try: ser.close()
        except Exception: pass
        ser = None
        raise

def send_code(code, repeats):
    with ser_lock:
        for _ in range(max(1, repeats)):
            _write_line("%02X" % code)
            time.sleep(0.06)

def push_matrix(line):
    """Matrix-Daten an den R4 (fire-and-forget; ohne R4 still übersprungen)."""
    with ser_lock:
        try:
            _write_line(line)
        except Exception:
            pass   # kein R4 -> Matrix-Update auslassen

def reader():
    """Continuously read serial and cache the R4's streamed frames ('F'+24 hex).
    Other lines (command echoes) are ignored. Read + write run on separate
    threads, which pyserial supports; on reconnect the global `ser` is re-fetched."""
    global latest_frame
    while True:
        s = ser
        if s is None:
            time.sleep(0.3); continue
        try:
            line = s.readline().decode(errors="replace").strip()
        except Exception:
            time.sleep(0.2); continue
        if line and line[0] == "F" and len(line) >= 25:
            latest_frame = line[1:25]

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
    global matrix_mode, _last_value, _last_beats, _last_spectrum
    mode = mode.lower()
    if mode == "db":
        mode = "pegel"
    if mode not in MODE_NUM:
        return False
    matrix_mode = mode
    save_mode()
    _last_value = None                       # erzwingt sofortiges Neu-Senden
    _last_beats = None
    _last_spectrum = None
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
    global _last_value, _last_beats, _last_flash_ts, _last_spectrum
    while True:
        m = matrix_mode
        if m == "off" or ser is None:   # kein Modus ODER kein R4 -> nicht hart pollen
            _last_beats = None
            time.sleep(0.6); continue
        interval = 0.10 if m in ("vu", "spektrum") else 0.12
        st = poll_disco()
        if st is not None:
            now = time.monotonic()
            level = st.get("level", 0.0) or 0.0
            idle = level < IDLE_LEVEL
            # --- Beat-Flash/Puls (rate-limitiert -> ruhig) ---
            if _needs_beat(m):
                beats = st.get("beats")
                if (not idle) and beats is not None and _last_beats is not None and beats > _last_beats \
                        and (now - _last_flash_ts) >= FLASH_MIN_GAP:
                    push_matrix("f"); _last_flash_ts = now
                _last_beats = beats
            else:
                _last_beats = None
            # --- Primaerwert ---
            if m == "bpm":
                bpm = int(round(st.get("bpm", 0) or 0))
                val = -1 if (idle or bpm <= 0) else bpm
                # nur bei spuerbarer Aenderung neu senden -> stabile Anzeige
                if val != _last_value and (val == -1 or _last_value in (None, -1) or abs(val - _last_value) >= 2):
                    _last_value = val; push_matrix("v%d" % val)
            elif _needs_level(m):
                val = -1 if idle else max(0, min(100, int(round(level * 100))))
                if val != _last_value:
                    _last_value = val; push_matrix("v%d" % val)
            # --- Spektrum ---
            if m == "spektrum":
                cols = _downsample12(st.get("bands") or [])
                if cols != _last_spectrum:
                    _last_spectrum = cols
                    push_matrix("s" + "".join(str(c) for c in cols))
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
        if cmd == "FRAME?":          # latest streamed R4 frame + mode (1:1 viewer)
            conn.sendall(("OK %s %s\n" % (latest_frame or "0" * 24, matrix_mode)).encode()); return
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
    # TCP-Server ZUERST -> Port 8799 lauscht IMMER, auch ohne R4
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((HOST, TCP_PORT)); srv.listen(8)
    print("IR-Bridge lauscht auf %s:%d (Matrix-Modus: %s)" % (HOST, TCP_PORT, matrix_mode), flush=True)
    # Serielle R4-Verbindung im Hintergrund (öffnet sobald der Arduino da ist)
    threading.Thread(target=serial_loop, daemon=True).start()
    threading.Thread(target=reader, daemon=True).start()   # cache streamed R4 frames
    threading.Thread(target=poller, daemon=True).start()
    while True:
        conn, _ = srv.accept()
        threading.Thread(target=handle, args=(conn,), daemon=True).start()

if __name__ == "__main__":
    main()
