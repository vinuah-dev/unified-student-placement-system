"""Builds the PBL presentation (PPTX + PDF) by driving Microsoft PowerPoint through COM (pywin32).

    python docs/build_presentation.py
    -> docs/PBL_Presentation_Smart_Classroom_Energy_Vineet_Shah.pptx (and .pdf for checking)

Slide size 16:9 = 960 x 540 points. Headings Cambria, body Calibri.
"""
import json
import sys
from pathlib import Path

import win32com.client
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "jira"))
import backlog  # noqa: E402

OUT = ROOT / "docs" / "PBL_Presentation_Smart_Classroom_Energy_Vineet_Shah.pptx"
W, H = 960, 540
M = 44  # side margin


def rgb(hex_color):
    r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
    return r + g * 256 + b * 65536


DARK = "0F2E1D"      # title / conclusion background
FOREST = "14532D"    # headings, key numbers
MINT = "E3F5EA"      # card fill
MINT_EDGE = "BFE3CB"
AMBER = "F59E0B"     # accent circles and highlights
INK = "1B2430"
MUTED = "5D6676"
WHITE = "FFFFFF"
RED = "A31F1F"
GREEN_OK = "166534"

HEAD, BODY = "Cambria", "Calibri"


class Deck:
    def __init__(self):
        self.app = win32com.client.Dispatch("PowerPoint.Application")
        self.pres = self.app.Presentations.Add(0)  # no window
        self.pres.PageSetup.SlideWidth = W
        self.pres.PageSetup.SlideHeight = H

    # ----- primitives -----
    def slide(self, background=WHITE):
        s = self.pres.Slides.Add(self.pres.Slides.Count + 1, 12)  # ppLayoutBlank
        s.FollowMasterBackground = 0
        s.Background.Fill.Solid()
        s.Background.Fill.ForeColor.RGB = rgb(background)
        return s

    @staticmethod
    def text(s, x, y, w, h, paragraphs, size=16, color=INK, font=BODY, bold=False, align=1, valign=1,
             space_after=0, bullets=False, italic=False, name=None):
        """paragraphs: str or list of str / (str, overrides) - one paragraph each."""
        tb = s.Shapes.AddTextbox(1, x, y, w, h)
        if name:
            tb.Name = name
        tf = tb.TextFrame
        tf.WordWrap = -1
        tf.AutoSize = 0
        tf.MarginLeft = tf.MarginRight = 0
        tf.MarginTop = tf.MarginBottom = 0
        tf.VerticalAnchor = valign  # 1 top, 3 middle, 4 bottom
        items = [paragraphs] if isinstance(paragraphs, (str, tuple)) else list(paragraphs)
        items = [p if isinstance(p, tuple) else (p, {}) for p in items]
        tf.TextRange.Text = "\r".join(p[0] for p in items)
        for i, (_, opts) in enumerate(items, 1):
            para = tf.TextRange.Paragraphs(i)
            f = para.Font
            f.Name = opts.get("font", font)
            f.Size = opts.get("size", size)
            f.Bold = -1 if opts.get("bold", bold) else 0
            f.Italic = -1 if opts.get("italic", italic) else 0
            f.Color.RGB = rgb(opts.get("color", color))
            pf = para.ParagraphFormat
            pf.Alignment = opts.get("align", align)  # 1 left, 2 center
            pf.SpaceAfter = opts.get("space_after", space_after)
            if opts.get("bullet", bullets):
                pf.Bullet.Visible = -1
                pf.Bullet.Character = 8226
                para.IndentLevel = 1
                tf.Ruler.Levels(1).FirstMargin = 0
                tf.Ruler.Levels(1).LeftMargin = 14
            else:
                pf.Bullet.Visible = 0
        return tb

    @staticmethod
    def box(s, x, y, w, h, fill=MINT, line=None, radius=0.12, shape=5, name=None):
        b = s.Shapes.AddShape(shape, x, y, w, h)
        if name:
            b.Name = name
        b.Fill.Solid()
        b.Fill.ForeColor.RGB = rgb(fill)
        if line:
            b.Line.Visible = -1
            b.Line.ForeColor.RGB = rgb(line)
            b.Line.Weight = 1
        else:
            b.Line.Visible = 0
        if shape == 5:
            b.Adjustments.SetItem(1, radius)
        b.Shadow.Visible = 0
        return b

    def circle(self, s, x, y, d, label, fill=AMBER, color=WHITE, size=18):
        c = self.box(s, x, y, d, d, fill=fill, shape=9)
        tf = c.TextFrame
        tf.MarginLeft = tf.MarginRight = tf.MarginTop = tf.MarginBottom = 0
        tf.TextRange.Text = label
        tf.TextRange.Font.Name = HEAD
        tf.TextRange.Font.Size = size
        tf.TextRange.Font.Bold = -1
        tf.TextRange.Font.Color.RGB = rgb(color)
        tf.TextRange.ParagraphFormat.Alignment = 2
        tf.VerticalAnchor = 3
        return c

    @staticmethod
    def picture(s, path, x, y, max_w, max_h, border=None, align="center"):
        iw, ih = Image.open(path).size
        scale = min(max_w / iw, max_h / ih)
        w, h = iw * scale, ih * scale
        px = x + (max_w - w) / 2 if align == "center" else x
        py = y + (max_h - h) / 2
        p = s.Shapes.AddPicture(str(path), 0, -1, px, py, w, h)
        if border:
            p.Line.Visible = -1
            p.Line.ForeColor.RGB = rgb(border)
            p.Line.Weight = 0.75
        return p

    def title(self, s, text, color=FOREST):
        return self.text(s, M, 26, W - 2 * M, 48, text, size=32, color=color, font=HEAD, bold=True, valign=3,
                         name="Title")

    @staticmethod
    def notes(s, text):
        s.NotesPage.Shapes.Placeholders(2).TextFrame.TextRange.Text = text

    def footer(self, s, n, dark=False):
        self.text(s, M, H - 26, 600, 16, "Smart Classroom Electricity Management · SE Lab PBL · Vineet Shah",
                  size=10, color=("9FB8A8" if dark else MUTED))
        self.text(s, W - M - 60, H - 26, 60, 16, str(n), size=10, color=("9FB8A8" if dark else MUTED), align=3)

    def save(self):
        self.pres.SaveAs(str(OUT), 24)
        self.pres.SaveAs(str(OUT.with_suffix(".pdf")), 32)
        self.pres.Close()


