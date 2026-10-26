"""Product backlog of the PBL project and its export to a Jira CSV import file.

    python jira/backlog.py      -> jira/jira_import.csv

Hierarchy: Epic -> Story / Task -> Subtask, plus the bugs recorded in docs/bugs.json.
In the Jira CSV importer map: Issue Id -> Issue ID, Parent -> Parent, Issue Type -> Issue Type,
Summary -> Summary, Description -> Description, Labels -> Labels,
Story point estimate -> Story point estimate. Leave Sprint unmapped: the importer only accepts numeric
sprint IDs, so the items were placed into SCEM Sprint 1-3 after the import.
"""
import csv
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent

# Sprint names must match the sprints created on the Jira board (SCEM board 2).
SPRINTS = {"S1": "SCEM Sprint 1", "S2": "SCEM Sprint 2", "S3": "SCEM Sprint 3"}
SPRINT_GOALS = {
    "S1": "Detection engine (Module 1) and requirements",
    "S2": "Dashboard, API, database and simulator (Module 2)",
    "S3": "Testing, bug fixing and documentation",
}

# (key, summary, description, labels)
EPICS = [
    ("E1", "Module 1: Vacancy and AC-State Detection Engine",
     "Edge decision engine: validates camera/sensor frames, confirms vacancy over consecutive frames, raises "
     "fan/light wastage alerts and infers the AC state from the 4-region temperature drop (FR-1.1 to FR-1.8).",
     "module-1"),
    ("E2", "Module 2: Monitoring Dashboard and Control",
     "REST API + SQLite database + web dashboard: room status and heatmap, alert acknowledgement, manual ESP32 "
     "relay override and detection settings (FR-2.1 to FR-2.7).", "module-2"),
    ("E3", "Testing and Quality Assurance",
     "Test case design (EP, BVA, validation), unit, integration and UI test automation, test execution, bug "
     "tracking and retesting.", "testing"),
    ("E4", "Project Setup and Documentation",
     "Requirements, project structure, simulator for the hardware, report and presentation.", "docs"),
]

