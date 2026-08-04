#!/usr/bin/env python3
"""
Teufel IR Serial Bridge (+ LED-Matrix-Anzeige)
==============================================
Haelt den seriellen Port zum Arduino (UNO R4 / Nano, IRremote-Sketch) dauerhaft
offen und nimmt IR-Befehle ueber einen lokalen TCP-Socket entgegen (kein
Arduino-Reset pro Tastendruck).

Zusaetzlich: die R4-LED-Matrix zeigt Pegel/dB/BPM/Effekte/Klima, **Uhr** (Mode 12,
digitale HH:MM), **Wanduhr** (Mode 13, analog) oder Iris-Overlay. Umschaltung aus dem
Smart-Home-Dashboard via powerhifi-controller -> "MATRIX <mode>".

TCP 127.0.0.1:8799 (eine Zeile):
    CMD_POWER            -> IR 1x
    CMD_VOLUME_DOWN 5    -> IR 5x
    MATRIX clock         -> Matrix-Modus setzen (off|clock|analog|db|bpm|…), persistent
    MATRIX?              -> aktuellen Modus abfragen -> "OK <mode>"
Serielles Protokoll zum Arduino: IR=<HEX>, Matrix-Modus=m<n>, Wert=v<int> (clock/analog: vHHMMSS).
"""
import serial, socket, threading, time, glob, os, json, urllib.request
import fcntl, math, re, subprocess

BAUD = 115200
HOST, TCP_PORT = "127.0.0.1", 8799
# disco-controller is colocated with the matrix bridge (raspi5); override via env if needed
DISCO_URL = os.environ.get("DISCO_URL", "http://127.0.0.1:5007/api/status")
MATRIX_FILE = "/home/pi/apps/powerhifi-controller/matrix_mode.txt"
IRIS_FILE = "/home/pi/apps/powerhifi-controller/matrix_iris.txt"
MODE_NUM = {"temp": 8, "humidity": 9, "off": 0, "pegel": 1, "bpm": 2, "smiley": 3,
            "vu": 4, "heart": 5, "spektrum": 6, "welle": 7, "db": 10, "clock": 12,
            "analog": 13}
IRIS_MODE = 11                 # firmware bitmap "IRIS" (overlay, not a saved mode)
CLOCK_MODE = 12                # firmware digital HH:MM (v=HHMMSS)
ANALOG_MODE = 13               # firmware analog wall-clock (v=HHMMSS)
CLOCK_MODES = frozenset({"clock", "analog"})
NO_DISCO_MODES = frozenset({"off", "welle", "temp", "humidity"}) | CLOCK_MODES
IRIS_DB = -20.0                # legacy fallback ≈70 SPL if status lacks warn_over/warn_thr
QUIET_LOG_FACTOR = 1.3         # LAUT/quiet_log damps reported dB → scale legacy thr too

