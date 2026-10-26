"""Module 2 test cases - Job Application and Tracking.

TC_M2_01-08 are unit tests of the application statechart in app/rules.py; TC_M2_09-42 go through the REST API
and database of a fresh server with the demo data. Expected results come from docs/requirements.md.
Test clock: 26-10-2026 10:00; J-1 closes 25-11-2026 10:00, J-2 closes 15-11-2026 10:00.
"""
from datetime import datetime

from app.rules import RuleError, next_state, tracking_id

from .helpers import with_server

MODULE = "M2 Application & Tracking"
MAIN_PATH = ["under_review", "shortlist", "schedule_interview", "interview_result", "offer_letter"]
J2_DEADLINE = datetime(2026, 11, 15, 10, 0)


def case(id, technique, scenario, data, expected, run):
    return dict(id=id, module=MODULE, technique=technique, scenario=scenario, data=data, expected=expected, run=run)


def state_after(state, *events):
    try:
        for e in events:
            state = next_state(state, e)
        return state
    except RuleError as e:
        return str(e)


def walk(state, events):
    seen = [state]
    for e in events:
        state = next_state(state, e)
        seen.append(state)
    return " -> ".join(seen)


def to_offer(srv, app_id=1):
    for e in MAIN_PATH:
        srv.event(app_id, e)


# ----- API scenarios -----
def applied_records(srv):
    srv.apply()
    a = srv.app.db.one("SELECT status, tracking_id FROM applications WHERE app_id = 1")
    rec = srv.count("notifications", "recipient_type = 'recruiter' AND recipient_id = 1 AND message LIKE ?",
                    ("%" + a["tracking_id"] + "%",))
    stu = srv.count("notifications", "recipient_type = 'student' AND recipient_id = 101 AND message LIKE ?",
                    ("%" + a["tracking_id"] + "%",))
    return "status=%s | recruiter notified=%s | student confirmation=%s" % (a["status"], rec > 0, stu > 0)


def at_deadline(srv, minutes_before):
    srv.clock.set(J2_DEADLINE)
    srv.clock.advance(minutes=-minutes_before)
    return srv.apply(job_id=2)


def duplicate(srv):
    srv.apply()
    return srv.apply()


def nothing_stored(srv):
    srv.apply(student_id=103)      # not eligible for J-1
    srv.apply(job_id=3)            # pending job
    srv.apply(resume_id=2)         # inactive resume
    return "applications=%d, history=%d" % (srv.count("applications"), srv.count("application_history"))


def history_after_review(srv):
    srv.apply()
    srv.event(1, "under_review")
    rows = srv.app.db.all("SELECT event, actor FROM application_history WHERE app_id = 1 ORDER BY id")
    told = srv.count("notifications", "recipient_type = 'student' AND recipient_id = 101 AND message LIKE "
                                      "'%Under Review%'")
    return "history: %s | student notified=%s" % (", ".join("%s by %s" % (r["event"], r["actor"]) for r in rows),
                                                   told > 0)


def first(srv, *steps):
    srv.apply()
    for s in steps[:-1]:
        s(srv)
    return steps[-1](srv)


def recruiter_lists(srv):
    srv.apply()
    srv.apply(student_id=103, job_id=2, resume_id=4)
    one = srv.call("GET", "/api/applications?recruiter_id=1")[1]
    two = srv.call("GET", "/api/applications?recruiter_id=2")[1]
    return "recruiter 1: %s | recruiter 2: %s" % ([a["tracking_id"] for a in one], [a["tracking_id"] for a in two])


def withdraw(srv, student_id=101):
    return srv.result("POST", "/api/applications/1/withdraw", {"student_id": student_id})


def accept(srv):
    srv.apply()
    to_offer(srv)
    msg = srv.event(1, "accept_offer", "student", 101)
    return "%s | is_placed=%d" % (msg, srv.app.db.one("SELECT is_placed FROM students WHERE student_id = 101")["is_placed"])


def second_offer(srv):
    srv.apply()
    srv.apply(job_id=2)
    to_offer(srv, 1)
    for e in MAIN_PATH:
        srv.event(2, e, "recruiter", 2)
    srv.event(1, "accept_offer", "student", 101)
    return srv.event(2, "accept_offer", "student", 101)


