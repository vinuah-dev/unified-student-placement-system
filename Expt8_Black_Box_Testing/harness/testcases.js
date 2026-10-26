// Black box test cases for four form interfaces of the Unified Student Placement System (USPS) website.
// Every case starts from the pre-loaded data: the server is restarted for each case with its clock fixed at
// 26-10-2026 10:00, so the deadlines of the demo jobs are fixed. Expected outputs come from the form
// specifications (inputs and outputs) in the test case document, not from running the code.

const F1 = "Post a Job", F2 = "Record Job Decision", F3 = "Apply for a Job", F4 = "Job Search";
const RECRUITER = (id) => "?role=recruiter&id=" + id;
const OFFICER = "?role=officer&id=1";
const STUDENT = (id) => "?role=student&id=" + id;

// ----- Form 1: Post a Job -----
const JOB = { title: "Backend Developer", description: "Design REST APIs and database schemas for the analytics platform.",
              ctc: "9", location: "Pune", deadline: "2026-11-05T17:00", min_cgpa: "7", max_backlogs: "0",
              branches: ["CSE", "IT"], batch: "" };
const JOB_IDS = { title: "jbTitle", description: "jbDescription", ctc: "jbCtc", location: "jbLocation",
                  deadline: "jbDeadline", min_cgpa: "jbMinCgpa", max_backlogs: "jbMaxBacklogs", batch: "jbBatch" };

function postJob(changes) {
  return async (doc) => {
    const v = Object.assign({}, JOB, changes);
    Object.entries(JOB_IDS).forEach(([k, id]) => { doc.getElementById(id).value = v[k]; });
    doc.querySelectorAll('input[name="jbBranch"]').forEach((b) => { b.checked = v.branches.includes(b.value); });
    return submit(doc, "jobForm", "jbResult");
  };
}

function job(id, technique, scenario, inputs, expected, changes, recruiter) {
  return { id, form: F1, technique, scenario, page: RECRUITER(recruiter || 1),
           user: recruiter === 3 ? "Recruiter Anil Rao - Vertex Labs (company not approved)"
                                 : "Recruiter Ritika Menon - Nimbus Analytics (approved)",
           inputs, expected, run: postJob(changes || {}) };
}

const POSTED = "Job J-5 submitted for approval (status: Pending).";
const OTHER = ["Other fields", "as in TC_PJ_01"];

// ----- Form 2: Record Job Decision -----
function decide(jobValue, decision, remarks) {
  return async (doc) => {
    doc.getElementById("dcJob").value = jobValue;
    doc.querySelectorAll('input[name="dcDecision"]').forEach((r) => { r.checked = r.value === decision; });
    doc.getElementById("dcRemarks").value = remarks;
    return submit(doc, "decisionForm", "dcResult");
  };
}

function decision(id, technique, scenario, inputs, expected, jobValue, choice, remarks) {
  return { id, form: F2, technique, scenario, page: OFFICER, user: "Placement Officer Dr. N. Bhagat",
           inputs, expected, run: decide(jobValue, choice, remarks) };
}

// ----- Form 3: Apply for a Job -----
async function chooseJob(doc, jobId) {
  setValue(doc, "apJob", String(jobId));
  await waitFor(() => text(doc, "apElig") !== "");
}

function apply(jobId, resume, note, twice) {
  return async (doc) => {
    if (jobId) await chooseJob(doc, jobId);
    if (resume !== undefined) doc.getElementById("apResume").value = resume;
    setValue(doc, "apNote", note);
    if (doc.getElementById("apSubmit").disabled) {
      return text(doc, "apElig") + " | Submit application button disabled";
    }
    let out = await submit(doc, "applyForm", "apResult");
    if (twice) out = await submit(doc, "applyForm", "apResult");
    return out;
  };
}

const STUDENTS = { 101: "Aarav Kulkarni (CSE, 2023-2027, CGPA 8.60, 0 backlogs)",
                   102: "Diya Joshi (IT, 2023-2027, CGPA 7.40, 0 backlogs)",
                   103: "Kabir Deshmukh (ECE, 2023-2027, CGPA 6.80, 1 backlog)",
                   104: "Meera Patil (CSE, CGPA 9.10, already placed)",
                   105: "Rohan Wankhede (ME, 2022-2026, CGPA 7.90, 2 backlogs)" };

