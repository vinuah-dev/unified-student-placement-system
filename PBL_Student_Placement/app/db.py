"""SQLite storage following the SRS database design (6.1): students, companies, recruiters, placement
officers, resumes, jobs (with their eligibility criteria), applications, eligibility checks,
application history and notifications. Demo data is seeded with deadlines relative to the current time.
"""
import json
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timedelta

SCHEMA = """
CREATE TABLE IF NOT EXISTS companies (
    company_id INTEGER PRIMARY KEY, name TEXT NOT NULL, industry TEXT, website TEXT,
    contact_person TEXT, is_approved INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS recruiters (
    recruiter_id INTEGER PRIMARY KEY, name TEXT NOT NULL, designation TEXT,
    company_id INTEGER NOT NULL REFERENCES companies(company_id));
CREATE TABLE IF NOT EXISTS placement_officers (
    officer_id INTEGER PRIMARY KEY, name TEXT NOT NULL, designation TEXT);
CREATE TABLE IF NOT EXISTS students (
    student_id INTEGER PRIMARY KEY, roll_no TEXT UNIQUE, name TEXT NOT NULL, department TEXT NOT NULL,
    batch TEXT NOT NULL, cgpa REAL NOT NULL, backlogs INTEGER NOT NULL, is_placed INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS resumes (
    resume_id INTEGER PRIMARY KEY, student_id INTEGER NOT NULL REFERENCES students(student_id),
    file_name TEXT NOT NULL, is_active INTEGER NOT NULL DEFAULT 1);
CREATE TABLE IF NOT EXISTS jobs (
    job_id INTEGER PRIMARY KEY AUTOINCREMENT, company_id INTEGER NOT NULL REFERENCES companies(company_id),
    posted_by INTEGER NOT NULL REFERENCES recruiters(recruiter_id), title TEXT NOT NULL, description TEXT NOT NULL,
    ctc REAL NOT NULL, location TEXT NOT NULL, deadline TEXT NOT NULL, status TEXT NOT NULL,
    criteria TEXT NOT NULL, remarks TEXT, decided_by INTEGER);
CREATE TABLE IF NOT EXISTS applications (
    app_id INTEGER PRIMARY KEY AUTOINCREMENT, tracking_id TEXT UNIQUE, student_id INTEGER NOT NULL,
    job_id INTEGER NOT NULL, resume_id INTEGER NOT NULL, cover_note TEXT, applied_on TEXT NOT NULL,
    status TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS application_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT, app_id INTEGER NOT NULL, from_state TEXT, to_state TEXT NOT NULL,
    event TEXT NOT NULL, actor TEXT NOT NULL, at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS eligibility_checks (
    elig_id INTEGER PRIMARY KEY AUTOINCREMENT, job_id INTEGER NOT NULL, student_id INTEGER NOT NULL,
    is_eligible INTEGER NOT NULL, remarks TEXT, checked_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS notifications (
    notif_id INTEGER PRIMARY KEY AUTOINCREMENT, recipient_type TEXT NOT NULL, recipient_id INTEGER NOT NULL,
    message TEXT NOT NULL, sent_at TEXT NOT NULL, read_flag INTEGER NOT NULL DEFAULT 0);
"""

COMPANIES = [
    (1, "Nimbus Analytics Pvt Ltd", "Software", "https://nimbus.example", "Ritika Menon", 1),
    (2, "Orbit Systems", "Embedded systems", "https://orbit.example", "Sameer Khan", 1),
    (3, "Vertex Labs", "Consulting", "https://vertex.example", "Anil Rao", 0),
]
RECRUITERS = [(1, "Ritika Menon", "HR Lead", 1), (2, "Sameer Khan", "Engineering Manager", 2),
              (3, "Anil Rao", "Talent Partner", 3)]
