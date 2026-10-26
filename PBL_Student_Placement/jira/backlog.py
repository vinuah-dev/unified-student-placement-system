"""Product backlog of the USPS PBL project and its export to a Jira CSV import file.

    python jira/backlog.py      -> jira/jira_import.csv

Hierarchy: Epic -> Story / Task -> Subtask, plus the bugs recorded in docs/bugs.json.
In the Jira CSV importer map: Issue Id -> Issue ID, Parent -> Parent, Issue Type -> Issue Type,
Summary -> Summary, Description -> Description, Labels -> Labels,
Story point estimate -> Story point estimate. Leave Sprint unmapped: the importer only accepts numeric
sprint IDs, so the items are placed into USPS Sprint 1-3 through the Jira REST API after the import.
"""
import csv
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent

SPRINTS = {"S1": "USPS Sprint 1", "S2": "USPS Sprint 2", "S3": "USPS Sprint 3"}
SPRINT_GOALS = {
    "S1": "Requirements and Module 1: job posting, approval, search and eligibility check",
    "S2": "Module 2: application, statechart workflow, tracking, notifications and live updates",
    "S3": "Testing (155 cases), bug fixing, retesting, report and presentation",
}

# (key, summary, description, labels)
EPICS = [
    ("E1", "Module 1: Job Posting and Eligibility Verification",
     "Recruiters post jobs with eligibility criteria, placement officers approve / reject / return them, students "
     "search published jobs and the system checks eligibility automatically with reasons "
     "(SRS 4.3-4.4, FR-09 to FR-14, UC-2; requirements FR-1.1 to FR-1.8).", "module-1"),
    ("E2", "Module 2: Job Application and Tracking",
     "Students apply with a resume, recruiters move applications through the Expt-5 statechart, students withdraw, "
     "accept or decline offers and track a timeline; notifications and live page updates "
     "(SRS 4.5, FR-15 to FR-17, UC-1; requirements FR-2.1 to FR-2.12).", "module-2"),
    ("E3", "Testing and Quality Assurance",
     "Test case design (Functional, Unit, Integration, BVA, EP, Validation), automation of unit, API, integration "
     "and Edge UI tests, test runs, defect logging and retesting.", "testing"),
    ("E4", "Project Setup and Documentation",
     "Requirements from the SRS, project structure and database, report and presentation.", "docs"),
]

