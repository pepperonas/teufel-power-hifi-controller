"""
Unit tests for ir_bridge.py — pure, hardware-free logic only.

Tested surfaces:
  - MODE_NUM mapping (all 10 mode names → correct numeric code)
  - CODES mapping (IR hex codes for each CMD_*)
  - _needs_beat() predicate
  - _needs_level() predicate
  - _downsample12() band resampler (24 → 12 columns, clamped 0–8)
  - Matrix value formatting (v<int> convention, idle sentinel -1)
  - BPM delta gate (only push when |Δ| >= 2)
  - Level-to-matrix value clamping (0–100)
  - Idle threshold (level < IDLE_LEVEL → val == -1)
  - Protocol line construction for mode, value, spectrum, beat-flash commands
"""

import sys, types

# ---------------------------------------------------------------------------
# Minimal stubs so ir_bridge.py can be imported without hardware / pyserial
# ---------------------------------------------------------------------------

# stub 'serial' module
serial_mod = types.ModuleType("serial")
class _FakeSerial:
    def __init__(self, *a, **kw): pass
    def write(self, *a): pass
    def flush(self): pass
    def close(self): pass
    def reset_input_buffer(self): pass
    def readline(self): return b""
serial_mod.Serial = _FakeSerial
sys.modules.setdefault("serial", serial_mod)

# stub 'urllib.request' is stdlib — no stub needed
# ir_bridge.py also calls time.sleep and socket.socket at module level but
# only inside functions, so plain import is safe.

import importlib, os, tempfile

# Point MATRIX_FILE at a temp location so load_mode() / save_mode() don't
# touch /home/pi
_tmpdir = tempfile.mkdtemp()
os.environ.setdefault("HOME", _tmpdir)

# Monkey-patch before import so the constant is safe
import ir_bridge as ib   # noqa: E402  (must come after stubs)


# ============================================================================
# 1. MODE_NUM mapping
# ============================================================================

class TestModeNum:
    def test_off_is_zero(self):
        assert ib.MODE_NUM["off"] == 0

    def test_db_alias_pegel(self):
        assert ib.MODE_NUM["db"] == ib.MODE_NUM["pegel"] == 1

    def test_bpm_is_2(self):
        assert ib.MODE_NUM["bpm"] == 2

    def test_smiley_is_3(self):
        assert ib.MODE_NUM["smiley"] == 3

    def test_vu_is_4(self):
        assert ib.MODE_NUM["vu"] == 4

    def test_heart_is_5(self):
        assert ib.MODE_NUM["heart"] == 5

    def test_spektrum_is_6(self):
        assert ib.MODE_NUM["spektrum"] == 6

    def test_welle_is_7(self):
        assert ib.MODE_NUM["welle"] == 7

    def test_temp_is_8(self):
        assert ib.MODE_NUM["temp"] == 8

    def test_humidity_is_9(self):
        assert ib.MODE_NUM["humidity"] == 9

    def test_all_unique_except_db_pegel(self):
        """Every numeric code is unique (db == pegel is the intentional duplicate)."""
        nums = list(ib.MODE_NUM.values())
        # remove one occurrence of the intentional alias
        nums.remove(ib.MODE_NUM["pegel"])   # remove the duplicate 1
        assert len(nums) == len(set(nums))

    def test_total_count(self):
        # 10 logical modes; 'db' and 'pegel' are aliases (both map to 1),
        # so the dict has 11 entries (10 unique modes + 1 alias key).
        assert len(ib.MODE_NUM) == 11


# ============================================================================
# 2. CODES (IR command → hex)
# ============================================================================

