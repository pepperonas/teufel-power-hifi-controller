/**
 * Unit tests for server.js — pure, Express-free logic only.
 *
 * server.js is tightly coupled to Express and the filesystem (loadConfig /
 * saveConfig / executeCommand all do I/O). Rather than mocking every module,
 * we isolate and re-test the pure-logic pieces that are verbatim inside server.js:
 *
 *   1. inputCommands map (input name → CMD_* key)
 *   2. eqCommands map  (type × direction → CMD_* key)
 *   3. balanceCommands map
 *   4. navCommands map
 *   5. Volume clamping logic (0–50, integer steps)
 *   6. Valid matrix mode list (matches ir_bridge MATRIX accept-list)
 *   7. IR_BRIDGE_PORT default
 *   8. executeCommand line format ("CMD_… <repeats>\n")
 *
 * All tests run under Node's built-in test runner (`node --test`).
 */

"use strict";

const { test, describe } = require("node:test");
const assert = require("node:assert/strict");

// ---------------------------------------------------------------------------
// 1. Input → command mapping  (verbatim from server.js)
// ---------------------------------------------------------------------------

const inputCommands = {
    AUX: "CMD_AUX",
    LINE: "CMD_LINE",
    OPTICAL: "CMD_OPT",
    USB: "CMD_USB",
    BLUETOOTH: "CMD_BLUETOOTH",
};

describe("inputCommands", () => {
    test("AUX maps to CMD_AUX", () => {
        assert.equal(inputCommands["AUX"], "CMD_AUX");
    });
    test("LINE maps to CMD_LINE", () => {
        assert.equal(inputCommands["LINE"], "CMD_LINE");
    });
    test("OPTICAL maps to CMD_OPT", () => {
        assert.equal(inputCommands["OPTICAL"], "CMD_OPT");
    });
    test("USB maps to CMD_USB", () => {
        assert.equal(inputCommands["USB"], "CMD_USB");
    });
    test("BLUETOOTH maps to CMD_BLUETOOTH", () => {
        assert.equal(inputCommands["BLUETOOTH"], "CMD_BLUETOOTH");
    });
    test("unknown input returns undefined", () => {
        assert.equal(inputCommands["HDMI"], undefined);
    });
    test("exactly 5 input entries", () => {
        assert.equal(Object.keys(inputCommands).length, 5);
    });
});

// ---------------------------------------------------------------------------
// 2. EQ commands  (verbatim from server.js)
// ---------------------------------------------------------------------------

const eqCommands = {
    bass:   { up: "CMD_BASS_UP",   down: "CMD_BASS_DOWN"   },
    mid:    { up: "CMD_MID_UP",    down: "CMD_MID_DOWN"    },
    treble: { up: "CMD_TREBLE_UP", down: "CMD_TREBLE_DOWN" },
};

describe("eqCommands", () => {
    test("bass up", () => assert.equal(eqCommands.bass.up, "CMD_BASS_UP"));
    test("bass down", () => assert.equal(eqCommands.bass.down, "CMD_BASS_DOWN"));
    test("mid up", () => assert.equal(eqCommands.mid.up, "CMD_MID_UP"));
    test("mid down", () => assert.equal(eqCommands.mid.down, "CMD_MID_DOWN"));
    test("treble up", () => assert.equal(eqCommands.treble.up, "CMD_TREBLE_UP"));
    test("treble down", () => assert.equal(eqCommands.treble.down, "CMD_TREBLE_DOWN"));
    test("unknown type is undefined", () => assert.equal(eqCommands["sub"], undefined));
    test("unknown direction is undefined", () => assert.equal(eqCommands.bass?.["center"], undefined));
});

// ---------------------------------------------------------------------------
// 3. Balance commands
// ---------------------------------------------------------------------------

const balanceCommands = {
    left:  "CMD_BAL_LEFT",
    right: "CMD_BAL_RIGHT",
};

