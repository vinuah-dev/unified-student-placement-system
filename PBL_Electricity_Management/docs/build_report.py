"""Builds the PBL project report (DOCX) from the code, requirements, Jira backlog, test results and evidence.

    python docs/build_report.py   ->  docs/PBL_Report_Smart_Classroom_Energy_Vineet_Shah.docx

Jira screenshots (evidence/jira, taken on 26-10-2026) are listed in JIRA_SHOTS and BUG_SHOTS.
"""
import json
import sys
from pathlib import Path

from docx import Document
from docx.enum.section import WD_ORIENT
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "jira"))
import backlog  # noqa: E402

OUT = ROOT / "docs" / "PBL_Report_Smart_Classroom_Energy_Vineet_Shah.docx"
BRAND = RGBColor(0x14, 0x53, 0x2D)
PASS = RGBColor(0x16, 0x65, 0x34)
FAIL = RGBColor(0xA3, 0x1F, 0x1F)
HEADER_FILL = "DCEFE3"
CODE_FILL = "F4F6F9"

# Screenshots taken in the Jira project on 26-10-2026, shown side by side in pairs.
JIRA_SHOTS = [
    ("sprint_planning.jpg", "Sprint planning - backlog items placed in SCEM Sprint 1 and Sprint 2"),
    ("board_sprint1_done.jpg", "SCEM Sprint 1 board - all work items moved to Done"),
    ("board_sprint3.jpg", "Active SCEM Sprint 3 board - report task In Progress"),
    ("epics_timeline.jpg", "Timeline - progress of the four epics"),
    ("project_summary.jpg", "Project summary - 45 work items created, 43 completed"),
    ("status_overview.jpg", "Status overview - Done 43, In Progress 2"),
]
BUG_SHOTS = [
    ("bugs_list.jpg", "The four bugs in Jira (resolved keys are struck through)"),
    ("bug_detail.jpg", "SCEM-25 (BUG-02): description, found by, severity, steps, sprint, labels"),
    ("bug_resolution_comment.jpg", "SCEM-25: fix and retest comment, resolved"),
]
JIRA_BUG_KEYS = {"BUG-01": "SCEM-24", "BUG-02": "SCEM-25", "BUG-03": "SCEM-26", "BUG-04": "SCEM-27"}
JIRA_SPRINTS = [  # name, goal, dates, state at the time of the report
    ("SCEM Sprint 1", "S1", "25-10-2026 19:30 - 19:50", "Completed"),
    ("SCEM Sprint 2", "S2", "25-10-2026 19:50 - 20:00", "Completed"),
    ("SCEM Sprint 3", "S3", "25-10-2026 20:00 - 01-11-2026", "Active"),
]


# ---------------- docx helpers ----------------

def shade(cell, fill):
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill)
    tc_pr.append(shd)


def row_flag(row, tag):
    tr_pr = row._tr.get_or_add_trPr()
    el = OxmlElement(tag)
    el.set(qn("w:val"), "true")
    tr_pr.append(el)


def set_cell(cell, text, size=9, bold=False, color=None):
    cell.text = ""
    p = cell.paragraphs[0]
    p.paragraph_format.space_after = Pt(0)
    lines = str(text).split("\n")
    for i, line in enumerate(lines):
        run = p.add_run(line)
        run.font.size = Pt(size)
        run.bold = bold
        if color:
            run.font.color.rgb = color
        if i < len(lines) - 1:
            run.add_break()


def table(doc, headers, rows, widths, size=9, keep_together=True):
    t = doc.add_table(rows=1, cols=len(headers))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False
    for i, h in enumerate(headers):
        set_cell(t.rows[0].cells[i], h, size=size, bold=True)
        shade(t.rows[0].cells[i], HEADER_FILL)
    row_flag(t.rows[0], "w:tblHeader")
    for r in rows:
        row = t.add_row()
        row_flag(row, "w:cantSplit")
        for i, v in enumerate(r):
            if isinstance(v, tuple):
                set_cell(row.cells[i], v[0], size=size, bold=True, color=v[1])
            else:
                set_cell(row.cells[i], v, size=size)
    for n, row in enumerate(t.rows):
        for i, w in enumerate(widths):
            row.cells[i].width = Cm(w)
        if keep_together and n < len(t.rows) - 1:
            for cell in row.cells:
                for p in cell.paragraphs:
                    p.paragraph_format.keep_with_next = True
    gap = doc.add_paragraph()
    gap.paragraph_format.space_after = Pt(2)
    return t