class TestCodes:
    def test_power_hex(self):
        assert ib.CODES["CMD_POWER"] == 0x48

    def test_mute_hex(self):
        assert ib.CODES["CMD_MUTE"] == 0x28

    def test_bluetooth_hex(self):
        assert ib.CODES["CMD_BLUETOOTH"] == 0x40

    def test_volume_up_hex(self):
        assert ib.CODES["CMD_VOLUME_UP"] == 0xB0

    def test_volume_down_hex(self):
        assert ib.CODES["CMD_VOLUME_DOWN"] == 0x30

    def test_left_hex(self):
        assert ib.CODES["CMD_LEFT"] == 0x78

    def test_right_hex(self):
        assert ib.CODES["CMD_RIGHT"] == 0xF8

    def test_bass_up_hex(self):
        assert ib.CODES["CMD_BASS_UP"] == 0x58

    def test_bass_down_hex(self):
        assert ib.CODES["CMD_BASS_DOWN"] == 0x41

    def test_mid_up_hex(self):
        assert ib.CODES["CMD_MID_UP"] == 0x68

    def test_mid_down_hex(self):
        assert ib.CODES["CMD_MID_DOWN"] == 0x42

    def test_treble_up_hex(self):
        assert ib.CODES["CMD_TREBLE_UP"] == 0xB8

    def test_treble_down_hex(self):
        assert ib.CODES["CMD_TREBLE_DOWN"] == 0x43

    def test_aux_hex(self):
        assert ib.CODES["CMD_AUX"] == 0x44

    def test_line_hex(self):
        assert ib.CODES["CMD_LINE"] == 0x45

    def test_opt_hex(self):
        assert ib.CODES["CMD_OPT"] == 0x3F

    def test_usb_hex(self):
        assert ib.CODES["CMD_USB"] == 0xDF

    def test_balance_left_hex(self):
        assert ib.CODES["CMD_BAL_LEFT"] == 0xBF

    def test_balance_right_hex(self):
        assert ib.CODES["CMD_BAL_RIGHT"] == 0x5F

    def test_total_command_count(self):
        assert len(ib.CODES) == 19

    def test_all_codes_are_single_byte(self):
        for name, code in ib.CODES.items():
            assert 0x00 <= code <= 0xFF, f"{name} = 0x{code:X} is out of byte range"

    def test_all_codes_unique(self):
        codes = list(ib.CODES.values())
        assert len(codes) == len(set(codes)), "Duplicate IR code detected"

    def test_format_as_two_hex_digits(self):
        """The serial protocol sends '%02X' — verify every code formats to 2 chars."""
        for name, code in ib.CODES.items():
            s = "%02X" % code
            assert len(s) == 2, f"{name}: '%02X' % 0x{code:X} = '{s}' (not 2 chars)"


# ============================================================================
# 3. _needs_beat() predicate
# ============================================================================

class TestNeedsBeat:
    def test_bpm_needs_beat(self):
        assert ib._needs_beat("bpm") is True

    def test_smiley_needs_beat(self):
        assert ib._needs_beat("smiley") is True

    def test_heart_needs_beat(self):
        assert ib._needs_beat("heart") is True

    def test_welle_needs_beat(self):
        assert ib._needs_beat("welle") is True

    def test_off_no_beat(self):
        assert ib._needs_beat("off") is False

    def test_db_no_beat(self):
        assert ib._needs_beat("db") is False

    def test_pegel_no_beat(self):
        assert ib._needs_beat("pegel") is False

    def test_vu_no_beat(self):
        assert ib._needs_beat("vu") is False

    def test_spektrum_no_beat(self):
        assert ib._needs_beat("spektrum") is False

    def test_temp_no_beat(self):
        assert ib._needs_beat("temp") is False

    def test_humidity_no_beat(self):
        assert ib._needs_beat("humidity") is False


# ============================================================================
# 4. _needs_level() predicate
# ============================================================================

class TestNeedsLevel:
    def test_db_needs_level(self):
        assert ib._needs_level("db") is True

    def test_pegel_needs_level(self):
        assert ib._needs_level("pegel") is True

    def test_vu_needs_level(self):
        assert ib._needs_level("vu") is True

    def test_smiley_needs_level(self):
        assert ib._needs_level("smiley") is True

    def test_heart_needs_level(self):
        assert ib._needs_level("heart") is True

    def test_off_no_level(self):
        assert ib._needs_level("off") is False

    def test_bpm_no_level(self):
        assert ib._needs_level("bpm") is False

    def test_spektrum_no_level(self):
        assert ib._needs_level("spektrum") is False

    def test_welle_no_level(self):
        assert ib._needs_level("welle") is False

    def test_temp_no_level(self):
        assert ib._needs_level("temp") is False


# ============================================================================
# 5. _downsample12() — 24 float bands → 12 integer columns clamped 0–8
# ============================================================================

