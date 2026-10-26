"""Shared helpers for the test cases: a test clock, a throw-away server with the demo data and an HTTP client."""
import json
import tempfile
import threading
import urllib.error
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

from app.server import create_server

START = datetime(2026, 10, 26, 10, 0)   # demo deadlines: J-1 +30 days, J-2 +20, J-3 +25, J-4 -1 day


class Clock:
    """Test clock: starts at START and only moves when a test moves it, so deadlines can be crossed."""

    def __init__(self, start=START):
        self.now = start

    def __call__(self):
        return self.now

    def advance(self, **delta):
        self.now += timedelta(**delta)

    def set(self, when):
        self.now = when


class TestServer:
    """Starts the real server on a free port with a new database seeded with the demo data."""

    def __init__(self, extra_static=None, db_path=None, clock=None):
        self.tmp = None
        if db_path is None:
            self.tmp = tempfile.TemporaryDirectory()
            db_path = str(Path(self.tmp.name) / "test.db")
        self.db_path = db_path
        self.clock = clock or Clock()
        self.server = create_server(db_path, port=0, extra_static=extra_static, clock=self.clock)
        self.app = self.server.app
        self.base = "http://127.0.0.1:%d" % self.server.server_address[1]
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def stop(self, cleanup=True):
        self.server.shutdown()
        self.server.server_close()
        self.app.db.conn.close()
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

    def result(self, method, path, body=None):
        return api_result(*self.call(method, path, body))

    def count(self, table, where="1", args=()):
        return self.app.db.one("SELECT COUNT(*) AS n FROM %s WHERE %s" % (table, where), args)["n"]

    # ---- shortcuts used by many cases ----
    def apply(self, student_id=101, job_id=1, resume_id=1, note=""):
        return self.result("POST", "/api/applications", {"student_id": student_id, "job_id": job_id,
                                                         "resume_id": resume_id, "cover_note": note})

    def event(self, app_id, event, role="recruiter", actor_id=1):
        return self.result("POST", "/api/applications/%d/events" % app_id,
                           {"event": event, "actor_role": role, "actor_id": actor_id})

    def decide(self, job_id, decision, remarks="", role="officer", actor_id=1):
        return self.result("POST", "/api/jobs/%d/decision" % job_id,
                           {"decision": decision, "remarks": remarks, "actor_role": role, "actor_id": actor_id})

    def board(self, query=""):
        status, body = self.call("GET", "/api/jobs?" + query)
        if status != 200:
            return api_result(status, body)
        return body


def api_result(status, body):
    """Formats an API response the way the test document shows actual results."""
    if isinstance(body, dict) and body.get("ok") is False:
        return "%d: %s" % (status, body["error"])
    if isinstance(body, dict) and "message" in body:
        return "%d: %s" % (status, body["message"])
    return "%d" % status


def with_server(fn, clock=None):
    """Wraps a case so it runs against its own fresh server (cases never depend on each other)."""
    def run():
        srv = TestServer(clock=clock() if clock else None)
        try:
            return fn(srv)
        finally:
            srv.stop()
    return run


def keys(jobs):
    return ", ".join("J-%d" % j["job_id"] for j in jobs)
