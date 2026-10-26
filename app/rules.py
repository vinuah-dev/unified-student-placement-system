"""Core business logic of the two PBL modules, kept free of HTTP and SQL so it can be unit tested.

Module 1 - Job Posting and Eligibility Verification (SRS 4.3, 4.4): validate_job_posting(), EligibilityCriteria
Module 2 - Job Application and Tracking (SRS 4.5): APPLICATION_TRANSITIONS, next_state(), tracking_id()

Class names follow the Class Diagram of Expt-3 (EligibilityCriteria.evaluate / getReasons, Application.updateStatus)
and the states follow the Application statechart of Expt-5.
"""
import re
from datetime import datetime

BRANCHES = ("CSE", "IT", "ECE", "EE", "ME", "CE")
BATCH_RE = re.compile(r"^(\d{4})-(\d{4})$")


class RuleError(ValueError):
    """A business-rule or validation failure; the message is shown to the user."""


# ---------------------------------------------------------------- Module 1

class EligibilityCriteria:
    """Rule-set attached to a job (FR-13). Any criterion left as None is not checked."""

    def __init__(self, min_cgpa=None, allowed_branches=None, max_backlogs=None, batch=None):
        self.min_cgpa = min_cgpa
        self.allowed_branches = list(allowed_branches) if allowed_branches else []
        self.max_backlogs = max_backlogs
        self.batch = batch

    def is_empty(self):
        return self.min_cgpa is None and not self.allowed_branches and self.max_backlogs is None and not self.batch

    def get_reasons(self, student):
        """Reasons why `student` (dict with cgpa, department, backlogs, batch) is not eligible (BR-03)."""
        reasons = []
        if self.min_cgpa is not None and student["cgpa"] < self.min_cgpa:
            reasons.append("CGPA %.2f is below the minimum %.2f." % (student["cgpa"], self.min_cgpa))
        if self.allowed_branches and student["department"] not in self.allowed_branches:
            reasons.append("Branch %s is not in the allowed branches (%s)."
                           % (student["department"], ", ".join(self.allowed_branches)))
        if self.max_backlogs is not None and student["backlogs"] > self.max_backlogs:
            reasons.append("Active backlogs %d exceed the maximum %d." % (student["backlogs"], self.max_backlogs))
        if self.batch and student["batch"] != self.batch:
            reasons.append("Batch %s does not match the required batch %s." % (student["batch"], self.batch))
        return reasons

    def evaluate(self, student):
        """FR-14: (is_eligible, reasons)."""
        reasons = self.get_reasons(student)
        return (len(reasons) == 0, reasons)

    def to_dict(self):
        return {"min_cgpa": self.min_cgpa, "allowed_branches": self.allowed_branches,
                "max_backlogs": self.max_backlogs, "batch": self.batch}


def _number(value, field):
    if isinstance(value, bool) or value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        raise RuleError("%s must be a number." % field)


def validate_job_posting(data, now):
    """FR-10 / UC-2 validation rules. Returns cleaned fields; raises RuleError with the first problem."""
    title = (data.get("title") or "").strip()
    if not 3 <= len(title) <= 120:
        raise RuleError("Title must be 3 to 120 characters.")
    description = (data.get("description") or "").strip()
    if not 20 <= len(description) <= 2000:
        raise RuleError("Description must be 20 to 2000 characters.")
    ctc = _number(data.get("ctc"), "Package (CTC)")
    if ctc is None or not 0 < ctc <= 100:
        raise RuleError("Package (CTC) must be a positive number up to 100 LPA.")
    location = (data.get("location") or "").strip()
    if not 2 <= len(location) <= 80:
        raise RuleError("Location is required (2 to 80 characters).")
    try:
        deadline = datetime.fromisoformat(str(data.get("deadline") or ""))
    except ValueError:
        raise RuleError("Deadline must be a future date and time.")
    if deadline <= now:
        raise RuleError("Deadline must be a future date and time.")

    min_cgpa = _number(data.get("min_cgpa"), "Minimum CGPA")
    if min_cgpa is not None and not 0 <= min_cgpa <= 10:
        raise RuleError("Minimum CGPA must be between 0 and 10.")
    max_backlogs = _number(data.get("max_backlogs"), "Maximum backlogs")
    if max_backlogs is not None and (max_backlogs != int(max_backlogs) or not 0 <= max_backlogs <= 10):
        raise RuleError("Maximum backlogs must be a whole number from 0 to 10.")
    branches = data.get("allowed_branches") or []
    if not isinstance(branches, list) or any(b not in BRANCHES for b in branches):
        raise RuleError("Allowed branches must be chosen from %s." % ", ".join(BRANCHES))
    batch = (data.get("batch") or "").strip()
    if batch:
        m = BATCH_RE.match(batch)
        if not m or int(m.group(2)) - int(m.group(1)) != 4:
            raise RuleError("Batch must look like 2023-2027.")
    criteria = EligibilityCriteria(min_cgpa, branches, None if max_backlogs is None else int(max_backlogs),
                                   batch or None)
    if criteria.is_empty():
        raise RuleError("At least one eligibility criterion is required.")
    return {"title": title, "description": description, "ctc": ctc, "location": location,
            "deadline": deadline, "criteria": criteria}