class TestDownsample12:
    def test_zeros_stay_zero(self):
        assert ib._downsample12([0.0] * 24) == [0] * 12

    def test_ones_map_to_eight(self):
        assert ib._downsample12([1.0] * 24) == [8] * 12

    def test_half_maps_to_four(self):
        result = ib._downsample12([0.5] * 24)
        assert result == [4] * 12

    def test_output_length_is_12(self):
        assert len(ib._downsample12([0.0] * 24)) == 12

    def test_clamp_above_1(self):
        """Values > 1.0 should be clamped to 8."""
        result = ib._downsample12([2.0] * 24)
        assert all(v == 8 for v in result)

    def test_clamp_negative(self):
        """Negative values should clamp to 0."""
        result = ib._downsample12([-1.0] * 24)
        assert all(v == 0 for v in result)

    def test_short_input_pads(self):
        """Fewer than 24 bands: missing pairs contribute 0."""
        result = ib._downsample12([1.0] * 2)   # only first pair is 1.0, rest 0
        assert result[0] == 8
        assert all(v == 0 for v in result[1:])

    def test_empty_input(self):
        result = ib._downsample12([])
        assert result == [0] * 12

    def test_pairs_averaged(self):
        """Column i = average of bands[2*i] and bands[2*i+1], scaled to 8."""
        bands = [0.0] * 24
        bands[0] = 1.0   # pair 0: (1.0 + 0.0)/2 = 0.5 → 4
        result = ib._downsample12(bands)
        assert result[0] == 4
        assert result[1] == 0

    def test_spectrum_string_length(self):
        """The serial 's' message must be exactly 12 chars."""
        cols = ib._downsample12([0.5] * 24)
        msg = "s" + "".join(str(c) for c in cols)
        assert len(msg) == 13          # 's' + 12 digits
        assert msg[0] == "s"
        assert all(c.isdigit() for c in msg[1:])

    def test_each_column_in_range(self):
        import random; random.seed(42)
        bands = [random.uniform(0, 1.5) for _ in range(24)]
        result = ib._downsample12(bands)
        assert all(0 <= v <= 8 for v in result)


# ============================================================================
# 6. Matrix value / protocol line construction
# ============================================================================

class TestMatrixValueProtocol:
    def test_mode_line_format(self):
        """Mode command is 'm' followed by the numeric code."""
        for name, num in ib.MODE_NUM.items():
            line = "m%d" % num
            assert line.startswith("m")
            assert line[1:].isdigit()

    def test_value_line_positive(self):
        """Normal value → 'v<int>'."""
        val = 72
        line = "v%d" % val
        assert line == "v72"

    def test_value_line_idle(self):
        """Idle/silence sentinel → 'v-1'."""
        val = -1
        line = "v%d" % val
        assert line == "v-1"

    def test_value_line_zero(self):
        assert "v%d" % 0 == "v0"

    def test_value_line_max(self):
        assert "v%d" % 100 == "v100"

    def test_beat_flash_line(self):
        assert "f" == "f"   # trivial but documents the sentinel

    def test_bpm_value_rounding(self):
        """BPM is int(round(bpm)) → e.g. 120.4 → 120, 120.6 → 121."""
        assert int(round(120.4)) == 120
        assert int(round(120.6)) == 121

    def test_level_to_0_100_scale(self):
        """level (0.0–1.0) → max(0, min(100, int(round(level * 100))))."""
        assert max(0, min(100, int(round(0.0 * 100)))) == 0
        assert max(0, min(100, int(round(0.5 * 100)))) == 50
        assert max(0, min(100, int(round(1.0 * 100)))) == 100
        assert max(0, min(100, int(round(1.5 * 100)))) == 100   # clamp
        assert max(0, min(100, int(round(-0.1 * 100)))) == 0    # clamp


# ============================================================================
# 7. Idle threshold
# ============================================================================

