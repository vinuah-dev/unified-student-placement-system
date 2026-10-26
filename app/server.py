"""REST API, database access and web UI server for the two PBL modules.

    python run.py            (or: python -m app.server --port 8091 --db data/usps.db)

Authentication (SRS 4.1) is outside the two modules; the dashboard chooses the acting user (student,
recruiter or placement officer) and every request names that actor, which the server checks against
the business rules (BR-02 officers approve postings, BR-07 recruiters touch only their own jobs).
"""
import argparse
import json
import math
import mimetypes
import secrets
import sqlite3
import threading
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from . import rules
from .db import HISTORY_SQL, NOTIFY_SQL, Database
from .rules import EligibilityCriteria, RuleError

STATIC_DIR = Path(__file__).resolve().parent / "static"
PER_PAGE = 10


class ApiError(Exception):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status
        self.message = message


def job_key(job_id):
    return "J-%d" % job_id


class PlacementApp:
    def __init__(self, db_path, clock=datetime.now):
        self.clock = clock
        self.db = Database(db_path, clock())
        # BUG-02/03 fix: every action that checks a state and then changes it runs under this one lock, so the
        # same request arriving twice at the same moment is applied once (re-entrant: event() calls withdraw()).
        self.lock = threading.RLock()
        self.boot = secrets.token_hex(3)
        self.changes = 0

    # ----- live updates: every open page polls this and redraws when it changes -----
    def changed(self):
        with self.lock:
            self.changes += 1

    def version(self):
        return {"version": "%s.%d" % (self.boot, self.changes)}

    # ----- lookups -----
    def _student(self, student_id):
        s = self.db.one("SELECT * FROM students WHERE student_id = ?", (student_id,))
        if not s:
            raise ApiError(404, "Student %s not found." % student_id)
        return s

    def _job(self, job_id):
        j = self.db.one("SELECT j.*, c.name AS company FROM jobs j JOIN companies c USING (company_id) "
                        "WHERE job_id = ?", (job_id,))
        if not j:
            raise ApiError(404, "Job %s not found." % (job_key(int(job_id)) if str(job_id).isdigit() else job_id))
        j["criteria"] = json.loads(j["criteria"])
        return j

    def _application(self, app_id):
        a = self.db.one("SELECT * FROM applications WHERE app_id = ?", (app_id,))
        if not a:
            raise ApiError(404, "Application %s not found." % app_id)
        return a

    def _recruiter(self, recruiter_id):
        r = self.db.one("SELECT r.*, c.is_approved FROM recruiters r JOIN companies c USING (company_id) "
                        "WHERE recruiter_id = ?", (recruiter_id,))
        if not r:
            raise ApiError(404, "Recruiter %s not found." % recruiter_id)
        return r

    @staticmethod
    def _criteria(job):
        c = job["criteria"]
        return EligibilityCriteria(c["min_cgpa"], c["allowed_branches"], c["max_backlogs"], c["batch"])

    def _now(self):
        return self.clock().isoformat(timespec="minutes")

    def _record_check(self, job, student, eligible, reasons):
        self.db.write("INSERT INTO eligibility_checks (job_id, student_id, is_eligible, remarks, checked_at) "
                      "VALUES (?, ?, ?, ?, ?)", (job["job_id"], student["student_id"], int(eligible),
                                                 " ".join(reasons), self.clock().isoformat(timespec="seconds")))

    def _notify_officers(self, message):
        for o in self.db.all("SELECT officer_id FROM placement_officers"):
            self.db.notify("officer", o["officer_id"], message, self.clock())

    # ----- meta -----
    def meta(self):
        return {"students": self.db.all("SELECT * FROM students ORDER BY student_id"),
                "recruiters": self.db.all("SELECT r.*, c.name AS company, c.is_approved FROM recruiters r "
                                          "JOIN companies c USING (company_id) ORDER BY recruiter_id"),
                "officers": self.db.all("SELECT * FROM placement_officers"),
                "resumes": self.db.all("SELECT * FROM resumes ORDER BY resume_id"),
                "branches": list(rules.BRANCHES), "student_events": list(rules.STUDENT_EVENTS),
                "transitions": [[e, s, t] for (e, s), t in rules.APPLICATION_TRANSITIONS.items()],
                "now": self._now()}

    # ================= Module 1: job posting and eligibility =================
    def post_job(self, body):
        recruiter = self._recruiter(body.get("recruiter_id"))
        if not recruiter["is_approved"]:
            raise ApiError(403, "Your company is not yet approved by the placement cell.")
        job = self._validated(body)
        job_id = self.db.write(
            "INSERT INTO jobs (company_id, posted_by, title, description, ctc, location, deadline, status, criteria) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', ?)",
            (recruiter["company_id"], recruiter["recruiter_id"], job["title"], job["description"], job["ctc"],
             job["location"], job["deadline"].isoformat(timespec="minutes"), json.dumps(job["criteria"].to_dict())))
        self._notify_officers("New job posting %s (%s) is waiting for approval." % (job_key(job_id), job["title"]))
        return {"ok": True, "job_id": job_id,
                "message": "Job %s submitted for approval (status: Pending)." % job_key(job_id)}

    def resubmit_job(self, job_id, body):
        """UC-2 A1: the recruiter edits a posting the officer returned and submits it again."""
        with self.lock:
            return self._resubmit_job(job_id, body)

    def _resubmit_job(self, job_id, body):
        job = self._job(job_id)
        recruiter = self._recruiter(body.get("recruiter_id"))
        if recruiter["recruiter_id"] != job["posted_by"]:
            raise ApiError(403, "You can edit only your own job postings.")
        if job["status"] != "returned":
            raise ApiError(409, "Only a posting returned for changes can be edited (status: %s)." % job["status"])
        new = self._validated(body)
        self.db.write("UPDATE jobs SET title = ?, description = ?, ctc = ?, location = ?, deadline = ?, criteria = ?, "
                      "status = 'pending', remarks = NULL, decided_by = NULL WHERE job_id = ?",
                      (new["title"], new["description"], new["ctc"], new["location"],
                       new["deadline"].isoformat(timespec="minutes"), json.dumps(new["criteria"].to_dict()), job_id))
        self._notify_officers("Job posting %s (%s) was resubmitted after changes." % (job_key(job_id), new["title"]))
        return {"ok": True, "job_id": job_id,
                "message": "Job %s resubmitted for approval (status: Pending)." % job_key(job_id)}

    def _validated(self, body):
        try:
            return rules.validate_job_posting(body, self.clock())
        except RuleError as e:
            raise ApiError(400, str(e))

    def decide_job(self, job_id, body):
        with self.lock:
            return self._decide_job(job_id, body)

    def _decide_job(self, job_id, body):
        if body.get("actor_role") != "officer" or not self.db.one(
                "SELECT 1 FROM placement_officers WHERE officer_id = ?", (body.get("actor_id"),)):
            raise ApiError(403, "Only a Placement Officer can approve or reject job postings.")
        job = self._job(job_id)
        try:
            status = rules.validate_job_decision(job["status"], body.get("decision"), body.get("remarks"))
        except RuleError as e:
            raise ApiError(409 if "not pending" in str(e) else 400, str(e))
        if status == "published" and job["deadline"] <= self._now():   # BUG-04 fix
            raise ApiError(409, "The deadline of %s has passed; return the posting so the recruiter can change it."
                           % job_key(job["job_id"]))
        remarks = (body.get("remarks") or "").strip()
        self.db.write("UPDATE jobs SET status = ?, remarks = ?, decided_by = ? WHERE job_id = ?",
                      (status, remarks, body.get("actor_id"), job_id))
        key = job_key(job["job_id"])
        if status == "published":
            criteria = self._criteria(job)
            notified = 0
            for s in self.db.all("SELECT * FROM students WHERE is_placed = 0"):
                if criteria.evaluate(s)[0]:
                    self.db.notify("student", s["student_id"], "New job for you: %s at %s (%s), apply before %s."
                                   % (job["title"], job["company"], key, job["deadline"].replace("T", " ")),
                                   self.clock())
                    notified += 1
            message = "Job %s published. %d eligible student(s) notified." % (key, notified)
        elif status == "rejected":
            message = "Job %s rejected. Recruiter notified." % key
        else:
            message = "Job %s returned to the recruiter for changes." % key
        self.db.notify("recruiter", job["posted_by"], "Your job %s (%s) was %s by the placement cell.%s"
                       % (key, job["title"], status, " Remarks: " + remarks if remarks else ""), self.clock())
        return {"ok": True, "status": status, "message": message}

    def eligibility(self, job_id, student_id):
        job = self._job(job_id)
        student = self._student(student_id)
        eligible, reasons = self._criteria(job).evaluate(student)
        self._record_check(job, student, eligible, reasons)
        return {"job_id": job["job_id"], "student_id": student["student_id"], "eligible": eligible,
                "reasons": reasons}

    def job_board(self, query):
        """FR-12: published jobs filtered and paginated; with student_id each job carries its eligibility."""
        student = self._student(query["student_id"]) if query.get("student_id") else None
        q = (query.get("q") or "").strip().lower()
        location = (query.get("location") or "").strip().lower()
        try:
            min_ctc = float(query["min_ctc"]) if query.get("min_ctc") else None
        except ValueError:
            raise ApiError(400, "Minimum package must be a number.")
        page = _whole(query.get("page", "1"), "Page", 1)
        per_page = _whole(query.get("per_page", str(PER_PAGE)), "Jobs per page", 1, 50)
        now = self._now()
        out = []
        for j in self.db.all("SELECT j.*, c.name AS company FROM jobs j JOIN companies c USING (company_id) "
                             "WHERE j.status = 'published'"):
            j["criteria"] = json.loads(j["criteria"])
            text = (j["title"] + " " + j["description"] + " " + j["company"]).lower()
            if q and q not in text:
                continue
            if location and location not in j["location"].lower():
                continue
            if min_ctc is not None and j["ctc"] < min_ctc:
                continue
            j["open"] = j["deadline"] > now
            if student:
                j["eligible"], j["reasons"] = self._criteria(j).evaluate(student)
                if query.get("eligible_only") in ("1", "true") and not j["eligible"]:
                    continue
            out.append(j)
        out.sort(key=lambda j: (not j["open"], j["deadline"]))
        pages = max(1, math.ceil(len(out) / per_page))
        return {"jobs": out[(page - 1) * per_page: page * per_page], "total": len(out), "page": page,
                "pages": pages, "per_page": per_page}

    def manage_jobs(self, query):
        sql = "SELECT j.*, c.name AS company FROM jobs j JOIN companies c USING (company_id) "
        if query.get("recruiter_id"):
            rows = self.db.all(sql + "WHERE posted_by = ? ORDER BY job_id DESC", (query["recruiter_id"],))
        elif query.get("status", "pending") == "all":
            rows = self.db.all(sql + "ORDER BY job_id DESC")
        else:
            rows = self.db.all(sql + "WHERE status = ? ORDER BY job_id", (query.get("status", "pending"),))
        for j in rows:
            j["criteria"] = json.loads(j["criteria"])
        return rows

    # ================= Module 2: application and tracking =================
    def apply(self, body):
        if not body.get("job_id"):
            raise ApiError(400, "Select a job to apply for.")
        with self.lock:
            student = self._student(body.get("student_id"))
            job = self._job(body.get("job_id"))
            key = job_key(job["job_id"])
            now = self.clock()
            if job["status"] != "published":
                raise ApiError(409, "Job %s is not open for applications." % key)
            if job["deadline"] <= now.isoformat(timespec="minutes"):
                raise ApiError(409, "The application deadline for %s has passed." % key)
            if student["is_placed"]:
                raise ApiError(409, "You are already placed; the placement policy blocks further applications.")
            eligible, reasons = self._criteria(job).evaluate(student)
            self._record_check(job, student, eligible, reasons)
            if not eligible:
                raise ApiError(409, "You are not eligible for %s: %s" % (key, " ".join(reasons)))
            dup = self.db.one("SELECT tracking_id FROM applications WHERE student_id = ? AND job_id = ?",
                              (student["student_id"], job["job_id"]))
            if dup:
                raise ApiError(409, "You have already applied to %s (tracking id %s)." % (key, dup["tracking_id"]))
            resume = self.db.one("SELECT * FROM resumes WHERE resume_id = ? AND student_id = ? AND is_active = 1",
                                 (body.get("resume_id"), student["student_id"]))
            if not resume:
                raise ApiError(400, "Select one of your active resumes.")
            note = (body.get("cover_note") or "").strip()
            if len(note) > 500:
                raise ApiError(400, "Cover note cannot exceed 500 characters.")
            stamp = now.isoformat(timespec="seconds")
            try:
                with self.db.transaction() as tx:
                    app_id = tx.execute("INSERT INTO applications (student_id, job_id, resume_id, cover_note, "
                                        "applied_on, status) VALUES (?, ?, ?, ?, ?, ?)",
                                        (student["student_id"], job["job_id"], resume["resume_id"], note, stamp,
                                         rules.APPLIED)).lastrowid
                    tid = rules.tracking_id(app_id, now.year)
                    tx.execute("UPDATE applications SET tracking_id = ? WHERE app_id = ?", (tid, app_id))
                    tx.execute(HISTORY_SQL, (app_id, None, rules.APPLIED, "submit",
                                             "student %d" % student["student_id"], stamp))
                    tx.execute(NOTIFY_SQL, ("recruiter", job["posted_by"], "New application %s from %s for %s."
                                            % (tid, student["name"], job["title"]), stamp))
                    tx.execute(NOTIFY_SQL, ("student", student["student_id"], "Your application %s for %s at %s "
                                            "was received." % (tid, job["title"], job["company"]), stamp))
            except sqlite3.Error:
                raise ApiError(500, "Your application could not be saved and nothing was stored. Please try again.")
        return {"ok": True, "app_id": app_id, "tracking_id": tid,
                "message": "Application submitted for %s. Tracking id %s." % (key, tid)}

    def _history(self, app_id, from_state, to_state, event, actor):
        self.db.write(HISTORY_SQL, (app_id, from_state, to_state, event, actor,
                                    self.clock().isoformat(timespec="seconds")))

    def withdraw(self, app_id, body):
        with self.lock:
            return self._withdraw(app_id, body)

    def _withdraw(self, app_id, body):
        app = self._application(app_id)
        if str(body.get("student_id")) != str(app["student_id"]):
            raise ApiError(403, "Only the student who applied can withdraw this application.")
        if app["status"] != rules.APPLIED:
            raise ApiError(409, "Only an application in the Applied state can be withdrawn (current: %s)."
                           % app["status"])
        job = self._job(app["job_id"])
        if job["deadline"] <= self._now():
            raise ApiError(409, "The deadline has passed; the application can no longer be withdrawn.")
        return self._move(app, job, "withdraw", "student %s" % app["student_id"])

    def event(self, app_id, body):
        with self.lock:
            return self._event(app_id, body)

    def _event(self, app_id, body):
        app = self._application(app_id)
        event = body.get("event")
        if event not in rules.STAFF_EVENTS + rules.STUDENT_EVENTS:
            raise ApiError(400, "Unknown event '%s'." % event)
        if event == "withdraw":
            return self.withdraw(app_id, {"student_id": body.get("actor_id")})
        job = self._job(app["job_id"])
        role, actor_id = body.get("actor_role"), body.get("actor_id")
        if event in rules.STUDENT_EVENTS:
            if role != "student" or str(actor_id) != str(app["student_id"]):
                raise ApiError(403, "Only the student who applied can respond to the offer.")
        else:
            owner = role == "recruiter" and str(actor_id) == str(job["posted_by"])
            officer = role == "officer" and self.db.one("SELECT 1 FROM placement_officers WHERE officer_id = ?",
                                                        (actor_id,))
            if not (owner or officer):
                raise ApiError(403, "Only the recruiter who posted this job or a Placement Officer can update "
                                    "this application.")
        if event == "accept_offer" and self._student(app["student_id"])["is_placed"]:
            raise ApiError(409, "You already hold an accepted offer; the placement policy allows only one.")
        return self._move(app, job, event, "%s %s" % (role, actor_id))

    def _move(self, app, job, event, actor):
        try:
            new_state = rules.next_state(app["status"], event)
        except RuleError as e:
            raise ApiError(409, str(e))
        self.db.write("UPDATE applications SET status = ? WHERE app_id = ?", (new_state, app["app_id"]))
        self._history(app["app_id"], app["status"], new_state, event, actor)
        if new_state == rules.ACCEPTED:
            self.db.write("UPDATE students SET is_placed = 1 WHERE student_id = ?", (app["student_id"],))
        self.db.notify("student", app["student_id"], "Your application %s for %s is now %s."
                       % (app["tracking_id"], job["title"], new_state), self.clock())
        return {"ok": True, "status": new_state,
                "message": "Application %s is now %s." % (app["tracking_id"], new_state)}

    def applications(self, query):
        sql = ("SELECT a.*, j.title, j.posted_by, c.name AS company, s.name AS student_name, s.roll_no, "
               "r.file_name AS resume FROM applications a JOIN jobs j USING (job_id) JOIN companies c "
               "ON c.company_id = j.company_id JOIN students s USING (student_id) JOIN resumes r USING (resume_id)")
        if query.get("student_id"):
            return self.db.all(sql + " WHERE a.student_id = ? ORDER BY app_id DESC", (query["student_id"],))
        if query.get("recruiter_id"):
            return self.db.all(sql + " WHERE j.posted_by = ? ORDER BY app_id DESC", (query["recruiter_id"],))
        return self.db.all(sql + " ORDER BY app_id DESC")

    def application_detail(self, app_id):
        app = self._application(app_id)
        app["history"] = self.db.all("SELECT * FROM application_history WHERE app_id = ? ORDER BY id", (app_id,))
        return app

    def notifications(self, query):
        return self.db.all("SELECT * FROM notifications WHERE recipient_type = ? AND recipient_id = ? "
                           "ORDER BY notif_id DESC", (query.get("recipient_type"), query.get("recipient_id")))