def card(d, s, x, y, w, h, heading, body, number=None, head_size=17, body_size=14):
    d.box(s, x, y, w, h, fill=MINT)
    tx = x + 18
    if number is not None:
        d.circle(s, x + 16, y + 16, 34, number, size=15)
        tx = x + 62
    d.text(s, tx, y + 18, w - (tx - x) - 16, 30, heading, size=head_size, bold=True, color=FOREST, font=HEAD)
    d.text(s, x + 18, y + 62, w - 36, h - 74, body, size=body_size, color=INK)


def stat(d, s, x, y, w, h, number, label, fill=MINT, num_color=FOREST, label_color=INK, num_size=36):
    d.box(s, x, y, w, h, fill=fill)
    d.text(s, x, y + 10, w, h * 0.55, number, size=num_size, bold=True, color=num_color, font=HEAD, align=2, valign=3)
    d.text(s, x + 8, y + h * 0.62, w - 16, h * 0.32, label, size=13, color=label_color, align=2)


def build():
    run1 = json.loads((ROOT / "results/run1-initial.json").read_text(encoding="utf-8"))["results"]
    run2 = json.loads((ROOT / "results/run2-retest.json").read_text(encoding="utf-8"))["results"]
    by_module = {}
    for r in run2:
        by_module[r["module"]] = by_module.get(r["module"], 0) + 1
    r1_fail = sum(r["status"] == "FAIL" for r in run1)
    r2_pass = sum(r["status"] == "PASS" for r in run2)
    counts = {}
    for row in backlog.rows():
        counts[row["Issue Type"]] = counts.get(row["Issue Type"], 0) + 1
    fig = ROOT / "docs/figures"
    ev = ROOT / "evidence"

    d = Deck()

    # 1 ---------------- title ----------------
    s = d.slide(DARK)
    d.text(s, M + 8, 70, 560, 20, "SOFTWARE ENGINEERING LAB · PROJECT-BASED LEARNING", size=13, color=AMBER, bold=True)
    d.text(s, M + 8, 104, 560, 150, "Smart Classroom Electricity Management System", size=40, color=WHITE,
           font=HEAD, bold=True)
    d.text(s, M + 8, 262, 540, 50, "Vacancy detection, AC-state inference and appliance control", size=19,
           color="BFE3CB")
    d.text(s, M + 8, 398, 560, 60, ["Vineet Shah  ·  Roll No. 28  ·  5S CSE, A6-B2",
                                    "Software Engineering Lab (24CS01PR0502)  ·  2026-27"], size=15,
           color="DDE7E1", space_after=4)
    for i, (num, label) in enumerate([("2", "modules built"), (str(len(run2)), "test cases"),
                                      (str(sum(counts.values())), "Jira work items")]):
        y = 64 + i * 140
        d.circle(s, 700, y, 118, num, fill=AMBER if i == 1 else FOREST, size=40)
        d.text(s, 830, y + 38, 110, 44, label, size=15, color="DDE7E1")
    d.notes(s, "Individual SE PBL project. The problem statement is from my Idea Lab project; for this PBL I "
               "built two software modules, managed the work in Jira and tested it with 78 test cases.")

    # 2 ---------------- problem ----------------
    s = d.slide()
    d.title(s, "Why classrooms waste electricity")
    cw = (W - 2 * M - 2 * 24) / 3
    problems = [("Appliances stay ON", "Lights, fans and ACs keep running after a lecture ends. Manual switching "
                                       "and fixed timers cannot follow irregular schedules."),
                ("Sensors miss the picture", "PIR sensors cannot see whether fans or lights are on, and miss "
                                             "people who sit still."),
                ("AC state is invisible", "One temperature sensor cannot tell whether the AC is still cooling "
                                          "an empty room.")]
    for i, (h_, b_) in enumerate(problems):
        card(d, s, M + i * (cw + 24), 112, cw, 200, h_, b_, number=str(i + 1))
    d.box(s, M, 340, W - 2 * M, 96, fill="FFF7E6")
    d.text(s, M + 20, 356, W - 2 * M - 40, 70,
           [("Proposed system", {"bold": True, "color": FOREST, "size": 15}),
            ("CCTV + YOLOv8 counts people, fans and lights; four DHT11 sensors read four room regions; an ESP32 "
             "switches relays; a web dashboard shows alerts and lets an operator act.", {"size": 14})],
           space_after=2)
    d.footer(s, 2)
    d.notes(s, "Problem statement from the Idea Lab project 'Electricity Management through Computer Vision & "
               "Temperature Sensing'.")

    # 3 ---------------- scope + architecture ----------------
    s = d.slide()
    d.title(s, "What this PBL builds")
    d.picture(s, fig / "architecture.png", M, 92, 560, 380, border="D7DCE4")
    x2 = M + 580
    card(d, s, x2, 96, W - M - x2, 176, "Implemented",
         "Module 1 - detection engine\nModule 2 - REST API, SQLite database and web dashboard", body_size=14)
    card(d, s, x2, 290, W - M - x2, 176, "Simulated",
         "CCTV + YOLOv8, four DHT11 sensors and the ESP32 are replaced by app/simulator.py, which sends the "
         "same data", body_size=14)
    d.text(s, M, 480, 560, 20, "Python 3.11 standard library · SQLite · HTML, CSS, JavaScript", size=12,
           color=MUTED)
    d.footer(s, 3)
    d.notes(s, "Green boxes are what I implemented. The hardware and the trained model were not available, so a "
               "simulator posts the same frames and executes relay commands like the ESP32.")

    # 4 ---------------- module 1 ----------------
    s = d.slide()
    d.title(s, "Module 1 · Vacancy and AC-state detection engine")
    d.picture(s, fig / "state_diagram.png", M, 84, W - 2 * M, 236)
    cw = (W - 2 * M - 2 * 20) / 3
    rules = [("Vacancy", "Room is vacant only after N consecutive frames with no people (default 10). Any "
                         "person resets the count."),
             ("Wastage alerts", "FAN_ON_VACANT and LIGHT_ON_VACANT are raised while the room is vacant, once "
                                "per occurrence."),
             ("AC inference", "After wait_seconds, mean temperature drop over the 4 regions >= threshold means "
                              "the AC is still ON.")]
    for i, (h_, b_) in enumerate(rules):
        card(d, s, M + i * (cw + 20), 334, cw, 162, h_, b_, head_size=16, body_size=13)
    d.footer(s, 4)
    d.notes(s, "app/engine.py - RoomMonitor processes one frame at a time and validates every input "
               "(counts 0-50, temperatures 0-50 deg C, increasing timestamps).")

    # 5 ---------------- module 2 ----------------
    s = d.slide()
    d.title(s, "Module 2 · Monitoring dashboard and control")
    d.picture(s, ev / "screens/dashboard_LAB-1.png", M, 86, 400, 410, border="D7DCE4", align="left")
    feats = [("Live room status", "state badge, people, fans and lights ON, AC check, 2x2 heatmap"),
             ("Alerts", "open alerts listed newest first; operator acknowledges with name and remarks"),
             ("Manual override", "fan or light ON/OFF queued for the ESP32, marked done when executed"),
             ("Settings", "vacancy frames, wait time and threshold, validated and stored in SQLite"),
             ("REST API", "/api/readings, /alerts, /override, /commands, /settings")]
    x2 = M + 432
    for i, (h_, b_) in enumerate(feats):
        y = 88 + i * 82
        d.box(s, x2, y, W - M - x2, 72, fill=MINT)
        d.circle(s, x2 + 14, y + 19, 34, str(i + 1), size=14, fill=FOREST)
        d.text(s, x2 + 62, y + 10, W - M - x2 - 76, 22, h_, size=15, bold=True, color=FOREST, font=HEAD)
        d.text(s, x2 + 62, y + 36, W - M - x2 - 76, 30, b_, size=13, color=INK)
    d.footer(s, 5)
    d.notes(s, "Screenshot from the simulator run on 25-10-2026: LAB-1 left with 2 fans, 6 lights and the AC "
               "on - three open alerts and a pending fan OFF command.")

    # 6 ---------------- jira ----------------
    s = d.slide()
    d.title(s, "Managed in Jira · space SCEM")
    stats = [(str(counts.get("Epic", 0)), "epics"), (str(counts.get("Story", 0)), "user stories"),
             (str(counts.get("Task", 0)), "tasks"), (str(counts.get("Subtask", 0)), "subtasks"),
             (str(counts.get("Bug", 0)), "bugs"), (str(len(backlog.SPRINTS)), "sprints")]
    sw, sh = 150, 112
    for i, (n, label) in enumerate(stats):
        col, row = i % 3, i // 3
        stat(d, s, M + col * (sw + 14), 104 + row * (sh + 16), sw, sh, n, label,
             fill=("FFF7E6" if label == "bugs" else MINT), num_color=(AMBER if label == "bugs" else FOREST))
    d.text(s, M, 362, 3 * sw + 28, 130,
           ["Epic -> Story / Task / Bug -> Subtask",
            "Backlog imported from jira/jira_import.csv",
            "Workflow: To Do -> In Progress -> Done",
            "Each bug carries steps, severity, priority and a fix + retest comment"],
           size=14, bullets=True, space_after=6)
    d.picture(s, ev / "jira/sprint_planning.jpg", W - M - 360, 84, 360, 414, border="D7DCE4")
    d.footer(s, 6)
    d.notes(s, "Site rbunagpur-team-zhx8jd75.atlassian.net, space Smart Classroom Electricity Management "
               "(key SCEM), Scrum, team-managed. Screenshot: sprint planning in the backlog.")

    # 7 ---------------- sprints ----------------
    s = d.slide()
    d.title(s, "Three sprints, tracked to Done")
    sprint_info = [("SCEM Sprint 1", "S1", "25-10 19:30-19:50", "Completed"),
                   ("SCEM Sprint 2", "S2", "25-10 19:50-20:00", "Completed"),
                   ("SCEM Sprint 3", "S3", "25-10 20:00 - 01-11", "Active")]
    rows = [["Sprint", "Goal", "Items", "Points", "State"]]
    for name, key, dates, state in sprint_info:
        items = [i for i in backlog.ITEMS if i[7] == key]
        n_items = len(items) + (4 if key == "S3" else 0)
        rows.append([name + "\n" + dates, backlog.SPRINT_GOALS[key], str(n_items), str(sum(i[6] for i in items)),
                     state])
    tw = 520
    t = s.Shapes.AddTable(len(rows), 5, M, 100, tw, 160).Table
    widths = [126, 200, 52, 56, 86]
    for c, wdt in enumerate(widths, 1):
        t.Columns(c).Width = wdt
    for r, row in enumerate(rows, 1):
        for c, val in enumerate(row, 1):
            cell = t.Cell(r, c).Shape
            cell.Fill.Solid()
            cell.Fill.ForeColor.RGB = rgb(FOREST if r == 1 else ("FFFFFF" if r % 2 else "F2F8F4"))
            tr = cell.TextFrame.TextRange
            tr.Text = val
            tr.Font.Name = BODY
            tr.Font.Size = 13 if r > 1 else 13
            tr.Font.Bold = -1 if r == 1 or c == 1 else 0
            tr.Font.Color.RGB = rgb(WHITE if r == 1 else (GREEN_OK if val == "Completed" else
                                                            (AMBER if val == "Active" else INK)))
            cell.TextFrame.MarginLeft = cell.TextFrame.MarginRight = 6
    d.text(s, M, 270, tw, 60, ["Sprint 3 holds the testing tasks and the four bugs; the report and "
                               "presentation task stays In Progress until submission."], size=13, color=MUTED)
    d.picture(s, ev / "jira/status_overview.jpg", W - M - 300, 84, 300, 414, border="D7DCE4")
    d.footer(s, 7)
    d.notes(s, "Status on 26-10-2026: 43 work items Done, 2 In Progress (SCEM-23 report and presentation, and its "
               "epic SCEM-4).")

    # 8 ---------------- testing ----------------
    s = d.slide()
    d.title(s, "%d automated test cases" % len(run2))
    mods = [("M1 Detection Engine", "Unit tests\nengine"), ("M2 Dashboard & Control", "API tests\nserver + DB"),
            ("Integration (M1 + M2)", "Integration\nend to end"), ("M2 Dashboard & Control (UI)", "UI tests\nin Edge")]
    sw = (W - 2 * M - 3 * 16) / 4
    for i, (key, label) in enumerate(mods):
        stat(d, s, M + i * (sw + 16), 96, sw, 128, str(by_module.get(key, 0)), label, num_size=40)
    tech = [("Functional", "every requirement checked through its output"),
            ("Equivalence partitioning", "valid and invalid classes for each input"),
            ("Boundary value analysis", "min-1, min, max, max+1 for every limit"),
            ("Validation", "every API and form error message"),
            ("Unit and integration", "engine alone, then engine + API + DB + ESP32 loop")]
    for i, (h_, b_) in enumerate(tech):
        y = 246 + i * 46
        d.circle(s, M, y + 4, 28, "✓", size=13, fill=FOREST)
        d.text(s, M + 40, y + 6, 260, 24, h_, size=15, bold=True, color=FOREST, font=HEAD)
        d.text(s, M + 300, y + 8, W - 2 * M - 300, 24, b_, size=14, color=INK)
    d.text(s, M, 482, W - 2 * M, 20, "Format: Test Case ID · Module · Test Scenario · Test Data · Expected Result · "
                                    "Actual Result · Status", size=12, color=MUTED, italic=True)
    d.footer(s, 8)
    d.notes(s, "Expected results come from the requirements (docs/requirements.md), written before the first run. "
               "python -m tests.run_tests executes all cases and records the actual result of each.")

    # 9 ---------------- bugs ----------------
    s = d.slide()
    d.title(s, "Run 1 found %d real bugs" % 4)
    stat(d, s, M, 100, 200, 150, "%d / %d" % (len(run1) - r1_fail, r1_fail), "Run 1: passed / failed",
         fill="FDECEC", num_color=RED, num_size=34)
    d.text(s, M + 200, 150, 50, 50, "→", size=32, color=MUTED, align=2, valign=3)
    stat(d, s, M + 250, 100, 200, 150, "%d / 0" % r2_pass, "Run 2 (retest): passed / failed",
         fill=MINT, num_color=GREEN_OK, num_size=34)
    d.text(s, M, 272, 450, 200, ["Each failure was analysed, logged as a Bug in Jira, fixed in code and "
                                 "retested.",
                                 "Fix and retest comments are on each bug (SCEM-24 to SCEM-27)."],
           size=14, bullets=True, space_after=8)
    bugs = [("BUG-01 · SCEM-24", "Minor / Medium", "Room with no readings shown as OCCUPIED"),
            ("BUG-02 · SCEM-25", "Major / High", "False AC alert at 0.499 deg C drop (rounding)"),
            ("BUG-03 · SCEM-26", "Minor / Low", "Missing room_id gave 404 'Room None'"),
            ("BUG-04 · SCEM-27", "Trivial / Low", "Settings errors showed internal field names")]
    x2 = M + 480
    for i, (k, sev, desc) in enumerate(bugs):
        y = 100 + i * 96
        d.box(s, x2, y, W - M - x2, 84, fill=("FFF7E6" if "Major" in sev else MINT))
        d.text(s, x2 + 16, y + 10, 200, 22, k, size=15, bold=True, color=FOREST, font=HEAD)
        d.text(s, W - M - 150, y + 12, 136, 20, sev, size=12, color=(RED if "Major" in sev else MUTED), align=3,
               bold=True)
        d.text(s, x2 + 16, y + 42, W - M - x2 - 32, 34, desc, size=14, color=INK)
    d.footer(s, 9)
    d.notes(s, "BUG-02 was the most serious: the mean drop was rounded to 2 decimals before the threshold "
               "comparison. Found by the BVA case threshold - 0.001.")

    # 10 ---------------- fix evidence ----------------
    s = d.slide()
    d.title(s, "Bug fix and retest evidence · BUG-01")
    pw = (W - 2 * M - 24) / 2
    for i, (img, label, col) in enumerate([("BUG-01_before.png", "Before fix: OCCUPIED, TC_UI_01 FAIL", RED),
                                           ("BUG-01_after.png", "After fix: NO DATA, TC_UI_01 PASS", GREEN_OK)]):
        x = M + i * (pw + 24)
        d.picture(s, ev / "bugs" / img, x, 92, pw, 330, border="D7DCE4")
        d.text(s, x, 432, pw, 24, label, size=15, bold=True, color=col, align=2)
    d.text(s, M, 470, W - 2 * M, 24, "Same seeded data, same test case, captured from the real dashboard in "
                                    "Microsoft Edge before and after the fix", size=12, color=MUTED, align=2)
    d.footer(s, 10)
    d.notes(s, "The dark bar at the top of each screenshot is added by the UI test harness and shows the test "
               "case, time and result.")

    # 11 ---------------- demo ----------------
    s = d.slide()
    d.title(s, "Live demonstration")
    steps = [("Start the server", "python -m app.server --port 8090"),
             ("Run the classroom simulator", "python -m app.simulator --room LAB-1 --scenario ac_left_on"),
             ("Watch and act", "alerts appear; acknowledge, override a fan, change a setting"),
             ("Run all tests", "python -m tests.run_tests")]
    for i, (h_, cmd) in enumerate(steps):
        y = 100 + i * 96
        d.circle(s, M, y + 8, 44, str(i + 1), size=18)
        d.text(s, M + 62, y + 6, 380, 24, h_, size=17, bold=True, color=FOREST, font=HEAD)
        d.text(s, M + 62, y + 36, 400, 40, cmd, size=13, color=INK,
               font=("Courier New" if cmd.startswith("python") else BODY))
    d.picture(s, ev / "screens/dashboard_CR-201.png", M + 470, 100, W - 2 * M - 470, 170, border="D7DCE4")
    d.text(s, M + 470, 280, W - 2 * M - 470, 40, "CR-201 after everything was switched off: AC inferred OFF "
                                                 "(room warmed by 0.24 deg C)", size=12, color=MUTED)
    d.picture(s, ev / "screens/override_success.png", M + 470, 330, W - 2 * M - 470, 160, border="D7DCE4")
    d.footer(s, 11)
    d.notes(s, "Demo order: server, simulator scenario ac_left_on for LAB-1 (fan, light and AC alerts), "
               "acknowledge an alert, send fan OFF, then all_off for CR-201, then the test run.")

    # 12 ---------------- conclusion ----------------
    s = d.slide(DARK)
    d.text(s, M + 8, 40, W - 2 * M, 50, "Conclusion and next steps", size=34, color=WHITE, font=HEAD, bold=True)
    d.text(s, M + 8, 116, 420, 300,
           [("What was achieved", {"bold": True, "color": AMBER, "size": 18, "font": HEAD}),
            ("Two working modules with database, validation and integration", {"bullet": True}),
            ("Jira project: %d work items, 3 sprints, bugs tracked to closure" % sum(counts.values()),
             {"bullet": True}),
            ("%d test cases; 4 bugs found, fixed and retested; %d / %d pass" % (len(run2), r2_pass, len(run2)),
             {"bullet": True})],
           size=16, color="E6EFE9", space_after=10)
    d.text(s, M + 470, 116, 420, 300,
           [("Next steps", {"bold": True, "color": AMBER, "size": 18, "font": HEAD}),
            ("Connect the real CCTV + YOLOv8, DHT11 sensors and ESP32", {"bullet": True}),
            ("MQTT between classroom node and server", {"bullet": True}),
            ("Daily energy-wastage report and mobile alerts", {"bullet": True})],
           size=16, color="E6EFE9", space_after=10)
    d.text(s, M + 8, 400, W - 2 * M, 40, "Thank you · Questions?", size=24, color=WHITE, font=HEAD, bold=True)
    d.notes(s, "Close with the results and the next steps toward the full hardware system.")

    d.save()
    print("saved", OUT, "and", OUT.with_suffix(".pdf"))


if __name__ == "__main__":
    build()