# (key, epic, type, summary, description, priority, points, sprint, labels)
ITEMS = [
    ("T1", "E4", "Task", "Write requirements for the two modules",
     "Derive FR-1.x and FR-2.x from the Idea Lab problem statement and record them in docs/requirements.md.",
     "High", 2, "S1", "docs"),
    ("T2", "E4", "Task", "Set up project structure (app/, tests/, docs/)",
     "Python 3.11 standard library only: http.server, sqlite3, unittest.", "Medium", 1, "S1", "docs"),
    ("US1", "E1", "Story", "Confirm vacancy over consecutive empty frames",
     "As a facility manager I want a room to be marked vacant only after N consecutive frames without people, so "
     "that short absences do not raise alerts.\nAcceptance: FR-1.3, FR-1.4; settings limit FR-1.8.",
     "High", 3, "S1", "module-1"),
    ("US2", "E1", "Story", "Alert when fans or lights are left ON in a vacant room",
     "As a facility manager I want an alert when a fan or light stays ON after everyone leaves.\n"
     "Acceptance: FR-1.5 (once per occurrence, again if switched off and on).", "High", 3, "S1", "module-1"),
    ("US3", "E1", "Story", "Infer AC state from the 4-region temperature drop",
     "As a facility manager I want to know if the AC is still running in a vacant room without a power meter.\n"
     "Acceptance: FR-1.6 (mean drop >= threshold after wait_seconds), FR-1.7 (cancel if someone enters).",
     "Highest", 5, "S1", "module-1"),
    ("US4", "E1", "Story", "Validate camera and sensor frames",
     "As the system I want invalid frames rejected with a clear message.\nAcceptance: FR-1.1, FR-1.2.",
     "Medium", 2, "S1", "module-1"),
    ("T3", "E4", "Task", "Build simulator for camera, DHT11 sensors and ESP32",
     "app/simulator.py: scenarios ac_left_on, all_off, occupied; executes pending relay commands like the ESP32.",
     "Medium", 3, "S2", "docs"),
    ("US5", "E2", "Story", "Receive readings through a REST API and store them",
     "As the sensor node I want to post readings to /api/readings so that they are processed and stored.\n"
     "Acceptance: FR-2.1.", "High", 3, "S2", "module-2"),
    ("US6", "E2", "Story", "Show room status and region heatmap on the dashboard",
     "As an operator I want to see the state, counts, AC check and a 2x2 temperature heatmap of a room.\n"
     "Acceptance: FR-2.2.", "High", 5, "S2", "module-2"),
    ("US7", "E2", "Story", "List and acknowledge open alerts",
     "As an operator I want to acknowledge alerts with my name and remarks.\nAcceptance: FR-2.3.",
     "High", 3, "S2", "module-2"),
    ("US8", "E2", "Story", "Manual fan/light override through the ESP32",
     "As an operator I want to switch fans or lights ON/OFF from the dashboard.\nAcceptance: FR-2.4, FR-2.5.",
     "High", 5, "S2", "module-2"),
    ("US9", "E2", "Story", "Edit detection settings from the dashboard",
     "As an administrator I want to change the vacancy, wait and threshold settings and keep them after a "
     "restart.\nAcceptance: FR-2.6, FR-2.7.", "Medium", 3, "S2", "module-2"),
    ("T4", "E3", "Task", "Design test cases (EP, BVA, validation, integration)",
     "78 test cases in the PBL format: TC ID, Module, Test Scenario, Test Data, Expected, Actual, Status.",
     "High", 3, "S3", "testing"),
    ("T5", "E3", "Task", "Automate unit tests for Module 1", "tests/engine_cases.py - 32 cases.", "High", 2, "S3",
     "testing"),
    ("T6", "E3", "Task", "Automate API and integration tests",
     "tests/api_cases.py - 24 Module 2 API cases and 7 integration cases.", "High", 3, "S3", "testing"),
    ("T7", "E3", "Task", "Automate dashboard UI tests in Microsoft Edge",
     "tests/ui - 15 UI cases that fill the forms and read the page.", "Medium", 3, "S3", "testing"),
    ("T8", "E3", "Task", "Execute test run 1 and log defects in Jira",
     "Run python -m tests.run_tests run1-initial; record every failure as a Bug.", "High", 1, "S3", "testing"),
    ("T9", "E3", "Task", "Retest after bug fixes (run 2)",
     "Run python -m tests.run_tests run2-retest; close bugs whose test cases pass.", "High", 1, "S3", "testing"),
    ("T10", "E4", "Task", "Prepare project report and presentation", "Report (PDF) and PPT for the PBL evaluation.",
     "Medium", 3, "S3", "docs"),
]

# (parent, summary)
SUBTASKS = [
    ("US1", "Implement vacancy counter in RoomMonitor"), ("US1", "Unit tests TC_M1_11 to TC_M1_13"),
    ("US2", "Implement fan/light wastage alerts"), ("US2", "Unit tests TC_M1_14 to TC_M1_18"),
    ("US3", "Implement Delta T calculation and AC inference"), ("US3", "Unit tests TC_M1_19 to TC_M1_26"),
    ("US4", "Implement Frame.from_dict validation"), ("US4", "Unit tests TC_M1_01 to TC_M1_10"),
    ("US5", "Create SQLite schema (rooms, readings, alerts, commands, settings)"),
    ("US5", "Implement POST /api/readings"),
    ("US6", "Build status card and heatmap UI"), ("US6", "UI tests TC_UI_01 to TC_UI_04"),
    ("US7", "Implement alert list and acknowledge API"), ("US7", "Build acknowledge form"),
    ("US8", "Implement override and command API"), ("US8", "Build override form and command list"),
    ("US9", "Implement settings API with persistence"), ("US9", "Build settings form"),
]


def bugs():
    return json.loads((ROOT / "docs" / "bugs.json").read_text(encoding="utf-8"))


def rows():
    out = []
    ids = {}

    # The team-managed space does not show the Priority field, so priority goes into the
    # description and a priority-<level> label.
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
