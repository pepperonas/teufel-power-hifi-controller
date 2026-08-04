"""
Regression tests for the serial-port deadlock (2026-08-04).

The R4's USB-CDC stops draining its endpoint every so often — this host browns
out constantly, which provokes it. pyserial defaults to `write_timeout=None`,
so the write parked in pselect6() forever *while holding ser_lock*. Everything
that needs the port then queued behind it: IR commands, matrix pushes and, worst
of all, the liveness watchdog's own nudge. The self-healing written for exactly
this failure was deadlocked by it.

Observed live before the fix: 17 handler threads in futex_wait, the watchdog
among them, one thread in pselect6 with a write fd set and a NULL timeout, and
`FRAME?` returning a frozen frame while the TCP listener still answered.

These tests pin the three places that must never block indefinitely.
"""
import sys, types, threading, time

serial_mod = types.ModuleType("serial")
class _FakeSerial:
    last_kwargs = None
    def __init__(self, *a, **kw):
        _FakeSerial.last_kwargs = kw
    def write(self, *a): pass
    def flush(self): pass
    def close(self): pass
    def reset_input_buffer(self): pass
    def readline(self): return b""
serial_mod.Serial = _FakeSerial
class _SerialTimeout(Exception): pass
serial_mod.SerialTimeoutException = _SerialTimeout
sys.modules.setdefault("serial", serial_mod)

import os, tempfile
os.environ.setdefault("MATRIX_FILE", tempfile.mktemp())

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import ir_bridge as ib   # noqa: E402


def test_serial_opens_with_a_write_timeout():
    """Without this the write blocks forever and takes ser_lock with it."""
    assert ib.SER_WRITE_TIMEOUT > 0
    # Patch the module's own reference: whichever test file imported first owns
    # the `serial` stub in sys.modules, so a local stub would simply be ignored.
    seen = {}
    class _Recorder(_FakeSerial):
        def __init__(self, *a, **kw):
            seen.update(kw)
            super().__init__(*a, **kw)
    orig = ib.serial.Serial
    ib.serial.Serial = _Recorder
    try:
        ib.try_open_serial(allow_reset=False)
    finally:
        ib.serial.Serial = orig
    assert seen.get("write_timeout") == ib.SER_WRITE_TIMEOUT, \
        "serial.Serial opened without write_timeout — writes can park indefinitely"


def test_send_code_fails_fast_when_the_port_is_held():
    """A queued keypress that lands minutes later is worse than an error."""
    ib.ser_lock.acquire()
    try:
        t0 = time.monotonic()
        try:
            ib.send_code(0x28, 1)
            raised = False
        except Exception:
            raised = True
        waited = time.monotonic() - t0
        assert raised, "send_code returned normally while the port was held"
        assert waited < ib.LOCK_WAIT_S + 1.0, f"send_code waited {waited:.1f}s"
    finally:
        ib.ser_lock.release()


def test_push_matrix_skips_rather_than_waits():
    """It runs on the poll loop; a frame two seconds late is worthless."""
    ib.ser_lock.acquire()
    try:
        t0 = time.monotonic()
        ib.push_matrix("m10")          # must not raise, must not block
        assert time.monotonic() - t0 < 1.5
    finally:
        ib.ser_lock.release()


def test_watchdog_resets_when_it_cannot_get_the_lock():
    """Not getting the lock while the R4 is silent IS the diagnosis, not a
    reason to wait — waiting is what stopped the watchdog from ever firing."""
    calls = []
    orig_reset, orig_sleep = ib.usb_reset_r4, time.sleep
    ib.usb_reset_r4 = lambda: (calls.append(1), True)[1]
    ib.ser = _FakeSerial()
    ib._serial_booted = True
    ib._last_rx = time.monotonic() - (ib.RX_STALE_S + 60)   # long silent
    ib.ser_lock.acquire()                                   # simulate stuck writer
    try:
        t = threading.Thread(target=ib.liveness_watchdog, daemon=True)
        t.start()
        deadline = time.monotonic() + 20
        while not calls and time.monotonic() < deadline:
            orig_sleep(0.2)
        assert calls, "watchdog never reset the R4 while the port was blocked"
        assert ib.ser is None, "watchdog kept the dead handle — serial_loop won't reopen"
    finally:
        ib.ser_lock.release()
        ib.usb_reset_r4 = orig_reset
