"""Module 1 test cases - Job Posting and Eligibility Verification.

TC_M1_01-37 are unit tests of app/rules.py (validate_job_posting, EligibilityCriteria, validate_job_decision);
TC_M1_38-59 go through the REST API and database of a fresh server with the demo data (docs/requirements.md).
Expected results are taken from the requirements, not from the code.
"""
from datetime import datetime

from app.rules import EligibilityCriteria, RuleError, validate_job_decision, validate_job_posting

from .helpers import START, keys, with_server

MODULE = "M1 Job Posting & Eligibility"
NOW = START   # 26-10-2026 10:00
VALID_JOB = {"title": "Backend Developer",
             "description": "Design REST APIs and database schemas for the analytics platform.",
             "ctc": 9, "location": "Pune", "deadline": "2026-11-05T17:00",
             "min_cgpa": 7, "allowed_branches": ["CSE"], "max_backlogs": 0, "batch": "2023-2027"}
NO_CRITERIA = {"min_cgpa": "", "allowed_branches": [], "max_backlogs": "", "batch": ""}

AARAV = {"cgpa": 8.60, "department": "CSE", "backlogs": 0, "batch": "2023-2027"}
DIYA = {"cgpa": 7.40, "department": "IT", "backlogs": 0, "batch": "2023-2027"}
KABIR = {"cgpa": 6.80, "department": "ECE", "backlogs": 1, "batch": "2023-2027"}
ROHAN = {"cgpa": 7.90, "department": "ME", "backlogs": 2, "batch": "2022-2026"}
J1_RULES = EligibilityCriteria(7.0, ["CSE", "IT"], 0, "2023-2027")


def posting(**changes):
    data = dict(VALID_JOB)
    data.update(changes)
    try:
        validate_job_posting(data, NOW)
        return "accepted"
    except RuleError as e:
        return str(e)


def eligibility(rules, student):
    ok, reasons = rules.evaluate(student)
    return "eligible" if ok else " | ".join(reasons)


def decision(status, choice, remarks):
    try:
        return validate_job_decision(status, choice, remarks)
    except RuleError as e:
        return str(e)


def case(id, technique, scenario, data, expected, run):
    return dict(id=id, module=MODULE, technique=technique, scenario=scenario, data=data, expected=expected, run=run)


def post(srv, recruiter_id=1, **changes):
    body = dict(VALID_JOB, recruiter_id=recruiter_id)
    body.update(changes)
    return srv.result("POST", "/api/jobs", body)


# ----- API scenarios -----
def post_valid(srv):
    msg = post(srv)
    job = srv.app.db.one("SELECT status FROM jobs WHERE job_id = 5")
    told = srv.count("notifications", "recipient_type = 'officer' AND message LIKE '%J-5%'")
    return "%s | status=%s | officer notified=%s" % (msg, job["status"], told > 0)


def approve_j3(srv):
    msg = srv.decide(3, "approve")
    ids = [r["recipient_id"] for r in srv.app.db.all(
        "SELECT recipient_id FROM notifications WHERE recipient_type = 'student' AND message LIKE '%J-3%' "
        "ORDER BY recipient_id")]
    return "%s | students notified: %s" % (msg, ids)


def return_j3(srv):
    msg = srv.decide(3, "return", "Add the batch criterion.")
    told = srv.count("notifications", "recipient_type = 'recruiter' AND recipient_id = 1 AND message LIKE '%J-3%' "
                                      "AND message LIKE '%Add the batch criterion.%'")
    return "%s | recruiter 1 told with remarks=%s" % (msg, told > 0)


def resubmit(srv, recruiter_id=1, first_return=True):
    if first_return:
        srv.decide(3, "return", "Add the batch criterion.")
    body = dict(VALID_JOB, recruiter_id=recruiter_id, title="Data Analyst", batch="2023-2027")
    msg = srv.result("PUT", "/api/jobs/3", body)
    return "%s | status=%s" % (msg, srv.app.db.one("SELECT status FROM jobs WHERE job_id = 3")["status"])


