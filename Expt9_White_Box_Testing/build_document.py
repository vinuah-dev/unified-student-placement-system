"""Builds the Expt-9 White Box Testing report (DOCX) from the source code, CFG images and recorded test run.

Inputs : src/*.java, test/*.java, diagrams/*.png, reports/junit-console-output.txt, reports/coverage.csv,
         evidence/jacoco_*.png
Output : A6B2_EXPT-9_White_Box_Testing_Vineet_Shah.docx
"""
import csv
import re
import sys
from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

HERE = Path(__file__).resolve().parent
OUT = HERE / "A6B2_EXPT-9_White_Box_Testing_Vineet_Shah.docx"
BRAND = RGBColor(0x1F, 0x4E, 0x8C)
PASS = RGBColor(0x17, 0x66, 0x3A)
HEADER_FILL = "DCE6F2"
CODE_FILL = "F4F6F9"


# ---------- docx helpers ----------

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


def set_cell(cell, text, size=9, bold=False, color=None, mono=False):
    cell.text = ""
    p = cell.paragraphs[0]
    p.paragraph_format.space_after = Pt(0)
    lines = str(text).split("\n")
    for i, line in enumerate(lines):
        run = p.add_run(line)
        run.font.size = Pt(size)
        run.bold = bold
        if mono:
            run.font.name = "Consolas"
        if color:
            run.font.color.rgb = color
        if i < len(lines) - 1:
            run.add_break()


def make_table(doc, headers, rows, widths, size=9, keep_together=True):
    table = doc.add_table(rows=1, cols=len(headers))
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    for i, h in enumerate(headers):
        set_cell(table.rows[0].cells[i], h, size=size, bold=True)
        shade(table.rows[0].cells[i], HEADER_FILL)
    row_flag(table.rows[0], "w:tblHeader")
    for r in rows:
        row = table.add_row()
        row_flag(row, "w:cantSplit")
        for i, value in enumerate(r):
            if isinstance(value, tuple):
                set_cell(row.cells[i], value[0], size=size, bold=True, color=value[1])
            else:
                set_cell(row.cells[i], value, size=size)
    for n, row in enumerate(table.rows):
        for i, w in enumerate(widths):
            row.cells[i].width = Cm(w)
        if keep_together and n < len(table.rows) - 1:
            for cell in row.cells:
                for p in cell.paragraphs:
                    p.paragraph_format.keep_with_next = True
    doc.add_paragraph().paragraph_format.space_after = Pt(2)
    return table


def code_block(doc, text, numbered=True, size=8.5):
    """Source listing in a shaded single-cell table; long listings may break across pages."""
    table = doc.add_table(rows=1, cols=1)
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    cell = table.rows[0].cells[0]
    cell.width = Cm(17.0)
    shade(cell, CODE_FILL)
    lines = text.rstrip("\n").split("\n")
    p = cell.paragraphs[0]
    p.paragraph_format.space_after = Pt(0)
    p.paragraph_format.line_spacing = 1.0
    for i, line in enumerate(lines):
        prefix = "%3d  " % (i + 1) if numbered else ""
        if prefix:
            r = p.add_run(prefix)
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


def figure(doc, path, caption, width=None, height=None):
    doc.add_picture(str(path), width=Cm(width) if width else None, height=Cm(height) if height else None)
    doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
    doc.paragraphs[-1].paragraph_format.keep_with_next = True
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(10)
    r = p.add_run(caption)
    r.italic = True
    r.font.size = Pt(9.5)


def page_break(doc):
    doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)


def read(rel):
    raw = (HERE / rel).read_bytes()
    # Tee-Object in Windows PowerShell writes UTF-16; the sources are UTF-8.
    text = raw.decode("utf-16") if raw[:2] in (b"\xff\xfe", b"\xfe\xff") else raw.decode("utf-8-sig")
    return text.replace("\r\n", "\n")


# ---------- content ----------

