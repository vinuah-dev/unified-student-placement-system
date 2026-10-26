"""Module 2: Monitoring dashboard and control - REST API, database and web UI server.

Run:  python -m app.server --port 8090 --db data/energy.db
The camera/sensor node (or app/simulator.py) posts readings to /api/readings; the dashboard in
app/static reads the room status and alerts, acknowledges alerts, sends manual relay commands that the
ESP32 controller picks up from /api/commands, and edits the detection settings.
"""
import argparse
import json
import mimetypes
import re
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .db import Database
from .engine import Frame, RoomMonitor, Settings, ValidationError

STATIC_DIR = Path(__file__).resolve().parent / "static"
NAME_RE = re.compile(r"^[A-Za-z. ]{3,40}$")
APPLIANCES = ("fan", "light")
ACTIONS = ("ON", "OFF")


class ApiError(Exception):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status
        self.message = message


class EnergyApp:
    """Application state shared by all request threads."""

    def __init__(self, db_path):
        self.db = Database(db_path)
        stored = self.db.load_settings()
        self.settings = Settings.from_dict(stored) if stored else Settings()
        self.monitors = {r["id"]: RoomMonitor(r["id"], self.settings) for r in self.db.rooms()}
        self.lock = threading.Lock()

    # ----- helpers -----
    def _room(self, room_id):
        if room_id is None or room_id == "":
            raise ApiError(400, "room_id is required.")
        if not isinstance(room_id, str) or not self.db.room(room_id):
            raise ApiError(404, "Room %s not found." % room_id)
        return room_id

    @staticmethod
    def _operator(value):
        value = value.strip() if isinstance(value, str) else ""
        if not NAME_RE.match(value):
            raise ApiError(400, "Operator name must be 3 to 40 characters (letters, spaces and dots only).")
        return value

    # ----- Module 1 integration: readings -----
    def post_reading(self, body):
        room_id = self._room(body.get("room_id"))
        try:
            frame = Frame.from_dict(body)
            with self.lock:
                monitor = self.monitors[room_id]
                alerts = monitor.process(frame)
                self.db.add_reading(room_id, frame, monitor.state)
                for a in alerts:
                    a["id"] = self.db.add_alert(a)
                status = monitor.status()
        except ValidationError as e:
            raise ApiError(400, str(e))
        return {"ok": True, "state": status["state"], "alerts": alerts}

    def room_status(self, room_id):
        room = self.db.room(self._room(room_id))
        with self.lock:
            room["status"] = self.monitors[room_id].status()
        room["open_alerts"] = len(self.db.alerts(room_id, "OPEN"))
        return room

    # ----- alerts -----
    def acknowledge(self, alert_id, body):
        alert = self.db.alert(alert_id)
        if not alert:
            raise ApiError(404, "Alert %s not found." % alert_id)
        if alert["status"] != "OPEN":
            raise ApiError(409, "Alert %s is already acknowledged." % alert_id)
        operator = self._operator(body.get("operator"))
        remarks = body.get("remarks") or ""
        if not isinstance(remarks, str) or len(remarks.strip()) > 200:
            raise ApiError(400, "Remarks cannot exceed 200 characters.")
        self.db.acknowledge_alert(alert_id, operator, remarks.strip())
        return {"ok": True, "message": "Alert %s acknowledged by %s." % (alert_id, operator)}

    # ----- manual override -----
    def override(self, body):
        room_id = self._room(body.get("room_id"))
        appliance = body.get("appliance")
        action = body.get("action")
        if appliance not in APPLIANCES:
            raise ApiError(400, "Appliance must be fan or light.")
        if action not in ACTIONS:
            raise ApiError(400, "Action must be ON or OFF.")
        operator = self._operator(body.get("operator"))
        reason = body.get("reason")
        reason = reason.strip() if isinstance(reason, str) else ""
        if not 5 <= len(reason) <= 100:
            raise ApiError(400, "Reason must be 5 to 100 characters.")
        cid = self.db.add_command(room_id, appliance, action, operator, reason)
        return {"ok": True, "command_id": cid,
                "message": "Command %d queued: switch %s %s in %s." % (cid, appliance, action, room_id)}

    def complete_command(self, command_id):
        cmd = self.db.command(command_id)
        if not cmd:
            raise ApiError(404, "Command %s not found." % command_id)
        if cmd["status"] != "PENDING":
            raise ApiError(409, "Command %s is already %s." % (command_id, cmd["status"]))
        self.db.complete_command(command_id)
        return {"ok": True}

    # ----- settings -----
    def update_settings(self, body):
        try:
            new = Settings.from_dict(body)
        except ValidationError as e:
            raise ApiError(400, str(e))
        self.db.save_settings(new.to_dict())
        with self.lock:
            self.settings = new
            for m in self.monitors.values():
                m.settings = new
        return {"ok": True, "settings": new.to_dict(), "message": "Settings saved."}