def code(doc, text, size=8, numbered=True):
    t = doc.add_table(rows=1, cols=1)
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    cell = t.rows[0].cells[0]
    cell.width = Cm(17.0)
    shade(cell, CODE_FILL)
    p = cell.paragraphs[0]
    p.paragraph_format.space_after = Pt(0)
    lines = text.rstrip("\n").split("\n")
    for i, line in enumerate(lines):
        if numbered:
            r = p.add_run("%3d  " % (i + 1))
            r.font.name = "Consolas"
            r.font.size = Pt(size)
            r.font.color.rgb = RGBColor(0x8A, 0x93, 0xA3)
        r = p.add_run(line)
        r.font.name = "Consolas"
        r.font.size = Pt(size)
        if i < len(lines) - 1:
            r.add_break()
    doc.add_paragraph().paragraph_format.space_after = Pt(2)


def heading(doc, text, level=1):
    h = doc.add_heading(text, level=level)
    for run in h.runs:
        run.font.color.rgb = BRAND
    return h


def para(doc, text, bold_prefix=None, size=11, after=6, italic=False):
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(after)
    if bold_prefix:
        r = p.add_run(bold_prefix)
        r.bold = True
        r.font.size = Pt(size)
    r = p.add_run(text)
    r.font.size = Pt(size)
    r.italic = italic
    return p


def bullet(doc, text, size=11):
    p = doc.add_paragraph(style="List Bullet")
    p.paragraph_format.space_after = Pt(2)
    r = p.add_run(text)
    r.font.size = Pt(size)


class Figures:
    def __init__(self):
        self.n = 0

    def add(self, doc, path, caption, width=None, height=None):
        self.n += 1
        doc.add_picture(str(path), width=Cm(width) if width else None, height=Cm(height) if height else None)
        doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
        doc.paragraphs[-1].paragraph_format.keep_with_next = True
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_after = Pt(10)
        r = p.add_run("Figure %d: %s" % (self.n, caption))
        r.italic = True
        r.font.size = Pt(9.5)

    def pair(self, doc, items, width=7.6):
        """Two screenshots side by side, each with its own caption."""
        t = doc.add_table(rows=2, cols=len(items))
        t.alignment = WD_TABLE_ALIGNMENT.CENTER
        row_flag(t.rows[0], "w:cantSplit")
        for i, (path, caption) in enumerate(items):
            self.n += 1
            pic = t.rows[0].cells[i].paragraphs[0]
            pic.alignment = WD_ALIGN_PARAGRAPH.CENTER
            pic.paragraph_format.keep_with_next = True
            pic.add_run().add_picture(str(path), width=Cm(width))
            cap = t.rows[1].cells[i].paragraphs[0]
            cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
            r = cap.add_run("Figure %d: %s" % (self.n, caption))
            r.italic = True
            r.font.size = Pt(9)
        doc.add_paragraph().paragraph_format.space_after = Pt(4)

    def pairs(self, doc, folder, shots):
        found = [(folder / f, c) for f, c in shots if (folder / f).exists()]
        for i in range(0, len(found), 2):
            self.pair(doc, found[i:i + 2])
        return len(found)


def section(doc, landscape):
    sec = doc.add_section()
    sec.orientation = WD_ORIENT.LANDSCAPE if landscape else WD_ORIENT.PORTRAIT
    a, b = Cm(29.7), Cm(21.0)
    sec.page_width, sec.page_height = (a, b) if landscape else (b, a)
    for side in ("left_margin", "right_margin", "top_margin", "bottom_margin"):
        setattr(sec, side, Cm(1.6 if landscape else 2.0))


def page_break(doc):
    doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)


def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8")


def line_count(rel):
    return len(read(rel).rstrip("\n").split("\n"))


# ---------------- content ----------------