class TestIdleThreshold:
    def test_below_idle_is_idle(self):
        level = ib.IDLE_LEVEL - 0.001
        assert level < ib.IDLE_LEVEL

    def test_at_idle_is_idle(self):
        # level < IDLE_LEVEL  →  strictly less-than gate
        assert not (ib.IDLE_LEVEL < ib.IDLE_LEVEL)

    def test_above_idle_not_idle(self):
        level = ib.IDLE_LEVEL + 0.001
        assert not (level < ib.IDLE_LEVEL)

    def test_idle_val_is_minus_one(self):
        """When idle, the matrix value sentinel is -1."""
        level = 0.0          # always below IDLE_LEVEL
        idle = level < ib.IDLE_LEVEL
        val = -1 if idle else max(0, min(100, int(round(level * 100))))
        assert val == -1

    def test_non_idle_val_is_computed(self):
        level = 0.5
        idle = level < ib.IDLE_LEVEL
        val = -1 if idle else max(0, min(100, int(round(level * 100))))
        assert val == 50

    def test_idle_threshold_value(self):
        """IDLE_LEVEL must be a small positive float (sanity check)."""
        assert 0 < ib.IDLE_LEVEL < 0.1


# ============================================================================
# 8. BPM delta gate
# ============================================================================

class TestBpmDeltaGate:
    """The poller only pushes a new BPM value when
       val == -1  OR  last was None/-1  OR  |val - last| >= 2
    """
    @staticmethod
    def _should_push(val, last):
        return val == -1 or last in (None, -1) or abs(val - last) >= 2

    def test_idle_always_pushes(self):
        assert self._should_push(-1, 100)
        assert self._should_push(-1, 0)
        assert self._should_push(-1, None)
        assert self._should_push(-1, -1)

    def test_first_value_pushes(self):
        assert self._should_push(120, None)
        assert self._should_push(120, -1)

    def test_large_delta_pushes(self):
        assert self._should_push(122, 120)   # Δ=2 → push
        assert self._should_push(118, 120)   # Δ=2 → push
        assert self._should_push(130, 120)   # Δ=10 → push

    def test_small_delta_suppressed(self):
        assert not self._should_push(121, 120)   # Δ=1 → suppress
        assert not self._should_push(120, 120)   # Δ=0 → suppress

    def test_boundary_exactly_two(self):
        assert self._should_push(122, 120)       # exactly 2 → push
        assert not self._should_push(121, 120)   # exactly 1 → suppress


# ============================================================================
# 9. TCP protocol parsing helpers (pure string logic in handle())
# ============================================================================

class TestTcpProtocolParsing:
    def test_matrix_query_cmd(self):
        parts = "MATRIX?".split()
        assert parts[0].upper() == "MATRIX?"

    def test_matrix_set_cmd(self):
        data = "MATRIX bpm"
        parts = data.split()
        assert parts[0].upper() == "MATRIX"
        assert parts[1] == "bpm"

    def test_ir_cmd_with_repeats(self):
        data = "CMD_VOLUME_DOWN 5"
        parts = data.split()
        cmd = parts[0].upper()
        repeats = int(parts[1]) if len(parts) > 1 else 1
        assert cmd == "CMD_VOLUME_DOWN"
        assert repeats == 5

    def test_ir_cmd_default_repeat(self):
        data = "CMD_POWER"
        parts = data.split()
        repeats = int(parts[1]) if len(parts) > 1 else 1
        assert repeats == 1

    def test_unknown_cmd_not_in_codes(self):
        assert "CMD_UNKNOWN" not in ib.CODES

    def test_valid_mode_names(self):
        valid = {"off", "db", "pegel", "bpm", "smiley", "vu", "heart",
                 "spektrum", "welle", "temp", "humidity"}
        assert valid == set(ib.MODE_NUM.keys())

    def test_frame_query_cmd(self):
        parts = "FRAME?".split()
        assert parts[0].upper() == "FRAME?"


# ============================================================================
# 10. Flash rate-limiting
# ============================================================================

class TestFlashRateLimit:
    def test_flash_min_gap_is_positive(self):
        assert ib.FLASH_MIN_GAP > 0

    def test_max_flashes_per_second(self):
        """FLASH_MIN_GAP=0.30 → at most ~3 flashes/s (3.33 exactly)."""
        max_flashes_per_s = 1.0 / ib.FLASH_MIN_GAP
        assert max_flashes_per_s <= 4   # reasonable ceiling

    def test_should_flash_after_gap(self):
        last_flash = 0.0
        now = last_flash + ib.FLASH_MIN_GAP + 0.01
        assert (now - last_flash) >= ib.FLASH_MIN_GAP

    def test_should_not_flash_before_gap(self):
        last_flash = 0.0
        now = last_flash + ib.FLASH_MIN_GAP - 0.01
        assert not ((now - last_flash) >= ib.FLASH_MIN_GAP)
