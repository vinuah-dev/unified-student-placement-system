"""Integration test cases: Module 1 (posting, approval, eligibility) and Module 2 (application, tracking) working
together through the REST API, the database and the notification table, as in the Expt-4 sequence diagram.
"""
import sqlite3
import threading
from datetime import datetime
from unittest import mock

from .helpers import TestServer, with_server
from .m1_cases import VALID_JOB
from .m2_cases import MAIN_PATH

MODULE = "Integration (M1 + M2)"


def case(id, technique, scenario, data, expected, run):
    return dict(id=id, module=MODULE, technique=technique, scenario=scenario, data=data, expected=expected, run=run)


def notified_students(srv, job_key):
    return [r["recipient_id"] for r in srv.app.db.all(
        "SELECT recipient_id FROM notifications WHERE recipient_type = 'student' AND message LIKE ? "
        "ORDER BY recipient_id", ("%" + job_key + "%",))]


def end_to_end(srv):
    """UC-2 then UC-1: post -> approve -> notify -> apply -> statechart to Accepted -> placement lock."""
    steps = [srv.result("POST", "/api/jobs", dict(VALID_JOB, recruiter_id=1, allowed_branches=["CSE", "IT"]))]
    steps.append(srv.decide(5, "approve"))
    steps.append("notified %s" % notified_students(srv, "J-5"))
    steps.append(srv.apply(student_id=102, job_id=5, resume_id=3))
    for e in MAIN_PATH:
        srv.event(1, e)
    steps.append(srv.event(1, "accept_offer", "student", 102))
    steps.append(srv.apply(student_id=102, job_id=1, resume_id=3))
    return " | ".join(steps)


def returned_then_published(srv):
    states = []
    srv.decide(3, "return", "Add the batch criterion.")
    states.append(srv.app.db.one("SELECT status FROM jobs WHERE job_id = 3")["status"])
    srv.result("PUT", "/api/jobs/3", dict(VALID_JOB, recruiter_id=1, title="Data Analyst"))
    states.append(srv.app.db.one("SELECT status FROM jobs WHERE job_id = 3")["status"])
    srv.decide(3, "approve")
    states.append(srv.app.db.one("SELECT status FROM jobs WHERE job_id = 3")["status"])
    on_board = any(j["job_id"] == 3 for j in srv.board("student_id=101")["jobs"])
    return "%s | on student board=%s" % (" -> ".join(states), on_board)


def rejected_posting(srv):
    srv.result("POST", "/api/jobs", dict(VALID_JOB, recruiter_id=1))
    srv.decide(5, "reject", "Duplicate of J-1.")
    on_board = any(j["job_id"] == 5 for j in srv.board()["jobs"])
    return "on board=%s | %s" % (on_board, srv.apply(job_id=5))


def rollback(srv):
    before = srv.count("notifications")
    with mock.patch("app.rules.tracking_id", side_effect=sqlite3.OperationalError("disk I/O error")):
        msg = srv.apply()
    return "%s | applications=%d, history=%d, new notifications=%d" % (
        msg, srv.count("applications"), srv.count("application_history"), srv.count("notifications") - before)


def deadline_crossing(srv):
    first = srv.apply(job_id=2)
    srv.clock.set(datetime(2026, 11, 15, 10, 0))       # J-2 deadline reached
    j2 = next(j for j in srv.board("student_id=101")["jobs"] if j["job_id"] == 2)
    late = srv.apply(student_id=102, job_id=2, resume_id=3)
    wd = srv.result("POST", "/api/applications/1/withdraw", {"student_id": 101})
    return " | ".join([first, "J-2 open=%s" % j2["open"], late, wd])


def board_matches_apply(srv):
    """For every demo student the eligibility shown on the board agrees with the outcome of applying to J-1."""
    out = []
    for sid, resume in ((101, 1), (102, 3), (103, 4), (105, 6)):
        shown = next(j for j in srv.board("student_id=%d" % sid)["jobs"] if j["job_id"] == 1)["eligible"]
        status = srv.call("POST", "/api/applications", {"student_id": sid, "job_id": 1, "resume_id": resume})[0]
        out.append("%d:%s/%d" % (sid, "eligible" if shown else "ineligible", status))
    return ", ".join(out)