# Condensed 2×5 font — mirrors firmware FONT2 for layout unit tests
FONT2 = (
    (0b11, 0b10, 0b10, 0b10, 0b11),  # 0
    (0b01, 0b11, 0b01, 0b01, 0b01),  # 1 (top flag)
    (0b11, 0b01, 0b11, 0b10, 0b11),  # 2
    (0b11, 0b01, 0b11, 0b01, 0b11),  # 3
    (0b10, 0b10, 0b11, 0b01, 0b01),  # 4
    (0b11, 0b10, 0b11, 0b01, 0b11),  # 5
    (0b11, 0b10, 0b11, 0b10, 0b11),  # 6
    (0b11, 0b01, 0b01, 0b01, 0b01),  # 7
    (0b11, 0b10, 0b11, 0b10, 0b11),  # 8
    (0b11, 0b10, 0b11, 0b01, 0b11),  # 9
)

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
iris_enabled = False       # Overlay: show "IRIS" while disco warn_over (shared thr)
_iris_showing = False      # currently displaying firmware mode 11
latest_frame = ""          # last 12x8 frame streamed by the R4 ('F'+24 hex), for the 1:1 viewer
_serial_booted = False     # True after open settled — reader may consume lines
# Liveness. A per-command "TX 0x<hex>" acknowledgement was tried here and had
# to go: in the streaming matrix modes the R4 floods the port with frames, the
# reader falls behind the ack window, and every working button gets reported as
# broken. Freshness of *any* line is the robust signal — see liveness_watchdog.
_last_rx = 0.0             # monotonic time of the last line received from the R4
RX_STALE_S = 25.0          # silence this long → probe, then re-enumerate
# pyserial defaults to write_timeout=None, i.e. an unbounded wait for the port to
# accept data. When the R4's CDC stops draining its endpoint — which this host
# provokes regularly via undervoltage — that write parks in pselect6() forever
# while holding ser_lock. Every IR command, every matrix push and, fatally, the
# liveness watchdog's own nudge then queue up behind it: the self-healing added
# for exactly this failure was itself deadlocked by it. Observed live with 17
# handler threads in futex_wait and the watchdog among them.
SER_WRITE_TIMEOUT = 1.0    # a healthy R4 accepts a line in microseconds
LOCK_WAIT_S = 2.5          # bound every wait for the port, callers included
_last_value = None
_last_beats = None
IDLE_LEVEL = 0.03          # Pegel darunter = Stille -> Matrix zeigt "--"
FLASH_MIN_GAP = 0.30       # max ~3 Beat-Flashes/s -> ruhigere BPM-/Beat-Anzeige
_last_flash_ts = 0.0
_log_seen = {}             # tag -> (msg, ts); dedupes the reconnect loop's log
LOG_REPEAT_S = 300.0       # re-state a standing condition at most every 5 min
_last_spectrum = None
IRIS_HOLD_S = 0.35         # min time to keep IRIS up (anti-flicker)
_iris_since = 0.0

def _needs_beat(m):   return m in ("bpm", "smiley", "heart", "welle")
def _needs_level(m):  return m in ("pegel", "vu", "smiley", "heart")
def _needs_dbfs(m):   return m == "db"
DBFS_IDLE = -200          # sentinel → firmware draws "--" (real dBFS is typically -60…0)

def pack_clock(hour, minute, second):
    """Pack local time as HHMMSS int for firmware mode 12 (`vHHMMSS`)."""
    h = max(0, min(23, int(hour)))
    m = max(0, min(59, int(minute)))
    s = max(0, min(59, int(second)))
    return h * 10000 + m * 100 + s

