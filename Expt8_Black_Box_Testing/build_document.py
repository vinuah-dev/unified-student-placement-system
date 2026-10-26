"""Builds the Expt-8 Black Box Testing test case document (DOCX) from the recorded test run.

Inputs : evidence/test-results.json and evidence/console.txt (written by run_tests.py)
         evidence/screenshots/*.png, evidence/run-summary.png
Output : A6B2_EXPT-8_Black_Box_Testing_Vineet_Shah.docx
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

HERE = Path(__file__).resolve().parent
EVIDENCE = HERE / "evidence"
OUT = HERE / "A6B2_EXPT-8_Black_Box_Testing_Vineet_Shah.docx"

BRAND = RGBColor(0x1F, 0x4E, 0x8C)
HEADER_FILL = "DCE6F2"

FORMS = [
    {
        "key": "Post a Job", "no": 1, "code": "PJ", "view": "Recruiter view", "submit": "Submit for approval",
        "purpose": "A recruiter of an approved company posts a job with its package, deadline and eligibility "
                   "criteria; it is stored as Pending for the placement cell (SRS FR-09, FR-10, FR-13).",
        "precondition": "Recruiter view open as Ritika Menon (Nimbus Analytics, approved) unless stated; data of "
                        "Tables 1-3; server date 26-10-2026 10:00.",
        "fields": [
            ("Job title", "Text box", "3 to 120 characters", "Title must be 3 to 120 characters."),
            ("Description", "Text area", "20 to 2000 characters", "Description must be 20 to 2000 characters."),
            ("Package (LPA)", "Text box", "A number, more than 0 and at most 100",
             "Package (CTC) must be a positive number up to 100 LPA. / Package (CTC) must be a number."),
            ("Location", "Text box", "2 to 80 characters", "Location is required (2 to 80 characters)."),
            ("Application deadline", "Date and time", "Later than the current date and time",
             "Deadline must be a future date and time."),
            ("Minimum CGPA", "Text box", "Optional; 0 to 10", "Minimum CGPA must be between 0 and 10."),
            ("Maximum active backlogs", "Text box", "Optional; whole number 0 to 10",
             "Maximum backlogs must be a whole number from 0 to 10."),
            ("Allowed branches", "Check boxes", "Optional; CSE, IT, ECE, EE, ME, CE", "-"),
            ("Batch", "Text box", "Optional; YYYY-YYYY spanning 4 years (e.g. 2023-2027)",
             "Batch must look like 2023-2027."),
            ("Eligibility criteria (as a group)", "Rule", "At least one of the four criteria",
             "At least one eligibility criterion is required."),
            ("Company of the recruiter", "Rule", "Approved by the placement cell",
             "Your company is not yet approved by the placement cell."),
        ],
        "success": "Job J-<id> submitted for approval (status: Pending).  The job appears in My job postings as "
                   "Pending.",
    },
    {
        "key": "Record Job Decision", "no": 2, "code": "JD", "view": "Placement Officer view",
        "submit": "Record decision",
        "purpose": "The placement officer approves, rejects or returns a pending job posting; on approval the "
                   "eligible students are notified (SRS FR-11, BR-02).",
        "precondition": "Placement Officer view open as Dr. N. Bhagat; J-3 Data Analyst is the pending posting "
                        "(Table 3). A confirmation dialog for Reject is answered OK.",
        "fields": [
            ("Job", "Drop-down", "A pending job posting", "Select a pending job posting."),
            ("Decision", "Radio buttons", "Approve, Reject or Return for changes",
             "Decision must be approve, reject or return."),
            ("Remarks", "Text box", "Reject / Return: 5 to 200 characters; Approve: optional, at most 200",
             "Remarks (5 to 200 characters) are required to reject or return a posting. / "
             "Remarks cannot exceed 200 characters."),
        ],
        "success": "Job J-<id> published. <n> eligible student(s) notified. / Job J-<id> rejected. Recruiter "
                   "notified. / Job J-<id> returned to the recruiter for changes.",
    },
    {
        "key": "Apply for a Job", "no": 3, "code": "AJ", "view": "Student view", "submit": "Submit application",
        "purpose": "A student applies to a published job with one of their resumes and an optional cover note and "
                   "receives a tracking id (SRS FR-15, UC-1, BR-03, BR-04, BR-05).",
        "precondition": "Student view open as the student named in the test case; data of Tables 1-3.",
        "fields": [
            ("Job", "Drop-down", "A published job the student is eligible for, before its deadline",
             "Select a job to apply for. / Not eligible: <unmet criteria> (Submit disabled) / The application "
             "deadline for J-<id> has passed. (Submit disabled) / You are already placed; the placement policy "
             "blocks further applications. / You have already applied to J-<id> (tracking id <tid>)."),
            ("Resume", "Drop-down", "One of the student's active resumes (the active one is pre-selected)",
             "Select one of your active resumes."),
            ("Cover note", "Text area", "Optional; at most 500 characters (counter shown)",
             "Cover note cannot exceed 500 characters."),
        ],
        "success": "Application submitted for J-<id>. Tracking id USPS-26-<nnnn>.",
    },
    {
        "key": "Job Search", "no": 4, "code": "JS", "view": "Student view (Job board)", "submit": "Search",
        "purpose": "A student searches the published jobs by keyword, location and minimum package and can show "
                   "only the jobs they are eligible for (SRS FR-12, FR-14).",
        "precondition": "Student view open as the student named in the test case; data of Tables 1-3.",
        "fields": [
            ("Keyword", "Text box", "Any text; matches job title, description or company, ignoring case", "-"),
            ("Location", "Text box", "Any text; part of the job location, ignoring case", "-"),
            ("Min package (LPA)", "Text box", "Optional; a number", "Minimum package must be a number."),
            ("Eligible only", "Check box", "Ticked or not", "-"),
        ],
        "success": "Job count and the matching jobs, open jobs first: '<n> jobs' followed by the job titles; "
                   "when nothing matches: 'No jobs match the filters.'",
    },
]


# ---------- docx helpers ----------

def shade(cell, fill):
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill)
    tc_pr.append(shd)


def repeat_header(row):
    tr_pr = row._tr.get_or_add_trPr()
    el = OxmlElement("w:tblHeader")
    el.set(qn("w:val"), "true")
    tr_pr.append(el)


def keep_row_together(row):
    tr_pr = row._tr.get_or_add_trPr()
    el = OxmlElement("w:cantSplit")
    el.set(qn("w:val"), "true")
    tr_pr.append(el)


def set_cell(cell, text, size=8.5, bold=False, color=None, align=None):
    cell.text = ""
    p = cell.paragraphs[0]
    p.paragraph_format.space_after = Pt(0)
    p.paragraph_format.space_before = Pt(0)
    if align:
        p.alignment = align
    lines = str(text).split("\n")
    for i, line in enumerate(lines):
        run = p.add_run(line)
        run.font.size = Pt(size)
        run.bold = bold
        if color:
            run.font.color.rgb = color
        if i < len(lines) - 1:
            run.add_break()


def make_table(doc, headers, rows, widths, size=8.5, header_size=None, keep_together=True):
    table = doc.add_table(rows=1, cols=len(headers))
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    for i, h in enumerate(headers):
        c = table.rows[0].cells[i]
        set_cell(c, h, size=header_size or size, bold=True)
        shade(c, HEADER_FILL)
    repeat_header(table.rows[0])
    for r in rows:
        row = table.add_row()
        keep_row_together(row)
        for i, value in enumerate(r):
            if isinstance(value, tuple):
                set_cell(row.cells[i], value[0], size=size, bold=True, color=value[1])
            else:
                set_cell(row.cells[i], value, size=size)
    for n, row in enumerate(table.rows):
        for i, w in enumerate(widths):
            row.cells[i].width = Cm(w)
        # Keep short tables on one page by chaining every row to the next one.
        if keep_together and n < len(table.rows) - 1:
            for cell in row.cells:
                for p in cell.paragraphs:
                    p.paragraph_format.keep_with_next = True
    return table


def heading(doc, text, level=1):
    h = doc.add_heading(text, level=level)
    for run in h.runs:
        run.font.color.rgb = BRAND
    return h


def para(doc, text, bold_prefix=None, size=11, after=6):
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(after)
    if bold_prefix:
        r = p.add_run(bold_prefix)
        r.bold = True
        r.font.size = Pt(size)
    r = p.add_run(text)
    r.font.size = Pt(size)
    return p


def bullet(doc, text, size=11):
    p = doc.add_paragraph(style="List Bullet")
    p.paragraph_format.space_after = Pt(2)
    r = p.add_run(text)
    r.font.size = Pt(size)


def caption(doc, text):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(10)
    r = p.add_run(text)
    r.italic = True
    r.font.size = Pt(9.5)


def new_section(doc, landscape):
    sec = doc.add_section()
    sec.orientation = WD_ORIENT.LANDSCAPE if landscape else WD_ORIENT.PORTRAIT
    long_side, short_side = Cm(29.7), Cm(21.0)
    sec.page_width, sec.page_height = (long_side, short_side) if landscape else (short_side, long_side)
    for side in ("left_margin", "right_margin", "top_margin", "bottom_margin"):
        setattr(sec, side, Cm(1.5))
    return sec


# ---------- content ----------

def inputs_text(inputs):
    return "\n".join("%s: %s" % (k, v) for k, v in inputs)


def main():
    data = json.loads((EVIDENCE / "test-results.json").read_text(encoding="utf-8"))
    results = data["results"]
    run_date = data["executedAt"].split()[0]
    edge_version = next((p.split("/")[1] for p in data["userAgent"].split() if p.startswith("Edg/")), "")

    doc = Document()
    normal = doc.styles["Normal"]
    normal.font.name = "Calibri"
    normal.font.size = Pt(11)
    sec = doc.sections[0]
    sec.page_width, sec.page_height = Cm(21.0), Cm(29.7)
    for side in ("left_margin", "right_margin", "top_margin", "bottom_margin"):
        setattr(sec, side, Cm(2.0))

    # ----- Title and particulars -----
    t = doc.add_paragraph()
    t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = t.add_run("A6B2_EXPT-8: BLACK BOX TESTING")
    r.bold = True
    r.font.size = Pt(18)
    r.font.color.rgb = BRAND
    s = doc.add_paragraph()
    s.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = s.add_run("Test Case Document - Unified Student Placement System (Website)")
    r.font.size = Pt(12.5)

    make_table(doc, ["Particular", "Details"], [
        ["Course", "Software Engineering Lab (24CS01PR0502)"],
        ["Experiment", "8 - Black Box Testing"],
        ["Name", "Vineet Shah"],
        ["Class / Batch", "5S CSE / A6 - B2"],
        ["Roll No.", "28"],
        ["Date of test execution", run_date],
        ["Application under test", "Unified Student Placement System (USPS) - placement portal (4 form interfaces)"],
        ["Faculty", "D A Borikar"],
    ], [5.0, 12.0], size=10.5)

    heading(doc, "Aim")
    para(doc, "To compile a test case document for a website having at least three form interfaces (excluding "
              "Login/Register forms) in a prescribed template, indicating the inputs and the outputs of every test case.")

    heading(doc, "Problem Statement / Application Under Test")
    para(doc, "The Unified Student Placement System (USPS) is the case study of my SE lab work (SRS, use cases, "
              "class, sequence, statechart and activity diagrams). It brings the campus placement process onto one "
              "website: recruiters post jobs with eligibility criteria, the placement officer approves them, the "
              "system checks each student against the criteria automatically, and students apply and track their "
              "applications. The website under test is the USPS prototype built for my SE PBL; its page has a "
              "Student, a Recruiter and a Placement Officer view and four form interfaces, none of which is a Login "
              "or Register form:")
    for f in FORMS:
        bullet(doc, "Form %d - %s (%s): %s" % (f["no"], f["key"], f["view"], f["purpose"]))

    heading(doc, "Black Box Testing - Techniques Used")
    para(doc, "Black box testing checks the software against its specification without looking at the internal code. "
              "The tester supplies inputs through the user interface and compares the output shown with the expected output.")
    bullet(doc, "Equivalence Partitioning (EP): each input is divided into valid and invalid classes, and one "
                "representative value from each class is tested.")
    bullet(doc, "Boundary Value Analysis (BVA): values at and just outside the limits (min-1, min, max, max+1) are "
                "tested, because errors are most likely at the edges of a range.")

    heading(doc, "Test Environment")
    make_table(doc, ["Item", "Details"], [
        ["Website", "Unified Student Placement System (HTML, CSS, JavaScript page; Python 3.11 REST server with "
                    "SQLite), served locally from ../PBL_Student_Placement"],
        ["Browser", "Microsoft Edge %s (headless) on Windows 11" % edge_version],
        ["Execution", "Each test case was executed through the user interface: the page is opened as the user of "
                      "the test case, the input data is entered in the fields, the button is clicked and the message "
                      "displayed on the page is recorded as the actual output (harness/case.html, run_tests.py)."],
        ["Test data", "The server is started afresh with the pre-loaded data of Tables 1-3 for every test case, "
                      "with its date and time fixed at %s so the job deadlines are fixed." % data["serverDate"]],
        ["Executed on", data["executedAt"]],
    ], [4.0, 13.0], size=10)

    heading(doc, "Test Data (Pre-loaded Records)")
    para(doc, "Table 1 - Students and their resumes", size=10, after=2)
    make_table(doc, ["ID", "Name", "Branch", "Batch", "CGPA", "Backlogs", "Placed", "Resumes"], [
        ["101", "Aarav Kulkarni", "CSE", "2023-2027", "8.60", "0", "No", "Aarav_Resume_v2.pdf (active), "
                                                                        "Aarav_Resume_v1.pdf (inactive)"],
        ["102", "Diya Joshi", "IT", "2023-2027", "7.40", "0", "No", "Diya_Resume.pdf"],
        ["103", "Kabir Deshmukh", "ECE", "2023-2027", "6.80", "1", "No", "Kabir_Resume.pdf"],
        ["104", "Meera Patil", "CSE", "2023-2027", "9.10", "0", "Yes", "Meera_Resume.pdf"],
        ["105", "Rohan Wankhede", "ME", "2022-2026", "7.90", "2", "No", "Rohan_Resume.pdf"],
    ], [1.0, 2.8, 1.3, 1.9, 1.2, 1.6, 1.3, 5.9], size=9)
    para(doc, "", after=2)
    para(doc, "Table 2 - Recruiters and companies; placement officer", size=10, after=2)
    make_table(doc, ["Recruiter", "Company", "Company approved"], [
        ["Ritika Menon", "Nimbus Analytics Pvt Ltd", "Yes"],
        ["Sameer Khan", "Orbit Systems", "Yes"],
        ["Anil Rao", "Vertex Labs", "No"],
        ["Placement officer: Dr. N. Bhagat", "-", "-"],
    ], [6.0, 6.0, 5.0], size=9)
    para(doc, "", after=2)
    para(doc, "Table 3 - Jobs", size=10, after=2)
    make_table(doc, ["Job", "Title", "Company", "Package", "Location", "Deadline", "Status", "Eligibility criteria"], [
        ["J-1", "Software Engineer", "Nimbus", "8.5 LPA", "Pune", "25-11-2026 10:00", "Published",
         "CGPA >= 7.0, CSE/IT, 0 backlogs, batch 2023-2027"],
        ["J-2", "Embedded Systems Engineer", "Orbit", "6.0 LPA", "Bengaluru", "15-11-2026 10:00", "Published",
         "CGPA >= 6.5, CSE/ECE/EE, <= 1 backlog"],
        ["J-3", "Data Analyst", "Nimbus", "7.0 LPA", "Hyderabad", "20-11-2026 10:00", "Pending",
         "CGPA >= 7.5, 0 backlogs"],
        ["J-4", "Firmware Intern", "Orbit", "3.6 LPA", "Nagpur", "25-10-2026 10:00 (passed)", "Published",
         "CGPA >= 6.0, ECE/EE"],
    ], [1.0, 2.6, 1.5, 1.5, 1.7, 2.4, 1.7, 4.6], size=8.5)

    # ----- Form specifications (inputs and outputs) -----
    new_section(doc, landscape=True)
    heading(doc, "Form Interfaces - Inputs and Outputs")
    for f in FORMS:
        heading(doc, "Form %d: %s  (%s)" % (f["no"], f["key"], f["view"]), level=2)
        make_table(doc, ["Input field", "Control", "Valid input", "Output (message) for invalid input"],
                   [list(x) for x in f["fields"]], [4.4, 2.8, 7.2, 12.3], size=9)
        para(doc, f["success"], bold_prefix="Output for valid input: ", size=9.5, after=10)

    # ----- Test case document -----
    new_section(doc, landscape=True)
    heading(doc, "Test Case Document")
    para(doc, "Template: TC ID | Test scenario (technique) | Pre-condition | Test steps | Input (test data) | "
              "Expected output | Actual output | Status. Dates are shown as dd-mm-yyyy; the test cases were "
              "executed on %s." % run_date, size=10)
    widths = [1.8, 3.4, 3.0, 2.9, 4.8, 4.4, 4.4, 1.5]
    for f in FORMS:
        heading(doc, "Form %d: %s" % (f["no"], f["key"]), level=2)
        rows = []
        for r in (x for x in results if x["form"] == f["key"]):
            steps = "1. Open the %s as %s\n2. Enter the input data\n3. Click '%s'" % (
                f["view"], r["user"].split(" (")[0], f["submit"])
            status_color = RGBColor(0x17, 0x66, 0x3A) if r["status"] == "PASS" else RGBColor(0xA3, 0x20, 0x20)
            rows.append([r["id"], "%s\n[%s]" % (r["scenario"], r["technique"]), f["precondition"], steps,
                         inputs_text(r["inputs"]), r["expected"], r["actual"], (r["status"], status_color)])
        make_table(doc, ["TC ID", "Test scenario (technique)", "Pre-condition", "Test steps", "Input (test data)",
                         "Expected output", "Actual output", "Status"], rows, widths, size=8, keep_together=False)
        para(doc, "", after=4)

    heading(doc, "Test Execution Summary")
    summary_rows = []
    for f in FORMS:
        rs = [x for x in results if x["form"] == f["key"]]
        passed = sum(1 for x in rs if x["status"] == "PASS")
        ep = sum(1 for x in rs if x["technique"].startswith("EP"))
        summary_rows.append(["Form %d: %s" % (f["no"], f["key"]), str(len(rs)), "%d / %d" % (ep, len(rs) - ep),
                             str(passed), str(len(rs) - passed)])
    total_pass = sum(1 for x in results if x["status"] == "PASS")
    total_ep = sum(1 for x in results if x["technique"].startswith("EP"))
    summary_rows.append([("Total", None), (str(len(results)), None),
                         ("%d / %d" % (total_ep, len(results) - total_ep), None), (str(total_pass), None),
                         (str(len(results) - total_pass), None)])
    make_table(doc, ["Form", "Test cases executed", "EP / BVA cases", "Passed", "Failed"], summary_rows,
               [8.0, 4.0, 4.0, 3.0, 3.0], size=10)

    # ----- Screenshots -----
    new_section(doc, landscape=False)
    heading(doc, "Execution Screenshots")
    para(doc, "Screenshots were captured in Microsoft Edge after each test case was executed. The dark bar at the top "
              "is added by the test harness and shows the test case ID, the time of execution, the actual output "
              "and the result.", size=10)
    shots = [
        ("TC_PJ_01", "Form 1 - valid job posting submitted for approval"),
        ("TC_PJ_05", "Form 1 - job title of 121 characters rejected (BVA, max + 1)"),
        ("TC_PJ_21", "Form 1 - recruiter of a company that is not approved"),
        ("TC_JD_01", "Form 2 - pending job J-3 approved, eligible student notified"),
        ("TC_JD_07", "Form 2 - reject with 4-character remarks refused (BVA, min - 1)"),
        ("TC_AJ_01", "Form 3 - application submitted with a tracking id"),
        ("TC_AJ_04", "Form 3 - ineligible student: unmet criteria listed, Submit disabled"),
        ("TC_AJ_10", "Form 3 - cover note of 501 characters refused (BVA, max + 1)"),
        ("TC_JS_03", "Form 4 - keyword search on the company name"),
        ("TC_JS_09", "Form 4 - minimum package typed in words"),
    ]
    for i, (tc, text) in enumerate(shots):
        doc.add_picture(str(EVIDENCE / "screenshots" / (tc + ".png")), width=Cm(13.6))
        doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
        doc.paragraphs[-1].paragraph_format.keep_with_next = True
        caption(doc, "Figure %d: %s - %s" % (i + 1, tc, text))
    doc.paragraphs[-1].add_run().add_break(WD_BREAK.PAGE)
    doc.add_picture(str(EVIDENCE / "run-summary.png"), height=Cm(22.0))
    doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
    doc.paragraphs[-1].paragraph_format.keep_with_next = True
    caption(doc, "Figure %d: Complete test run (run_tests.py) - %d test cases executed, %d passed, %d failed"
            % (len(shots) + 1, len(results), total_pass, len(results) - total_pass))

    heading(doc, "Conclusion")
    para(doc, "A test case document was prepared for four form interfaces of the Unified Student Placement System "
              "website: Post a Job, Record Job Decision, Apply for a Job and Job Search. Using Equivalence "
              "Partitioning and Boundary Value Analysis, %d test cases were designed with their inputs and expected "
              "outputs. All test cases were executed through the user interface and the actual outputs were "
              "recorded: %d passed and %d failed." % (len(results), total_pass, len(results) - total_pass))

    doc.save(OUT)
    print("saved", OUT)


if __name__ == "__main__":
    sys.exit(main())