function application(id, technique, scenario, student, inputs, expected, run) {
  return { id, form: F3, technique, scenario, page: STUDENT(student), user: "Student " + STUDENTS[student],
           inputs, expected, run };
}

// ----- Form 4: Job Search -----
function search(values) {
  return async (doc) => {
    const ids = { keyword: "fKeyword", location: "fLocation", min: "fMinCtc" };
    Object.entries(ids).forEach(([k, id]) => { doc.getElementById(id).value = values[k] || ""; });
    doc.getElementById("fEligible").checked = !!values.eligible;
    doc.getElementById("jobCount").textContent = "…";
    doc.querySelector('#searchForm button[type="submit"]').click();
    await waitFor(() => text(doc, "jobCount") !== "…");
    if (/error/.test(doc.getElementById("searchResult").className)) return text(doc, "searchResult");
    const titles = [...doc.querySelectorAll("#jobRows tr[data-job] strong")].map((s) => s.textContent);
    const count = text(doc, "jobCount").replace(/[()]/g, "");
    return count + ": " + (titles.length ? titles.join(", ") : text(doc, "jobRows"));
  };
}

function find(id, technique, scenario, student, inputs, expected, values) {
  return { id, form: F4, technique, scenario, page: STUDENT(student), user: "Student " + STUDENTS[student],
           inputs, expected, run: search(values) };
}

const ALL3 = "3 jobs: Embedded Systems Engineer, Software Engineer, Firmware Intern";
const NONE = "0 jobs: No jobs match the filters.";
const A120 = "A".repeat(120), A121 = "A".repeat(121);
const R200 = "R".repeat(200), R201 = "R".repeat(201);