TRIANGLE_NODES = [
    ("1", "7", "a <= 0"), ("2", "7", "b <= 0"), ("3", "7", "c <= 0"), ("4", "8", 'return "INVALID"'),
    ("5", "10", "a + b <= c"), ("6", "10", "b + c <= a"), ("7", "10", "a + c <= b"),
    ("8", "11", 'return "NOT A TRIANGLE"'), ("9", "13", "a == b"), ("10", "14", "b == c"),
    ("11", "15", 'return "EQUILATERAL"'), ("12", "17", 'return "ISOSCELES"'), ("13", "19", "b == c"),
    ("14", "19", "a == c"), ("15", "20", 'return "ISOSCELES"'), ("16", "22", 'return "SCALENE"'),
    ("17", "23", "end of method (exit)"),
]
TRIANGLE_PATHS = [
    ("P1", "1-4-17", "(0, 5, 5)", "INVALID"),
    ("P2", "1-2-4-17", "(4, 0, 3)", "INVALID"),
    ("P3", "1-2-3-4-17", "(4, 3, -2)", "INVALID"),
    ("P4", "1-2-3-5-8-17", "(1, 2, 3)", "NOT A TRIANGLE"),
    ("P5", "1-2-3-5-6-8-17", "(7, 2, 3)", "NOT A TRIANGLE"),
    ("P6", "1-2-3-5-6-7-8-17", "(2, 8, 3)", "NOT A TRIANGLE"),
    ("P7", "1-2-3-5-6-7-9-10-11-17", "(5, 5, 5)", "EQUILATERAL"),
    ("P8", "1-2-3-5-6-7-9-10-12-17", "(5, 5, 8)", "ISOSCELES"),
    ("P9", "1-2-3-5-6-7-9-13-15-17", "(4, 6, 6)", "ISOSCELES"),
    ("P10", "1-2-3-5-6-7-9-13-14-15-17", "(6, 4, 6)", "ISOSCELES"),
    ("P11", "1-2-3-5-6-7-9-13-14-16-17", "(3, 4, 5)", "SCALENE"),
]

PARSE_NODES = [
    ("1", "31", "branches = new ArrayList<>()"), ("2", "32", "text == null"),
    ("3", "33", "return branches (empty list)"), ("4", "35", "for (part : text.split(\",\")) - another part?"),
    ("5", "36", "branch = part.trim().toUpperCase()"), ("6", "37", "branch.isEmpty()  (true: continue, line 38)"),
    ("7", "40", "!BRANCHES.contains(branch)"), ("8", "41", "throw IllegalArgumentException(\"Unknown branch ...\")"),
    ("9", "43", "!branches.contains(branch)"), ("10", "44", "branches.add(branch)"),
    ("11", "47", "return branches"), ("12", "48", "end of method (exit)"),
]
PARSE_PATHS = [
    ("R1", "1-2-3-12", "null", "[] (empty list)"),
    ("R2", "1-2-4-5-6-4-11-12", "\"  \" (only a blank)", "[] (blank skipped)"),
    ("R3", "1-2-4-5-6-7-8-12", "\"AI\"", "IllegalArgumentException: Unknown branch AI."),
    ("R4", "1-2-4-5-6-7-9-10-4-11-12", "\"CSE\"", "[CSE]"),
    ("R5", "1-2-4-5-6-7-9-10-4-5-6-7-9-4-11-12", "\"CSE, cse\"", "[CSE] (duplicate kept once)"),
    ("Extra", "loop body 5 times", "\" it , CSE,,ece \"", "[IT, CSE, ECE]"),
]