JOB_DECISIONS = {"approve": "published", "reject": "rejected", "return": "returned"}


def validate_job_decision(job_status, decision, remarks):
    """FR-11 / BR-02: officer decision on a pending posting. Returns the new job status."""
    if job_status != "pending":
        raise RuleError("This job is not pending approval (status: %s)." % job_status)
    if decision not in JOB_DECISIONS:
        raise RuleError("Decision must be approve, reject or return.")
    remarks = (remarks or "").strip()
    if decision != "approve" and not 5 <= len(remarks) <= 200:
        raise RuleError("Remarks (5 to 200 characters) are required to reject or return a posting.")
    if len(remarks) > 200:
        raise RuleError("Remarks cannot exceed 200 characters.")
    return JOB_DECISIONS[decision]


# ---------------------------------------------------------------- Module 2

APPLIED, UNDER_REVIEW, SHORTLISTED = "Applied", "Under Review", "Shortlisted"
INTERVIEW, SELECTED, OFFER_ISSUED = "Interview Scheduled", "Selected", "Offer Issued"
ACCEPTED, REJECTED, WITHDRAWN = "Accepted", "Rejected", "Withdrawn"
FINAL_STATES = (ACCEPTED, REJECTED, WITHDRAWN)

# (event, from state) -> to state, exactly as in the Expt-5 statechart.
APPLICATION_TRANSITIONS = {
    ("under_review", APPLIED): UNDER_REVIEW,
    ("withdraw", APPLIED): WITHDRAWN,
    ("shortlist", UNDER_REVIEW): SHORTLISTED,
    ("reject", UNDER_REVIEW): REJECTED,
    ("schedule_interview", SHORTLISTED): INTERVIEW,
    ("reject", SHORTLISTED): REJECTED,
    ("reschedule", INTERVIEW): INTERVIEW,
    ("interview_result", INTERVIEW): SELECTED,
    ("reject", INTERVIEW): REJECTED,
    ("offer_letter", SELECTED): OFFER_ISSUED,
    ("reject", SELECTED): REJECTED,
    ("accept_offer", OFFER_ISSUED): ACCEPTED,
    ("reject_offer", OFFER_ISSUED): REJECTED,
}
STUDENT_EVENTS = ("withdraw", "accept_offer", "reject_offer")
STAFF_EVENTS = tuple(sorted({e for e, _ in APPLICATION_TRANSITIONS} - set(STUDENT_EVENTS)))


def next_state(state, event):
    """Application.updateStatus(): the state after `event`, or RuleError if the statechart forbids it."""
    if (event, state) not in APPLICATION_TRANSITIONS:
        raise RuleError("Event '%s' is not allowed when the application is %s." % (event, state))
    return APPLICATION_TRANSITIONS[(event, state)]


def tracking_id(app_id, year):
    """Unique tracking id issued on submission (FR-15), e.g. USPS-26-0007."""
    return "USPS-%02d-%04d" % (year % 100, app_id)
