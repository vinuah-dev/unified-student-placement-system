# SE Lab – Expt-8 (Black Box), Expt-9 (White Box) and PBL

## Submission files
- `Expt8_Black_Box_Testing/A6B2_EXPT-8_Black_Box_Testing_Vineet_Shah.pdf` (and `.docx`)
- `Expt9_White_Box_Testing/A6B2_EXPT-9_White_Box_Testing_Vineet_Shah.pdf` (and `.docx`)
- `PBL_Student_Placement/docs/PBL_Report_Student_Placement_Vineet_Shah.pdf` (and `.docx`)
- `PBL_Student_Placement/docs/PBL_Presentation_Student_Placement_Vineet_Shah.pptx` (and `.pdf`)

To re-export a PDF after editing a `.docx`:

```
powershell -ExecutionPolicy Bypass -File docx_to_pdf.ps1 <file.docx> <file.pdf>
```

## Expt-8: re-running the black-box tests
Expt-8 tests four forms of the USPS website (`PBL_Student_Placement`): Post a Job, Record Job Decision,
Apply for a Job and Job Search - 56 EP/BVA cases in `harness/testcases.js`.

```
cd Expt8_Black_Box_Testing
python run_tests.py --shots      # every case on a fresh server in headless Edge -> evidence/
python build_document.py
```

`harness/case.html?tc=TC_PJ_01` (served by the USPS server) runs one case and leaves the page showing its result.
The earlier Leave Management version is kept in `old_leave_management/`.

## Expt-9: re-running the JUnit suite
JDK 21 (Temurin) is at `C:\Users\vinee\.jdks\jdk-21.0.12.1+1`. JUnit 5.11.4 and JaCoCo 0.8.12 are in `lib/`.

```
$env:JAVA_HOME = "C:\Users\vinee\.jdks\jdk-21.0.12.1+1"
powershell -ExecutionPolicy Bypass -File Expt9_White_Box_Testing\run_tests.ps1
```

Part 1 is `Triangle`; Part 2 is `EligibilityCriteria` (+ `Student`) from the USPS class diagram. This writes
`reports/junit-console-output.txt`, the JUnit XML reports, and the JaCoCo report in `reports/coverage/`.
`python diagrams/draw_cfg.py` redraws the CFGs, and `python build_document.py` rebuilds the report. The earlier
LeaveService version of Part 2 is kept in `old_leave_management/`.

## PBL – Unified Student Placement System (`PBL_Student_Placement/`)
Two modules of the SE lab case study (USPS SRS), Python 3.11 standard library only:
- `app/rules.py` – business rules: posting validation, `EligibilityCriteria`, officer decisions, the Expt-5
  application statechart (`APPLICATION_TRANSITIONS`), tracking ids
- `app/server.py`, `app/db.py`, `app/static/` – REST API, SQLite (SRS 6.1 tables) and the page with student,
  recruiter and placement-officer views; every open page polls `/api/version` and updates itself
- Module 1 = job posting and eligibility verification, Module 2 = job application and tracking

```
cd PBL_Student_Placement
python run.py                       # http://127.0.0.1:8091
python -m tests.run_tests run4      # all 155 test cases (UI cases run in headless Edge)
```

Requirements: `docs/requirements.md`. Bugs: `docs/bugs.json`. Test results of runs 1-4: `results/`. Evidence
screenshots: `evidence/` (`ui/`, `bugs/`, `jira/`). Jira space **USPS** at rbunagpur-team-zhx8jd75.atlassian.net
(keys in `jira/jira_keys.json`, backlog in `jira/backlog.py`). Rebuild the report with `python docs/build_report.py`
and the deck with `python docs/build_presentation.py` (needs PowerPoint).

`PBL_Electricity_Management/` is an earlier PBL on the wrong topic (Smart Classroom) and is not the submission.
