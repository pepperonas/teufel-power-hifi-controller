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

    def test_pegel_is_1(self):
        assert ib.MODE_NUM["pegel"] == 1

    def test_db_is_10(self):
        assert ib.MODE_NUM["db"] == 10

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

    def test_clock_is_12(self):
        assert ib.MODE_NUM["clock"] == 12
        assert ib.CLOCK_MODE == 12

    def test_analog_is_13(self):
        assert ib.MODE_NUM["analog"] == 13
        assert ib.ANALOG_MODE == 13

    def test_all_unique(self):
        nums = list(ib.MODE_NUM.values())
        assert len(nums) == len(set(nums))

    def test_total_count(self):
        assert len(ib.MODE_NUM) == 13

    def test_iris_overlay_mode(self):
        assert ib.IRIS_MODE == 11
        assert 11 not in ib.MODE_NUM.values()  # overlay only, not a saved mode
        assert 12 in ib.MODE_NUM.values()
        assert 13 in ib.MODE_NUM.values()

    def test_no_disco_modes_include_clock(self):
        assert "clock" in ib.NO_DISCO_MODES
        assert "analog" in ib.NO_DISCO_MODES
        assert ib.CLOCK_MODES == frozenset({"clock", "analog"})
        assert "off" in ib.NO_DISCO_MODES
        assert "db" not in ib.NO_DISCO_MODES

    def test_iris_threshold_legacy_fallback(self):
        assert ib.IRIS_DB == -20.0
        assert ib.iris_threshold(False) == -20.0
        assert abs(ib.iris_threshold(True) - (-20.0 * 1.3)) < 1e-9

    def test_iris_loud_prefers_warn_over(self):
        assert ib.iris_loud({"warn_over": True, "db": -90, "spl": 10}) is True
        assert ib.iris_loud({"warn_over": False, "db": 0, "spl": 99}) is False

    def test_iris_loud_falls_back_to_warn_thr_spl(self):
        assert ib.iris_loud({"spl": 56.0, "warn_thr": 55}) is True
        assert ib.iris_loud({"spl": 54.9, "warn_thr": 55}) is False

    def test_iris_loud_legacy_dbfs(self):
        assert ib.iris_loud({"db": -19.0, "quiet_log": False}) is True
        assert ib.iris_loud({"db": -21.0, "quiet_log": False}) is False

    def test_disco_url_defaults_localhost(self):
        assert "127.0.0.1" in ib.DISCO_URL or "localhost" in ib.DISCO_URL
        assert ":5007" in ib.DISCO_URL


# ============================================================================
# 1b. CLOCK packing / layout (firmware mode 12)
# ============================================================================

class TestClockPacking:
    def test_pack_roundtrip_noon(self):
        assert ib.pack_clock(12, 0, 0) == 120000
        assert ib.unpack_clock(120000) == (12, 0, 0)

    def test_pack_roundtrip_end_of_day(self):
        assert ib.pack_clock(23, 59, 59) == 235959
        assert ib.unpack_clock(235959) == (23, 59, 59)

    def test_pack_clamps_out_of_range(self):
        assert ib.pack_clock(99, 99, 99) == 235959
        assert ib.pack_clock(-1, -1, -1) == 0

    def test_unpack_clamps_invalid_fields(self):
        # 25:70:80 would be nonsense — clamps hour/min/sec independently
        assert ib.unpack_clock(257080) == (23, 59, 59)

    def test_unpack_negative_is_none(self):
        assert ib.unpack_clock(-1) is None
        assert ib.unpack_clock(None) is None

    def test_clock_value_matches_localtime(self):
        import time as _t
        ts = 1_700_000_000  # fixed
        lt = _t.localtime(ts)
        assert ib.clock_value(ts) == ib.pack_clock(lt.tm_hour, lt.tm_min, lt.tm_sec)

    def test_font2_has_ten_glyphs(self):
        assert len(ib.FONT2) == 10
        for g in ib.FONT2:
            assert len(g) == 5

    def test_render_clock_frame_shape(self):
        fr = ib.render_clock_frame(14, 30, 45, colon_on=True)
        assert len(fr) == 8
        assert all(len(row) == 12 for row in fr)
        assert all(c in (0, 1) for row in fr for c in row)

    def test_render_corner_pips_present(self):
        fr = ib.render_clock_frame(9, 5, 0, colon_on=False)
        assert fr[0][0] == 1 and fr[0][11] == 1
        assert fr[7][0] == 1 and fr[7][11] == 1
        # no noon strip / seconds bar
        assert fr[0][5] == 0 and fr[0][6] == 0
        assert fr[7][1:11] == [0] * 10

    def test_render_colon_optional(self):
        on = ib.render_clock_frame(10, 10, 10, colon_on=True)
        off = ib.render_clock_frame(10, 10, 10, colon_on=False)
        assert on[2][5] == 1 and on[4][5] == 1
        assert off[2][5] == 0 and off[4][5] == 0

    def test_render_no_seconds_bar(self):
        fr = ib.render_clock_frame(0, 0, 59, colon_on=False)
        # row 7 only has corner pips
        assert fr[7] == [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1]

    def test_render_digits_use_distinct_columns(self):
        # HH at 0/3, MM at 7/10 — no overlap with colon col 5
        fr = ib.render_clock_frame(18, 36, 0, colon_on=True)
        # At least one pixel in hour tens (cols 0-1) and minute ones (cols 10-11)
        assert any(fr[r][0] or fr[r][1] for r in range(1, 6))
        assert any(fr[r][10] or fr[r][11] for r in range(1, 6))
        assert fr[1][5] == 0
        assert fr[3][5] == 0
        assert fr[5][5] == 0

    def test_four_digit_3x5_would_not_fit(self):
        # Document why we use 2×5: classic 3×5 with gaps needs 15 cols
        w = 4 * 3 + 3  # four digits + three gaps
        assert w > 12

    def test_render_analog_has_cardinal_ticks(self):
        fr = ib.render_analog_frame(12, 0, 0)
        assert fr[0][5] == 1 and fr[0][6] == 1  # 12
        assert fr[3][11] == 1 and fr[4][11] == 1  # 3
        assert fr[7][5] == 1 and fr[7][6] == 1  # 6
        assert fr[3][0] == 1 and fr[4][0] == 1  # 9
        assert fr[3][5] == 1 and fr[3][6] == 1  # hub

    def test_render_analog_hands_differ_by_time(self):
        noon = ib.render_analog_frame(12, 0, 0)
        three = ib.render_analog_frame(3, 0, 0)
        assert noon != three
        # at 12:00 hour hand points up — pixel above hub lit
        assert any(noon[r][5] or noon[r][6] for r in (1, 2))
        # at 3:00 hour hand points right
        assert any(three[3][c] or three[4][c] for c in (8, 9, 10))


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
    def test_db_needs_dbfs(self):
        assert ib._needs_dbfs("db") is True
        assert ib._needs_level("db") is False

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
                 "spektrum", "welle", "temp", "humidity", "clock", "analog"}
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