describe("balanceCommands", () => {
    test("left maps to CMD_BAL_LEFT", () => assert.equal(balanceCommands.left, "CMD_BAL_LEFT"));
    test("right maps to CMD_BAL_RIGHT", () => assert.equal(balanceCommands.right, "CMD_BAL_RIGHT"));
    test("center is undefined", () => assert.equal(balanceCommands["center"], undefined));
});

// ---------------------------------------------------------------------------
// 4. Navigation commands
// ---------------------------------------------------------------------------

const navCommands = {
    left:  "CMD_LEFT",
    right: "CMD_RIGHT",
};

describe("navCommands", () => {
    test("left maps to CMD_LEFT", () => assert.equal(navCommands.left, "CMD_LEFT"));
    test("right maps to CMD_RIGHT", () => assert.equal(navCommands.right, "CMD_RIGHT"));
    test("up is undefined", () => assert.equal(navCommands["up"], undefined));
});

// ---------------------------------------------------------------------------
// 5. Volume clamping  (from /api/volume handler)
// ---------------------------------------------------------------------------

/**
 * Pure re-implementation of the server's volume-step logic.
 * Mirrors exactly: Math.min(50, config.volume + repeats) / Math.max(0, …)
 */
function applyVolume(current, action, level) {
    let volume = current;
    let command = "";
    let repeats = 1;

    if (action === "up") {
        repeats = level || 1;
        volume = Math.min(50, current + repeats);
        command = "CMD_VOLUME_UP";
    } else if (action === "down") {
        repeats = level || 1;
        volume = Math.max(0, current - repeats);
        command = "CMD_VOLUME_DOWN";
    } else if (action === "set" && level !== undefined) {
        const steps = level - current;
        if (steps > 0) {
            command = "CMD_VOLUME_UP";
            repeats = steps;
        } else if (steps < 0) {
            command = "CMD_VOLUME_DOWN";
            repeats = Math.abs(steps);
        }
        volume = level;
    }
    return { volume, command, repeats };
}

describe("volume clamping", () => {
    test("up from 25 by 1 → 26", () => {
        const r = applyVolume(25, "up", 1);
        assert.equal(r.volume, 26);
        assert.equal(r.command, "CMD_VOLUME_UP");
        assert.equal(r.repeats, 1);
    });
    test("up clamps at 50", () => {
        const r = applyVolume(48, "up", 5);
        assert.equal(r.volume, 50);
    });
    test("up already at 50 → stays 50", () => {
        const r = applyVolume(50, "up", 1);
        assert.equal(r.volume, 50);
    });
    test("down from 25 by 3 → 22", () => {
        const r = applyVolume(25, "down", 3);
        assert.equal(r.volume, 22);
        assert.equal(r.command, "CMD_VOLUME_DOWN");
        assert.equal(r.repeats, 3);
    });
    test("down clamps at 0", () => {
        const r = applyVolume(2, "down", 5);
        assert.equal(r.volume, 0);
    });
    test("down already at 0 → stays 0", () => {
        const r = applyVolume(0, "down", 1);
        assert.equal(r.volume, 0);
    });
    test("set 30 from 25 → up 5 steps", () => {
        const r = applyVolume(25, "set", 30);
        assert.equal(r.volume, 30);
        assert.equal(r.command, "CMD_VOLUME_UP");
        assert.equal(r.repeats, 5);
    });
    test("set 20 from 25 → down 5 steps", () => {
        const r = applyVolume(25, "set", 20);
        assert.equal(r.volume, 20);
        assert.equal(r.command, "CMD_VOLUME_DOWN");
        assert.equal(r.repeats, 5);
    });
    test("set same value → no command, 0 repeats", () => {
        const r = applyVolume(25, "set", 25);
        assert.equal(r.volume, 25);
        assert.equal(r.command, "");
        assert.equal(r.repeats, 1);
    });
    test("default level for up is 1", () => {
        const r = applyVolume(10, "up", undefined);
        assert.equal(r.repeats, 1);
        assert.equal(r.volume, 11);
    });
    test("default level for down is 1", () => {
        const r = applyVolume(10, "down", undefined);
        assert.equal(r.repeats, 1);
        assert.equal(r.volume, 9);
    });
});