def concurrent_duplicates(srv):
    statuses = []

    def go():
        statuses.append(srv.call("POST", "/api/applications", {"student_id": 101, "job_id": 1, "resume_id": 1})[0])
    threads = [threading.Thread(target=go) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    return "responses %s | applications stored=%d" % (sorted(statuses), srv.count("applications"))


def survives_restart():
    first = TestServer()
    first.apply()
    tmp = first.tmp
    first.stop(cleanup=False)
    again = TestServer(db_path=first.db_path, clock=first.clock)
    try:
        return "students=%d, jobs=%d, applications=%d, status=%s" % (
            again.count("students"), again.count("jobs"), again.count("applications"),
            again.app.db.one("SELECT status FROM applications WHERE app_id = 1")["status"])
    finally:
        again.stop(cleanup=False)
        tmp.cleanup()


def version_changes(srv):
    v = lambda: srv.call("GET", "/api/version")[1]["version"]
    start = v()
    srv.board("student_id=101")
    srv.call("GET", "/api/applications")
    after_reads = v()
    srv.apply(student_id=103)                     # rejected: not eligible
    after_rejected = v()
    srv.result("POST", "/api/jobs", dict(VALID_JOB, recruiter_id=2))
    after_post = v()
    return "after reads: %s | after rejected request: %s | after job posted: %s" % (
        "changed" if after_reads != start else "same", "changed" if after_rejected != after_reads else "same",
        "changed" if after_post != after_rejected else "same")


def burst(srv, path, body, n):
    """Sends n identical requests at the same moment; returns the sorted status codes."""
    gate = threading.Barrier(n)
    out = []

    def go():
        gate.wait()
        out.append(srv.call("POST", path, body)[0])
    threads = [threading.Thread(target=go) for _ in range(n)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    return sorted(out)


def repeated_approvals():
    """10 trials: 6 identical approvals of J-3 at once (double clicks / two officers)."""
    bad = 0
    for _ in range(10):
        srv = TestServer()
        try:
            codes = burst(srv, "/api/jobs/3/decision", {"decision": "approve", "actor_role": "officer", "actor_id": 1}, 6)
            told = srv.count("notifications", "recipient_type = 'student' AND message LIKE '%J-3%'")
            bad += codes.count(200) != 1 or told != 1
        finally:
            srv.stop()
    return "trials with a double decision: %d of 10" % bad


def repeated_status_changes():
    """10 trials: 8 identical 'under_review' requests at once for one application."""
    bad = 0
    for _ in range(10):
        srv = TestServer()
        try:
            srv.apply()
            codes = burst(srv, "/api/applications/1/events",
                          {"event": "under_review", "actor_role": "recruiter", "actor_id": 1}, 8)
            bad += codes.count(200) != 1 or srv.count("application_history") != 2
        finally:
            srv.stop()
    return "trials with a double status change: %d of 10" % bad


CASES = [
    case("TC_INT_01", "Integration / Functional", "Complete placement flow across both modules",
         "recruiter 1 posts J-5 (CGPA>=7, CSE/IT, 0 backlogs, 2023-2027) -> officer approves -> student 102 "
         "applies -> recruiter takes it to Offer Issued -> student accepts -> student applies to J-1",
         "200: Job J-5 submitted for approval (status: Pending). | 200: Job J-5 published. 2 eligible student(s) "
         "notified. | notified [101, 102] | 200: Application submitted for J-5. Tracking id USPS-26-0001. | "
         "200: Application USPS-26-0001 is now Accepted. | 409: You are already placed; the placement policy "
         "blocks further applications.", with_server(end_to_end)),
    case("TC_INT_02", "Integration / Functional", "Returned posting is fixed, resubmitted and published (UC-2 A1)",
         "officer returns J-3 -> recruiter 1 resubmits -> officer approves", "returned -> pending -> published | "
         "on student board=True", with_server(returned_then_published)),
    case("TC_INT_03", "Integration / Functional", "Rejected posting is never visible or open (UC-2 E2)",
         "post J-5 -> officer rejects -> student 101 applies to J-5",
         "on board=False | 409: Job J-5 is not open for applications.", with_server(rejected_posting)),
    case("TC_INT_04", "Integration / Exception (UC-1 E4)", "Database error while saving rolls everything back",
         "tracking-id step fails with 'disk I/O error' during student 101 -> J-1",
         "500: Your application could not be saved and nothing was stored. Please try again. | applications=0, "
         "history=0, new notifications=0", with_server(rollback)),
    case("TC_INT_05", "Integration / BVA", "Crossing the deadline closes the job for apply and withdraw",
         "101 applies to J-2, clock moves to J-2 deadline, 102 applies, 101 withdraws",
         "200: Application submitted for J-2. Tracking id USPS-26-0001. | J-2 open=False | 409: The application "
         "deadline for J-2 has passed. | 409: The deadline has passed; the application can no longer be withdrawn.",
         with_server(deadline_crossing)),
    case("TC_INT_06", "Integration / Functional", "Eligibility on the job board matches the apply check (BR-03)",
         "students 101, 102, 103, 105 vs J-1", "101:eligible/200, 102:eligible/200, 103:ineligible/409, "
         "105:ineligible/409", with_server(board_matches_apply)),
    case("TC_INT_07", "Integration / Concurrency", "Five simultaneous identical applications",
         "5 parallel POSTs student 101 -> J-1", "responses [200, 409, 409, 409, 409] | applications stored=1",
         with_server(concurrent_duplicates)),
    case("TC_INT_08", "Integration / Persistence", "Data is kept after a server restart and not re-seeded",
         "apply, stop server, start a new server on the same database file",
         "students=5, jobs=4, applications=1, status=Applied", survives_restart),
    case("TC_INT_09", "Integration / Functional", "Data version that open pages poll for live updates (FR-2.12)",
         "GET /api/version before and after reads, a rejected apply and a job posting",
         "after reads: same | after rejected request: same | after job posted: changed", with_server(version_changes)),
    case("TC_INT_10", "Integration / Concurrency", "Same approval sent several times at once (FR-1.4)",
         "10 trials of 6 simultaneous 'approve J-3' requests", "trials with a double decision: 0 of 10",
         repeated_approvals),
    case("TC_INT_11", "Integration / Concurrency", "Same status change sent several times at once (FR-2.5)",
         "10 trials of 8 simultaneous 'under_review' requests", "trials with a double status change: 0 of 10",
         repeated_status_changes),
]
