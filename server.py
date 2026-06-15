#!/usr/bin/env python3
"""Teufel Power HiFi controller — Flask + pigpio (replaces the old Node/Express
server that shelled out to the IR script per click).

The proven NEC IR logic is reused verbatim from teufel-power-hifi-controller.py
(imported via importlib because of the hyphenated filename) so the exact, working
timing/codes are kept. A single persistent pigpio handle is shared across requests
and serialised by one in-process lock — no subprocess spawn, no cross-process
pigpio wave race (the old flock workaround is no longer needed).

API is byte-for-byte compatible with the previous server.js so the dashboard /
nginx /proxy/hifi/ routes keep working unchanged.
"""

import datetime
import importlib.util
import json
import os
import threading

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

HERE = os.path.dirname(os.path.abspath(__file__))
PORT = int(os.environ.get("PORT", "5002"))
CONFIG_FILE = os.path.join(HERE, "controller-config.json")

# ---- reuse the existing, proven IR module (hyphenated name → importlib) ------
_spec = importlib.util.spec_from_file_location(
    "teufel_ir", os.path.join(HERE, "teufel-power-hifi-controller.py"))
teufel_ir = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(teufel_ir)
COMMANDS = teufel_ir.COMMANDS

_ir_lock = threading.Lock()
_remote = None


def _send(command, repeats=1):
    """Serialise all IR sends through one persistent TeufelIRRemote handle.

    Retries once with a fresh handle so a stale connection (e.g. after pigpiod
    restarted under us) recovers transparently within the same request.
    """
    global _remote
    with _ir_lock:
        for attempt in (1, 2):
            try:
                if _remote is None:
                    _remote = teufel_ir.TeufelIRRemote()
                if repeats > 1:
                    _remote.send_repeating(command, repeats)
                else:
                    _remote.send_command(command)
                return
            except Exception:
                _remote = None      # drop the broken handle, then retry once
                if attempt == 2:
                    raise


# ---- persistent device state (same file/shape as the Node version) ----------
DEFAULT_CONFIG = {
    "pythonScriptPath": os.path.join(HERE, "teufel-power-hifi-controller.py"),
    "lastCommand": None,
    "volume": 25,
    "currentInput": "BLUETOOTH",
    "muted": False,
    "powered": False,
}
_cfg_lock = threading.Lock()


def load_config():
    try:
        with open(CONFIG_FILE) as f:
            return {**DEFAULT_CONFIG, **json.load(f)}
    except (OSError, ValueError):
        return dict(DEFAULT_CONFIG)


config = load_config()


def save_config():
    with _cfg_lock:
        try:
            with open(CONFIG_FILE, "w") as f:
                json.dump(config, f, indent=2)
        except OSError:
            pass


def _do(command, repeats=1):
    _send(command, repeats)
    config["lastCommand"] = command
    save_config()


# ---- Flask app --------------------------------------------------------------
app = Flask(__name__, static_folder=None)
CORS(app)


@app.route("/")
def index():
    return send_from_directory(os.path.join(HERE, "public"), "index.html")


@app.route("/api/health")
def health():
    return jsonify(status="OK",
                   timestamp=datetime.datetime.now().isoformat(),
                   config=config)


@app.route("/api/status")
def status():
    return jsonify(powered=config["powered"], volume=config["volume"],
                   currentInput=config["currentInput"], muted=config["muted"],
                   lastCommand=config["lastCommand"])


@app.route("/api/power", methods=["POST"])
def power():
    try:
        _do("CMD_POWER")
        config["powered"] = not config["powered"]
        save_config()
        return jsonify(success=True, powered=config["powered"])
    except Exception as e:
        return jsonify(error=str(e)), 500


@app.route("/api/volume", methods=["POST"])
def volume():
    data = request.get_json(silent=True) or {}
    action, level = data.get("action"), data.get("level")
    try:
        command, repeats = "", 1
        if action == "up":
            command, repeats = "CMD_VOLUME_UP", (level or 1)
            config["volume"] = min(50, config["volume"] + repeats)
        elif action == "down":
            command, repeats = "CMD_VOLUME_DOWN", (level or 1)
            config["volume"] = max(0, config["volume"] - repeats)
        elif action == "set" and level is not None:
            steps = level - config["volume"]
            if steps > 0:
                command, repeats = "CMD_VOLUME_UP", steps
            elif steps < 0:
                command, repeats = "CMD_VOLUME_DOWN", abs(steps)
            config["volume"] = level
        if command and repeats > 0:
            _do(command, repeats)
        save_config()
        return jsonify(success=True, volume=config["volume"])
    except Exception as e:
        return jsonify(error=str(e)), 500


@app.route("/api/mute", methods=["POST"])
def mute():
    try:
        _do("CMD_MUTE")
        config["muted"] = not config["muted"]
        save_config()
        return jsonify(success=True, muted=config["muted"])
    except Exception as e:
        return jsonify(error=str(e)), 500


@app.route("/api/input", methods=["POST"])
def select_input():
    data = request.get_json(silent=True) or {}
    inputs = {"AUX": "CMD_AUX", "LINE": "CMD_LINE", "OPTICAL": "CMD_OPT",
              "USB": "CMD_USB", "BLUETOOTH": "CMD_BLUETOOTH"}
    command = inputs.get(data.get("input"))
    if not command:
        return jsonify(error="Invalid input"), 400
    try:
        _do(command)
        config["currentInput"] = data["input"]
        save_config()
        return jsonify(success=True, currentInput=config["currentInput"])
    except Exception as e:
        return jsonify(error=str(e)), 500


@app.route("/api/eq", methods=["POST"])
def eq():
    data = request.get_json(silent=True) or {}
    eq_cmds = {
        "bass": {"up": "CMD_BASS_UP", "down": "CMD_BASS_DOWN"},
        "mid": {"up": "CMD_MID_UP", "down": "CMD_MID_DOWN"},
        "treble": {"up": "CMD_TREBLE_UP", "down": "CMD_TREBLE_DOWN"},
    }
    command = eq_cmds.get(data.get("type"), {}).get(data.get("action"))
    if not command:
        return jsonify(error="Invalid EQ command"), 400
    try:
        _do(command)
        return jsonify(success=True, command=command)
    except Exception as e:
        return jsonify(error=str(e)), 500


@app.route("/api/balance", methods=["POST"])
def balance():
    data = request.get_json(silent=True) or {}
    cmds = {"left": "CMD_BAL_LEFT", "right": "CMD_BAL_RIGHT"}
    command = cmds.get(data.get("direction"))
    if not command:
        return jsonify(error="Invalid balance direction"), 400
    try:
        _do(command)
        return jsonify(success=True, command=command)
    except Exception as e:
        return jsonify(error=str(e)), 500


@app.route("/api/navigation", methods=["POST"])
def navigation():
    data = request.get_json(silent=True) or {}
    cmds = {"left": "CMD_LEFT", "right": "CMD_RIGHT"}
    command = cmds.get(data.get("direction"))
    if not command:
        return jsonify(error="Invalid navigation direction"), 400
    try:
        _do(command)
        return jsonify(success=True, command=command)
    except Exception as e:
        return jsonify(error=str(e)), 500


@app.route("/<path:p>")
def static_files(p):
    return send_from_directory(os.path.join(HERE, "public"), p)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT, threaded=True)