# (key, epic, type, summary, description, priority, points, sprint, labels)
ITEMS = [
    ("T1", "E4", "Task", "Derive the requirements of the two modules from the SRS",
     "FR-1.x and FR-2.x with exact messages in docs/requirements.md, from SRS 4.3-4.5, UC-1, UC-2, BR-01 to BR-08 "
     "and the Expt-3/4/5 diagrams.", "High", 2, "S1", "docs"),
    ("T2", "E4", "Task", "Set up project structure and SQLite schema (SRS 6.1)",
     "app/ (rules, db, server, static), tests/, docs/. Tables: students, companies, recruiters, "
     "placement_officers, resumes, jobs, applications, application_history, eligibility_checks, notifications. "
     "Python 3.11 standard library only.", "Medium", 2, "S1", "docs"),
    ("US1", "E1", "Story", "Recruiter posts a job with eligibility criteria",
     "As a recruiter of an approved company I want to post a job with package, deadline and eligibility criteria "
     "so that the placement cell can publish it.\nAcceptance: FR-1.1, FR-1.2, FR-1.3 (FR-09, FR-10, FR-13).",
     "Highest", 5, "S1", "module-1"),
    ("US2", "E1", "Story", "Placement officer approves, rejects or returns a posting",
     "As a placement officer I want to approve, reject or return postings with remarks so that only checked jobs "
     "reach students.\nAcceptance: FR-1.4 (FR-11, BR-02).", "High", 3, "S1", "module-1"),
    ("US3", "E1", "Story", "Recruiter edits and resubmits a returned posting",
     "As a recruiter I want to fix a posting the officer returned and submit it again.\nAcceptance: FR-1.5 "
     "(UC-2 A1).", "Medium", 2, "S1", "module-1"),
    ("US4", "E1", "Story", "Student searches and filters published jobs",
     "As a student I want to search jobs by keyword, location, package and eligibility.\nAcceptance: FR-1.6 "
     "(FR-12).", "High", 3, "S1", "module-1"),
    ("US5", "E1", "Story", "Automatic eligibility check with reasons",
     "As a student I want to see whether I am eligible for a job and which criteria I do not meet.\n"
     "Acceptance: FR-1.7, FR-1.8 (FR-14, BR-03).", "Highest", 5, "S1", "module-1"),
    ("US6", "E2", "Story", "Student applies to a job with a resume and cover note",
     "As an eligible student I want to apply before the deadline and get a tracking id.\nAcceptance: FR-2.1 to "
     "FR-2.4 (FR-15, UC-1, BR-04, BR-05).", "Highest", 5, "S2", "module-2"),
    ("US7", "E2", "Story", "Recruiter moves applications through the selection stages",
     "As a recruiter I want to review, shortlist, schedule, select and make offers to my own applicants.\n"
     "Acceptance: FR-2.5, FR-2.6 (Expt-5 statechart, BR-07, BR-08).", "High", 5, "S2", "module-2"),
    ("US8", "E2", "Story", "Student withdraws an application before the deadline",
     "As a student I want to withdraw an application I no longer want.\nAcceptance: FR-2.7 (FR-16).",
     "Medium", 2, "S2", "module-2"),
    ("US9", "E2", "Story", "Student accepts or declines an offer",
     "As a student I want to respond to an offer; accepting marks me placed.\nAcceptance: FR-2.8 (BR-01, BR-05).",
     "High", 3, "S2", "module-2"),
    ("US10", "E2", "Story", "Application status timeline and notifications",
     "As a student I want a timeline of each application and notifications of every change.\nAcceptance: "
     "FR-2.9 to FR-2.11 (FR-17, FR-25).", "High", 3, "S2", "module-2"),
    ("US11", "E2", "Story", "Pages update live when another user changes data",
     "As any user I want my open page to show new jobs, approvals and status changes without reloading.\n"
     "Acceptance: FR-2.12.", "Medium", 3, "S2", "module-2"),
    ("T3", "E3", "Task", "Design test cases in the PBL format",
     "155 test cases: TC ID, Module, Test Scenario, Test Data, Expected Result, Actual Result, Status; "
     "techniques Functional, Unit, Integration, BVA, EP, Validation.", "High", 3, "S3", "testing"),
    ("T4", "E3", "Task", "Automate Module 1 unit and API tests",
     "tests/m1_cases.py - 61 cases (TC_M1_01 to TC_M1_61).", "High", 3, "S3", "testing"),
    ("T5", "E3", "Task", "Automate Module 2 unit and API tests",
     "tests/m2_cases.py - 42 cases (TC_M2_01 to TC_M2_42).", "High", 3, "S3", "testing"),
    ("T6", "E3", "Task", "Automate integration tests",
     "tests/integration_cases.py - 11 cases incl. rollback, concurrency, restart and live-update version.",
     "High", 2, "S3", "testing"),
    ("T7", "E3", "Task", "Automate UI tests in Microsoft Edge",
     "tests/ui - 41 cases that fill the forms, press the buttons and read the page.", "Medium", 3, "S3", "testing"),
    ("T8", "E3", "Task", "Execute test run 1 and log defects",
     "python -m tests.run_tests run1: 151 cases, 136 passed, 15 failed -> BUG-01.", "High", 1, "S3", "testing"),
    ("T9", "E3", "Task", "Retest after the BUG-01 fix (run 2)",
     "python -m tests.run_tests run2: 151 cases, 151 passed.", "High", 1, "S3", "testing"),
    ("T10", "E3", "Task", "Exploratory testing, run 3 and retest run 4",
     "Exploratory session found BUG-02, BUG-03, BUG-04; 4 new cases; run3 152/155 passed; after fixes run4 "
     "155/155 passed.", "High", 2, "S3", "testing"),
    ("T11", "E4", "Task", "Prepare project report and presentation", "Report (DOCX/PDF) and PPT for the PBL "
     "evaluation.", "Medium", 3, "S3", "docs"),
]

