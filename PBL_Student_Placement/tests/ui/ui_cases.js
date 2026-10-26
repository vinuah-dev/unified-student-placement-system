// User-interface test cases. They drive the real web page (loaded in an iframe from the same server) through
// its DOM only: choose values, press the buttons, read what is displayed. The server starts with the demo
// data and its clock fixed at 26-10-2026 10:00. Cases run in this order on the same server, so later cases
// see what earlier ones created (J-5, application USPS-26-0001, ...), as a tester working through the list would.

const M1 = "M1 Job Posting & Eligibility (UI)";
const M2 = "M2 Application & Tracking (UI)";
const STUDENT = (id) => "?role=student&id=" + id;
const RECRUITER = (id) => "?role=recruiter&id=" + id;
const OFFICER = "?role=officer&id=1";
const GOOD_JOB = { title: "Backend Developer", description: "Design REST APIs and database schemas for the analytics platform.",
                   ctc: "9", location: "Pune", deadline: "2026-11-05T17:00", min_cgpa: "7", max_backlogs: "0",
                   branches: ["CSE", "IT"], batch: "" };

function text(doc, id) { return doc.getElementById(id).textContent.trim(); }
function rows(doc, tbodyId) { return [...doc.querySelectorAll("#" + tbodyId + " tr")]; }
async function idle(doc) { await sleep(60); await waitFor(() => doc.body.dataset.busy !== "1"); }

function setValue(doc, id, v) {
  const el = doc.getElementById(id);
  el.value = v;
  el.dispatchEvent(new Event("input"));
  el.dispatchEvent(new Event("change"));
}

async function submit(doc, formId, resultId) {
  const res = doc.getElementById(resultId);
  res.className = "result";
  res.textContent = "";
  doc.querySelector("#" + formId + ' button[type="submit"]').click();
  await waitFor(() => /success|error/.test(res.className));
  await idle(doc);
  return text(doc, resultId);
}

async function search(doc, values) {
  Object.entries(values).forEach(([id, v]) => {
    const el = doc.getElementById(id);
    if (el.type === "checkbox") el.checked = v; else el.value = v;
  });
  doc.getElementById("jobCount").textContent = "…";
  doc.querySelector('#searchForm button[type="submit"]').click();
  await waitFor(() => text(doc, "jobCount") !== "…");
}

function boardRows(doc) { return rows(doc, "jobRows").filter((tr) => tr.dataset.job); }
function boardRow(doc, jobId) { return boardRows(doc).find((tr) => tr.dataset.job === String(jobId)); }
function badges(el) { return [...el.querySelectorAll(".badge")].map((b) => b.textContent).join(", "); }

async function chooseJob(doc, jobId) {
  setValue(doc, "apJob", String(jobId));
  await waitFor(() => text(doc, "apElig") !== "");
}

function selectedText(doc, id) { const s = doc.getElementById(id); return s.options[s.selectedIndex].textContent; }

function fillJob(doc, v) {
  const ids = { title: "jbTitle", description: "jbDescription", ctc: "jbCtc", location: "jbLocation", deadline: "jbDeadline",
                min_cgpa: "jbMinCgpa", max_backlogs: "jbMaxBacklogs", batch: "jbBatch" };
  Object.entries(ids).forEach(([k, id]) => { if (k in v) doc.getElementById(id).value = v[k]; });
  if (v.branches) doc.querySelectorAll('input[name="jbBranch"]').forEach((b) => { b.checked = v.branches.includes(b.value); });
}

function decide(doc, jobId, decision, remarks) {
  doc.getElementById("dcJob").value = jobId ? String(jobId) : "";
  doc.querySelectorAll('input[name="dcDecision"]').forEach((r) => { r.checked = r.value === decision; });
  doc.getElementById("dcRemarks").value = remarks || "";
  return submit(doc, "decisionForm", "dcResult");
}

