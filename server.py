#!/usr/bin/env python3
"""Simple Tracker Sheet server.

Serves the app and stores the tracker data in a JSON file so everybody who
opens the page edits the same data. Standard library only.

    python3 server.py                 # http://localhost:8000
    python3 server.py --port 9000 --data /srv/tracker
    python3 server.py --set-pin       # set / reset the edit PIN (asks for it)
    python3 server.py --set-pin 5678  # set / reset the edit PIN directly

The edit PIN starts as 1234 until it is changed.
"""
import argparse
import getpass
import hashlib
import hmac
import json
import os
import re
import secrets
import threading
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

APP_DIR = Path(__file__).resolve().parent
STATIC_FILES = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/index.html": ("index.html", "text/html; charset=utf-8"),
    "/vendor/xlsx.full.min.js": ("vendor/xlsx.full.min.js", "text/javascript; charset=utf-8"),
    "/vendor/exceljs.min.js": ("vendor/exceljs.min.js", "text/javascript; charset=utf-8"),
}
PIN_RE = re.compile(r"^\d{4,8}$")
DEFAULT_PIN = "1234"
MAX_BODY = 20 * 1024 * 1024
TOKEN_TTL = 15 * 60          # seconds of inactivity before an unlock expires
MAX_FAILS = 5                # wrong PINs per client before a cool-down
FAIL_COOLDOWN = 5 * 60


class ApiError(Exception):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status


class Store:
    """Tracker data and PIN, persisted as JSON files in `data_dir`."""

    def __init__(self, data_dir):
        self.dir = Path(data_dir)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.data_file = self.dir / "tracker.json"
        self.pin_file = self.dir / "pin.json"
        self.lock = threading.Lock()
        self.data = self._read(self.data_file) or {"version": 0, "lastId": 0, "issues": [], "labels": []}
        self.pin = self._read(self.pin_file)
        if self.pin is None:
            self.set_pin(DEFAULT_PIN)
            print(f"No PIN was set: the edit PIN is now {DEFAULT_PIN} (change it in the app or with --set-pin).")
        self.tokens = {}     # token -> expiry timestamp
        self.fails = {}      # client ip -> (count, first failure time)

    @staticmethod
    def _read(path):
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return None

    @staticmethod
    def _write(path, obj):
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=1), encoding="utf-8")
        os.replace(tmp, path)

    # ---- data ----
    def state(self, since=None):
        with self.lock:
            d = self.data
            if since is not None and since == d["version"]:
                return {"version": d["version"], "unchanged": True}
            return {"version": d["version"], "issues": d["issues"], "labels": d["labels"],
                    "hasPin": self.pin is not None}

    def _commit(self):
        self.data["version"] += 1
        self._write(self.data_file, self.data)

    def sync(self, upsert, delete, labels):
        if not isinstance(upsert, list) or not isinstance(delete, list):
            raise ApiError(HTTPStatus.BAD_REQUEST, "upsert and delete must be lists")
        for it in upsert:
            if not isinstance(it, dict) or not isinstance(it.get("id"), int) or it["id"] <= 0:
                raise ApiError(HTTPStatus.BAD_REQUEST, "every issue needs a positive integer id")
        if labels is not None and not (isinstance(labels, list) and all(isinstance(l, str) for l in labels)):
            raise ApiError(HTTPStatus.BAD_REQUEST, "labels must be a list of strings")
        with self.lock:
            d = self.data
            index = {it["id"]: i for i, it in enumerate(d["issues"])}
            for it in upsert:
                if it["id"] in index:
                    d["issues"][index[it["id"]]] = it
                else:
                    index[it["id"]] = len(d["issues"])
                    d["issues"].append(it)
                d["lastId"] = max(d["lastId"], it["id"])
            gone = {i for i in delete if isinstance(i, int)}
            if gone:
                d["issues"] = [it for it in d["issues"] if it["id"] not in gone]
            if labels is not None:
                d["labels"] = labels
            self._commit()
            return {"version": d["version"]}

    def new_issue(self):
        with self.lock:
            d = self.data
            d["lastId"] = max([d["lastId"], *(it["id"] for it in d["issues"])]) + 1
            issue = {"id": d["lastId"], "name": [], "description": [], "labels": [],
                     "assignee": "", "approvedBy": "", "bg": {}}
            d["issues"].append(issue)
            self._commit()
            return issue

    # ---- PIN & sessions ----
    @staticmethod
    def _hash(pin, salt):
        return hashlib.pbkdf2_hmac("sha256", pin.encode(), bytes.fromhex(salt), 200_000).hex()

    def set_pin(self, pin):
        if not PIN_RE.match(pin or ""):
            raise ApiError(HTTPStatus.BAD_REQUEST, "PIN must be 4-8 digits")
        salt = secrets.token_hex(16)
        with self.lock:
            self.pin = {"salt": salt, "hash": self._hash(pin, salt)}
            self._write(self.pin_file, self.pin)

    def check_pin(self, pin, client):
        now = time.time()
        with self.lock:
            count, since = self.fails.get(client, (0, now))
            if count >= MAX_FAILS and now - since < FAIL_COOLDOWN:
                raise ApiError(HTTPStatus.TOO_MANY_REQUESTS, "Too many wrong PINs, try again in a few minutes")
            ok = self.pin is not None and hmac.compare_digest(
                self._hash(str(pin or ""), self.pin["salt"]), self.pin["hash"])
            if ok:
                self.fails.pop(client, None)
            else:
                self.fails[client] = (count + 1, since) if now - since < FAIL_COOLDOWN else (1, now)
        if not ok:
            time.sleep(0.5)
            raise ApiError(HTTPStatus.FORBIDDEN, "Wrong PIN")

    def new_token(self):
        token = secrets.token_urlsafe(24)
        with self.lock:
            self.tokens[token] = time.time() + TOKEN_TTL
        return token

    def require_token(self, token):
        now = time.time()
        with self.lock:
            self.tokens = {t: exp for t, exp in self.tokens.items() if exp > now}
            if token not in self.tokens:
                raise ApiError(HTTPStatus.UNAUTHORIZED, "Locked: enter the PIN to edit")
            self.tokens[token] = now + TOKEN_TTL

    def drop_token(self, token):
        with self.lock:
            self.tokens.pop(token, None)