def main():
    run1 = json.loads(read("results/run1-initial.json"))
    run2 = json.loads(read("results/run2-retest.json"))
    bugs = json.loads(read("docs/bugs.json"))
    results = run2["results"]
    run1_by_id = {r["id"]: r for r in run1["results"]}
    figs = Figures()

    doc = Document()
    doc.styles["Normal"].font.name = "Calibri"
    doc.styles["Normal"].font.size = Pt(11)
    sec = doc.sections[0]
    sec.page_width, sec.page_height = Cm(21.0), Cm(29.7)
    for side in ("left_margin", "right_margin", "top_margin", "bottom_margin"):
        setattr(sec, side, Cm(2.0))

    # ----- title page -----
    for text, size, bold, color, before in (
            ("Software Engineering Lab - Project-Based Learning (PBL)", 13, False, None, 40),
            ("Smart Classroom Electricity Management System", 24, True, BRAND, 30),
            ("Vacancy detection, AC-state inference and appliance control", 13, False, None, 6),
            ("Individual Project Report", 13, True, None, 30)):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before = Pt(before)
        r = p.add_run(text)
        r.font.size = Pt(size)
        r.bold = bold
        if color:
            r.font.color.rgb = color
    doc.add_paragraph().paragraph_format.space_after = Pt(30)
    table(doc, ["Particular", "Details"], [
        ["Name", "Vineet Shah"],
        ["Class / Batch", "5S CSE / A6 - B2"],
        ["Roll No.", "28"],
        ["Course", "Software Engineering Lab (24CS01PR0502)"],
        ["Academic year", "2026-27"],
        ["Implemented modules", "Module 1: Vacancy and AC-State Detection Engine\n"
                                "Module 2: Monitoring Dashboard and Control"],
        ["Project management", "Jira (epics, user stories, tasks, sub-tasks, sprints, bugs)"],
        ["Date", "25-10-2026"],
    ], [5.0, 12.0], size=11)
    page_break(doc)

    # ----- 1. problem statement -----
    heading(doc, "1. Project Title and Problem Statement")
    para(doc, "Smart Classroom Electricity Management System", bold_prefix="Title: ")
    para(doc, "Lights, fans and air conditioners stay on in classrooms and laboratories after people leave. "
              "Manual switching and fixed timers cannot follow irregular lecture schedules, which raises "
              "utility bills and wastes energy. PIR sensors cannot recognise appliances and miss people who "
              "sit still, and a single temperature sensor cannot tell whether the AC is still running.")
    para(doc, "The proposed system watches the room with a CCTV camera and a YOLOv8 detector (people, fans and "
              "lights), measures the temperature of four room regions with DHT11 sensors, confirms that the room "
              "is vacant, raises alerts for appliances left on, infers whether the AC is still running from the "
              "temperature drop (Delta T) across the four regions, and lets an operator switch fans and lights "
              "through an ESP32 relay controller from a web dashboard.")
    para(doc, "The problem statement comes from my Idea Lab project \"Electricity Management through Computer "
              "Vision & Temperature Sensing\". For this individual SE PBL, two software modules of that system "
              "were selected, implemented, managed in Jira and tested.", italic=True, size=10.5)

    # ----- 2. system / modules -----
    heading(doc, "2. System and Module Description")
    figs.add(doc, ROOT / "docs/figures/architecture.png",
             "Architecture of the prototype (green boxes are the two implemented modules)", width=16.5)
    table(doc, ["Part", "Role in this prototype"], [
        ["Module 1 - Vacancy and AC-State Detection Engine (app/engine.py)",
         "Validates each frame, confirms vacancy over consecutive empty frames, raises fan/light wastage "
         "alerts and infers the AC state from the 4-region Delta T."],
        ["Module 2 - Monitoring Dashboard and Control (app/server.py, app/db.py, app/static)",
         "REST API and SQLite database; web dashboard with room status, heatmap, alert acknowledgement, "
         "manual relay override and detection settings."],
        ["Classroom node (app/simulator.py)",
         "The CCTV + YOLOv8 detector, the four DHT11 sensors and the ESP32 controller were not available "
         "for this prototype. The simulator sends the same frames to the API and executes relay commands "
         "exactly as the ESP32 would."],
    ], [6.0, 11.0], size=9.5)
    table(doc, ["Item", "Technology"], [
        ["Language / runtime", "Python 3.11 (standard library only: http.server, sqlite3, json, unittest)"],
        ["Database", "SQLite (tables: rooms, readings, alerts, commands, settings)"],
        ["User interface", "HTML, CSS, JavaScript (fetch API), served by the Python server"],
        ["Testing", "Python test runner and unittest; dashboard UI tests in headless Microsoft Edge"],
        ["Project management", "Jira - backlog, sprints, board, bug tracking"],
    ], [4.0, 13.0], size=9.5)

    # ----- 3-5. Jira -----
    heading(doc, "3. Jira Project")
    counts = {}
    for r in backlog.rows():
        counts[r["Issue Type"]] = counts.get(r["Issue Type"], 0) + 1
    table(doc, ["Item", "Details"], [
        ["Jira space (project)", "Smart Classroom Electricity Management - key SCEM (Scrum, team-managed)"],
        ["Site", "rbunagpur-team-zhx8jd75.atlassian.net"],
        ["Work items", "%d epics, %d user stories, %d tasks, %d subtasks, %d bugs = %d" % (
            counts.get("Epic", 0), counts.get("Story", 0), counts.get("Task", 0), counts.get("Subtask", 0),
            counts.get("Bug", 0), sum(counts.values()))],
        ["Hierarchy", "Epic -> Story / Task / Bug -> Subtask (SCEM-1 to SCEM-4 are the epics)"],
        ["Workflow", "To Do -> In Progress -> Done"],
        ["Status on 26-10-2026", "43 Done, 2 In Progress (SCEM-23 report and presentation, and its epic SCEM-4)"],
    ], [4.2, 12.8], size=9.5)
    para(doc, "The backlog was written in jira/backlog.py and imported into Jira with the CSV importer "
              "(jira/jira_import.csv). Work items were then planned into three sprints and moved through the "
              "workflow as the work was completed; each bug was moved to In Progress, given a fix and retest "
              "comment, and closed.", size=10)
    table(doc, ["Epic", "Jira key", "Description", "Label"],
          [[e[1], "SCEM-%d" % (n + 1), e[2], e[3]] for n, e in enumerate(backlog.EPICS)], [4.6, 1.8, 8.9, 1.7],
          size=9)
    sprint_rows = []
    for name, key, dates, state in JIRA_SPRINTS:
        items = [i for i in backlog.ITEMS if i[7] == key]
        keys = ", ".join("SCEM-%d" % (5 + backlog.ITEMS.index(i)) for i in items)
        if key == "S3":
            keys += ", SCEM-24 to SCEM-27 (bugs)"
        sprint_rows.append([name + "\n" + backlog.SPRINT_GOALS[key], dates, keys,
                            str(sum(i[6] for i in items)), state])
    table(doc, ["Sprint and goal", "Dates", "Work items", "Points", "State"], sprint_rows,
          [5.2, 3.2, 5.6, 1.4, 1.6], size=9)
    figs.pairs(doc, ROOT / "evidence/jira", JIRA_SHOTS)

    heading(doc, "4. Product Backlog")
    table(doc, ["Jira key", "Type", "Summary", "Epic", "Priority", "Points", "Sprint"],
          [["SCEM-%d" % (5 + n), i[2], i[3], "SCEM-%d" % (int(i[1][1]),), i[5], str(i[6]), i[7]]
           for n, i in enumerate(backlog.ITEMS)],
          [1.7, 1.3, 7.2, 1.5, 1.6, 1.3, 1.4], size=8.5, keep_together=False)
    para(doc, "Sub-tasks (%d): %s." % (len(backlog.SUBTASKS), "; ".join("%s - %s" % s for s in backlog.SUBTASKS)),
         size=9.5)

    heading(doc, "5. User Stories")
    table(doc, ["Key", "User story and acceptance criteria", "Points"],
          [[i[0], i[3] + "\n" + i[4], str(i[6])] for i in backlog.ITEMS if i[2] == "Story"],
          [1.4, 14.0, 1.6], size=9, keep_together=False)

    # ----- 6. implementation -----
    heading(doc, "6. Implementation of the Two Modules")
    heading(doc, "6.1 Module 1: Vacancy and AC-State Detection Engine", 2)
    para(doc, "The engine (app/engine.py, class RoomMonitor) receives one frame at a time. A frame carries the "
              "YOLOv8 counts (people, fans ON, lights ON) and the four DHT11 temperatures. The room becomes "
              "vacant only after N consecutive empty frames; the four temperatures are then recorded and, after "
              "wait_seconds, compared with the current ones. A mean drop of at least delta_t_threshold means the "
              "AC is still cooling an empty room.")
    figs.add(doc, ROOT / "docs/figures/state_diagram.png", "Room states maintained by Module 1", width=16.5)
    table(doc, ["ID", "Functional requirement (Module 1)"], [
        ["FR-1.1", "Accept frames: timestamp, people, fans_on, lights_on and exactly 4 region temperatures."],
        ["FR-1.2", "Input validation: counts are whole numbers 0-50, temperatures 0-50 deg C (DHT11 range), "
                   "timestamps strictly increasing."],
        ["FR-1.3", "Vacancy is confirmed after at least vacancy_frames consecutive frames with people = 0; any "
                   "person resets the count."],
        ["FR-1.4", "On vacancy the four temperatures are recorded and the state becomes CHECKING_AC."],
        ["FR-1.5", "FAN_ON_VACANT / LIGHT_ON_VACANT alerts while vacant, once per occurrence."],
        ["FR-1.6", "After wait_seconds: mean drop >= delta_t_threshold -> AC inferred ON and AC_ON_VACANT."],
        ["FR-1.7", "A person entering during the check cancels it; the room is OCCUPIED again."],
        ["FR-1.8", "Settings: vacancy_frames 1-300, wait_seconds 30-600, delta_t_threshold 0.1-5.0."],
    ], [1.8, 15.2], size=9.5)
    para(doc, "Core of the engine - RoomMonitor.process() (complete file in Appendix A):", size=10)
    src = read("app/engine.py").split("\n")
    start = next(i for i, l in enumerate(src) if "def process(self, frame):" in l)
    end = next(i for i, l in enumerate(src) if "def _appliance_alerts" in l)
    code(doc, "\n".join(src[start:end]).rstrip(), size=8, numbered=False)

    heading(doc, "6.2 Module 2: Monitoring Dashboard and Control", 2)
    para(doc, "The server (app/server.py) exposes a REST API, passes readings to Module 1, stores readings, "
              "alerts, relay commands and settings in SQLite (app/db.py) and serves the dashboard (app/static). "
              "The dashboard refreshes every 2 seconds.")
    table(doc, ["Method and path", "Purpose", "Validation / errors"], [
        ["POST /api/readings", "Frame from the classroom node -> Module 1 -> stored with any alerts",
         "400 room_id is required / frame errors (FR-1.2); 404 unknown room; 400 invalid JSON"],
        ["GET /api/rooms, /api/rooms/<id>", "Room details, engine status and open alert count", "404 unknown room"],
        ["GET /api/alerts?room=&status=", "Alerts, newest first", "-"],
        ["POST /api/alerts/<id>/ack", "Acknowledge an alert", "operator 3-40 letters; remarks <= 200; 404; 409"],
        ["POST /api/override", "Queue a fan/light ON/OFF command for the ESP32",
         "appliance fan/light; action ON/OFF; operator; reason 5-100"],
        ["GET /api/commands, POST /api/commands/<id>/done", "ESP32 reads and completes commands", "404; 409"],
        ["GET / PUT /api/settings", "Detection settings, stored in the database", "limits of FR-1.8"],
    ], [5.0, 6.2, 5.8], size=8.5)
    table(doc, ["Table", "Columns"], [
        ["rooms", "id, name, fans, lights, acs"],
        ["readings", "id, room_id, ts, people, fans_on, lights_on, t1, t2, t3, t4, state"],
        ["alerts", "id, room_id, ts, type, message, value, status, ack_by, ack_remarks, ack_at"],
        ["commands", "id, room_id, appliance, action, operator, reason, status, created_at, done_at"],
        ["settings", "key, value"],
    ], [3.0, 14.0], size=9)
    table(doc, ["ID", "Functional requirement (Module 2)"], [
        ["FR-2.1", "Receive readings through the API, pass them to Module 1, store readings and alerts."],
        ["FR-2.2", "Show state, counts, AC check, last reading and a 2x2 heatmap; NO DATA for rooms without readings."],
        ["FR-2.3", "List open alerts and acknowledge one (operator name and optional remarks)."],
        ["FR-2.4", "Manual override of fans/lights with operator name and reason."],
        ["FR-2.5", "ESP32 picks up pending commands and marks them done."],
        ["FR-2.6", "Edit settings on the dashboard; stored, applied at once, kept after restart."],
        ["FR-2.7", "Dashboard validation messages use the field labels shown on the form."],
    ], [1.8, 15.2], size=9.5)
    figs.add(doc, ROOT / "evidence/screens/dashboard_LAB-1.png",
             "Dashboard - LAB-1 after the class left with 2 fans, 6 lights and the AC on (simulator run on "
             "25-10-2026); a fan OFF command is pending for the ESP32", width=16.0)
    figs.add(doc, ROOT / "evidence/screens/dashboard_CR-201.png",
             "Dashboard - CR-201 after everything was switched off: AC inferred OFF (room warmed by 0.24 deg C)",
             width=16.0)
    para(doc, "Integration: readings flow from the classroom node through the API into Module 1; the alerts it "
              "returns are written to the database and shown by the dashboard. Commands sent from the dashboard "
              "are stored as PENDING, executed by the ESP32 (simulated) and marked DONE; the next readings then "
              "show the appliance switched off. Settings saved on the dashboard are applied to the running engine.",
         size=10.5)

    # ----- 7. source code -----
    heading(doc, "7. Source Code")
    files = ["app/engine.py", "app/server.py", "app/db.py", "app/simulator.py", "app/static/index.html",
             "app/static/app.js", "app/static/style.css", "tests/helpers.py", "tests/engine_cases.py",
             "tests/api_cases.py", "tests/ui/ui_cases.js", "tests/run_tests.py", "tests/test_unit.py",
             "jira/backlog.py"]
    table(doc, ["File", "Lines", "Contents"], [[f, str(line_count(f)), d] for f, d in zip(files, [
        "Module 1 - frame validation, RoomMonitor state machine, settings",
        "Module 2 - REST API, request validation, static file server",
        "Module 2 - SQLite schema and data access",
        "Simulated camera + DHT11 + ESP32 node",
        "Dashboard page", "Dashboard logic (polling, forms)", "Dashboard styles",
        "Test helpers: frame builders, throw-away server, HTTP client",
        "32 Module 1 test cases", "24 Module 2 API cases and 7 integration cases", "15 dashboard UI test cases",
        "Executes all cases and records actual results", "unittest entry point", "Jira backlog and CSV export"])],
        [5.5, 1.5, 10.0], size=9)
    code(doc, "python -m app.server --port 8090 --db data/energy.db        # start server + dashboard\n"
              "python -m app.simulator --room LAB-1 --scenario ac_left_on  # simulated classroom node\n"
              "python -m tests.run_tests run2-retest                        # execute all 78 test cases\n"
              "python -m unittest -v tests.test_unit                        # unit + API + integration via unittest",
         size=8, numbered=False)

    # ----- 8. test cases (landscape) -----
    section(doc, landscape=True)
    heading(doc, "8. Test Cases and Test Results")
    techniques = [("Unit testing", "Module 1 engine methods tested directly (TC_M1_xx)"),
                  ("Functional testing", "Every functional requirement checked through its output"),
                  ("Integration testing", "Engine + API + database + ESP32 command loop (TC_INT_xx, TC_UI_08)"),
                  ("Boundary Value Analysis", "min-1 / min / max / max+1 for temperatures, counts, frames, wait, "
                                              "threshold, name, remarks and reason lengths"),
                  ("Equivalence Partitioning", "valid and invalid classes for every input field"),
                  ("Validation testing", "every error message of the API and of the dashboard forms")]
    table(doc, ["Technique", "How it was applied"], [list(t) for t in techniques], [5.0, 21.0], size=9.5)
    by_module = {}
    for r in results:
        by_module.setdefault(r["module"], []).append(r)
    para(doc, "Test cases were designed from the requirements (docs/requirements.md) before execution. They are "
              "automated: Python cases call the engine or the running server; UI cases fill the dashboard forms "
              "in Microsoft Edge and read the displayed result. Actual results below are from the final run "
              "(run2-retest, %s); the first run is compared in Section 10." % run2["executed_at"].replace("T", " "),
         size=10)
    widths = [1.8, 2.7, 4.3, 5.3, 5.3, 5.3, 1.5]
    for module, rs in by_module.items():
        heading(doc, module, level=2)
        rows = []
        for r in rs:
            rows.append([r["id"], r["module"].split(" (")[0], "%s\n[%s]" % (r["scenario"], r["technique"]),
                         r["data"], r["expected"], r["actual"], (r["status"], PASS if r["status"] == "PASS" else FAIL)])
        table(doc, ["Test Case ID", "Module", "Test Scenario", "Test Data", "Expected Result", "Actual Result",
                    "Status"], rows, widths, size=8, keep_together=False)
    summary = []
    for module, rs in by_module.items():
        r1 = [run1_by_id[r["id"]] for r in rs]
        summary.append([module, str(len(rs)), str(sum(x["status"] == "PASS" for x in r1)),
                        str(sum(x["status"] == "FAIL" for x in r1)), str(sum(x["status"] == "PASS" for x in rs)),
                        str(sum(x["status"] == "FAIL" for x in rs))])
    summary.append([("Total", None), (str(len(results)), None),
                    (str(sum(x["status"] == "PASS" for x in run1["results"])), None),
                    (str(sum(x["status"] == "FAIL" for x in run1["results"])), None),
                    (str(sum(x["status"] == "PASS" for x in results)), None),
                    (str(sum(x["status"] == "FAIL" for x in results)), None)])
    heading(doc, "Test execution summary", level=2)
    table(doc, ["Module", "Test cases", "Run 1 passed", "Run 1 failed", "Run 2 (retest) passed",
                "Run 2 (retest) failed"], summary, [8.0, 3.0, 3.6, 3.6, 4.0, 4.0], size=10)

    # ----- 9-10. bugs -----
    heading(doc, "9. Bugs Recorded in Jira")
    para(doc, "Every failure of run 1 was analysed and recorded as a Bug in Jira (SCEM Sprint 3). BUG-01 was first "
              "noticed while exploring the dashboard and is reproduced by TC_UI_01.", size=10)
    table(doc, ["Bug ID", "Bug description", "Steps to reproduce", "Severity / Priority", "Status", "Resolution"],
          [["%s\n(%s)" % (b["id"], JIRA_BUG_KEYS[b["id"]]),
            "%s\n\nExpected: %s\nActual: %s\nFound by: %s" % (b["summary"], b["expected"], b["actual"],
                                                                         b["found_by"]),
            "\n".join("%d. %s" % (i, s) for i, s in enumerate(b["steps"], 1)),
            "%s / %s" % (b["severity"], b["priority"]), b["status"], b["resolution"] + "\nRetest: " + b["retest"]]
           for b in bugs], [1.6, 6.8, 6.2, 2.6, 1.6, 7.2], size=8, keep_together=False)
    figs.pairs(doc, ROOT / "evidence/jira", BUG_SHOTS[:2])
    figs.pairs(doc, ROOT / "evidence/jira", BUG_SHOTS[2:])

    heading(doc, "10. Bug Fixing and Retesting Evidence")
    table(doc, ["Test case", "Bug", "Run 1 (before fix) - actual", "Run 1", "Run 2 (after fix) - actual", "Run 2"],
          [[tc, b["id"], run1_by_id[tc]["actual"], (run1_by_id[tc]["status"], FAIL),
            next(r for r in results if r["id"] == tc)["actual"],
            (next(r for r in results if r["id"] == tc)["status"], PASS)]
           for b in bugs for tc in [x for x in run1_by_id if run1_by_id[x]["status"] == "FAIL"
                                    and x in b["found_by"]]],
          [2.2, 1.8, 8.0, 1.5, 8.0, 1.5], size=8.5)
    section(doc, landscape=False)
    figs.add(doc, ROOT / "evidence/bugs/BUG-01_before.png", "BUG-01 before the fix: CR-201 has no readings but "
             "is shown as OCCUPIED (TC_UI_01 FAIL)", width=15.0)
    figs.add(doc, ROOT / "evidence/bugs/BUG-01_after.png", "BUG-01 after the fix: NO DATA (TC_UI_01 PASS)",
             width=15.0)
    figs.add(doc, ROOT / "evidence/bugs/BUG-04_before.png", "BUG-04 before the fix: internal field name in the "
             "message (TC_UI_14 FAIL)", width=15.0)
    figs.add(doc, ROOT / "evidence/bugs/BUG-04_after.png", "BUG-04 after the fix: message uses the form label "
             "(TC_UI_14 PASS)", width=15.0)
    para(doc, "Run 1 console output (failures only):", size=10)
    code(doc, "\n".join(l for l in read("results/run1-initial-console.txt").split("\n")
                        if "FAIL" in l or "expected" in l or "actual" in l or "executed" in l), size=7.5,
         numbered=False)
    para(doc, "Run 2 console output (last lines):", size=10)
    code(doc, "\n".join(read("results/run2-retest-console.txt").rstrip().split("\n")[-6:]), size=7.5, numbered=False)

    # ----- 11. demo -----
    heading(doc, "11. Final Working Demonstration")
    for step in ["Start the server: python -m app.server --port 8090 --db data/demo.db and open "
                 "http://127.0.0.1:8090.",
                 "Run the classroom simulator: python -m app.simulator --room LAB-1 --scenario ac_left_on.",
                 "Watch LAB-1 change from OCCUPIED to CHECKING AC to VACANT; fan, light and AC alerts appear.",
                 "Acknowledge an alert, send a fan OFF override, change a setting; run the all_off scenario "
                 "for CR-201 to show the AC OFF result.",
                 "Run python -m tests.run_tests to execute all 78 test cases."]:
        bullet(doc, step, size=10.5)
    para(doc, "Simulator log of the demonstration run (25-10-2026):", size=10)
    code(doc, read("results/demo-simulator-log.txt"), size=7.5, numbered=False)
    figs.add(doc, ROOT / "evidence/screens/ack_success.png", "Alert acknowledged from the dashboard (TC_UI_07)",
             width=15.0)
    figs.add(doc, ROOT / "evidence/screens/override_success.png", "Manual override command queued (TC_UI_09)",
             width=15.0)

    # ----- 12. conclusion -----
    heading(doc, "12. Conclusion and Future Scope")
    para(doc, "Two modules of the Smart Classroom Electricity Management System were implemented individually: "
              "the vacancy and AC-state detection engine, and the monitoring dashboard with database, alerts, "
              "manual ESP32 override and settings. The work was planned and tracked in Jira as epics, user stories, "
              "tasks, sub-tasks and three sprints. %d test cases using functional, unit, integration, boundary "
              "value, equivalence partitioning and validation testing were executed. The first run found %d "
              "defects (%d failing test cases); all were recorded in Jira, fixed and retested, and the final run "
              "passed all %d test cases." % (len(results), len(bugs),
                                             sum(x["status"] == "FAIL" for x in run1["results"]), len(results)))
    for f in ["Connect the real CCTV + YOLOv8 detector, DHT11 sensors and ESP32 in place of the simulator.",
              "MQTT between the classroom node and the server, as in the original architecture.",
              "Daily energy report (hours of wasted appliance runtime per room) and mobile notifications."]:
        bullet(doc, f, size=10.5)

    page_break(doc)
    heading(doc, "Appendix A: app/engine.py (Module 1)")
    code(doc, read("app/engine.py"), size=7.5)

    doc.save(OUT)
    print("saved", OUT, "| figures:", figs.n)


if __name__ == "__main__":
    main()