def make_handler(app, extra_static=None):
    mounts = {name: Path(d).resolve() for name, d in (extra_static or {}).items()}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):  # keep the console quiet during tests
            pass

        def _send(self, status, payload, content_type="application/json"):
            body = payload if isinstance(payload, bytes) else json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def _body(self):
            length = int(self.headers.get("Content-Length") or 0)
            try:
                data = json.loads(self.rfile.read(length) or b"{}")
            except json.JSONDecodeError:
                raise ApiError(400, "Request body must be valid JSON.")
            if not isinstance(data, dict):
                raise ApiError(400, "Request body must be a JSON object.")
            return data

        def _route(self, method):
            url = urlparse(self.path)
            parts = [p for p in url.path.split("/") if p]
            query = {k: v[0] for k, v in parse_qs(url.query).items()}
            if not parts or parts[0] != "api":
                return self._static(url.path)
            route = parts[1:]
            if method == "GET" and route == ["rooms"]:
                return [app.room_status(r["id"]) for r in app.db.rooms()]
            if method == "GET" and len(route) == 2 and route[0] == "rooms":
                return app.room_status(route[1])
            if method == "POST" and route == ["readings"]:
                return app.post_reading(self._body())
            if method == "GET" and route == ["alerts"]:
                return app.db.alerts(query.get("room"), query.get("status"))
            if method == "POST" and len(route) == 3 and route[0] == "alerts" and route[2] == "ack":
                return app.acknowledge(_int_id(route[1], "Alert"), self._body())
            if method == "POST" and route == ["override"]:
                return app.override(self._body())
            if method == "GET" and route == ["commands"]:
                return app.db.commands(query.get("room"), query.get("status"))
            if method == "POST" and len(route) == 3 and route[0] == "commands" and route[2] == "done":
                return app.complete_command(_int_id(route[1], "Command"))
            if method == "GET" and route == ["settings"]:
                return app.settings.to_dict()
            if method in ("PUT", "POST") and route == ["settings"]:
                return app.update_settings(self._body())
            raise ApiError(404, "Not found.")

        def _static(self, path):
            rel = "index.html" if path in ("", "/") else path.lstrip("/")
            root = STATIC_DIR
            first, _, rest = rel.partition("/")
            if first in mounts:          # extra folders, e.g. the UI test harness during test runs
                root, rel = mounts[first], rest
            target = (root / rel).resolve()
            if root not in target.parents or not target.is_file():
                raise ApiError(404, "Not found.")
            ctype = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
            self._send(200, target.read_bytes(), ctype)
            return None

        def _handle(self, method):
            try:
                result = self._route(method)
                if result is not None:
                    self._send(200, result)
            except ApiError as e:
                self._send(e.status, {"ok": False, "error": e.message})

        def do_GET(self):
            self._handle("GET")

        def do_POST(self):
            self._handle("POST")

        def do_PUT(self):
            self._handle("PUT")

    return Handler


def _int_id(text, label):
    if not text.isdigit():
        raise ApiError(404, "%s %s not found." % (label, text))
    return int(text)


def create_server(db_path, port=8090, host="127.0.0.1", extra_static=None):
    app = EnergyApp(db_path)
    server = ThreadingHTTPServer((host, port), make_handler(app, extra_static))
    server.app = app
    return server


def main():
    parser = argparse.ArgumentParser(description="Smart classroom electricity management server")
    parser.add_argument("--port", type=int, default=8090)
    parser.add_argument("--db", default="data/energy.db")
    args = parser.parse_args()
    Path(args.db).parent.mkdir(parents=True, exist_ok=True)
    server = create_server(args.db, args.port)
    print("Dashboard running at http://127.0.0.1:%d  (database: %s)" % (args.port, args.db), flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