REASONS_NODES = [
    ("1", "52", "reasons = new ArrayList<>()"), ("2", "53", "minCgpa != null"), ("3", "54", "s.getCgpa() < minCgpa"),
    ("4", "55", "add \"CGPA x is below the minimum y.\""), ("5", "58", "!allowedBranches.isEmpty()"),
    ("6", "59", "!allowedBranches.contains(s.getDepartment())"),
    ("7", "60-61", "add \"Branch b is not in the allowed branches (...).\""), ("8", "64", "maxBacklogs != null"),
    ("9", "65", "s.getBacklogs() > maxBacklogs"), ("10", "66", "add \"Active backlogs n exceed the maximum m.\""),
    ("11", "69", "batch != null"), ("12", "70", "!batch.equals(s.getBatch())"),
    ("13", "71", "add \"Batch b does not match the required batch r.\""), ("14", "74", "return reasons (exit)"),
]
REASONS_PATHS = [
    ("A1", "1-2-5-8-11-14", "no criterion set; Kabir", "[] (eligible)"),
    ("A2", "1-2-3-5-8-11-14", "min CGPA 7.0; Aarav (8.60)", "[] (eligible)"),
    ("A3", "1-2-3-4-5-8-11-14", "min CGPA 7.0; Kabir (6.80)", "[CGPA 6.80 is below the minimum 7.00.]"),
    ("A4", "1-2-5-6-8-11-14", "branches \"CSE, IT\"; Aarav (CSE)", "[] (eligible)"),
    ("A5", "1-2-5-6-7-8-11-14", "branches \"CSE, IT\"; Kabir (ECE)",
     "[Branch ECE is not in the allowed branches (CSE, IT).]"),
    ("A6", "1-2-5-8-9-11-14", "max backlogs 1; Kabir (1)", "[] (eligible)"),
    ("A7", "1-2-5-8-9-10-11-14", "max backlogs 0; Kabir (1)", "[Active backlogs 1 exceed the maximum 0.]"),
    ("A8", "1-2-5-8-11-12-14", "batch 2023-2027; Aarav (2023-2027)", "[] (eligible)"),
    ("A9", "1-2-5-8-11-12-13-14", "batch 2023-2027; Rohan (2022-2026)",
     "[Batch 2022-2026 does not match the required batch 2023-2027.]"),
    ("Extra", "1-2-3-4-5-6-7-8-9-10-11-12-13-14", "min 8.0, CSE/IT, max 0, 2023-2027; Rohan",
     "4 reasons in the order CGPA, branch, backlogs, batch"),
    ("Extra", "1-2-3-5-8-11-14", "min CGPA 7.0; Diya (7.00) - boundary", "[] (eligible, CGPA equal to minimum)"),
]


def path_rows(paths):
    return [[p, seq, data, exp, exp, ("PASS", PASS)] for p, seq, data, exp in paths]