class Handler(BaseHTTPRequestHandler):
    store = None  # set in main()

    def log_message(self, fmt, *args):
        if not self.path.startswith("/api/state"):  # skip the polling noise
            super().log_message(fmt, *args)

    def _send(self, status, body, ctype="application/json; charset=utf-8"):
        if not isinstance(body, bytes):
            body = json.dumps(body, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _body(self):
        length = int(self.headers.get("Content-Length") or 0)
        if length > MAX_BODY:
            raise ApiError(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "Request too large")
        try:
            return json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError:
            raise ApiError(HTTPStatus.BAD_REQUEST, "Invalid JSON")

    def _token(self):
        self.store.require_token(self.headers.get("X-Token", ""))

    def do_GET(self):
        url = urlparse(self.path)
        try:
            if url.path == "/api/state":
                since = parse_qs(url.query).get("since", [None])[0]
                return self._send(200, self.store.state(int(since) if since and since.isdigit() else None))
            if url.path in STATIC_FILES:
                name, ctype = STATIC_FILES[url.path]
                return self._send(200, (APP_DIR / name).read_bytes(), ctype)
            self._send(404, {"error": "Not found"})
        except ApiError as e:
            self._send(e.status, {"error": str(e)})

    def do_POST(self):
        path = urlparse(self.path).path
        s = self.store
        try:
            body = self._body()
            client = self.client_address[0]
            if path == "/api/pin/setup":
                if s.pin is not None:
                    raise ApiError(HTTPStatus.CONFLICT, "A PIN is already set")
                s.set_pin(body.get("pin"))
                return self._send(200, {"token": s.new_token()})
            if path == "/api/unlock":
                s.check_pin(body.get("pin"), client)
                return self._send(200, {"token": s.new_token()})
            if path == "/api/lock":
                s.drop_token(self.headers.get("X-Token", ""))
                return self._send(200, {})
            self._token()
            if path == "/api/pin/change":
                s.check_pin(body.get("old"), client)
                s.set_pin(body.get("new"))
                return self._send(200, {})
            if path == "/api/sync":
                return self._send(200, s.sync(body.get("upsert", []), body.get("delete", []), body.get("labels")))
            if path == "/api/issues":
                return self._send(200, {"issue": s.new_issue()})
            self._send(404, {"error": "Not found"})
        except ApiError as e:
            self._send(e.status, {"error": str(e)})


def main():
    ap = argparse.ArgumentParser(description="Simple Tracker Sheet server")
    ap.add_argument("--host", default="0.0.0.0", help="address to listen on (default: all interfaces)")
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--data", default=str(APP_DIR / "data"), help="folder for tracker.json and pin.json")
    ap.add_argument("--set-pin", nargs="?", const="", metavar="PIN",
                    help="set or reset the edit PIN, then exit (asks for it when no PIN is given)")
    args = ap.parse_args()

    store = Store(args.data)
    if args.set_pin is not None:
        pin = args.set_pin
        if not pin:
            pin = getpass.getpass("New PIN (4-8 digits): ")
            if pin != getpass.getpass("Repeat PIN: "):
                raise SystemExit("PINs do not match")
        try:
            store.set_pin(pin)
        except ApiError as e:
            raise SystemExit(str(e))
        print("PIN saved.")
        return

    Handler.store = store
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    shown = "localhost" if args.host in ("0.0.0.0", "") else args.host
    print(f"Simple Tracker Sheet on http://{shown}:{args.port}  (data: {store.dir})")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