const TEST_CASES = [
  // ================= Form 1: Post a Job =================
  job("TC_PJ_01", "EP (valid class)", "All fields valid", [["Job title", "Backend Developer"],
      ["Description", "Design REST APIs and database schemas for the analytics platform. (65 chars)"],
      ["Package (LPA)", "9"], ["Location", "Pune"], ["Deadline", "05-11-2026 17:00"], ["Minimum CGPA", "7"],
      ["Maximum backlogs", "0"], ["Branches", "CSE, IT"], ["Batch", "(blank)"]], POSTED),
  job("TC_PJ_02", "BVA (min - 1)", "Job title of 2 characters", [["Job title", "QA (2 chars)"], OTHER],
      "Title must be 3 to 120 characters.", { title: "QA" }),
  job("TC_PJ_03", "BVA (min)", "Job title of 3 characters", [["Job title", "SDE (3 chars)"], OTHER], POSTED,
      { title: "SDE" }),
  job("TC_PJ_04", "BVA (max)", "Job title of 120 characters", [["Job title", "'A' x 120"], OTHER], POSTED,
      { title: A120 }),
  job("TC_PJ_05", "BVA (max + 1)", "Job title of 121 characters", [["Job title", "'A' x 121"], OTHER],
      "Title must be 3 to 120 characters.", { title: A121 }),
  job("TC_PJ_06", "BVA (min - 1)", "Description of 19 characters", [["Description", "Write code for APIs (19 chars)"], OTHER],
      "Description must be 20 to 2000 characters.", { description: "Write code for APIs" }),
  job("TC_PJ_07", "BVA (min)", "Description of 20 characters", [["Description", "Write code for APIs. (20 chars)"], OTHER],
      POSTED, { description: "Write code for APIs." }),
  job("TC_PJ_08", "BVA (min - 1)", "Package of 0 LPA", [["Package (LPA)", "0"], OTHER],
      "Package (CTC) must be a positive number up to 100 LPA.", { ctc: "0" }),
  job("TC_PJ_09", "BVA (min)", "Package just above 0", [["Package (LPA)", "0.1"], OTHER], POSTED, { ctc: "0.1" }),
  job("TC_PJ_10", "BVA (max)", "Package of 100 LPA", [["Package (LPA)", "100"], OTHER], POSTED, { ctc: "100" }),
  job("TC_PJ_11", "BVA (max + 0.5)", "Package above 100 LPA", [["Package (LPA)", "100.5"], OTHER],
      "Package (CTC) must be a positive number up to 100 LPA.", { ctc: "100.5" }),
  job("TC_PJ_12", "EP (invalid class)", "Package typed in words", [["Package (LPA)", "nine"], OTHER],
      "Package (CTC) must be a number.", { ctc: "nine" }),
  job("TC_PJ_13", "EP (invalid class)", "Location left blank", [["Location", "(blank)"], OTHER],
      "Location is required (2 to 80 characters).", { location: "" }),
  job("TC_PJ_14", "BVA (equal to now)", "Deadline equal to the current date and time",
      [["Deadline", "26-10-2026 10:00 (= now)"], OTHER], "Deadline must be a future date and time.",
      { deadline: "2026-10-26T10:00" }),
  job("TC_PJ_15", "BVA (now + 1 min)", "Deadline one minute in the future", [["Deadline", "26-10-2026 10:01"], OTHER],
      POSTED, { deadline: "2026-10-26T10:01" }),
  job("TC_PJ_16", "EP (invalid class)", "Deadline not entered", [["Deadline", "(blank)"], OTHER],
      "Deadline must be a future date and time.", { deadline: "" }),
  job("TC_PJ_17", "BVA (max + 0.01)", "Minimum CGPA above 10", [["Minimum CGPA", "10.01"], OTHER],
      "Minimum CGPA must be between 0 and 10.", { min_cgpa: "10.01" }),
  job("TC_PJ_18", "BVA (max + 1)", "Maximum backlogs above 10", [["Maximum backlogs", "11"], OTHER],
      "Maximum backlogs must be a whole number from 0 to 10.", { max_backlogs: "11" }),
  job("TC_PJ_19", "EP (invalid class)", "Batch that does not span 4 years", [["Batch", "2023-2026"], OTHER],
      "Batch must look like 2023-2027.", { batch: "2023-2026" }),
  job("TC_PJ_20", "EP (invalid class)", "No eligibility criterion given",
      [["Minimum CGPA, Maximum backlogs, Batch", "(blank)"], ["Branches", "none ticked"], OTHER],
      "At least one eligibility criterion is required.", { min_cgpa: "", max_backlogs: "", branches: [], batch: "" }),
  job("TC_PJ_21", "EP (invalid class)", "Recruiter of a company not approved by the placement cell",
      [["All fields", "as in TC_PJ_01"]], "Your company is not yet approved by the placement cell.", {}, 3),

  // ================= Form 2: Record Job Decision =================
  decision("TC_JD_01", "EP (valid class)", "Approve the pending posting without remarks",
           [["Job", "J-3 Data Analyst - Nimbus Analytics"], ["Decision", "Approve"], ["Remarks", "(blank)"]],
           "Job J-3 published. 1 eligible student(s) notified.", "3", "approve", ""),
  decision("TC_JD_02", "EP (valid class)", "Reject with remarks",
           [["Job", "J-3"], ["Decision", "Reject"], ["Remarks", "Package below the campus minimum. (33 chars)"]],
           "Job J-3 rejected. Recruiter notified.", "3", "reject", "Package below the campus minimum."),
  decision("TC_JD_03", "EP (valid class)", "Return for changes with remarks",
           [["Job", "J-3"], ["Decision", "Return for changes"], ["Remarks", "Please add the batch criterion. (31 chars)"]],
           "Job J-3 returned to the recruiter for changes.", "3", "return", "Please add the batch criterion."),
  decision("TC_JD_04", "EP (invalid class)", "No job selected",
           [["Job", "-- Select --"], ["Decision", "Approve"], ["Remarks", "(blank)"]],
           "Select a pending job posting.", "", "approve", ""),
  decision("TC_JD_05", "EP (invalid class)", "No decision selected",
           [["Job", "J-3"], ["Decision", "(none)"], ["Remarks", "(blank)"]],
           "Decision must be approve, reject or return.", "3", "", ""),
  decision("TC_JD_06", "EP (invalid class)", "Reject without remarks",
           [["Job", "J-3"], ["Decision", "Reject"], ["Remarks", "(blank)"]],
           "Remarks (5 to 200 characters) are required to reject or return a posting.", "3", "reject", ""),
  decision("TC_JD_07", "BVA (min - 1)", "Reject with remarks of 4 characters",
           [["Job", "J-3"], ["Decision", "Reject"], ["Remarks", "Late (4 chars)"]],
           "Remarks (5 to 200 characters) are required to reject or return a posting.", "3", "reject", "Late"),
  decision("TC_JD_08", "BVA (min)", "Reject with remarks of 5 characters",
           [["Job", "J-3"], ["Decision", "Reject"], ["Remarks", "Spam. (5 chars)"]],
           "Job J-3 rejected. Recruiter notified.", "3", "reject", "Spam."),
  decision("TC_JD_09", "BVA (max)", "Return with remarks of 200 characters",
           [["Job", "J-3"], ["Decision", "Return for changes"], ["Remarks", "'R' x 200"]],
           "Job J-3 returned to the recruiter for changes.", "3", "return", R200),
  decision("TC_JD_10", "BVA (max + 1)", "Return with remarks of 201 characters",
           [["Job", "J-3"], ["Decision", "Return for changes"], ["Remarks", "'R' x 201"]],
           "Remarks (5 to 200 characters) are required to reject or return a posting.", "3", "return", R201),
  decision("TC_JD_11", "BVA (max)", "Approve with remarks of 200 characters",
           [["Job", "J-3"], ["Decision", "Approve"], ["Remarks", "'R' x 200"]],
           "Job J-3 published. 1 eligible student(s) notified.", "3", "approve", R200),
  decision("TC_JD_12", "BVA (max + 1)", "Approve with remarks of 201 characters",
           [["Job", "J-3"], ["Decision", "Approve"], ["Remarks", "'R' x 201"]],
           "Remarks cannot exceed 200 characters.", "3", "approve", R201),

  // ================= Form 3: Apply for a Job =================
  application("TC_AJ_01", "EP (valid class)", "Eligible student applies with the pre-selected active resume", 101,
              [["Job", "J-1 Software Engineer - Nimbus Analytics"], ["Resume", "Aarav_Resume_v2.pdf (pre-selected)"],
               ["Cover note", "Keen on backend work. (21 chars)"]],
              "Application submitted for J-1. Tracking id USPS-26-0001.", apply(1, undefined, "Keen on backend work.")),
  application("TC_AJ_02", "EP (valid class)", "Cover note left blank (optional)", 102,
              [["Job", "J-1"], ["Resume", "Diya_Resume.pdf (pre-selected)"], ["Cover note", "(blank)"]],
              "Application submitted for J-1. Tracking id USPS-26-0001.", apply(1, undefined, "")),
  application("TC_AJ_03", "EP (invalid class)", "No job selected", 101,
              [["Job", "-- Select a job --"], ["Resume", "Aarav_Resume_v2.pdf"], ["Cover note", "(blank)"]],
              "Select a job to apply for.", apply(0, undefined, "")),
  application("TC_AJ_04", "EP (invalid class)", "Student not eligible for the job", 103,
              [["Job", "J-1 Software Engineer (CGPA >= 7.0, CSE/IT, 0 backlogs)"], ["Resume", "Kabir_Resume.pdf"],
               ["Cover note", "(blank)"]],
              "Not eligible: CGPA 6.80 is below the minimum 7.00. Branch ECE is not in the allowed branches (CSE, IT). " +
              "Active backlogs 1 exceed the maximum 0. | Submit application button disabled", apply(1, undefined, "")),
  application("TC_AJ_05", "EP (invalid class)", "Job whose deadline has passed", 103,
              [["Job", "J-4 Firmware Intern (deadline 25-10-2026 10:00)"], ["Resume", "Kabir_Resume.pdf"],
               ["Cover note", "(blank)"]],
              "The application deadline for J-4 has passed. | Submit application button disabled",
              apply(4, undefined, "")),
  application("TC_AJ_06", "EP (invalid class)", "Student who is already placed", 104,
              [["Job", "J-1"], ["Resume", "Meera_Resume.pdf"], ["Cover note", "(blank)"]],
              "You are already placed; the placement policy blocks further applications.", apply(1, undefined, "")),
  application("TC_AJ_07", "EP (invalid class)", "Inactive resume selected", 101,
              [["Job", "J-1"], ["Resume", "Aarav_Resume_v1.pdf (inactive)"], ["Cover note", "(blank)"]],
              "Select one of your active resumes.", apply(1, "2", "")),
  application("TC_AJ_08", "EP (invalid class)", "No resume selected", 101,
              [["Job", "J-1"], ["Resume", "-- Select a resume --"], ["Cover note", "(blank)"]],
              "Select one of your active resumes.", apply(1, "", "")),
  application("TC_AJ_09", "BVA (max)", "Cover note of 500 characters", 101,
              [["Job", "J-1"], ["Resume", "Aarav_Resume_v2.pdf"], ["Cover note", "'a' x 500"]],
              "Application submitted for J-1. Tracking id USPS-26-0001.", apply(1, undefined, "a".repeat(500))),
  application("TC_AJ_10", "BVA (max + 1)", "Cover note of 501 characters", 101,
              [["Job", "J-1"], ["Resume", "Aarav_Resume_v2.pdf"], ["Cover note", "'a' x 501"]],
              "Cover note cannot exceed 500 characters.", apply(1, undefined, "a".repeat(501))),
  application("TC_AJ_11", "EP (invalid class)", "Applying to the same job a second time", 101,
              [["Job", "J-1 (Submit pressed twice)"], ["Resume", "Aarav_Resume_v2.pdf"], ["Cover note", "(blank)"]],
              "You have already applied to J-1 (tracking id USPS-26-0001).", apply(1, undefined, "", true)),

  // ================= Form 4: Job Search =================
  find("TC_JS_01", "EP (valid class)", "No filter: all published jobs, open ones first", 101,
       [["Keyword, Location, Min package", "(blank)"], ["Eligible only", "unticked"]], ALL3, {}),
  find("TC_JS_02", "EP (valid class)", "Keyword in the job title", 101, [["Keyword", "software"]],
       "1 job: Software Engineer", { keyword: "software" }),
  find("TC_JS_03", "EP (valid class)", "Keyword in the company name, upper case", 101, [["Keyword", "ORBIT"]],
       "2 jobs: Embedded Systems Engineer, Firmware Intern", { keyword: "ORBIT" }),
  find("TC_JS_04", "EP (invalid class)", "Keyword that matches no job", 101, [["Keyword", "doctor"]], NONE,
       { keyword: "doctor" }),
  find("TC_JS_05", "EP (valid class)", "Location filter", 101, [["Location", "pune"]], "1 job: Software Engineer",
       { location: "pune" }),
  find("TC_JS_06", "BVA (equal)", "Minimum package equal to a job's package (6 LPA)", 101, [["Min package", "6"]],
       "2 jobs: Embedded Systems Engineer, Software Engineer", { min: "6" }),
  find("TC_JS_07", "BVA (equal + 0.1)", "Minimum package just above 6 LPA", 101, [["Min package", "6.1"]],
       "1 job: Software Engineer", { min: "6.1" }),
  find("TC_JS_08", "BVA (max + 0.1)", "Minimum package above the highest package (8.5 LPA)", 101,
       [["Min package", "8.6"]], NONE, { min: "8.6" }),
  find("TC_JS_09", "EP (invalid class)", "Minimum package typed in words", 101, [["Min package", "abc"]],
       "Minimum package must be a number.", { min: "abc" }),
  find("TC_JS_10", "EP (valid class)", "Eligible only - ECE student", 103, [["Eligible only", "ticked"]],
       "2 jobs: Embedded Systems Engineer, Firmware Intern", { eligible: true }),
  find("TC_JS_11", "EP (valid class)", "Eligible only - student eligible for no job", 105,
       [["Eligible only", "ticked"]], NONE, { eligible: true }),
  find("TC_JS_12", "EP (valid class)", "Keyword and location together", 101,
       [["Keyword", "engineer"], ["Location", "Bengaluru"]], "1 job: Embedded Systems Engineer",
       { keyword: "engineer", location: "Bengaluru" }),
];