def unpack_clock(v):
    """Unpack HHMMSS — mirrors firmware drawClock clamps."""
    if v is None:
        return None
    try:
        v = int(v)
    except (TypeError, ValueError):
        return None
    if v < 0:
        return None
    s = v % 100
    m = (v // 100) % 100
    h = v // 10000
    if s > 59:
        s = 59
    if m > 59:
        m = 59
    if h > 23:
        h = 23
    return h, m, s

def clock_value(ts=None):
    """Current local time as HHMMSS for matrix clock / analog modes."""
    lt = time.localtime(ts)
    return pack_clock(lt.tm_hour, lt.tm_min, lt.tm_sec)

def _blit_mini_digit(frame, d, x, y_top):
    if d < 0 or d > 9:
        return
    for r, bits in enumerate(FONT2[d]):
        if bits & 2:
            frame[y_top + r][x] = 1
        if bits & 1:
            frame[y_top + r][x + 1] = 1

def _frame_px(frame, x, y):
    if 0 <= x < 12 and 0 <= y < 8:
        frame[y][x] = 1

def _frame_line(frame, x0, y0, x1, y1):
    dx, sx = abs(x1 - x0), (1 if x0 < x1 else -1)
    dy, sy = -abs(y1 - y0), (1 if y0 < y1 else -1)
    err = dx + dy
    while True:
        _frame_px(frame, x0, y0)
        if x0 == x1 and y0 == y1:
            break
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x0 += sx
        if e2 <= dx:
            err += dx
            y0 += sy

def _frame_hand(frame, cx, cy, ang_deg, length):
    rad = math.radians(ang_deg)
    x1 = int(round(cx + math.sin(rad) * length))
    y1 = int(round(cy - math.cos(rad) * length))
    _frame_line(frame, int(round(cx)), int(round(cy)), x1, y1)

def render_clock_frame(hour, minute, second, colon_on=True):
    """Software 8×12 frame mirroring firmware drawClock (digital, no bars)."""
    frame = [[0] * 12 for _ in range(8)]
    parts = unpack_clock(pack_clock(hour, minute, second))
    if parts is None:
        return frame
    h, m, _s = parts
    y = 1
    _frame_px(frame, 0, 0)
    _frame_px(frame, 11, 0)
    _frame_px(frame, 0, 7)
    _frame_px(frame, 11, 7)
    _blit_mini_digit(frame, h // 10, 0, y)
    _blit_mini_digit(frame, h % 10, 3, y)
    if colon_on:
        _frame_px(frame, 5, y + 1)
        _frame_px(frame, 5, y + 3)
    _blit_mini_digit(frame, m // 10, 7, y)
    _blit_mini_digit(frame, m % 10, 10, y)
    return frame

def render_analog_frame(hour, minute, second):
    """Software 8×12 frame mirroring firmware drawAnalogClock."""
    frame = [[0] * 12 for _ in range(8)]
    parts = unpack_clock(pack_clock(hour, minute, second))
    if parts is None:
        return frame
    h, m, s = parts
    cx, cy = 5.5, 3.5
    for x, y in ((5, 0), (6, 0), (11, 3), (11, 4), (5, 7), (6, 7), (0, 3), (0, 4),
                 (9, 1), (10, 6), (2, 6), (1, 1)):
        _frame_px(frame, x, y)
    h_ang = ((h % 12) + m / 60.0) * 30.0
    m_ang = (m + s / 60.0) * 6.0
    s_ang = s * 6.0
    _frame_hand(frame, cx, cy, h_ang, 2.15)
    _frame_hand(frame, cx, cy, m_ang, 3.25)
    rad = math.radians(s_ang)
    _frame_px(frame, int(round(cx + math.sin(rad) * 3.7)),
              int(round(cy - math.cos(rad) * 3.7)))
    _frame_px(frame, 5, 3)
    _frame_px(frame, 6, 3)
    return frame

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

R4_USB_ID = "2341:1002"                    # Arduino UNO R4 WiFi
_USBDEVFS_RESET = (ord("U") << 8) | 20


def _log_once(tag, msg):
    """Log a standing condition once, then at most every LOG_REPEAT_S.

    The reconnect loop runs every 3 s. While the board is physically off the bus
    that produced ~2400 lines an hour — and because two different messages
    alternated, deduping on the text alone caught none of them. Hence a per-tag
    key: each condition speaks for itself, and none of them drowns the one line
    that matters when the R4 finally comes back."""
    prev = _log_seen.get(tag)
    now = time.monotonic()
    if prev and prev[0] == msg and now - prev[1] < LOG_REPEAT_S:
        return
    _log_seen[tag] = (msg, now)
    print(msg, flush=True)


def _log_reset():
    """Clear the suppression so the next failure is reported immediately."""
    _log_seen.clear()


def usb_reset_r4():
    """Re-enumerate the R4 over USB — the only remote way back from a wedged CDC.

    This host browns out constantly (hundreds of `Undervoltage detected` per
    day), and a glitched USB link leaves the board still accepting writes while
    it stops answering anything. From the Pi that is indistinguishable from
    healthy hardware: matrix updates and IR codes go into the void and every
    layer above reports success. Only re-enumeration brings it back; a service
    restart does not, because the wedge sits in the device, not in the handle.

    Needs write access to the bus node — see
    /etc/udev/rules.d/99-arduino-r4-usbreset.rules (MODE 0660, GROUP plugdev).
    """
    try:
        out = subprocess.check_output(["lsusb"], text=True, timeout=5)
    except Exception as e:
        print("USB-Reset: lsusb nicht nutzbar:", e, flush=True)
        return False
    m = re.search(r"Bus (\d+) Device (\d+): ID " + re.escape(R4_USB_ID), out)
    if not m:
        _log_once("nobus", "USB-Reset: R4 %s nicht am Bus" % R4_USB_ID)
        return False
    path = "/dev/bus/usb/%s/%s" % (m.group(1), m.group(2))
    try:
        fd = os.open(path, os.O_WRONLY)
    except OSError as e:
        print("USB-Reset: %s nicht schreibbar (udev-Regel fehlt?): %s" % (path, e), flush=True)
        return False
    try:
        fcntl.ioctl(fd, _USBDEVFS_RESET, 0)
        print("USB-Reset auf %s abgesetzt" % path, flush=True)
        return True
    except OSError as e:
        print("USB-Reset fehlgeschlagen:", e, flush=True)
        return False
    finally:
        os.close(fd)


def try_open_serial(allow_reset=True):
    """Ein einzelner Verbindungsversuch zum R4. Setzt `ser` bei Erfolg, sonst None."""
    global ser, _serial_booted, latest_frame
    port = find_port()
    try:
        _serial_booted = False
        # Plain open — matching a working interactive session. No 1200-touch,
        # no dsrdtr flags (both have wedged this R4's USB-CDC in the past).
        s = serial.Serial(port, BAUD, timeout=0.4, write_timeout=SER_WRITE_TIMEOUT)
        try:
            s.reset_input_buffer()
        except Exception:
            pass
        # Quick probe: if the board is in loop(), m0 yields "M0".
        try:
            s.write(b"m0\n")
            s.flush()
        except Exception:
            pass
        saw = False
        deadline = time.monotonic() + 2.0
        while time.monotonic() < deadline:
            try:
                line = s.readline().decode(errors="replace").strip()
            except Exception:
                break
            if not line:
                continue
            if line.lower() == "ready" or line[0] in ("M", "F"):
                saw = True
                if line[0] == "F" and len(line) >= 25:
                    latest_frame = line[1:25]
                break
        if not saw and allow_reset:
            # Writes land but nothing ever comes back — a wedged CDC, not a
            # stale handle. Re-enumerate and retry once; otherwise the board
            # stays a black hole until someone unplugs it.
            print("R4 antwortet nicht auf die m0-Probe — versuche USB-Reset", flush=True)
            try:
                s.close()
            except Exception:
                pass
            ser = None
            _serial_booted = False
            if usb_reset_r4():
                time.sleep(5.0)
                return try_open_serial(allow_reset=False)
            return False
        ser = s
        _serial_booted = True
        globals()["_last_rx"] = time.monotonic()   # arm the watchdog from now
        _log_reset()
        print("Serial offen: %s (ready=%s)" % (port, saw), flush=True)
        return True
    except Exception as e:
        _log_once("open", "Serial-Open-Fehler: %s" % e)
        ser = None
        _serial_booted = False
        if allow_reset:
            # The CDC can break hard enough that open() itself fails with EIO.
            # Nothing short of re-enumeration clears that, and without it the
            # bridge would retry a dead node forever.
            if usb_reset_r4():
                time.sleep(5.0)
                return try_open_serial(allow_reset=False)
        return False

def serial_loop():
    """Hält die R4-Verbindung am Leben; (re)öffnet sobald der Arduino auftaucht.
       Läuft im Hintergrund, damit der TCP-Server auch OHNE R4 lauscht."""
    global _last_value, _last_beats, _last_spectrum
    while True:
        if ser is None:
            if try_open_serial():
                # USB-Replug/Reset: R4 bootet neu → Mode + Werte neu spiegeln.
                # Ein einzelner Push kurz nach open() geht oft verloren; deshalb
                # Last-Values invalidieren und Mode zweimal mit Abstand senden.
                _last_value = None
                _last_beats = None
                _last_spectrum = None
                for delay in (0.5, 2.0, 5.0):
                    time.sleep(delay)
                    try:
                        push_matrix("m%d" % MODE_NUM[matrix_mode])
                        if matrix_mode in CLOCK_MODES:
                            push_matrix("v%d" % clock_value())
                            _last_value = clock_value()
                    except Exception:
                        pass
            else:
                time.sleep(3); continue
        time.sleep(2)

def _write_line(line):
    """Eine Zeile an den Arduino schreiben. Lock muss gehalten werden.
       Ohne/defektem R4: `ser=None` setzen (serial_loop öffnet neu) + Fehler werfen."""
    global ser, _serial_booted
    if ser is None:
        raise RuntimeError("R4 nicht verbunden")
    try:
        ser.write((line + "\n").encode()); ser.flush()
    except Exception as e:
        print("Write-Fehler, markiere R4 als getrennt:", e, flush=True)
        try: ser.close()
        except Exception: pass
        ser = None
        _serial_booted = False
        raise

def send_code(code, repeats):
    """Emit an IR code. Fire-and-forget: the firmware echoes `TX 0x<hex>`, but
    waiting for it here is not viable while the matrix stream saturates the
    port. liveness_watchdog covers the case the ack was meant to catch.

    Fails fast if the port is busy. Blocking here just stacks handler threads
    behind a wedge — the caller already timed out and a queued keypress that
    lands minutes later is worse than none."""
    if not ser_lock.acquire(timeout=LOCK_WAIT_S):
        raise RuntimeError("R4 belegt (Port blockiert)")
    try:
        for _ in range(max(1, repeats)):
            _write_line("%02X" % code)
            time.sleep(0.06)
    finally:
        ser_lock.release()


def push_matrix(line):
    """Matrix-Daten an den R4 (fire-and-forget; ohne R4 still übersprungen).

    Skips rather than waits: this runs on the poll loop, and a frame that is
    two seconds late is worthless anyway."""
    if not ser_lock.acquire(timeout=0.5):
        return
    try:
        _write_line(line)
    except Exception:
        pass       # kein R4 -> Matrix-Update auslassen
    finally:
        ser_lock.release()

def reader():
    """Continuously read serial and cache the R4's streamed frames ('F'+24 hex).
    Other lines (command echoes) are ignored. Read + write run on separate
    threads, which pyserial supports; on reconnect the global `ser` is re-fetched."""
    global latest_frame, _last_rx
    while True:
        s = ser
        if s is None or not _serial_booted:
            time.sleep(0.3); continue
        try:
            line = s.readline().decode(errors="replace").strip()
        except Exception:
            time.sleep(0.2); continue
        if line:
            _last_rx = time.monotonic()
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

def load_iris():
    global iris_enabled
    try:
        v = open(IRIS_FILE).read().strip().lower()
        iris_enabled = v in ("1", "true", "on", "yes")
    except Exception:
        iris_enabled = False

def save_iris():
    try:
        with open(IRIS_FILE, "w") as f:
            f.write("1" if iris_enabled else "0")
    except Exception as e:
        print("Iris-Save-Fehler:", e, flush=True)

def set_iris(enabled):
    """Iris-Overlay ein/aus. Persistiert; bei Aus sofort zurück zum Effekt-Modus."""
    global iris_enabled, _iris_showing, _last_value, _last_beats, _last_spectrum
    iris_enabled = bool(enabled)
    save_iris()
    if not iris_enabled and _iris_showing:
        _iris_showing = False
        _last_value = None
        _last_beats = None
        _last_spectrum = None
        push_matrix("m%d" % MODE_NUM[matrix_mode])
    return True

def iris_threshold(quiet_log):
    """Legacy dBFS fallback when disco status has neither warn_over nor warn_thr."""
    return IRIS_DB * QUIET_LOG_FACTOR if quiet_log else IRIS_DB

def iris_loud(st):
    """Same loud predicate as disco Warnung + Strip-Warn (status.warn_over).

    Prefer the server bit so Matrix „IRIS“, page/card wash and LED strip fire
    at the configured warn_thr with identical rounding. Fallbacks keep older
    disco builds working.
    """
    if not st:
        return False
    wo = st.get("warn_over")
    if isinstance(wo, bool):
        return wo
    # Prefer SPL + warn_thr (same units as the UI number field)
    try:
        spl = st.get("spl")
        thr = st.get("warn_thr")
        if spl is not None and thr is not None:
            return round(float(spl), 1) > float(thr)
    except (TypeError, ValueError):
        pass
    # Legacy: reported dBFS vs fixed Iris mark
    raw = st.get("db")
    try:
        db = float(raw) if raw is not None else None
    except (TypeError, ValueError):
        db = None
    thr = iris_threshold(bool(st.get("quiet_log")))
    return db is not None and db > thr

def set_matrix_mode(mode):
    global matrix_mode, _last_value, _last_beats, _last_spectrum, _iris_showing
    mode = mode.lower()
    if mode not in MODE_NUM:
        return False
    matrix_mode = mode
    save_mode()
    _last_value = None                       # erzwingt sofortiges Neu-Senden
    _last_beats = None
    _last_spectrum = None
    if not _iris_showing:
        push_matrix("m%d" % MODE_NUM[mode])  # Indikator/Clear sofort aktualisieren
    return True

def poll_disco():
    try:
        with urllib.request.urlopen(DISCO_URL, timeout=2) as r:
            return json.loads(r.read().decode())
    except Exception:
        return None

def _apply_iris_overlay(st, now):
    """Wenn Iris an und warn_over (gemeinsame Schwelle) → Mode 11 „IRIS“."""
    global _iris_showing, _iris_since, _last_value, _last_beats, _last_spectrum
    if not iris_enabled or st is None:
        if _iris_showing:
            _iris_showing = False
            _last_value = None
            _last_beats = None
            _last_spectrum = None
            push_matrix("m%d" % MODE_NUM[matrix_mode])
        return False
    loud = iris_loud(st)
    if loud:
        if not _iris_showing:
            _iris_showing = True
            _iris_since = now
            push_matrix("m%d" % IRIS_MODE)
        return True
    # unter Schwelle: Hold kurz halten gegen Flackern
    if _iris_showing and (now - _iris_since) >= IRIS_HOLD_S:
        _iris_showing = False
        _last_value = None
        _last_beats = None
        _last_spectrum = None
        push_matrix("m%d" % MODE_NUM[matrix_mode])
        return False
    return _iris_showing

def poller():
    """Schiebt periodisch Wert/Beat auf die Matrix, wenn ein Modus aktiv ist.
       Idle (Stille) -> "--"; im BPM-Modus zusaetzlich Beat-Flash + schnelleres Polling.
       Iris-Overlay: bei warn_over (gemeinsame warn_thr) kurz „IRIS“ (Mode 11)."""
    global _last_value, _last_beats, _last_flash_ts, _last_spectrum
    _last_mode_push = 0.0
    while True:
        m = matrix_mode
        now = time.monotonic()
        # Mode periodisch nachschieben (USB-Replug / R4-WDT-Reset): sonst bleibt
        # die Matrix leer, wenn der erste mN-Push während des Boots verloren ging.
        if ser is not None and (now - _last_mode_push) >= 8.0:
            _last_mode_push = now
            try:
                if _iris_showing:
                    push_matrix("m%d" % IRIS_MODE)
                elif m != "off":
                    push_matrix("m%d" % MODE_NUM[m])
                    _last_value = None
                    _last_spectrum = None
            except Exception:
                pass
        if ser is None:
            _last_beats = None
            time.sleep(0.6); continue

        # Clock / Wanduhr ohne Iris: Pi-Lokalzeit, kein Disco-Poll
        if m in CLOCK_MODES and not iris_enabled:
            val = clock_value()
            if val != _last_value:
                _last_value = val
                push_matrix("v%d" % val)
            time.sleep(0.25); continue

        need_disco = iris_enabled or m not in NO_DISCO_MODES
        if not need_disco:
            _last_beats = None
            time.sleep(0.6); continue
        interval = 0.10 if (iris_enabled or m in ("vu", "spektrum")) else 0.12
        st = poll_disco()
        now = time.monotonic()
        if _apply_iris_overlay(st, now):
            time.sleep(interval); continue
        if m in CLOCK_MODES:
            val = clock_value()
            if val != _last_value:
                _last_value = val
                push_matrix("v%d" % val)
            time.sleep(0.25); continue
        if m in ("off", "welle", "temp", "humidity"):
            _last_beats = None
            time.sleep(0.6); continue
        if st is not None:
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
            elif _needs_dbfs(m):
                # Phone-comparable SPL (disco status.spl). Idle → sentinel for "--".
                raw = st.get("spl")
                if raw is None and st.get("db") is not None:
                    raw = float(st["db"]) + float(st.get("spl_offset") or 90)
                if idle or raw is None:
                    val = DBFS_IDLE
                else:
                    val = int(round(float(raw)))
                    if val < 0: val = 0
                    if val > 99: val = 99
                if val != _last_value and (val == DBFS_IDLE or _last_value in (None, DBFS_IDLE) or abs(val - _last_value) >= 1):
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
            conn.sendall(("OK %s iris=%d\n" % (matrix_mode, 1 if iris_enabled else 0)).encode()); return
        if cmd == "IRIS?":
            conn.sendall(("OK %d\n" % (1 if iris_enabled else 0)).encode()); return
        if cmd == "IRIS":
            arg = (parts[1] if len(parts) > 1 else "").lower()
            if arg in ("1", "on", "true", "yes"):
                set_iris(True)
            elif arg in ("0", "off", "false", "no"):
                set_iris(False)
            else:
                conn.sendall(b"ERR iris\n"); return
            conn.sendall(("OK %d\n" % (1 if iris_enabled else 0)).encode()); return
        if cmd == "FRAME?":          # latest streamed R4 frame + mode (1:1 viewer)
            shown = "iris" if _iris_showing else matrix_mode
            conn.sendall(("OK %s %s\n" % (latest_frame or "0" * 24, shown)).encode()); return
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

def liveness_watchdog():
    """Re-enumerate the R4 when it stops talking.

    The board can wedge while the port stays open and writes keep succeeding, so
    nothing upstream notices: matrix updates and IR codes vanish into the void
    and every layer still reports success. This host browns out constantly
    (hundreds of `Undervoltage detected` a day), which makes that a recurring
    event, so it has to heal without someone unplugging a cable.
    """
    global ser, _serial_booted
    while True:
        time.sleep(5.0)
        if ser is None or not _serial_booted:
            continue                       # serial_loop owns (re)connects
        if time.monotonic() - _last_rx < RX_STALE_S:
            continue
        # Nudge before judging: in "off" the R4 streams nothing by itself, but
        # it always answers a mode command with "M<n>".
        # Never wait on ser_lock here. Failing to get it while nothing has come
        # back for RX_STALE_S is not a reason to keep waiting — it IS the
        # diagnosis: a writer is parked on a port that stopped draining. Waiting
        # for that lock is exactly what kept this watchdog from ever firing.
        if ser_lock.acquire(timeout=LOCK_WAIT_S):
            try:
                _write_line("m%d" % MODE_NUM.get(matrix_mode, 0))
            except Exception:
                continue                   # write failed → serial_loop reopens
            finally:
                ser_lock.release()
            time.sleep(3.0)
            quiet = time.monotonic() - _last_rx
            if quiet < RX_STALE_S:
                continue
            print("R4 seit %.0fs stumm — USB-Reset" % quiet, flush=True)
        else:
            print("R4 stumm und Port seit >%.1fs belegt — USB-Reset erzwungen"
                  % LOCK_WAIT_S, flush=True)
        if usb_reset_r4():
            # Deliberately outside the lock: whoever holds it is the stuck
            # writer, and re-enumeration is what frees it (its write fails once
            # the device is gone). Drop the handle so serial_loop reopens; the
            # stuck thread cleans up through its own exception path.
            s, ser, _serial_booted = ser, None, False
            try:
                if s:
                    s.close()
            except Exception:
                pass


def main():
    load_mode()
    load_iris()
    # TCP-Server ZUERST -> Port 8799 lauscht IMMER, auch ohne R4
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((HOST, TCP_PORT)); srv.listen(8)
    print("IR-Bridge lauscht auf %s:%d (Matrix-Modus: %s, iris=%s)" % (
        HOST, TCP_PORT, matrix_mode, iris_enabled), flush=True)
    # Serielle R4-Verbindung im Hintergrund (öffnet sobald der Arduino da ist)
    threading.Thread(target=serial_loop, daemon=True).start()
    threading.Thread(target=reader, daemon=True).start()   # cache streamed R4 frames
    threading.Thread(target=poller, daemon=True).start()
    threading.Thread(target=liveness_watchdog, daemon=True).start()
    while True:
        conn, _ = srv.accept()
        threading.Thread(target=handle, args=(conn,), daemon=True).start()

if __name__ == "__main__":
    main()