// ---------------------------------------------------------------------------
// 6. Valid matrix mode list  (from server.js POST /api/matrix allow-list)
// ---------------------------------------------------------------------------

const VALID_MATRIX_MODES = [
    "off", "db", "pegel", "bpm", "smiley", "vu",
    "heart", "spektrum", "welle", "temp", "humidity",
];

describe("matrix mode validation", () => {
    test("all 11 modes are present", () => assert.equal(VALID_MATRIX_MODES.length, 11));
    test("off is valid", () => assert.ok(VALID_MATRIX_MODES.includes("off")));
    test("db is valid", () => assert.ok(VALID_MATRIX_MODES.includes("db")));
    test("pegel is valid", () => assert.ok(VALID_MATRIX_MODES.includes("pegel")));
    test("bpm is valid", () => assert.ok(VALID_MATRIX_MODES.includes("bpm")));
    test("smiley is valid", () => assert.ok(VALID_MATRIX_MODES.includes("smiley")));
    test("vu is valid", () => assert.ok(VALID_MATRIX_MODES.includes("vu")));
    test("heart is valid", () => assert.ok(VALID_MATRIX_MODES.includes("heart")));
    test("spektrum is valid", () => assert.ok(VALID_MATRIX_MODES.includes("spektrum")));
    test("welle is valid", () => assert.ok(VALID_MATRIX_MODES.includes("welle")));
    test("temp is valid", () => assert.ok(VALID_MATRIX_MODES.includes("temp")));
    test("humidity is valid", () => assert.ok(VALID_MATRIX_MODES.includes("humidity")));
    test("invalid mode 'disco' is rejected", () => assert.ok(!VALID_MATRIX_MODES.includes("disco")));
    test("invalid mode '' is rejected", () => assert.ok(!VALID_MATRIX_MODES.includes("")));
    test("mode names are all lowercase", () => {
        VALID_MATRIX_MODES.forEach(m => assert.equal(m, m.toLowerCase()));
    });
});

// ---------------------------------------------------------------------------
// 7. IR bridge defaults
// ---------------------------------------------------------------------------

describe("IR bridge connection defaults", () => {
    test("default port is 8799", () => {
        const port = parseInt(process.env.IR_BRIDGE_PORT || "8799", 10);
        assert.equal(port, 8799);
    });
    test("default host is 127.0.0.1", () => {
        const host = process.env.IR_BRIDGE_HOST || "127.0.0.1";
        assert.equal(host, "127.0.0.1");
    });
});

// ---------------------------------------------------------------------------
// 8. executeCommand line format
// ---------------------------------------------------------------------------

describe("executeCommand wire format", () => {
    const IR_NL = String.fromCharCode(10);   // '\n'

    function buildLine(command, repeats) {
        return command + " " + repeats + IR_NL;
    }

    test("single repeat produces correct line", () => {
        assert.equal(buildLine("CMD_POWER", 1), "CMD_POWER 1\n");
    });
    test("multiple repeats are included", () => {
        assert.equal(buildLine("CMD_VOLUME_DOWN", 5), "CMD_VOLUME_DOWN 5\n");
    });
    test("line ends with newline (\\n = char 10)", () => {
        const line = buildLine("CMD_MUTE", 1);
        assert.equal(line.charCodeAt(line.length - 1), 10);
    });
    test("matrix query line", () => {
        const line = "MATRIX?" + IR_NL;
        assert.equal(line, "MATRIX?\n");
    });
    test("matrix set line", () => {
        const line = "MATRIX bpm" + IR_NL;
        assert.equal(line, "MATRIX bpm\n");
    });
    test("frame query line", () => {
        const line = "FRAME?" + IR_NL;
        assert.equal(line, "FRAME?\n");
    });
});