def full_history(srv):
    srv.apply()
    to_offer(srv)
    srv.event(1, "accept_offer", "student", 101)
    h = srv.call("GET", "/api/applications/1")[1]["history"]
    return "%d entries: %s" % (len(h), ", ".join(x["event"] for x in h))


def newest_first(srv):
    srv.apply()
    srv.event(1, "under_review")
    srv.event(1, "shortlist")
    n = srv.call("GET", "/api/notifications?recipient_type=student&recipient_id=101")[1]
    return "%d notifications, newest is about Shortlisted=%s" % (len(n), "Shortlisted" in n[0]["message"])


def my_apps_order(srv):
    srv.apply()
    srv.apply(job_id=2)
    return ", ".join(a["tracking_id"] for a in srv.call("GET", "/api/applications?student_id=101")[1])


CASES = [
    # ---------------- unit: statechart (FR-2.5) ----------------
    case("TC_M2_01", "Unit / Functional", "First recruiter step from Applied", "Applied + under_review",
         "Under Review", lambda: state_after("Applied", "under_review")),
    case("TC_M2_02", "Unit / Functional", "Main success path of the statechart",
         "Applied + under_review, shortlist, schedule_interview, interview_result, offer_letter, accept_offer",
         "Applied -> Under Review -> Shortlisted -> Interview Scheduled -> Selected -> Offer Issued -> Accepted",
         lambda: walk("Applied", MAIN_PATH + ["accept_offer"])),
    case("TC_M2_03", "Unit / Functional", "Rescheduling keeps the interview state", "Interview Scheduled + reschedule",
         "Interview Scheduled", lambda: state_after("Interview Scheduled", "reschedule")),
    case("TC_M2_04", "Unit / EP", "Reject from each state that allows it",
         "reject from Under Review, Shortlisted, Interview Scheduled, Selected", "Rejected, Rejected, Rejected, Rejected",
         lambda: ", ".join(state_after(s, "reject") for s in
                           ("Under Review", "Shortlisted", "Interview Scheduled", "Selected"))),
    case("TC_M2_05", "Unit / Validation / BR-08", "Offer letter before the candidate is selected",
         "Shortlisted + offer_letter", "Event 'offer_letter' is not allowed when the application is Shortlisted.",
         lambda: state_after("Shortlisted", "offer_letter")),
    case("TC_M2_06", "Unit / Validation", "Withdraw after the review has started", "Under Review + withdraw",
         "Event 'withdraw' is not allowed when the application is Under Review.",
         lambda: state_after("Under Review", "withdraw")),
    case("TC_M2_07", "Unit / Validation", "Any step from a final state", "Accepted + reject",
         "Event 'reject' is not allowed when the application is Accepted.", lambda: state_after("Accepted", "reject")),
    case("TC_M2_08", "Unit / BVA", "Tracking id format at the smallest and largest 4-digit numbers",
         "tracking_id(1, 2026), tracking_id(9999, 2026)", "USPS-26-0001, USPS-26-9999",
         lambda: tracking_id(1, 2026) + ", " + tracking_id(9999, 2026)),

    # ---------------- API: submission (FR-2.1, FR-2.2) ----------------
    case("TC_M2_09", "Functional (API) / UC-1", "Eligible student applies with the active resume",
         "student 101 -> J-1, resume 1, cover note ''", "200: Application submitted for J-1. Tracking id USPS-26-0001.",
         with_server(lambda s: s.apply())),
    case("TC_M2_10", "Functional (API)", "Stored status and notifications after applying", "student 101 -> J-1",
         "status=Applied | recruiter notified=True | student confirmation=True", with_server(applied_records)),
    case("TC_M2_11", "Validation (API)", "Applying to a job that is not published", "student 101 -> J-3 (pending)",
         "409: Job J-3 is not open for applications.", with_server(lambda s: s.apply(job_id=3))),
    case("TC_M2_12", "Validation (API) / BR-04", "Applying after the deadline (UC-1 E2)",
         "student 103 -> J-4 (deadline 25-10-2026 10:00)", "409: The application deadline for J-4 has passed.",
         with_server(lambda s: s.apply(student_id=103, job_id=4, resume_id=4))),
    case("TC_M2_13", "BVA (API)", "Applying one minute before the deadline", "clock 15-11-2026 09:59, J-2",
         "200: Application submitted for J-2. Tracking id USPS-26-0001.", with_server(lambda s: at_deadline(s, 1))),
    case("TC_M2_14", "BVA (API)", "Applying exactly at the deadline", "clock 15-11-2026 10:00, J-2",
         "409: The application deadline for J-2 has passed.", with_server(lambda s: at_deadline(s, 0))),
    case("TC_M2_15", "Validation (API) / BR-05", "Already placed student applies", "student 104 (placed) -> J-1",
         "409: You are already placed; the placement policy blocks further applications.",
         with_server(lambda s: s.apply(student_id=104, resume_id=5))),
    case("TC_M2_16", "Validation (API) / BR-03", "Ineligible student applies (UC-1 E1)", "student 103 -> J-1",
         "409: You are not eligible for J-1: CGPA 6.80 is below the minimum 7.00. Branch ECE is not in the "
         "allowed branches (CSE, IT). Active backlogs 1 exceed the maximum 0.",
         with_server(lambda s: s.apply(student_id=103, resume_id=4))),
    case("TC_M2_17", "Validation (API)", "Second application to the same job (UC-1 E3)", "student 101 -> J-1 twice",
         "409: You have already applied to J-1 (tracking id USPS-26-0001).", with_server(duplicate)),
    case("TC_M2_18", "EP (API, invalid)", "Inactive resume selected", "resume 2 (Aarav v1, inactive)",
         "400: Select one of your active resumes.", with_server(lambda s: s.apply(resume_id=2))),
    case("TC_M2_19", "EP (API, invalid)", "Another student's resume selected", "resume 3 (Diya's)",
         "400: Select one of your active resumes.", with_server(lambda s: s.apply(resume_id=3))),
    case("TC_M2_20", "Validation (API)", "No resume selected", "resume_id=null",
         "400: Select one of your active resumes.", with_server(lambda s: s.apply(resume_id=None))),
    case("TC_M2_21", "BVA (API, max)", "Cover note of 500 characters", "cover_note='a'*500",
         "200: Application submitted for J-1. Tracking id USPS-26-0001.", with_server(lambda s: s.apply(note="a" * 500))),
    case("TC_M2_22", "BVA (API, max+1)", "Cover note of 501 characters", "cover_note='a'*501",
         "400: Cover note cannot exceed 500 characters.", with_server(lambda s: s.apply(note="a" * 501))),
    case("TC_M2_23", "Functional (API)", "Rejected submissions leave no record (UC-1 postcondition)",
         "ineligible, pending job, inactive resume", "applications=0, history=0", with_server(nothing_stored)),

    # ---------------- API: workflow and authorisation (FR-2.5, FR-2.6) ----------------
    case("TC_M2_24", "Functional (API)", "Recruiter moves the application to review", "recruiter 1: under_review",
         "200: Application USPS-26-0001 is now Under Review.",
         with_server(lambda s: first(s, lambda x: x.event(1, "under_review")))),
    case("TC_M2_25", "Functional (API)", "Status change is stored in the history and the student is notified",
         "apply, then under_review by recruiter 1",
         "history: submit by student 101, under_review by recruiter 1 | student notified=True",
         with_server(history_after_review)),
    case("TC_M2_26", "Validation (API) / BR-08", "Offer letter straight from Applied", "recruiter 1: offer_letter",
         "409: Event 'offer_letter' is not allowed when the application is Applied.",
         with_server(lambda s: first(s, lambda x: x.event(1, "offer_letter")))),
    case("TC_M2_27", "Functional (API) / BR-07", "Recruiter of another company changes the application",
         "recruiter 2 (Orbit): under_review on a J-1 application",
         "403: Only the recruiter who posted this job or a Placement Officer can update this application.",
         with_server(lambda s: first(s, lambda x: x.event(1, "under_review", "recruiter", 2)))),
    case("TC_M2_28", "Functional (API)", "Placement officer changes the application", "officer 1: under_review",
         "200: Application USPS-26-0001 is now Under Review.",
         with_server(lambda s: first(s, lambda x: x.event(1, "under_review", "officer", 1)))),
    case("TC_M2_29", "Functional (API) / BR-07", "Recruiter sees only applicants of own jobs",
         "101 -> J-1 (recruiter 1), 103 -> J-2 (recruiter 2)",
         "recruiter 1: ['USPS-26-0001'] | recruiter 2: ['USPS-26-0002']", with_server(recruiter_lists)),
    case("TC_M2_30", "Functional (API)", "Student tries a recruiter step on own application", "student 101: shortlist",
         "403: Only the recruiter who posted this job or a Placement Officer can update this application.",
         with_server(lambda s: first(s, lambda x: x.event(1, "shortlist", "student", 101)))),
    case("TC_M2_31", "Functional (API)", "Recruiter tries to accept the offer for the student",
         "Offer Issued, recruiter 1: accept_offer", "403: Only the student who applied can respond to the offer.",
         with_server(lambda s: first(s, to_offer, lambda x: x.event(1, "accept_offer")))),
    case("TC_M2_32", "EP (API, invalid)", "Event name that does not exist", "event='hire'",
         "400: Unknown event 'hire'.", with_server(lambda s: first(s, lambda x: x.event(1, "hire")))),

    # ---------------- API: withdrawal (FR-2.7) ----------------
    case("TC_M2_33", "Functional (API) / FR-16", "Student withdraws before the deadline", "student 101, Applied",
         "200: Application USPS-26-0001 is now Withdrawn.", with_server(lambda s: first(s, withdraw))),
    case("TC_M2_34", "Functional (API)", "Another student tries to withdraw it", "student 102 withdraws app 1",
         "403: Only the student who applied can withdraw this application.",
         with_server(lambda s: first(s, lambda x: withdraw(x, 102)))),
    case("TC_M2_35", "Validation (API)", "Withdraw after the review has started", "status Under Review",
         "409: Only an application in the Applied state can be withdrawn (current: Under Review).",
         with_server(lambda s: first(s, lambda x: x.event(1, "under_review"), withdraw))),
    case("TC_M2_36", "BVA (API)", "Withdraw after the deadline", "clock moved to 25-11-2026 10:00 (J-1 deadline)",
         "409: The deadline has passed; the application can no longer be withdrawn.",
         with_server(lambda s: first(s, lambda x: x.clock.set(datetime(2026, 11, 25, 10, 0)), withdraw))),
    case("TC_M2_37", "Validation (API)", "Applying again after withdrawing (UC-1 E3)", "withdraw, then apply to J-1",
         "409: You have already applied to J-1 (tracking id USPS-26-0001).",
         with_server(lambda s: first(s, withdraw, lambda x: x.apply()))),

    # ---------------- API: offers and tracking (FR-2.8, FR-2.9, FR-2.11) ----------------
    case("TC_M2_38", "Functional (API) / BR-01", "Student accepts the offer and becomes placed",
         "Offer Issued, student 101: accept_offer", "200: Application USPS-26-0001 is now Accepted. | is_placed=1",
         with_server(accept)),
    case("TC_M2_39", "Functional (API) / BR-01", "Accepting a second offer", "offers for J-1 and J-2, accept J-1 then J-2",
         "409: You already hold an accepted offer; the placement policy allows only one.", with_server(second_offer)),
    case("TC_M2_40", "Functional (API)", "Student declines the offer", "Offer Issued, student 101: reject_offer",
         "200: Application USPS-26-0001 is now Rejected.",
         with_server(lambda s: first(s, to_offer, lambda x: x.event(1, "reject_offer", "student", 101)))),
    case("TC_M2_41", "Functional (API) / FR-17", "Timeline holds every step with its actor",
         "full path to Accepted, GET /api/applications/1",
         "7 entries: submit, under_review, shortlist, schedule_interview, interview_result, offer_letter, accept_offer",
         with_server(full_history)),
    case("TC_M2_42", "Functional (API)", "Notifications and applications are listed newest first",
         "apply J-1, under_review, shortlist; apply J-2",
         "3 notifications, newest is about Shortlisted=True | USPS-26-0002, USPS-26-0001",
         with_server(lambda s: newest_first(s) + " | " + my_apps_order(s))),
]