def board_keys(srv, query):
    b = srv.board(query)
    return b if isinstance(b, str) else keys(b["jobs"])


def board_open_flags(srv):
    b = srv.board("student_id=101")
    return ", ".join("J-%d %s" % (j["job_id"], "open" if j["open"] else "closed") for j in b["jobs"])


def board_page(srv):
    b = srv.board("per_page=2&page=2")
    return "page %d of %d (%d jobs): %s" % (b["page"], b["pages"], b["total"], keys(b["jobs"]))


def eligibility_api(srv):
    before = srv.count("eligibility_checks")
    status, body = srv.call("GET", "/api/jobs/1/eligibility?student_id=105")
    after = srv.count("eligibility_checks")
    return "%d: eligible=%s; %s; recorded=%d" % (status, body["eligible"], " ".join(body["reasons"]), after - before)


def expired(srv, choice, remarks):
    srv.clock.set(datetime(2026, 11, 20, 10, 0))
    msg = srv.decide(3, choice, remarks)
    return "%s | status=%s" % (msg, srv.app.db.one("SELECT status FROM jobs WHERE job_id = 3")["status"])


CASES = [
    # ---------------- unit: job posting validation (FR-1.1, FR-1.2) ----------------
    case("TC_M1_01", "Unit / EP (valid)", "Valid job posting with all criteria",
         "Backend Developer, 9 LPA, Pune, deadline 05-11-2026 17:00, CGPA>=7, CSE, 0 backlogs, 2023-2027",
         "accepted", lambda: posting()),
    case("TC_M1_02", "Unit / BVA (min-1)", "Title of 2 characters", "title='QA'",
         "Title must be 3 to 120 characters.", lambda: posting(title="QA")),
    case("TC_M1_03", "Unit / BVA (min)", "Title of 3 characters", "title='SDE'", "accepted",
         lambda: posting(title="SDE")),
    case("TC_M1_04", "Unit / BVA (max)", "Title of 120 characters", "title='A'*120", "accepted",
         lambda: posting(title="A" * 120)),
    case("TC_M1_05", "Unit / BVA (max+1)", "Title of 121 characters", "title='A'*121",
         "Title must be 3 to 120 characters.", lambda: posting(title="A" * 121)),
    case("TC_M1_06", "Unit / BVA (min-1)", "Description of 19 characters", "description='Write code for APIs' (19)",
         "Description must be 20 to 2000 characters.", lambda: posting(description="Write code for APIs")),
    case("TC_M1_07", "Unit / BVA (min-1)", "Package of 0 LPA", "ctc=0",
         "Package (CTC) must be a positive number up to 100 LPA.", lambda: posting(ctc=0)),
    case("TC_M1_08", "Unit / BVA (min)", "Package just above 0", "ctc=0.1", "accepted", lambda: posting(ctc=0.1)),
    case("TC_M1_09", "Unit / BVA (max)", "Package of 100 LPA", "ctc=100", "accepted", lambda: posting(ctc=100)),
    case("TC_M1_10", "Unit / BVA (max+)", "Package above 100 LPA", "ctc=100.5",
         "Package (CTC) must be a positive number up to 100 LPA.", lambda: posting(ctc=100.5)),
    case("TC_M1_11", "Unit / EP (invalid)", "Package typed as words", "ctc='eight'",
         "Package (CTC) must be a number.", lambda: posting(ctc="eight")),
    case("TC_M1_12", "Unit / Validation", "Location left empty", "location=''",
         "Location is required (2 to 80 characters).", lambda: posting(location="")),
    case("TC_M1_13", "Unit / BVA (equal)", "Deadline equal to the current time", "deadline=26-10-2026 10:00 (= now)",
         "Deadline must be a future date and time.", lambda: posting(deadline="2026-10-26T10:00")),
    case("TC_M1_14", "Unit / BVA (now+1 min)", "Deadline one minute in the future", "deadline=26-10-2026 10:01",
         "accepted", lambda: posting(deadline="2026-10-26T10:01")),
    case("TC_M1_15", "Unit / EP (invalid)", "Deadline that is not a date", "deadline='next friday'",
         "Deadline must be a future date and time.", lambda: posting(deadline="next friday")),
    case("TC_M1_16", "Unit / Validation", "No eligibility criterion given (UC-2 E1)", "all four criteria blank",
         "At least one eligibility criterion is required.", lambda: posting(**NO_CRITERIA)),
    case("TC_M1_17", "Unit / BVA (max)", "Minimum CGPA of 10", "min_cgpa=10", "accepted",
         lambda: posting(min_cgpa=10)),
    case("TC_M1_18", "Unit / BVA (max+)", "Minimum CGPA above 10", "min_cgpa=10.01",
         "Minimum CGPA must be between 0 and 10.", lambda: posting(min_cgpa=10.01)),
    case("TC_M1_19", "Unit / BVA (min-1)", "Maximum backlogs of -1", "max_backlogs=-1",
         "Maximum backlogs must be a whole number from 0 to 10.", lambda: posting(max_backlogs=-1)),
    case("TC_M1_20", "Unit / EP (invalid)", "Maximum backlogs not a whole number", "max_backlogs=1.5",
         "Maximum backlogs must be a whole number from 0 to 10.", lambda: posting(max_backlogs=1.5)),
    case("TC_M1_21", "Unit / EP (invalid)", "Branch that does not exist", "allowed_branches=['CSE', 'AI']",
         "Allowed branches must be chosen from CSE, IT, ECE, EE, ME, CE.",
         lambda: posting(allowed_branches=["CSE", "AI"])),
    case("TC_M1_22", "Unit / EP (invalid)", "Batch spanning 3 years", "batch='2023-2026'",
         "Batch must look like 2023-2027.", lambda: posting(batch="2023-2026")),
    case("TC_M1_23", "Unit / EP (valid)", "Only one criterion (batch) given", "batch='2024-2028', others blank",
         "accepted", lambda: posting(**dict(NO_CRITERIA, batch="2024-2028"))),

    # ---------------- unit: automatic eligibility check (FR-1.7) ----------------
    case("TC_M1_24", "Unit / EP (eligible)", "Student meeting every criterion of J-1",
         "Aarav: CSE, CGPA 8.60, 0 backlogs, 2023-2027 vs J-1", "eligible", lambda: eligibility(J1_RULES, AARAV)),
    case("TC_M1_25", "Unit / BVA (equal)", "CGPA exactly equal to the minimum", "CGPA 7.00 vs min 7.0",
         "eligible", lambda: eligibility(J1_RULES, dict(AARAV, cgpa=7.0))),
    case("TC_M1_26", "Unit / BVA (min-0.01)", "CGPA just below the minimum", "CGPA 6.99 vs min 7.0",
         "CGPA 6.99 is below the minimum 7.00.", lambda: eligibility(J1_RULES, dict(AARAV, cgpa=6.99))),
    case("TC_M1_27", "Unit / EP (invalid class)", "Branch not in the allowed list", "Diya as ME student vs CSE/IT",
         "Branch ME is not in the allowed branches (CSE, IT).",
         lambda: eligibility(J1_RULES, dict(DIYA, department="ME"))),
    case("TC_M1_28", "Unit / BVA (equal, max+1)", "Backlogs equal to and one above the maximum",
         "max 1 backlog: student with 1, then with 2",
         "eligible / Active backlogs 2 exceed the maximum 1.",
         lambda: " / ".join(eligibility(EligibilityCriteria(None, None, 1, None), dict(KABIR, backlogs=b))
                            for b in (1, 2))),
    case("TC_M1_29", "Unit / Functional", "Several unmet criteria are all reported", "Kabir (ECE, 6.80, 1) vs J-1",
         "CGPA 6.80 is below the minimum 7.00. | Branch ECE is not in the allowed branches (CSE, IT). | "
         "Active backlogs 1 exceed the maximum 0.", lambda: eligibility(J1_RULES, KABIR)),
    case("TC_M1_30", "Unit / Functional", "Batch does not match", "Rohan (ME, 2 backlogs, 2022-2026) vs J-1",
         "Branch ME is not in the allowed branches (CSE, IT). | Active backlogs 2 exceed the maximum 0. | "
         "Batch 2022-2026 does not match the required batch 2023-2027.", lambda: eligibility(J1_RULES, ROHAN)),
    case("TC_M1_31", "Unit / EP", "Criteria that are not set are not checked", "rule: only CGPA >= 6.0; Rohan",
         "eligible", lambda: eligibility(EligibilityCriteria(6.0, None, None, None), ROHAN)),

    # ---------------- unit: officer decision (FR-1.4) ----------------
    case("TC_M1_32", "Unit / EP (valid)", "Approve without remarks", "pending, approve, remarks=''",
         "published", lambda: decision("pending", "approve", "")),
    case("TC_M1_33", "Unit / BVA (min-1)", "Reject with 4-character remarks", "reject, remarks='Late'",
         "Remarks (5 to 200 characters) are required to reject or return a posting.",
         lambda: decision("pending", "reject", "Late")),
    case("TC_M1_34", "Unit / BVA (min)", "Reject with 5-character remarks", "reject, remarks='Spam.'",
         "rejected", lambda: decision("pending", "reject", "Spam.")),
    case("TC_M1_35", "Unit / BVA (max+1)", "Approve with 201-character remarks", "approve, remarks='x'*201",
         "Remarks cannot exceed 200 characters.", lambda: decision("pending", "approve", "x" * 201)),
    case("TC_M1_36", "Unit / EP (invalid)", "Unknown decision", "decision='hold'",
         "Decision must be approve, reject or return.", lambda: decision("pending", "hold", "")),
    case("TC_M1_37", "Unit / Validation", "Deciding a job that is already published", "status=published, approve",
         "This job is not pending approval (status: published).", lambda: decision("published", "approve", "")),

    # ---------------- API + database ----------------
    case("TC_M1_38", "Functional (API)", "Recruiter of an approved company posts a job (UC-2 step 1-2)",
         "POST /api/jobs as recruiter 1 (Nimbus) with the valid posting",
         "200: Job J-5 submitted for approval (status: Pending). | status=pending | officer notified=True",
         with_server(post_valid)),
    case("TC_M1_39", "Functional (API) / FR-09", "Recruiter of a company that is not approved",
         "POST /api/jobs as recruiter 3 (Vertex Labs, not approved)",
         "403: Your company is not yet approved by the placement cell.", with_server(lambda s: post(s, 3))),
    case("TC_M1_40", "Validation (API)", "Server validates the posting, not only the page", "title=''",
         "400: Title must be 3 to 120 characters.", with_server(lambda s: post(s, title=""))),
    case("TC_M1_41", "Functional (API) / BR-02", "Recruiter tries to approve a posting",
         "POST /api/jobs/3/decision approve as recruiter 1",
         "403: Only a Placement Officer can approve or reject job postings.",
         with_server(lambda s: s.decide(3, "approve", role="recruiter"))),
    case("TC_M1_42", "Functional (API) / FR-25", "Officer approves J-3; eligible unplaced students notified",
         "J-3 needs CGPA>=7.5, 0 backlogs; students 101-105",
         "200: Job J-3 published. 1 eligible student(s) notified. | students notified: [101]",
         with_server(approve_j3)),
    case("TC_M1_43", "Validation (API)", "Officer rejects without remarks", "decision=reject, remarks=''",
         "400: Remarks (5 to 200 characters) are required to reject or return a posting.",
         with_server(lambda s: s.decide(3, "reject"))),
    case("TC_M1_44", "Functional (API)", "Officer returns J-3 with remarks (UC-2 A1)",
         "decision=return, remarks='Add the batch criterion.'",
         "200: Job J-3 returned to the recruiter for changes. | recruiter 1 told with remarks=True",
         with_server(return_j3)),
    case("TC_M1_45", "Validation (API)", "Deciding a job that is already published", "approve J-1 (published)",
         "409: This job is not pending approval (status: published).",
         with_server(lambda s: s.decide(1, "approve"))),
    case("TC_M1_46", "Functional (API)", "Recruiter edits and resubmits the returned posting",
         "PUT /api/jobs/3 by recruiter 1 after it was returned",
         "200: Job J-3 resubmitted for approval (status: Pending). | status=pending", with_server(resubmit)),
    case("TC_M1_47", "Functional (API)", "Another recruiter tries to edit the returned posting",
         "PUT /api/jobs/3 by recruiter 2", "403: You can edit only your own job postings. | status=returned",
         with_server(lambda s: resubmit(s, recruiter_id=2))),
    case("TC_M1_48", "Validation (API)", "Editing a posting that was not returned", "PUT /api/jobs/3 while pending",
         "409: Only a posting returned for changes can be edited (status: pending). | status=pending",
         with_server(lambda s: resubmit(s, first_return=False))),
    case("TC_M1_49", "Functional (API) / FR-12", "Students see only published jobs, open ones first",
         "GET /api/jobs (J-3 is pending, J-4 deadline passed)", "J-2, J-1, J-4",
         with_server(lambda s: board_keys(s, ""))),
    case("TC_M1_50", "Functional (API)", "Jobs whose deadline passed are marked closed", "GET /api/jobs?student_id=101",
         "J-2 open, J-1 open, J-4 closed", with_server(board_open_flags)),
    case("TC_M1_51", "EP (API)", "Keyword search ignores case and looks in the description", "q=FIRMWARE",
         "J-2, J-4", with_server(lambda s: board_keys(s, "q=FIRMWARE"))),
    case("TC_M1_52", "EP (API)", "Keyword search on company name", "q=nimbus", "J-1",
         with_server(lambda s: board_keys(s, "q=nimbus"))),
    case("TC_M1_53", "EP (API)", "Location filter", "location=pune", "J-1",
         with_server(lambda s: board_keys(s, "location=pune"))),
    case("TC_M1_54", "BVA (API)", "Minimum package equal to a job's package", "min_ctc=6 (J-2 is 6.0 LPA)",
         "J-2, J-1", with_server(lambda s: board_keys(s, "min_ctc=6"))),
    case("TC_M1_55", "EP (API, invalid)", "Minimum package that is not a number", "min_ctc=abc",
         "400: Minimum package must be a number.", with_server(lambda s: board_keys(s, "min_ctc=abc"))),
    case("TC_M1_56", "Functional (API)", "Eligible-only filter", "student 103 (ECE, 6.80, 1 backlog), eligible_only=1",
         "J-2, J-4", with_server(lambda s: board_keys(s, "student_id=103&eligible_only=1"))),
    case("TC_M1_57", "Functional (API)", "Pagination of the job list", "per_page=2&page=2",
         "page 2 of 2 (3 jobs): J-4", with_server(board_page)),
    case("TC_M1_58", "BVA (API, min-1)", "Page number 0", "page=0",
         "400: Page must be a whole number of at least 1.", with_server(lambda s: board_keys(s, "page=0"))),
    case("TC_M1_59", "Functional (API) / FR-14", "Eligibility check with reasons is recorded",
         "GET /api/jobs/1/eligibility?student_id=105",
         "200: eligible=False; Branch ME is not in the allowed branches (CSE, IT). Active backlogs 2 exceed the "
         "maximum 0. Batch 2022-2026 does not match the required batch 2023-2027.; recorded=1",
         with_server(eligibility_api)),
    case("TC_M1_60", "BVA (API)", "Approving a posting after its deadline has passed",
         "clock 20-11-2026 10:00 (= J-3 deadline), officer approves J-3",
         "409: The deadline of J-3 has passed; return the posting so the recruiter can change it. | status=pending",
         with_server(lambda s: expired(s, "approve", ""))),
    case("TC_M1_61", "Functional (API)", "An expired posting can still be returned to the recruiter",
         "clock 20-11-2026 10:00, officer returns J-3 with remarks",
         "200: Job J-3 returned to the recruiter for changes. | status=returned",
         with_server(lambda s: expired(s, "return", "Please extend the deadline."))),
]