def _whole(text, label, low, high=None):
    if not str(text).isdigit() or int(text) < low or (high is not None and int(text) > high):
        raise ApiError(400, "%s must be a whole number %s." % (label, "from %d to %d" % (low, high) if high
                                                               else "of at least %d" % low))
    return int(text)


def _num(text, label):
    if not text.isdigit():
        raise ApiError(404, "%s %s not found." % (label, text))
    return int(text)


def make_handler(app, extra_static=None):
    mounts = {name: Path(d).resolve() for name, d in (extra_static or {}).items()}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
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
            q = {k: v[0] for k, v in parse_qs(url.query).items()}
            if not parts or parts[0] != "api":
                return self._static(url.path) if method == "GET" else _not_found()
            r = parts[1:]
            if method == "GET" and r == ["version"]:
                return app.version()
            if method == "GET" and r == ["meta"]:
                return app.meta()
            if method == "GET" and r == ["jobs"]:
                return app.job_board(q)
            if method == "GET" and r == ["jobs", "manage"]:
                return app.manage_jobs(q)
            if method == "POST" and r == ["jobs"]:
                return app.post_job(self._body())
            if method == "PUT" and len(r) == 2 and r[0] == "jobs":
                return app.resubmit_job(_num(r[1], "Job"), self._body())
            if method == "POST" and len(r) == 3 and r[0] == "jobs" and r[2] == "decision":
                return app.decide_job(_num(r[1], "Job"), self._body())
            if method == "GET" and len(r) == 3 and r[0] == "jobs" and r[2] == "eligibility":
                return app.eligibility(_num(r[1], "Job"), q.get("student_id"))
            if method == "POST" and r == ["applications"]:
                return app.apply(self._body())
            if method == "GET" and r == ["applications"]:
                return app.applications(q)
            if method == "GET" and len(r) == 2 and r[0] == "applications":
                return app.application_detail(_num(r[1], "Application"))
            if method == "POST" and len(r) == 3 and r[0] == "applications" and r[2] == "withdraw":
                return app.withdraw(_num(r[1], "Application"), self._body())
            if method == "POST" and len(r) == 3 and r[0] == "applications" and r[2] == "events":
                return app.event(_num(r[1], "Application"), self._body())
            if method == "GET" and r == ["notifications"]:
                return app.notifications(q)
            return _not_found()

        def _static(self, path):
            rel = "index.html" if path in ("", "/") else path.lstrip("/")
            root = STATIC_DIR
            first, _, rest = rel.partition("/")
            if first in mounts:
                root, rel = mounts[first], rest
            target = (root / rel).resolve()
            if root not in target.parents or not target.is_file():
                _not_found()
            self._send(200, target.read_bytes(), mimetypes.guess_type(target.name)[0] or "application/octet-stream")
            return None

        def _handle(self, method):
            try:
                result = self._route(method)
                if result is not None:
                    if method != "GET":
                        app.changed()
                    self._send(200, result)
            except ApiError as e:
                self._send(e.status, {"ok": False, "error": e.message})
            except Exception as e:  # never leave the client without an answer
                self._send(500, {"ok": False, "error": "Internal server error (%s)." % type(e).__name__})

        def do_GET(self):
            self._handle("GET")

        def do_POST(self):
            self._handle("POST")

        def do_PUT(self):
            self._handle("PUT")

    return Handler


def _not_found():
    raise ApiError(404, "Not found.")


def create_server(db_path, port=8091, host="127.0.0.1", extra_static=None, clock=datetime.now):
    app = PlacementApp(db_path, clock)
    server = ThreadingHTTPServer((host, port), make_handler(app, extra_static))
    server.app = app
    return server


def main():
    parser = argparse.ArgumentParser(description="Unified Student Placement System - PBL prototype")
    parser.add_argument("--port", type=int, default=8091)
    parser.add_argument("--db", default="data/usps.db")
    args = parser.parse_args()
    Path(args.db).parent.mkdir(parents=True, exist_ok=True)
    server = create_server(args.db, args.port)
    print("Placement portal running at http://127.0.0.1:%d  (database: %s)" % (args.port, args.db), flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
