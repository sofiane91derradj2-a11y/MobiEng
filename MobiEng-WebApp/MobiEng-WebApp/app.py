"""
MobiEng Web Server
==================
Production-ready Flask application that:
  • Serves the MobiEng app at /
  • Provides /storage/* API for persistent server-side data storage
  • Provides /api/backup and /api/restore endpoints
  • Provides /api/users/* for multi-user data isolation
  • Supports multiple concurrent users via session-based storage folders
  • Can run locally (python app.py) or with a WSGI server (gunicorn)
"""

import os
import re
import json
import time
import uuid
import logging
from pathlib import Path
from flask import (
    Flask, request, jsonify, send_file,
    session, make_response, abort
)

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent.resolve()
APP_DIR  = BASE_DIR / "app"
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# ── App setup ─────────────────────────────────────────────────────────────────
app = Flask(__name__, static_folder=str(APP_DIR), static_url_path="")
app.secret_key = os.environ.get("SECRET_KEY", os.urandom(32))
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_HTTPONLY"] = True

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
log = logging.getLogger("mobieng")

# ── Session / User helpers ────────────────────────────────────────────────────
def _get_user_id() -> str:
    """Return a persistent anonymous user ID stored in the browser session."""
    if "uid" not in session:
        session["uid"] = str(uuid.uuid4())
    return session["uid"]

def _user_dir(uid: str) -> Path:
    """Return (and create) the storage directory for this user."""
    # Sanitize uid to safe characters only
    safe = re.sub(r"[^a-zA-Z0-9\-]", "", uid)[:64]
    d = DATA_DIR / safe
    d.mkdir(parents=True, exist_ok=True)
    return d

def _key_path(user_dir: Path, key: str) -> Path:
    safe = "".join(c if c.isalnum() or c in "._-" else f"_{ord(c):02x}_" for c in key)
    return user_dir / f"{safe}.json"

def _read_all(user_dir: Path) -> dict:
    result = {}
    for p in user_dir.glob("*.json"):
        try:
            obj = json.loads(p.read_text(encoding="utf-8"))
            result[obj.get("key", p.stem)] = obj.get("value")
        except Exception:
            pass
    return result

# ── Storage API ───────────────────────────────────────────────────────────────

@app.route("/storage/keys")
def storage_keys():
    uid  = _get_user_id()
    udir = _user_dir(uid)
    keys = list(_read_all(udir).keys())
    return jsonify({"keys": keys})

@app.route("/storage/get/<path:key>")
def storage_get(key):
    uid  = _get_user_id()
    udir = _user_dir(uid)
    path = _key_path(udir, key)
    if not path.exists():
        return jsonify({"found": False, "value": None})
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
        return jsonify({"found": True, "value": obj.get("value")})
    except Exception:
        return jsonify({"found": False, "value": None})

@app.route("/storage/set", methods=["POST"])
def storage_set():
    uid  = _get_user_id()
    udir = _user_dir(uid)
    body  = request.get_json(force=True, silent=True) or {}
    key   = body.get("key", "")
    value = body.get("value")
    if not key:
        return jsonify({"ok": False, "error": "missing key"}), 400
    path = _key_path(udir, key)
    path.write_text(
        json.dumps({"key": key, "value": value, "updated": time.time()},
                   ensure_ascii=False),
        encoding="utf-8"
    )
    return jsonify({"ok": True})

@app.route("/storage/remove", methods=["POST"])
def storage_remove():
    uid  = _get_user_id()
    udir = _user_dir(uid)
    body = request.get_json(force=True, silent=True) or {}
    key  = body.get("key", "")
    path = _key_path(udir, key)
    if path.exists():
        path.unlink()
    return jsonify({"ok": True})

@app.route("/storage/clear", methods=["POST"])
def storage_clear():
    uid  = _get_user_id()
    udir = _user_dir(uid)
    for p in udir.glob("*.json"):
        p.unlink(missing_ok=True)
    return jsonify({"ok": True})

# ── Backup / Restore ──────────────────────────────────────────────────────────

@app.route("/api/backup", methods=["GET"])
def api_backup():
    uid  = _get_user_id()
    udir = _user_dir(uid)
    all_data = _read_all(udir)
    backup = {
        "v":       "mobieng-web-backup-1",
        "uid":     uid,
        "created": time.time(),
        "data":    all_data
    }
    response = make_response(json.dumps(backup, ensure_ascii=False, indent=2))
    response.headers["Content-Type"] = "application/json"
    response.headers["Content-Disposition"] = 'attachment; filename="mobieng-backup.json"'
    return response

@app.route("/api/restore", methods=["POST"])
def api_restore():
    uid  = _get_user_id()
    udir = _user_dir(uid)
    body = request.get_json(force=True, silent=True) or {}
    data = body.get("data", {})
    if not isinstance(data, dict):
        return jsonify({"ok": False, "error": "invalid format"}), 400
    for key, value in data.items():
        path = _key_path(udir, key)
        path.write_text(
            json.dumps({"key": key, "value": value, "updated": time.time()},
                       ensure_ascii=False),
            encoding="utf-8"
        )
    log.info("Restored %d keys for user %s", len(data), uid[:8])
    return jsonify({"ok": True, "restored": len(data)})

@app.route("/api/storage/info", methods=["GET"])
def api_storage_info():
    uid  = _get_user_id()
    udir = _user_dir(uid)
    files = list(udir.glob("*.json"))
    total = sum(f.stat().st_size for f in files)
    return jsonify({
        "ok":    True,
        "uid":   uid,
        "files": len(files),
        "bytes": total,
        "mb":    round(total / 1024 / 1024, 4)
    })

# ── Health check ──────────────────────────────────────────────────────────────

@app.route("/health")
def health():
    return jsonify({"status": "ok", "version": "8.0.1"})

# ── Serve the app ─────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return send_file(APP_DIR / "index.html")

@app.route("/<path:filename>")
def static_files(filename):
    full = APP_DIR / filename
    if full.exists() and full.is_file():
        return send_file(full)
    abort(404)

# ── Dev entry point ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("DEBUG", "false").lower() == "true"
    log.info("MobiEng Web starting on http://%s:%d", host, port)
    app.run(host=host, port=port, debug=debug)