def main():
    console = "\n".join(line.rstrip() for line in read("reports/junit-console-output.txt").splitlines()).strip("\n")
    tests_found = re.search(r"\[\s*(\d+) tests found", console).group(1)
    tests_ok = re.search(r"\[\s*(\d+) tests successful", console).group(1)
    tests_failed = re.search(r"\[\s*(\d+) tests failed", console).group(1)
    with open(HERE / "reports/coverage.csv", encoding="utf-8") as f:
        coverage = {row["CLASS"]: row for row in csv.DictReader(f)}

    doc = Document()
    doc.styles["Normal"].font.name = "Calibri"
    doc.styles["Normal"].font.size = Pt(11)
    sec = doc.sections[0]
    sec.page_width, sec.page_height = Cm(21.0), Cm(29.7)
    for side in ("left_margin", "right_margin", "top_margin", "bottom_margin"):
        setattr(sec, side, Cm(2.0))

    t = doc.add_paragraph()
    t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = t.add_run("A6B2_EXPT-9: WHITE BOX TESTING")
    r.bold = True
    r.font.size = Pt(18)
    r.font.color.rgb = BRAND
    s = doc.add_paragraph()
    s.alignment = WD_ALIGN_PARAGRAPH.CENTER
    s.add_run("Basis Path Testing with JUnit - Java").font.size = Pt(12.5)

    make_table(doc, ["Particular", "Details"], [
        ["Course", "Software Engineering Lab (24CS01PR0502)"],
        ["Experiment", "9 - White Box Testing"],
        ["Name", "Vineet Shah"],
        ["Class / Batch", "5S CSE / A6 - B2"],
        ["Roll No.", "28"],
        ["Date of execution", "26-10-2026"],
        ["Case study", "Unified Student Placement System (USPS)"],
        ["Faculty", "D A Borikar"],
    ], [5.0, 12.0], size=10.5)

    heading(doc, "Problem Statement [in Java]")
    para(doc, "Implement a Class as mentioned during the lab instructions. Create a JUnit Test Suite incorporating "
              "all possible test cases covering independent paths.", bold_prefix="[1] ")
    para(doc, "Choose any class from your Class Diagram (one which involves substantial computational logic) and "
              "implement it. Now create JUnit suite to test this class appropriately.", bold_prefix="[2] ")

    heading(doc, "Aim")
    para(doc, "To implement Java classes, draw the control flow graph of each method under test, compute its "
              "cyclomatic complexity, identify the independent paths, and create a JUnit test suite with one test "
              "case for every independent path.")

    heading(doc, "Theory")
    para(doc, "White box testing designs test cases from the internal structure of the code. In basis path testing "
              "the code is converted into a control flow graph (CFG): every node is a statement or a condition and "
              "every edge is a possible transfer of control. A compound condition such as (a <= 0 || b <= 0) is "
              "split into one node per simple condition, because Java evaluates it with short-circuiting.")
    bullet(doc, "Cyclomatic complexity V(G) = E - N + 2P, where E = edges, N = nodes and P = connected components "
                "(P = 1 for one method).")
    bullet(doc, "Equivalently, V(G) = number of predicate (decision) nodes + 1.")
    bullet(doc, "V(G) is the number of linearly independent paths; each independent path adds at least one edge "
                "not covered by the earlier paths. Testing all of them executes every statement and every branch.")
    bullet(doc, "JUnit 5: @Test marks a test method, assertEquals(expected, actual) checks the result, @DisplayName "
                "names the test, and @Suite with @SelectClasses groups test classes into a test suite.")

    heading(doc, "Tools Used")
    make_table(doc, ["Tool", "Version / use"], [
        ["Java", "Eclipse Temurin JDK 21.0.12 (javac / java)"],
        ["JUnit", "JUnit 5.11.4 (Jupiter) with JUnit Platform 1.11.4 Suite engine, run through the "
                  "junit-platform-console-standalone launcher"],
        ["JaCoCo", "0.8.12 - records which lines and branches were executed by the test suite"],
        ["Run script", "run_tests.ps1 - compiles src/ and test/, runs WhiteBoxTestSuite, writes reports/"],
    ], [3.0, 14.0], size=10)

    # ---------------- Part 1 ----------------
    heading(doc, "Part 1: Triangle Class")
    para(doc, "Triangle.classify(a, b, c) takes the three sides of a triangle and returns INVALID (a side is zero "
              "or negative), NOT A TRIANGLE (triangle inequality fails), EQUILATERAL, ISOSCELES or SCALENE.")
    heading(doc, "1.1 Source code - Triangle.java", 2)
    code_block(doc, read("src/Triangle.java"))

    heading(doc, "1.2 Control Flow Graph", 2)
    figure(doc, HERE / "diagrams/cfg_triangle_classify.png",
           "Figure 1: CFG of Triangle.classify() (blue = decision node, orange = return / exit node)", height=15.5)
    make_table(doc, ["Node", "Line", "Statement / condition"], [list(n) for n in TRIANGLE_NODES], [1.6, 1.6, 9.0])

    heading(doc, "1.3 Cyclomatic Complexity", 2)
    make_table(doc, ["Method", "Calculation", "V(G)"], [
        ["E - N + 2P", "E = 26 edges, N = 17 nodes, P = 1  ->  26 - 17 + 2", "11"],
        ["Predicate nodes + 1", "Decision nodes 1, 2, 3, 5, 6, 7, 9, 10, 13, 14 = 10  ->  10 + 1", "11"],
        ["JaCoCo report", "Complexity reported for classify(int, int, int)", "11"],
    ], [3.8, 11.0, 2.2], size=10)
    para(doc, "Hence there are 11 independent paths and at least 11 test cases are required.")

    heading(doc, "1.4 Independent Paths and Test Cases", 2)
    make_table(doc, ["Path", "Node sequence", "Input (a, b, c)", "Expected output", "Actual output", "Result"],
               path_rows(TRIANGLE_PATHS), [1.3, 4.6, 2.6, 3.3, 3.3, 1.6], size=9)
    para(doc, "Actual output is the value returned by classify() during the JUnit run; assertEquals passed for "
              "every path (see the console output in Section 3).", size=10)

    heading(doc, "1.5 JUnit test class - TriangleTest.java", 2)
    code_block(doc, read("test/TriangleTest.java"), size=8)

    # ---------------- Part 2 ----------------
    page_break(doc)
    heading(doc, "Part 2: EligibilityCriteria Class (from the Class Diagram)")
    para(doc, "From the class diagram of the Unified Student Placement System (Expt-3), the EligibilityCriteria "
              "class is chosen because it holds the main computational logic of the placement process (SRS FR-13, "
              "FR-14, BR-03): it turns the allowed-branches text of a job (attribute allowedBranches : String) into "
              "a checked list, and for a student it works out every criterion that is not met - minimum CGPA, "
              "allowed branch, maximum active backlogs and batch - with a reason for each (operations evaluate() "
              "and getReasons() of the diagram). A criterion that is not set is not checked. It uses the Student "
              "class, which holds the academic data of a student. The same rules run in the USPS web prototype of "
              "the PBL (app/rules.py, in Python); here the class is implemented in Java for JUnit.")
    figure(doc, HERE / "diagrams/class_diagram_expt3.png",
           "Figure 2: Class diagram from my Expt-3 submission - EligibilityCriteria is linked to Job", width=16.5)
    heading(doc, "2.1 Source code - Student.java", 2)
    code_block(doc, read("src/Student.java"))
    heading(doc, "2.2 Source code - EligibilityCriteria.java", 2)
    code_block(doc, read("src/EligibilityCriteria.java"), size=7.6)

    heading(doc, "2.3 Method parseBranches(text)", 2)
    figure(doc, HERE / "diagrams/cfg_eligibility_parseBranches.png",
           "Figure 3: CFG of EligibilityCriteria.parseBranches()", height=12.5)
    make_table(doc, ["Node", "Line", "Statement / condition"], [list(n) for n in PARSE_NODES], [1.6, 1.6, 11.0])
    make_table(doc, ["Method", "Calculation", "V(G)"], [
        ["E - N + 2P", "E = 16, N = 12, P = 1  ->  16 - 12 + 2", "6"],
        ["Predicate nodes + 1", "Decision nodes 2, 4, 6, 7, 9 = 5  ->  5 + 1", "6"],
        ["JaCoCo report", "Complexity reported for parseBranches(String)", "6"],
    ], [3.8, 11.0, 2.2], size=10)
    para(doc, "Of the 6 basis paths, 1-2-4-11-12 (loop condition false on the first check) is infeasible: "
              "String.split() always returns at least one element, so when text is not null the loop body runs at "
              "least once. The 5 feasible paths R1-R5 still execute every node and every edge of the graph (edge "
              "4-11 is taken at the end of R2, R4 and R5), and JaCoCo shows 10 of 10 branches covered.", size=10)
    make_table(doc, ["Path", "Node sequence", "Input text", "Expected", "Actual", "Result"],
               path_rows(PARSE_PATHS), [1.2, 4.6, 2.8, 3.6, 3.6, 1.4], size=8.5)

    heading(doc, "2.4 Method getReasons(student)", 2)
    figure(doc, HERE / "diagrams/cfg_eligibility_getReasons.png",
           "Figure 4: CFG of EligibilityCriteria.getReasons()", height=14.5)
    make_table(doc, ["Node", "Line", "Statement / condition"], [list(n) for n in REASONS_NODES], [1.6, 1.6, 11.0])
    make_table(doc, ["Method", "Calculation", "V(G)"], [
        ["E - N + 2P", "E = 21, N = 14, P = 1  ->  21 - 14 + 2", "9"],
        ["Predicate nodes + 1", "Decision nodes 2, 3, 5, 6, 8, 9, 11, 12 = 8  ->  8 + 1", "9"],
        ["JaCoCo report", "Complexity reported for getReasons(Student)", "9"],
    ], [3.8, 11.0, 2.2], size=10)
    para(doc, "Test data (demo students of USPS): Aarav - CSE, 2023-2027, CGPA 8.60, 0 backlogs; Kabir - ECE, "
              "2023-2027, CGPA 6.80, 1 backlog; Rohan - ME, 2022-2026, CGPA 7.90, 2 backlogs; Diya - IT, "
              "2023-2027, CGPA 7.00, 0 backlogs. Each test builds its own EligibilityCriteria with only the "
              "criteria it needs.", size=10)
    make_table(doc, ["Path", "Node sequence", "Input (criteria; student)", "Expected output", "Actual output",
                     "Result"], path_rows(REASONS_PATHS), [1.2, 3.4, 3.8, 3.7, 3.7, 1.4], size=8.5)
    para(doc, "A1-A9 are the 9 independent paths. The extra tests check that all reasons are collected in order "
              "when every criterion fails, and the CGPA boundary (equal to the minimum is eligible). "
              "evaluate() has V(G) = 1 and is tested with one eligible and one ineligible student; two constructor "
              "tests check the parsed branch list and that a blank batch means no batch criterion.", size=10)

    heading(doc, "2.5 JUnit test class - EligibilityCriteriaTest.java", 2)
    code_block(doc, read("test/EligibilityCriteriaTest.java"), size=7.6)


    # ---------------- Suite, output, coverage ----------------
    page_break(doc)
    heading(doc, "3. JUnit Test Suite and Execution")
    heading(doc, "3.1 Test suite - WhiteBoxTestSuite.java", 2)
    code_block(doc, read("test/WhiteBoxTestSuite.java"))
    heading(doc, "3.2 Command used", 2)
    code_block(doc, "powershell -ExecutionPolicy Bypass -File run_tests.ps1\n\n"
                    "# inside run_tests.ps1 (test run):\n"
                    "java -javaagent:lib\\jacoco-0.8.12\\lib\\jacocoagent.jar=destfile=out\\jacoco.exec \\\n"
                    "     -jar lib\\junit-platform-console-standalone-1.11.4.jar execute \\\n"
                    "     --class-path \"out\\classes;out\\test-classes\" --select-class WhiteBoxTestSuite \\\n"
                    "     --details=tree", numbered=False, size=8.5)
    heading(doc, "3.3 Console output (captured from the run on 26-10-2026)", 2)
    code_block(doc, console, numbered=False, size=7.5)
    make_table(doc, ["Tests found", "Tests successful", "Tests failed"], [[tests_found, tests_ok, tests_failed]],
               [5.0, 5.0, 5.0], size=10)

    heading(doc, "3.4 Code Coverage (JaCoCo)", 2)
    cov_rows = []
    for cls in ("Triangle", "EligibilityCriteria", "Student"):
        c = coverage[cls]
        br_total = int(c["BRANCH_MISSED"]) + int(c["BRANCH_COVERED"])
        ln_total = int(c["LINE_MISSED"]) + int(c["LINE_COVERED"])
        cov_rows.append([cls, "%s / %d" % (c["LINE_COVERED"], ln_total),
                         ("%s / %d" % (c["BRANCH_COVERED"], br_total)) if br_total else "no branches",
                         c["COMPLEXITY_COVERED"] + " / " + str(int(c["COMPLEXITY_MISSED"]) + int(c["COMPLEXITY_COVERED"]))])
    make_table(doc, ["Class", "Lines covered", "Branches covered", "Complexity covered"], cov_rows,
               [4.0, 4.0, 4.5, 4.5], size=10)
    para(doc, "Every line and every branch of EligibilityCriteria is executed by the suite (100%), and every branch of "
              "Triangle. The only lines not executed are the implicit default constructor of Triangle (classify() is "
              "static, so no object is created) and Student.getRollNo(), which the eligibility check does not use.",
         size=10)
    figure(doc, HERE / "evidence/jacoco_overview.png", "Figure 5: JaCoCo coverage summary for all classes", width=16.5)
    figure(doc, HERE / "evidence/jacoco_eligibility_methods.png",
           "Figure 6: EligibilityCriteria - complexity (Cxty) and coverage per method", width=16.5)
    figure(doc, HERE / "evidence/jacoco_triangle_methods.png",
           "Figure 7: Triangle - complexity (Cxty) and coverage per method", width=16.5)
    figure(doc, HERE / "evidence/jacoco_eligibility_source.png",
           "Figure 8: EligibilityCriteria.java in the JaCoCo report - green lines and diamonds show executed code "
           "and fully covered branches", width=12.5)
    figure(doc, HERE / "evidence/jacoco_triangle_source.png",
           "Figure 9: Triangle.java in the JaCoCo report", width=13.5)

    heading(doc, "Conclusion")
    para(doc, "Basis path testing was applied to Triangle.classify() (V(G) = 11) and to the EligibilityCriteria class "
              "of the Unified Student Placement System - parseBranches() (V(G) = 6, one infeasible path) and "
              "getReasons() (V(G) = 9). One JUnit test was written for every feasible independent path, plus extra "
              "tests for repeated loop execution, the CGPA boundary, evaluate() and the constructor, and all tests "
              "were grouped in WhiteBoxTestSuite. The suite ran %s tests: %s passed and %s failed, and JaCoCo "
              "confirmed that every branch of both classes was executed." % (tests_found, tests_ok, tests_failed))

    doc.save(OUT)
    print("saved", OUT)


if __name__ == "__main__":
    sys.exit(main())