function appRow(doc, tbodyId, tracking) { return rows(doc, tbodyId).find((tr) => tr.children[0].textContent === tracking); }

async function staffStep(doc, tracking, label) {
  const tr = appRow(doc, "applicantRows", tracking);
  const sel = tr.querySelector("select");
  const opt = [...sel.options].find((o) => o.textContent === label);
  sel.value = opt ? opt.value : "";
  const res = doc.getElementById("stResult");
  res.className = "result";
  tr.querySelector("button").click();
  await waitFor(() => /success|error/.test(res.className));
  await idle(doc);
  return text(doc, "stResult");
}

function nextOptions(doc, tracking) {
  return [...appRow(doc, "applicantRows", tracking).querySelectorAll("select option")].slice(1).map((o) => o.textContent).join(", ");
}

async function myAppButton(doc, tracking, label, answered = true) {
  const btn = [...appRow(doc, "myAppRows", tracking).querySelectorAll("button")].find((b) => b.textContent === label);
  const res = doc.getElementById("appResult");
  res.className = "result";
  btn.click();
  if (label === "Timeline") { await waitFor(() => !doc.getElementById("timelineBox").hidden); return ""; }
  if (!answered) { await sleep(300); return text(doc, "appResult"); }   // confirmation cancelled: nothing is sent
  await waitFor(() => /success|error/.test(res.className));
  await idle(doc);
  return text(doc, "appResult");
}

function timeline(doc) {
  const done = [...doc.querySelectorAll("#stepper li.done")].map((li) => li.textContent).join(", ");
  const cur = doc.querySelector("#stepper li.current, #stepper li.end-bad");
  return "done: " + done + " | current: " + (cur ? cur.textContent : "-") + " | " +
    doc.querySelectorAll("#historyList li").length + " history entries";
}