# (parent, summary)
SUBTASKS = [
    ("US1", "Implement validate_job_posting() and EligibilityCriteria"), ("US1", "Build Post a job form"),
    ("US1", "Unit tests TC_M1_01 to TC_M1_23"),
    ("US2", "Implement decision API with remarks rules"), ("US2", "Build officer approval screen"),
    ("US3", "Implement PUT /api/jobs/<id> resubmission"), ("US3", "Add Edit & resubmit to My job postings"),
    ("US4", "Implement job board API with filters and pagination"), ("US4", "Build job board and search form"),
    ("US5", "Implement eligibility check with reasons and logging"), ("US5", "Show eligibility badges and reasons"),
    ("US6", "Implement apply API with ordered checks and rollback"), ("US6", "Build apply form"),
    ("US7", "Implement statechart transitions and authorisation"), ("US7", "Build applicant list with next steps"),
    ("US8", "Implement withdraw API"), ("US9", "Implement offer response and placement lock"),
    ("US10", "Build My applications, timeline and notifications"),
    ("US11", "Add /api/version and page polling with notification pop-up"),
]


def bugs():
    return json.loads((ROOT / "docs" / "bugs.json").read_text(encoding="utf-8"))


def rows():
    out = []
    ids = {}

    # The team-managed space does not show the Priority field on its create screen, so priority also goes into
    # the description and a priority-<level> label; the field itself is set through the API after the import.
    def add(key, issue_type, summary, description, priority="", parent="", points="", sprint="", labels=""):
        ids[key] = len(ids) + 1
        if priority:
            description = (description + "\n\n" if description else "") + "Priority: " + priority
            labels = (labels + " " if labels else "") + "priority-" + priority.lower()
        out.append({"Issue Id": ids[key], "Parent": ids.get(parent, ""), "Issue Type": issue_type,
                    "Summary": summary, "Description": description, "Labels": labels,
                    "Story point estimate": points, "Sprint": SPRINTS.get(sprint, "")})

    for key, summary, description, labels in EPICS:
        add(key, "Epic", summary, description, "High", labels=labels)
    for key, epic, itype, summary, description, priority, points, sprint, labels in ITEMS:
        add(key, itype, summary, description, priority, epic, points, sprint, labels)
    for n, (parent, summary) in enumerate(SUBTASKS, 1):
        add("ST%d" % n, "Subtask", summary, "", "", parent, "", "", "")   # subtasks follow their parent's sprint
    for b in bugs():
        description = "%s\n\nFound by: %s\nSeverity: %s\n\nSteps to reproduce:\n%s\n\nExpected: %s\nActual: %s\n\n" \
                      "Resolution: %s\nRetest: %s" % (
                          b["description"], b["found_by"], b["severity"],
                          "\n".join("%d. %s" % (i, s) for i, s in enumerate(b["steps"], 1)),
                          b["expected"], b["actual"], b["resolution"], b["retest"])
        add(b["id"], "Bug", "[%s] %s" % (b["id"], b["summary"]), description, b["priority"],
            "E1" if b["module"].startswith("M1") else "E2", "", "S3", "bug severity-" + b["severity"].lower())
    return out


def main():
    out = rows()
    with open(HERE / "jira_import.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(out[0].keys()))
        writer.writeheader()
        writer.writerows(out)
    counts = {}
    for r in out:
        counts[r["Issue Type"]] = counts.get(r["Issue Type"], 0) + 1
    print("jira_import.csv:", len(out), "issues", counts)


if __name__ == "__main__":
    main()