OFFICERS = [(1, "Dr. N. Bhagat", "Training and Placement Officer")]
STUDENTS = [
    (101, "R23CS101", "Aarav Kulkarni", "CSE", "2023-2027", 8.60, 0, 0),
    (102, "R23IT102", "Diya Joshi", "IT", "2023-2027", 7.40, 0, 0),
    (103, "R23EC103", "Kabir Deshmukh", "ECE", "2023-2027", 6.80, 1, 0),
    (104, "R23CS104", "Meera Patil", "CSE", "2023-2027", 9.10, 0, 1),
    (105, "R22ME105", "Rohan Wankhede", "ME", "2022-2026", 7.90, 2, 0),
]
NOTIFY_SQL = "INSERT INTO notifications (recipient_type, recipient_id, message, sent_at) VALUES (?, ?, ?, ?)"
HISTORY_SQL = ("INSERT INTO application_history (app_id, from_state, to_state, event, actor, at) "
               "VALUES (?, ?, ?, ?, ?, ?)")

RESUMES = [(1, 101, "Aarav_Resume_v2.pdf", 1), (2, 101, "Aarav_Resume_v1.pdf", 0), (3, 102, "Diya_Resume.pdf", 1),
           (4, 103, "Kabir_Resume.pdf", 1), (5, 104, "Meera_Resume.pdf", 1), (6, 105, "Rohan_Resume.pdf", 1)]


def seed_jobs(now):
    def crit(min_cgpa, branches, backlogs, batch):
        return json.dumps({"min_cgpa": min_cgpa, "allowed_branches": branches, "max_backlogs": backlogs,
                           "batch": batch})
    day = timedelta(days=1)
    return [
        (1, 1, 1, "Software Engineer", "Build and maintain web services for analytics products in a small "
         "agile team.", 8.5, "Pune", (now + 30 * day).isoformat(timespec="minutes"), "published",
         crit(7.0, ["CSE", "IT"], 0, "2023-2027")),
        (2, 2, 2, "Embedded Systems Engineer", "Develop firmware for sensor and controller boards and test it "
         "on hardware.", 6.0, "Bengaluru", (now + 20 * day).isoformat(timespec="minutes"), "published",
         crit(6.5, ["CSE", "ECE", "EE"], 1, None)),
        (3, 1, 1, "Data Analyst", "Prepare dashboards and reports from product usage data for business teams.",
         7.0, "Hyderabad", (now + 25 * day).isoformat(timespec="minutes"), "pending",
         crit(7.5, [], 0, None)),
        (4, 2, 2, "Firmware Intern", "Six-month internship on board bring-up and device drivers for IoT "
         "products.", 3.6, "Nagpur", (now - 1 * day).isoformat(timespec="minutes"), "published",
         crit(6.0, ["ECE", "EE"], None, None)),
    ]


class Database:
    def __init__(self, path, now=None):
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.lock = threading.Lock()
        with self.lock, self.conn:
            self.conn.executescript(SCHEMA)
            if not self.conn.execute("SELECT COUNT(*) FROM students").fetchone()[0]:
                self._seed(now or datetime.now())

    def _seed(self, now):
        c = self.conn
        c.executemany("INSERT INTO companies VALUES (?, ?, ?, ?, ?, ?)", COMPANIES)
        c.executemany("INSERT INTO recruiters VALUES (?, ?, ?, ?)", RECRUITERS)
        c.executemany("INSERT INTO placement_officers VALUES (?, ?, ?)", OFFICERS)
        c.executemany("INSERT INTO students VALUES (?, ?, ?, ?, ?, ?, ?, ?)", STUDENTS)
        c.executemany("INSERT INTO resumes VALUES (?, ?, ?, ?)", RESUMES)
        c.executemany("INSERT INTO jobs (job_id, company_id, posted_by, title, description, ctc, location, "
                      "deadline, status, criteria) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", seed_jobs(now))

    def all(self, sql, args=()):
        with self.lock:
            return [dict(r) for r in self.conn.execute(sql, args).fetchall()]

    def one(self, sql, args=()):
        rows = self.all(sql, args)
        return rows[0] if rows else None

    def write(self, sql, args=()):
        with self.lock, self.conn:
            return self.conn.execute(sql, args).lastrowid

    @contextmanager
    def transaction(self):
        """Statements run on the yielded connection are committed together or rolled back together (UC-1 E4)."""
        with self.lock:
            try:
                yield self.conn
                self.conn.commit()
            except BaseException:
                self.conn.rollback()
                raise

    def notify(self, recipient_type, recipient_id, message, now):
        return self.write(NOTIFY_SQL, (recipient_type, recipient_id, message, now.isoformat(timespec="seconds")))