async function otherUser(method, path, body) {   // a change made by somebody else, in another browser
  const res = await fetch(path, { method: method, headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  return (await res.json()).message;
}

const UI_CASES = [
  // ---------------- Module 1: profile, job board, eligibility ----------------
  { id: "TC_UI_01", module: M1, technique: "Functional (UI)", page: STUDENT(101),
    scenario: "Student profile used for the eligibility check", data: "Acting as student 101",
    expected: "Aarav Kulkarni | Not placed | R23CS101 | CSE | 2023-2027 | 8.60 | 0",
    run: async (doc) => ["pfName", "pfPlaced", "pfRoll", "pfBranch", "pfBatch", "pfCgpa", "pfBacklogs"].map((id) => text(doc, id)).join(" | ") },
  { id: "TC_UI_02", module: M1, technique: "Functional (UI)", page: STUDENT(101),
    scenario: "Job board lists published jobs, open first, with eligibility", data: "Acting as student 101",
    expected: "(3 jobs) J-2: Eligible | J-1: Eligible | J-4: Closed, Not eligible",
    run: async (doc) => text(doc, "jobCount") + " " + boardRows(doc).map((tr) => "J-" + tr.dataset.job + ": " + badges(tr)).join(" | ") },
  { id: "TC_UI_03", module: M1, technique: "Functional (UI) / FR-1.8", page: STUDENT(105),
    scenario: "Ineligible job shows the unmet criteria and Apply is disabled", data: "Student 105 (ME, 2 backlogs, 2022-2026), row J-1",
    expected: "Not eligible: Branch ME is not in the allowed branches (CSE, IT). / Active backlogs 2 exceed the maximum 0. / " +
              "Batch 2022-2026 does not match the required batch 2023-2027. | Apply disabled=true",
    run: async (doc) => {
      const tr = boardRow(doc, 1);
      const reasons = [...tr.querySelectorAll(".reasons li")].map((li) => li.textContent).join(" / ");
      return badges(tr) + ": " + reasons + " | Apply disabled=" + tr.querySelector("button").disabled;
    } },
  { id: "TC_UI_04", module: M1, technique: "EP (UI)", page: STUDENT(101),
    scenario: "Keyword search ignores case", data: "Keyword 'FIRMWARE'",
    expected: "(2 jobs) Embedded Systems Engineer, Firmware Intern",
    run: async (doc) => {
      await search(doc, { fKeyword: "FIRMWARE" });
      return text(doc, "jobCount") + " " + boardRows(doc).map((tr) => tr.querySelector("strong").textContent).join(", ");
    } },
  { id: "TC_UI_05", module: M1, technique: "EP (UI, invalid)", page: STUDENT(101),
    scenario: "Minimum package that is not a number", data: "Min package 'abc'",
    expected: "Minimum package must be a number.",
    run: async (doc) => { await search(doc, { fMinCtc: "abc" }); return text(doc, "searchResult"); } },
  { id: "TC_UI_06", module: M1, technique: "Functional (UI)", page: STUDENT(103),
    scenario: "'Eligible only' filter", data: "Student 103 (ECE, 6.80, 1 backlog), Eligible only ticked",
    expected: "(2 jobs) Embedded Systems Engineer, Firmware Intern",
    run: async (doc) => {
      await search(doc, { fEligible: true });
      return text(doc, "jobCount") + " " + boardRows(doc).map((tr) => tr.querySelector("strong").textContent).join(", ");
    } },

  // ---------------- Module 2: apply form ----------------
  { id: "TC_UI_07", module: M2, technique: "Functional (UI) / FR-2.3", page: STUDENT(101),
    scenario: "Active resume is pre-selected, inactive one is labelled", data: "Student 101 has v2 (active) and v1 (inactive)",
    expected: "selected: Aarav_Resume_v2.pdf | options: Aarav_Resume_v2.pdf, Aarav_Resume_v1.pdf (inactive)",
    run: async (doc) => "selected: " + selectedText(doc, "apResume") + " | options: " +
      [...doc.getElementById("apResume").options].slice(1).map((o) => o.textContent).join(", ") },
  { id: "TC_UI_08", module: M2, technique: "Validation (UI) / UC-1 E1", page: STUDENT(103),
    scenario: "Choosing a job the student is not eligible for", data: "Student 103 chooses J-1",
    expected: "Not eligible: CGPA 6.80 is below the minimum 7.00. Branch ECE is not in the allowed branches (CSE, IT). " +
              "Active backlogs 1 exceed the maximum 0. | Submit disabled=true",
    run: async (doc) => { await chooseJob(doc, 1); return text(doc, "apElig") + " | Submit disabled=" + doc.getElementById("apSubmit").disabled; } },
  { id: "TC_UI_09", module: M2, technique: "Validation (UI) / UC-1 E2", page: STUDENT(103),
    scenario: "Choosing a job whose deadline has passed", data: "Student 103 chooses J-4 (closed)",
    expected: "The application deadline for J-4 has passed. | Submit disabled=true",
    run: async (doc) => { await chooseJob(doc, 4); return text(doc, "apElig") + " | Submit disabled=" + doc.getElementById("apSubmit").disabled; } },
  { id: "TC_UI_10", module: M1, technique: "Functional (UI)", page: STUDENT(101),
    scenario: "Apply button on the board opens the job in the apply form", data: "Click Apply on J-1",
    expected: "J-1 Software Engineer - Nimbus Analytics Pvt Ltd | You meet the eligibility criteria for this job.",
    run: async (doc) => {
      boardRow(doc, 1).querySelector("button").click();
      await waitFor(() => text(doc, "apElig") !== "");
      return selectedText(doc, "apJob") + " | " + text(doc, "apElig");
    } },
  { id: "TC_UI_11", module: M2, technique: "Functional (UI) / UC-1", page: STUDENT(101),
    scenario: "Eligible student submits an application", data: "J-1, resume pre-selected, cover note 'Keen on backend work.'",
    expected: "Application submitted for J-1. Tracking id USPS-26-0001.",
    run: async (doc) => { await chooseJob(doc, 1); setValue(doc, "apNote", "Keen on backend work."); return submit(doc, "applyForm", "apResult"); } },
  { id: "TC_UI_12", module: M2, technique: "Functional (UI) / FR-2.9", page: STUDENT(101),
    scenario: "Application appears in My applications with its timeline", data: "Click Timeline on USPS-26-0001",
    expected: "USPS-26-0001 | J-1 Software Engineer | Applied | done:  | current: Applied | 1 history entries",
    run: async (doc) => {
      const tr = appRow(doc, "myAppRows", "USPS-26-0001");
      await myAppButton(doc, "USPS-26-0001", "Timeline");
      return [tr.children[0].textContent, tr.children[1].textContent, badges(tr)].join(" | ") + " | " + timeline(doc);
    } },
  { id: "TC_UI_13", module: M2, technique: "Functional (UI) / FR-2.11", page: STUDENT(101),
    scenario: "Confirmation notification shown to the student", data: "Notifications of student 101",
    expected: "(1) mentions USPS-26-0001=true",
    run: async (doc) => text(doc, "notifCount") + " mentions USPS-26-0001=" + text(doc, "notifList").includes("USPS-26-0001") },
  { id: "TC_UI_14", module: M2, technique: "Validation (UI) / UC-1 E3", page: STUDENT(101),
    scenario: "Applying to the same job again", data: "Student 101, J-1 again",
    expected: "You have already applied to J-1 (tracking id USPS-26-0001).",
    run: async (doc) => { await chooseJob(doc, 1); return submit(doc, "applyForm", "apResult"); } },
  { id: "TC_UI_15", module: M2, technique: "BVA (UI, max+1)", page: STUDENT(102),
    scenario: "Cover note of 501 characters", data: "Student 102, J-1, cover note 'a'*501",
    expected: "501 / 500 (over) | Cover note cannot exceed 500 characters.",
    run: async (doc) => {
      await chooseJob(doc, 1);
      setValue(doc, "apNote", "a".repeat(501));
      const counter = text(doc, "apCount") + (doc.getElementById("apCount").className === "over" ? " (over)" : "");
      return counter + " | " + await submit(doc, "applyForm", "apResult");
    } },
  { id: "TC_UI_16", module: M2, technique: "EP (UI, invalid)", page: STUDENT(101),
    scenario: "Inactive resume chosen", data: "Student 101, J-2, resume Aarav_Resume_v1.pdf (inactive)",
    expected: "Select one of your active resumes.",
    run: async (doc) => { await chooseJob(doc, 2); doc.getElementById("apResume").value = "2"; return submit(doc, "applyForm", "apResult"); } },
  { id: "TC_UI_17", module: M2, technique: "Functional (UI) / FR-2.10", page: STUDENT(101), confirm: false,
    scenario: "Withdraw asks for confirmation; cancelling keeps the application", data: "Withdraw USPS-26-0001, answer Cancel",
    expected: "confirmation asked=true | status: Applied",
    run: async (doc, win) => {
      await myAppButton(doc, "USPS-26-0001", "Withdraw", false);
      return "confirmation asked=" + (win.__confirms.length === 1) + " | status: " + badges(appRow(doc, "myAppRows", "USPS-26-0001"));
    } },

  // ---------------- Module 2: recruiter workflow ----------------
  { id: "TC_UI_18", module: M2, technique: "Functional (UI) / BR-07", page: RECRUITER(2),
    scenario: "Recruiter of another company does not see the applicant", data: "Recruiter 2 (Orbit Systems)",
    expected: "No applications yet.",
    run: async (doc) => text(doc, "applicantRows") },
  { id: "TC_UI_19", module: M2, technique: "Functional (UI)", page: RECRUITER(1),
    scenario: "Next steps offered for an Applied application follow the statechart", data: "Recruiter 1, USPS-26-0001 (Applied)",
    expected: "Aarav Kulkarni | R23CS101 | Aarav_Resume_v2.pdf | Applied | next: Move to review",
    run: async (doc) => {
      const tr = appRow(doc, "applicantRows", "USPS-26-0001");
      return [1, 2, 4].map((i) => tr.children[i].textContent).join(" | ") + " | " + badges(tr) + " | next: " + nextOptions(doc, "USPS-26-0001");
    } },
  { id: "TC_UI_20", module: M2, technique: "Validation (UI)", page: RECRUITER(1),
    scenario: "Update without choosing a next step", data: "Recruiter 1, USPS-26-0001, -- Select --",
    expected: "Select the next step for USPS-26-0001.",
    run: async (doc) => staffStep(doc, "USPS-26-0001", "") },
  { id: "TC_UI_21", module: M2, technique: "Functional (UI)", page: RECRUITER(1),
    scenario: "Recruiter moves the application to review", data: "Recruiter 1, USPS-26-0001, Move to review",
    expected: "Application USPS-26-0001 is now Under Review. | next: Shortlist, Reject",
    run: async (doc) => (await staffStep(doc, "USPS-26-0001", "Move to review")) + " | next: " + nextOptions(doc, "USPS-26-0001") },
  { id: "TC_UI_22", module: M2, technique: "Functional (UI) / FR-2.9", page: STUDENT(101),
    scenario: "Student timeline after the review started", data: "Student 101, Timeline of USPS-26-0001",
    expected: "done: Applied | current: Under Review | 2 history entries",
    run: async (doc) => { await myAppButton(doc, "USPS-26-0001", "Timeline"); return timeline(doc); } },

  // ---------------- Module 1: posting and approval ----------------
  { id: "TC_UI_23", module: M1, technique: "Validation (UI)", page: RECRUITER(1),
    scenario: "Job form submitted empty", data: "All fields blank",
    expected: "Title must be 3 to 120 characters.",
    run: async (doc) => submit(doc, "jobForm", "jbResult") },
  { id: "TC_UI_24", module: M1, technique: "Validation (UI)", page: RECRUITER(1),
    scenario: "Deadline in the past", data: "Valid job, deadline 20-10-2026 10:00",
    expected: "Deadline must be a future date and time.",
    run: async (doc) => { fillJob(doc, Object.assign({}, GOOD_JOB, { deadline: "2026-10-20T10:00" })); return submit(doc, "jobForm", "jbResult"); } },
  { id: "TC_UI_25", module: M1, technique: "Validation (UI) / UC-2 E1", page: RECRUITER(1),
    scenario: "No eligibility criterion given", data: "Valid job, criteria all blank",
    expected: "At least one eligibility criterion is required.",
    run: async (doc) => {
      fillJob(doc, Object.assign({}, GOOD_JOB, { min_cgpa: "", max_backlogs: "", branches: [], batch: "" }));
      return submit(doc, "jobForm", "jbResult");
    } },
  { id: "TC_UI_26", module: M1, technique: "Functional (UI) / UC-2", page: RECRUITER(1),
    scenario: "Recruiter posts a valid job", data: "Backend Developer, 9 LPA, Pune, 05-11-2026 17:00, CGPA>=7, CSE/IT, 0 backlogs",
    expected: "Job J-5 submitted for approval (status: Pending). | J-5 Backend Developer Pending",
    run: async (doc) => {
      fillJob(doc, GOOD_JOB);
      const msg = await submit(doc, "jobForm", "jbResult");
      const tr = rows(doc, "myJobRows").find((r) => r.dataset.job === "5");
      return msg + " | " + [0, 1, 2].map((i) => tr.children[i].textContent).join(" ");
    } },
  { id: "TC_UI_27", module: M1, technique: "Functional (UI) / FR-09", page: RECRUITER(3),
    scenario: "Recruiter of an unapproved company", data: "Recruiter 3 (Vertex Labs) submits a valid job",
    expected: "note shown=true | Your company is not yet approved by the placement cell.",
    run: async (doc) => {
      const shown = !doc.getElementById("companyNote").hidden;
      fillJob(doc, GOOD_JOB);
      return "note shown=" + shown + " | " + await submit(doc, "jobForm", "jbResult");
    } },
  { id: "TC_UI_28", module: M1, technique: "Functional (UI)", page: OFFICER,
    scenario: "Officer sees the pending postings", data: "Officer 1",
    expected: "J-3 Data Analyst, J-5 Backend Developer",
    run: async (doc) => rows(doc, "pendingRows").map((tr) => tr.children[0].textContent + " " + tr.children[2].textContent).join(", ") },
  { id: "TC_UI_29", module: M1, technique: "Validation (UI)", page: OFFICER,
    scenario: "Decision not chosen", data: "J-3, no decision",
    expected: "Decision must be approve, reject or return.",
    run: async (doc) => decide(doc, 3, "", "") },
  { id: "TC_UI_30", module: M1, technique: "Validation (UI)", page: OFFICER,
    scenario: "Reject without remarks (after confirming)", data: "J-3, Reject, remarks blank",
    expected: "confirmation asked=true | Remarks (5 to 200 characters) are required to reject or return a posting.",
    run: async (doc, win) => { const msg = await decide(doc, 3, "reject", ""); return "confirmation asked=" + (win.__confirms.length === 1) + " | " + msg; } },
  { id: "TC_UI_31", module: M1, technique: "Functional (UI) / UC-2 A1", page: OFFICER,
    scenario: "Officer returns a posting with remarks", data: "J-3, Return, 'Please add the batch criterion.'",
    expected: "Job J-3 returned to the recruiter for changes. | pending: J-5",
    run: async (doc) => (await decide(doc, 3, "return", "Please add the batch criterion.")) + " | pending: " +
      rows(doc, "pendingRows").map((tr) => tr.children[0].textContent).join(", ") },
  { id: "TC_UI_32", module: M1, technique: "Functional (UI) / FR-1.5", page: RECRUITER(1),
    scenario: "Recruiter edits and resubmits the returned posting", data: "J-3, Edit & resubmit, batch 2023-2027",
    expected: "Returned: Please add the batch criterion. | form: Data Analyst, 7.5 | Job J-3 resubmitted for approval (status: Pending).",
    run: async (doc) => {
      const tr = rows(doc, "myJobRows").find((r) => r.dataset.job === "3");
      const before = badges(tr) + ": " + tr.children[4].textContent;
      tr.querySelector("button").click();
      const form = "form: " + doc.getElementById("jbTitle").value + ", " + doc.getElementById("jbMinCgpa").value;
      doc.getElementById("jbBatch").value = "2023-2027";
      return before + " | " + form + " | " + await submit(doc, "jobForm", "jbResult");
    } },
  { id: "TC_UI_33", module: M1, technique: "Functional (UI) / FR-1.4", page: OFFICER,
    scenario: "Officer approves J-5; eligible students are notified", data: "J-5, Approve",
    expected: "Job J-5 published. 2 eligible student(s) notified.",
    run: async (doc) => decide(doc, 5, "approve", "") },
  { id: "TC_UI_34", module: M1, technique: "Functional (UI)", page: STUDENT(102),
    scenario: "Approved job reaches an eligible student", data: "Student 102 (IT, 7.40, 0 backlogs)",
    expected: "J-5: Eligible | notified about J-5=true",
    run: async (doc) => "J-5: " + badges(boardRow(doc, 5)) + " | notified about J-5=" + text(doc, "notifList").includes("J-5") },

  // ---------------- Module 2: offer and placement ----------------
  { id: "TC_UI_35", module: M2, technique: "Functional (UI)", page: RECRUITER(1),
    scenario: "Recruiter takes the application to Offer Issued", data: "Shortlist, Schedule interview, Mark selected, Issue offer letter",
    expected: "Application USPS-26-0001 is now Offer Issued. | status: Offer Issued",
    run: async (doc) => {
      let msg = "";
      for (const step of ["Shortlist", "Schedule interview", "Mark selected", "Issue offer letter"]) msg = await staffStep(doc, "USPS-26-0001", step);
      return msg + " | status: " + badges(appRow(doc, "applicantRows", "USPS-26-0001"));
    } },
  { id: "TC_UI_36", module: M2, technique: "Functional (UI) / BR-01", page: STUDENT(101),
    scenario: "Student accepts the offer and becomes placed", data: "Accept offer on USPS-26-0001, confirm",
    expected: "Application USPS-26-0001 is now Accepted. | profile: Placed",
    run: async (doc) => (await myAppButton(doc, "USPS-26-0001", "Accept offer")) + " | profile: " + text(doc, "pfPlaced") },
  { id: "TC_UI_37", module: M2, technique: "Validation (UI) / BR-05", page: STUDENT(101),
    scenario: "Placed student applies to another job", data: "Student 101 (placed), J-5",
    expected: "You are already placed; the placement policy blocks further applications.",
    run: async (doc) => { await chooseJob(doc, 5); return submit(doc, "applyForm", "apResult"); } },
  { id: "TC_UI_38", module: M2, technique: "Functional (UI) / FR-2.9", page: STUDENT(101),
    scenario: "Timeline after acceptance", data: "Timeline of USPS-26-0001",
    expected: "done: Applied, Under Review, Shortlisted, Interview Scheduled, Selected, Offer Issued | current: Accepted | 7 history entries",
    run: async (doc) => { await myAppButton(doc, "USPS-26-0001", "Timeline"); return timeline(doc); } },

  // ---------------- real-time updates and layout ----------------
  { id: "TC_UI_39", module: M1, technique: "Integration (UI) / FR-2.12", page: OFFICER,
    scenario: "Job posted by a recruiter elsewhere appears on the officer's open page", data: "Recruiter 2 posts 'IoT Support Engineer' from another browser",
    expected: "J-6 IoT Support Engineer appeared without reload | popup: New job posting J-6 (IoT Support Engineer) is waiting for approval.",
    run: async (doc) => {
      await otherUser("POST", "/api/jobs", { recruiter_id: 2, title: "IoT Support Engineer", description: "Install and support IoT gateways at customer sites.",
                                             ctc: 5.5, location: "Nagpur", deadline: "2026-11-28T17:00", min_cgpa: 6.5, allowed_branches: ["CSE", "ECE", "EE"] });
      await waitFor(() => rows(doc, "pendingRows").some((tr) => tr.dataset.job === "6"), 6000);
      await waitFor(() => !doc.getElementById("toast").hidden, 3000);
      return "J-6 IoT Support Engineer appeared without reload | popup: " + doc.getElementById("toast").childNodes[1].textContent;
    } },
  { id: "TC_UI_40", module: M2, technique: "Integration (UI) / FR-2.12", page: STUDENT(103),
    scenario: "Job approved elsewhere appears on the student's open job board", data: "Officer approves J-6 from another browser; student 103 (ECE) is eligible",
    expected: "J-6: Eligible appeared without reload",
    run: async (doc) => {
      await otherUser("POST", "/api/jobs/6/decision", { decision: "approve", actor_role: "officer", actor_id: 1 });
      await waitFor(() => boardRow(doc, 6), 6000);
      return "J-6: " + badges(boardRow(doc, 6)) + " appeared without reload";
    } },
  { id: "TC_UI_41", module: M2, technique: "Functional (UI) / NFR-18", page: STUDENT(101), width: 390,
    scenario: "Page fits a phone screen", data: "Frame width 390 px",
    expected: "horizontal page scroll=false",
    run: async (doc) => "horizontal page scroll=" + (doc.documentElement.scrollWidth > doc.documentElement.clientWidth) },
];
