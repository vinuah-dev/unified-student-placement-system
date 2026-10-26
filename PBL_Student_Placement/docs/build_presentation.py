"""Builds the PBL presentation (PPTX + PDF) by driving Microsoft PowerPoint through COM (pywin32).

    python docs/build_presentation.py
    -> docs/PBL_Presentation_Student_Placement_Vineet_Shah.pptx (and .pdf for checking)

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

OUT = ROOT / "docs" / "PBL_Presentation_Student_Placement_Vineet_Shah.pptx"
W, H = 960, 540
M = 44  # side margin


def rgb(hex_color):
    r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
    return r + g * 256 + b * 65536


DARK = "0F1B3D"      # title / conclusion background
NAVY = "1E3A8A"      # headings, key numbers
LIGHT = "E3E9F8"     # card fill
AMBER = "F59E0B"     # accent circles and highlights
INK = "1B2430"
MUTED = "5D6676"
WHITE = "FFFFFF"
RED = "A31F1F"
GREEN_OK = "166534"
WARM = "FFF7E6"

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
    def box(s, x, y, w, h, fill=LIGHT, line=None, radius=0.12, shape=5, name=None):
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

    def title(self, s, text, color=NAVY):
        return self.text(s, M, 26, W - 2 * M, 48, text, size=30, color=color, font=HEAD, bold=True, valign=3,
                         name="Title")

    @staticmethod
    def notes(s, text):
        s.NotesPage.Shapes.Placeholders(2).TextFrame.TextRange.Text = text

    def footer(self, s, n, dark=False):
        self.text(s, M, H - 26, 600, 16, "Unified Student Placement System · SE Lab PBL · Vineet Shah, Roll No. 28",
                  size=10, color=("A9B6D6" if dark else MUTED))
        self.text(s, W - M - 60, H - 26, 60, 16, str(n), size=10, color=("A9B6D6" if dark else MUTED), align=3)

    def save(self):
        self.pres.SaveAs(str(OUT), 24)
        self.pres.SaveAs(str(OUT.with_suffix(".pdf")), 32)
        self.pres.Close()


def card(d, s, x, y, w, h, heading, body, number=None, head_size=17, body_size=14, fill=LIGHT):
    d.box(s, x, y, w, h, fill=fill)
    tx = x + 18
    if number is not None:
        d.circle(s, x + 16, y + 16, 34, number, size=15)
        tx = x + 62
    d.text(s, tx, y + 18, w - (tx - x) - 16, 30, heading, size=head_size, bold=True, color=NAVY, font=HEAD)
    d.text(s, x + 18, y + 62, w - 36, h - 74, body, size=body_size, color=INK)


def stat(d, s, x, y, w, h, number, label, fill=LIGHT, num_color=NAVY, label_color=INK, num_size=36):
    d.box(s, x, y, w, h, fill=fill)
    d.text(s, x, y + 10, w, h * 0.55, number, size=num_size, bold=True, color=num_color, font=HEAD, align=2, valign=3)
    d.text(s, x + 8, y + h * 0.62, w - 16, h * 0.32, label, size=13, color=label_color, align=2)


def feature_list(d, s, x, y, w, items, step=80, box_h=70):
    for i, (h_, b_) in enumerate(items):
        yy = y + i * step
        d.box(s, x, yy, w, box_h, fill=LIGHT)
        d.circle(s, x + 14, yy + (box_h - 34) / 2, 34, str(i + 1), size=14, fill=NAVY)
        d.text(s, x + 62, yy + 9, w - 76, 22, h_, size=15, bold=True, color=NAVY, font=HEAD)
        d.text(s, x + 62, yy + 33, w - 76, box_h - 36, b_, size=12.5, color=INK)


def build():
    runs = {k: json.loads((ROOT / ("results/%s.json" % k)).read_text(encoding="utf-8"))["results"]
            for k in ("run1", "run2", "run3", "run4")}
    final = runs["run4"]
    by_module = {}
    for r in final:
        key = "UI" if r["module"].endswith("(UI)") else r["module"]
        by_module[key] = by_module.get(key, 0) + 1

    def pf(k):
        rs = runs[k]
        return sum(r["status"] == "PASS" for r in rs), sum(r["status"] == "FAIL" for r in rs)
    counts = {}
    for row in backlog.rows():
        counts[row["Issue Type"]] = counts.get(row["Issue Type"], 0) + 1
    keys = json.loads((ROOT / "jira/jira_keys.json").read_text(encoding="utf-8"))["keys"]
    fig = ROOT / "docs/figures"
    ev = ROOT / "evidence"

    d = Deck()

    # 1 ---------------- title ----------------
    s = d.slide(DARK)
    d.text(s, M + 8, 70, 560, 20, "SOFTWARE ENGINEERING LAB · PROJECT-BASED LEARNING", size=13, color=AMBER, bold=True)
    d.text(s, M + 8, 104, 580, 150, "Unified Student Placement System", size=42, color=WHITE, font=HEAD, bold=True)
    d.text(s, M + 8, 262, 560, 50, "Job Posting & Eligibility Verification  ·  Job Application & Tracking", size=18,
           color="C7D2F0")
    d.text(s, M + 8, 398, 560, 60, ["Vineet Shah  ·  Roll No. 28  ·  5S CSE, A6-B2",
                                    "Software Engineering Lab (24CS01PR0502)  ·  Prof. D. A. Borikar"], size=15,
           color="DDE3F2", space_after=4)
    for i, (num, label) in enumerate([("2", "modules built"), (str(len(final)), "test cases"),
                                      (str(sum(counts.values())), "Jira work items")]):
        y = 64 + i * 140
        d.circle(s, 700, y, 118, num, fill=AMBER if i == 1 else NAVY, size=40)
        d.text(s, 830, y + 38, 110, 44, label, size=15, color="DDE3F2")
    d.notes(s, "SE PBL on my lab case study, the Unified Student Placement System. Two modules of the SRS were built, "
               "managed in Jira and tested with %d test cases." % len(final))

    # 2 ---------------- problem ----------------
    s = d.slide()
    d.title(s, "Why campus placement needs one system")
    cw = (W - 2 * M - 2 * 24) / 3
    problems = [("Manual screening", "Placement officers check every student against every company's CGPA, branch "
                                     "and backlog rules by hand."),
                ("Errors and missed deadlines", "Ineligible and duplicate applications, stale copies of data in "
                                                "spreadsheets, late applications."),
                ("No visibility", "Students and recruiters cannot see where an application stands; updates go out "
                                  "by e-mail and notice boards.")]
    for i, (h_, b_) in enumerate(problems):
        card(d, s, M + i * (cw + 24), 112, cw, 200, h_, b_, number=str(i + 1))
    d.box(s, M, 340, W - 2 * M, 96, fill=WARM)
    d.text(s, M + 20, 356, W - 2 * M - 40, 70,
           [("USPS (my SE lab SRS)", {"bold": True, "color": NAVY, "size": 15}),
            ("One web platform for students, recruiters and the placement cell: approved job postings, automatic "
             "eligibility with reasons, applications with tracking ids and a live status timeline.", {"size": 14})],
           space_after=2)
    d.footer(s, 2)
    d.notes(s, "Problem statement from the SRS scope (1.4): spreadsheets, e-mail threads and notice boards are "
               "replaced by one platform.")

    # 3 ---------------- scope + architecture ----------------
    s = d.slide()
    d.title(s, "What this PBL builds")
    d.picture(s, fig / "architecture.png", M, 88, 560, 390, border="D7DCE4")
    x2 = M + 580
    card(d, s, x2, 92, W - M - x2, 182, "Implemented",
         "Module 1 - job posting, approval, search, eligibility check\nModule 2 - application, statechart "
         "workflow, tracking, notifications", body_size=13.5)
    card(d, s, x2, 290, W - M - x2, 182, "Built from my lab work",
         "SRS FR-09 to FR-17, use cases UC-1 / UC-2, Expt-3 class diagram, Expt-5 statechart, SRS 6.1 tables",
         body_size=13.5)
    d.text(s, M, 486, 560, 20, "Python 3.11 standard library · SQLite · HTML, CSS, JavaScript", size=12,
           color=MUTED)
    d.footer(s, 3)
    d.notes(s, "Three-tier design from SRS 2.1. Login, interview scheduling, offer documents and reports are other "
               "SRS modules and are outside this PBL; the page lets me pick the acting user.")

    # 4 ---------------- module 1 ----------------
    s = d.slide()
    d.title(s, "Module 1 · Job posting and eligibility verification")
    d.picture(s, ev / "ui/TC_UI_03.png", M, 86, 420, 410, border="D7DCE4", align="left")
    feature_list(d, s, M + 444, 88, W - M - (M + 444), [
        ("Post a job (FR-10)", "title, package, location, deadline + eligibility rule-set; validated on the server"),
        ("Company approval (FR-09)", "recruiter of an unapproved company cannot post"),
        ("Officer decision (FR-11, BR-02)", "approve, reject or return with remarks; returned jobs are resubmitted"),
        ("Search and filter (FR-12)", "keyword, location, minimum package, eligible only, pages"),
        ("Eligibility check (FR-14, BR-03)", "every unmet criterion listed; Apply disabled when not eligible")],
        step=82, box_h=72)
    d.footer(s, 4)
    d.notes(s, "Screenshot: student Rohan (ME, 2 backlogs, batch 2022-2026) sees every unmet criterion and the Apply "
               "button is disabled. Rules are in app/rules.py - EligibilityCriteria.evaluate() from the Expt-3 "
               "class diagram.")

    # 5 ---------------- module 2 ----------------
    s = d.slide()
    d.title(s, "Module 2 · Job application and tracking")
    d.picture(s, fig / "statechart_expt5.png", M, 82, W - 2 * M, 240)
    cw = (W - 2 * M - 2 * 20) / 3
    rules = [("Apply (UC-1)", "published, before deadline, not placed, eligible, no duplicate, own active resume; "
                              "tracking id USPS-26-0001; saved in one transaction"),
             ("Statechart (Expt-5)", "every step goes through next_state(); offers only after selection (BR-08); "
                                     "recruiters touch only their own applicants (BR-07)"),
             ("Tracking (FR-17)", "timeline with every step and actor, notifications, withdraw before the "
                                  "deadline, accept marks the student placed (BR-01)")]
    for i, (h_, b_) in enumerate(rules):
        card(d, s, M + i * (cw + 20), 334, cw, 166, h_, b_, head_size=16, body_size=12.5)
    d.footer(s, 5)
    d.notes(s, "The statechart I drew in Expt-5 is coded as a transition table (APPLICATION_TRANSITIONS); anything "
               "the diagram does not allow is refused with a 409 message.")

    # 6 ---------------- live pages ----------------
    s = d.slide()
    d.title(s, "Three roles, one live page")
    pw = (W - 2 * M - 24) / 2
    for i, (img, label) in enumerate([("TC_UI_39.png", "Officer: a job posted by a recruiter elsewhere appears "
                                                       "without reload, with a pop-up"),
                                      ("TC_UI_38.png", "Student: status timeline after accepting the offer")]):
        x = M + i * (pw + 24)
        d.picture(s, ev / "ui" / img, x, 88, pw, 340, border="D7DCE4")
        d.text(s, x, 436, pw, 40, label, size=13, color=INK, align=2)
    d.text(s, M, 482, W - 2 * M, 20, "Every open page asks /api/version every 2 seconds and redraws itself when anyone "
                                    "changes data", size=12, color=MUTED, align=2, italic=True)
    d.footer(s, 6)
    d.notes(s, "Recruiter posts -> officer's pending list updates; officer approves -> eligible students' job boards "
               "update and they get a 'New job for you' notification.")

    # 7 ---------------- jira ----------------
    s = d.slide()
    d.title(s, "Managed in Jira · space USPS")
    stats = [(str(counts["Epic"]), "epics"), (str(counts["Story"]), "user stories"), (str(counts["Task"]), "tasks"),
             (str(counts["Subtask"]), "sub-tasks"), (str(counts["Bug"]), "bugs"), (str(len(backlog.SPRINTS)), "sprints")]
    sw, sh = 150, 112
    for i, (n, label) in enumerate(stats):
        col, row = i % 3, i // 3
        stat(d, s, M + col * (sw + 14), 100 + row * (sh + 16), sw, sh, n, label,
             fill=(WARM if label == "bugs" else LIGHT), num_color=(AMBER if label == "bugs" else NAVY))
    d.text(s, M, 358, 3 * sw + 28, 140,
           ["Epic -> Story / Task / Bug -> Sub-task, with story points and priorities",
            "Workflow: To Do -> In Progress -> In Review -> Done",
            "Two members: my institute ID (admin) and my second ID, invited, with 14 work items assigned",
            "Each bug has steps, severity, priority and a fix + retest comment"],
           size=13.5, bullets=True, space_after=6)
    d.picture(s, ev / "jira/01_backlog_sprint3.png", W - M - 380, 92, 380, 400, border="D7DCE4")
    d.footer(s, 7)
    d.notes(s, "Site rbunagpur-team-zhx8jd75.atlassian.net, space Unified Student Placement System (key USPS), Scrum, "
               "team-managed. Screenshot: backlog of the active Sprint 3.")

    # 8 ---------------- sprints ----------------
    s = d.slide()
    d.title(s, "Three sprints, tracked to Done")
    sprint_info = [("USPS Sprint 1", "S1", "26-10 10:30-10:50", "Completed"),
                   ("USPS Sprint 2", "S2", "26-10 10:50-11:05", "Completed"),
                   ("USPS Sprint 3", "S3", "26-10 - 02-11", "Active")]
    rows = [["Sprint", "Goal", "Items", "Points", "State"]]
    for name, key, dates, state in sprint_info:
        items = [i for i in backlog.ITEMS if i[7] == key]
        rows.append([name + "\n" + dates, backlog.SPRINT_GOALS[key], str(len(items) + (4 if key == "S3" else 0)),
                     str(sum(i[6] for i in items)), state])
    tw = 520
    t = s.Shapes.AddTable(len(rows), 5, M, 96, tw, 160).Table
    for c, wdt in enumerate([126, 206, 50, 54, 84], 1):
        t.Columns(c).Width = wdt
    for r, row in enumerate(rows, 1):
        for c, val in enumerate(row, 1):
            cell = t.Cell(r, c).Shape
            cell.Fill.Solid()
            cell.Fill.ForeColor.RGB = rgb(NAVY if r == 1 else ("FFFFFF" if r % 2 else "F1F4FB"))
            tr = cell.TextFrame.TextRange
            tr.Text = val
            tr.Font.Name = BODY
            tr.Font.Size = 12.5
            tr.Font.Bold = -1 if r == 1 or c == 1 else 0
            tr.Font.Color.RGB = rgb(WHITE if r == 1 else (GREEN_OK if val == "Completed" else
                                                            (AMBER if val == "Active" else INK)))
            cell.TextFrame.MarginLeft = cell.TextFrame.MarginRight = 6
    d.text(s, M, 330, tw, 120, ["Sprint 3 holds the testing tasks and the four bugs; the report and presentation "
                                "task stays In Progress until submission.",
                                "47 of 49 work items Done on 26-10-2026."], size=13.5, color=MUTED, space_after=8)
    d.picture(s, ev / "jira/08_reports_dashboard.png", W - M - 340, 92, 340, 400, border="D7DCE4")
    d.footer(s, 8)
    d.notes(s, "Reports dashboard: 49 work items by status, type and assignee.")

    # 9 ---------------- testing ----------------
    s = d.slide()
    d.title(s, "%d automated test cases" % len(final))
    mods = [("M1 Job Posting & Eligibility", "Module 1\nunit + API"), ("M2 Application & Tracking",
                                                                       "Module 2\nunit + API"),
            ("Integration (M1 + M2)", "Integration\nend to end"), ("UI", "UI tests\nin Edge")]
    sw = (W - 2 * M - 3 * 16) / 4
    for i, (key, label) in enumerate(mods):
        stat(d, s, M + i * (sw + 16), 92, sw, 128, str(by_module.get(key, 0)), label, num_size=40)
    tech = [("Functional", "every requirement checked through the API and the page"),
            ("Equivalence partitioning", "valid / invalid classes: words for numbers, unknown branch, wrong resume"),
            ("Boundary value analysis", "CGPA 6.99 / 7.00, cover note 500 / 501, apply 1 min before / at deadline"),
            ("Validation", "every API and form error message"),
            ("Unit and integration", "rules alone, then both modules + DB: rollback, concurrency, restart")]
    for i, (h_, b_) in enumerate(tech):
        y = 240 + i * 46
        d.circle(s, M, y + 4, 28, "✓", size=13, fill=NAVY)
        d.text(s, M + 40, y + 6, 250, 24, h_, size=15, bold=True, color=NAVY, font=HEAD)
        d.text(s, M + 290, y + 8, W - 2 * M - 290, 24, b_, size=13.5, color=INK)
    d.text(s, M, 482, W - 2 * M, 20, "Format: Test Case ID · Module · Test Scenario · Test Data · Expected Result · "
                                    "Actual Result · Status", size=12, color=MUTED, italic=True)
    d.footer(s, 9)
    d.notes(s, "Expected results come from docs/requirements.md, written before the first run. A fixed test clock "
               "lets the tests cross deadlines. python -m tests.run_tests records the actual result of each case.")

    # 10 ---------------- runs and bugs ----------------
    s = d.slide()
    d.title(s, "Testing found 4 real bugs")
    runs_info = [("run1", "Run 1", RED, "FDECEC"), ("run2", "Run 2 retest", GREEN_OK, LIGHT),
                 ("run3", "Run 3 +4 cases", RED, "FDECEC"), ("run4", "Run 4 retest", GREEN_OK, LIGHT)]
    for i, (k, label, col, fill) in enumerate(runs_info):
        p_, f_ = pf(k)
        stat(d, s, M + (i % 2) * 222, 96 + (i // 2) * 128, 206, 112, "%d / %d" % (p_, p_ + f_), label + ": passed",
             fill=fill, num_color=col, num_size=28)
    d.text(s, M, 362, 430, 130, ["Run 1: 15 UI failures, one root cause (BUG-01)",
                                 "Exploratory testing after run 2 found BUG-02 to BUG-04; new cases written",
                                 "Every bug logged in Jira, fixed, retested"],
           size=13.5, bullets=True, space_after=6)
    bugs = [("BUG-01 · %s" % keys["BUG-01"], "Major / High", "Active resume not pre-selected; apply refused"),
            ("BUG-02 · %s" % keys["BUG-02"], "Major / High", "Double approval at once, students notified twice"),
            ("BUG-03 · %s" % keys["BUG-03"], "Major / High", "Same status change applied twice at once"),
            ("BUG-04 · %s" % keys["BUG-04"], "Minor / Medium", "Posting approved after its deadline")]
    x2 = M + 470
    for i, (k, sev, desc) in enumerate(bugs):
        y = 96 + i * 98
        d.box(s, x2, y, W - M - x2, 86, fill=(WARM if "Major" in sev else LIGHT))
        d.text(s, x2 + 16, y + 10, 220, 22, k, size=15, bold=True, color=NAVY, font=HEAD)
        d.text(s, W - M - 150, y + 12, 136, 20, sev, size=12, color=(RED if "Major" in sev else MUTED), align=3,
               bold=True)
        d.text(s, x2 + 16, y + 44, W - M - x2 - 32, 34, desc, size=13.5, color=INK)
    d.footer(s, 10)
    d.notes(s, "BUG-02 and BUG-03 are race conditions: two requests read the same state before either saved. Fixed "
               "with one re-entrant lock around every check-and-update. BUG-04 also changed requirement FR-1.4.")

    # 11 ---------------- fix evidence ----------------
    s = d.slide()
    d.title(s, "Bug fix and retest evidence · BUG-01")
    pw = (W - 2 * M - 24) / 2
    for i, (img, label, col) in enumerate([("BUG-01_before_TC_UI_11.png", "Before fix: TC_UI_11 FAIL (run 1)", RED),
                                           ("BUG-01_after_TC_UI_11.png", "After fix: TC_UI_11 PASS (run 2)",
                                            GREEN_OK)]):
        x = M + i * (pw + 24)
        d.picture(s, ev / "bugs" / img, x, 92, pw, 330, border="D7DCE4")
        d.text(s, x, 432, pw, 24, label, size=15, bold=True, color=col, align=2)
    d.text(s, M, 470, W - 2 * M, 24, "Same demo data and test case, captured from the real page in Microsoft Edge "
                                    "before and after the fix", size=12, color=MUTED, align=2)
    d.footer(s, 11)
    d.notes(s, "The dark bar at the top of each screenshot is added by the UI test harness and shows the test case, "
               "time and result. Evidence for BUG-02 to BUG-04 is in the report (run 3 vs run 4).")

    # 12 ---------------- demo ----------------
    s = d.slide()
    d.title(s, "Live demonstration")
    steps = [("Start the portal", "python run.py  ->  http://127.0.0.1:8091"),
             ("Recruiter posts, officer approves", "two windows: the job appears live, students are notified"),
             ("Student applies and is tracked", "tracking id, statechart steps, timeline, accept offer"),
             ("Run all tests", "python -m tests.run_tests")]
    for i, (h_, cmd) in enumerate(steps):
        y = 96 + i * 96
        d.circle(s, M, y + 8, 44, str(i + 1), size=18)
        d.text(s, M + 62, y + 6, 390, 24, h_, size=17, bold=True, color=NAVY, font=HEAD)
        d.text(s, M + 62, y + 36, 400, 40, cmd, size=13, color=INK,
               font=("Courier New" if cmd.startswith("python") else BODY))
    d.picture(s, ev / "ui/TC_UI_40.png", M + 470, 92, W - 2 * M - 470, 350, border="D7DCE4")
    d.text(s, M + 470, 452, W - 2 * M - 470, 40, "Approved job reaches the eligible student's open job board "
                                                 "without a reload", size=12, color=MUTED, align=2)
    d.footer(s, 12)
    d.notes(s, "Demo order: recruiter Ritika posts, officer approves in the second window, Diya applies, recruiter "
               "takes the application to Offer Issued, Diya accepts and becomes placed; then the test run.")

    # 13 ---------------- conclusion ----------------
    s = d.slide(DARK)
    d.text(s, M + 8, 40, W - 2 * M, 50, "Conclusion and next steps", size=34, color=WHITE, font=HEAD, bold=True)
    p4, _ = pf("run4")
    d.text(s, M + 8, 116, 420, 300,
           [("What was achieved", {"bold": True, "color": AMBER, "size": 18, "font": HEAD}),
            ("Two working modules of my SRS with database, validation, statechart and live pages", {"bullet": True}),
            ("Jira space: %d work items, 3 sprints, 2 members, bugs tracked to closure" % sum(counts.values()),
             {"bullet": True}),
            ("%d test cases; 4 bugs found, fixed and retested; %d / %d pass" % (len(final), p4, len(final)),
             {"bullet": True})],
           size=16, color="E6EBF7", space_after=10)
    d.text(s, M + 470, 116, 420, 300,
           [("Next steps", {"bold": True, "color": AMBER, "size": 18, "font": HEAD}),
            ("Login and role-based access (SRS 4.1)", {"bullet": True}),
            ("Interview scheduling and offer letters (SRS 4.6, 4.7)", {"bullet": True}),
            ("E-mail notifications and placement reports", {"bullet": True})],
           size=16, color="E6EBF7", space_after=10)
    d.text(s, M + 8, 400, W - 2 * M, 40, "Thank you · Questions?", size=24, color=WHITE, font=HEAD, bold=True)
    d.notes(s, "Close with the results and the remaining SRS modules.")

    d.save()
    print("saved", OUT, "and", OUT.with_suffix(".pdf"))


if __name__ == "__main__":
    build()
