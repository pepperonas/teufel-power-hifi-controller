"""Contract tests: API + docs expose matrix clock mode 12."""
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_SERVER = (_ROOT / "server.js").read_text()
_README = (_ROOT / "README.md").read_text()
_BRIDGE = (_ROOT / "ir_bridge.py").read_text()
_MATRIX_HTML = (_ROOT / "public" / "matrix.html").read_text()


def test_server_allowlist_includes_clock():
    assert '"clock"' in _SERVER
    # still rejects unknown junk — allowlist is an array literal
    assert "Invalid mode" in _SERVER


def test_bridge_defines_clock_helpers():
    for name in (
        "pack_clock",
        "unpack_clock",
        "clock_value",
        "clock_seconds_bar",
        "render_clock_frame",
        "CLOCK_MODE",
        '"clock": 12',
    ):
        assert name in _BRIDGE


def test_bridge_clock_skips_disco_poll():
    assert "NO_DISCO_MODES" in _BRIDGE
    assert '"clock"' in _BRIDGE
    assert "clock_value()" in _BRIDGE


def test_readme_documents_clock_mode():
    low = _README.lower()
    assert "clock" in low or "uhr" in low
    assert "12" in _README
    assert "HHMMSS" in _README or "hhmmss" in low or "2×5" in _README or "2x5" in low


def test_matrix_viewer_names_clock():
    assert 'clock:"Uhr"' in _MATRIX_HTML or "clock:\"Uhr\"" in _MATRIX_HTML
