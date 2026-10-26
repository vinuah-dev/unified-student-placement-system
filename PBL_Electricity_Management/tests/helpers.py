"""Shared helpers for the test cases: frame builders, a throw-away server and a small HTTP client."""
import json
import tempfile
import threading
import urllib.error
import urllib.request
from pathlib import Path

from app.engine import Frame, RoomMonitor, Settings, ValidationError
from app.server import create_server


def frame(ts, people=0, fans=0, lights=0, temps=(25.0, 25.0, 25.0, 25.0)):
    return {"timestamp": ts, "people": people, "fans_on": fans, "lights_on": lights, "temps": list(temps)}


def check_frame(data):
    """Returns 'accepted' or the validation message for one frame."""
    try:
        Frame.from_dict(data)
        return "accepted"
    except ValidationError as e:
        return str(e)


def check_settings(data):
    try:
        Settings.from_dict(data)
        return "accepted"
    except ValidationError as e:
        return str(e)


def run_frames(frames, settings=None):
    """Feeds frames to a new monitor; returns (monitor, list of alert types)."""
    monitor = RoomMonitor("LAB-1", settings or Settings())
    alerts = []
    for f in frames:
        alerts += [a["type"] for a in monitor.process(Frame.from_dict(f))]
    return monitor, alerts


def describe(monitor, alerts):
    s = monitor.status()
    return "state=%s, alerts=[%s]" % (s["state"], ", ".join(alerts))


class TestServer:
    """Starts the real server on a free port with an empty temporary database."""

    def __init__(self, extra_static=None, db_path=None):
        self.tmp = None
        if db_path is None:
            self.tmp = tempfile.TemporaryDirectory()
            db_path = str(Path(self.tmp.name) / "test.db")
        self.db_path = db_path
        self.server = create_server(db_path, port=0, extra_static=extra_static)
        self.base = "http://127.0.0.1:%d" % self.server.server_address[1]
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def stop(self, cleanup=True):
        self.server.shutdown()
        self.server.server_close()
        self.server.app.db.conn.close()
        if cleanup and self.tmp:
            self.tmp.cleanup()

    def call(self, method, path, body=None, raw=None):
        """Returns (http status, parsed JSON body)."""
        data = raw if raw is not None else (json.dumps(body).encode("utf-8") if body is not None else None)
        req = urllib.request.Request(self.base + path, data=data, method=method,
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req) as res:
                return res.status, json.loads(res.read())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read())


def api_result(status, body):
    """Formats an API response the way the test document shows actual results."""
    if isinstance(body, dict) and body.get("ok") is False:
        return "%d: %s" % (status, body["error"])
    if isinstance(body, dict) and "message" in body:
        return "%d: %s" % (status, body["message"])
    return "%d" % status
