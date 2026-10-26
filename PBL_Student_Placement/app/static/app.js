// Placement portal: role switcher plus the student, recruiter and officer screens of the two PBL modules.
(function () {
  const $ = (id) => document.getElementById(id);
  const params = new URLSearchParams(location.search);   // e.g. /?role=recruiter&id=1
  let meta = null;
  let role = ["student", "recruiter", "officer"].includes(params.get("role")) ? params.get("role") : "student";
  let actorId = params.get("id");
  let timelineApp = null;
  let page = 1;
  let boardJobs = [];     // every published job with this student's eligibility (apply form)
  let editingJob = null;  // job id while a returned posting is being edited
  let seenVersion = null; // server data version the page was last drawn from
  const lastNotif = {};   // newest notification id seen per acting user
  let toastTimer = null;

  const EVENT_LABELS = {
    under_review: "Move to review", shortlist: "Shortlist", schedule_interview: "Schedule interview",
    reschedule: "Reschedule interview", interview_result: "Mark selected", offer_letter: "Issue offer letter",
    reject: "Reject", withdraw: "Withdraw", accept_offer: "Accept offer", reject_offer: "Decline offer"
  };
  const PATH = ["Applied", "Under Review", "Shortlisted", "Interview Scheduled", "Selected", "Offer Issued", "Accepted"];

  async function api(method, path, body) {
    const res = await fetch(path, {
      method: method,
      headers: body ? { "Content-Type": "application/json" } : {},
      body: body ? JSON.stringify(body) : undefined
    });
    return { ok: res.ok, data: await res.json() };
  }

  function showResult(el, ok, text) {
    el.className = "result " + (ok ? "success" : "error");
    el.textContent = text;
  }

  function clearResult(el) {
    el.className = "result";
    el.textContent = "";
  }

  function fmt(iso) {
    if (!iso) return "-";
    return new Date(iso).toLocaleString("en-IN", { day: "2-digit", month: "short", year: "numeric",
                                                     hour: "2-digit", minute: "2-digit" });
  }

  function cell(tr, content) {
    const td = document.createElement("td");
    if (content instanceof Node) td.appendChild(content); else td.textContent = content;
    tr.appendChild(td);
    return td;
  }

  function badge(text, cls) {
    const b = document.createElement("span");
    b.className = "badge " + (cls || "st-" + text.toLowerCase().replace(/\s+/g, "-"));
    b.textContent = text;
    return b;
  }

  function button(text, cls, onClick) {
    const b = document.createElement("button");
    b.type = "button";
    b.textContent = text;
    if (cls) b.className = cls;
    b.addEventListener("click", onClick);
    return b;
  }

  function emptyRow(tbody, cols, text) {
    tbody.innerHTML = '<tr><td colspan="' + cols + '" class="muted"></td></tr>';
    tbody.querySelector("td").textContent = text;
  }

  // Numbers are sent as numbers; anything else is sent as typed so the server can reject it.
  function numberOrText(value) {
    const v = value.trim();
    return v !== "" && !isNaN(Number(v)) ? Number(v) : v;
  }

  function jobKey(id) { return "J-" + id; }

  function criteriaText(c) {
    const parts = [];
    if (c.min_cgpa !== null) parts.push("CGPA ≥ " + c.min_cgpa);
    if (c.allowed_branches.length) parts.push(c.allowed_branches.join("/"));
    if (c.max_backlogs !== null) parts.push("backlogs ≤ " + c.max_backlogs);
    if (c.batch) parts.push("batch " + c.batch);
    return parts.join(", ") || "-";
  }

  function staffEvents(status) {
    return meta.transitions.filter(function (t) {
      return t[1] === status && !meta.student_events.includes(t[0]);
    }).map(function (t) { return t[0]; });
  }

  // ---------------- role and acting user ----------------
  function actors() {
    if (role === "student") return meta.students.map(function (s) { return [s.student_id, s.name + " (" + s.roll_no + ")"]; });
    if (role === "recruiter") return meta.recruiters.map(function (r) { return [r.recruiter_id, r.name + " - " + r.company]; });
    return meta.officers.map(function (o) { return [o.officer_id, o.name]; });
  }

  function fillActors() {
    const list = actors();
    if (!list.some(function (a) { return String(a[0]) === String(actorId); })) actorId = String(list[0][0]);
    $("actor").innerHTML = "";
    list.forEach(function (a) {
      const o = document.createElement("option");
      o.value = String(a[0]);
      o.textContent = a[1];
      $("actor").appendChild(o);
    });
    $("actor").value = String(actorId);
    $("role").value = role;
    document.querySelectorAll("[data-role]").forEach(function (el) {
      el.hidden = !el.dataset.role.split(" ").includes(role);
    });
    history.replaceState(null, "", "?role=" + role + "&id=" + actorId);
  }

  // live = the redraw was caused by someone else's change (another tab, user or role)
  async function refresh(live) {
    document.body.dataset.busy = "1";   // lets the UI tests wait until every list is redrawn
    try {
      seenVersion = (await api("GET", "/api/version")).data.version;
      meta = (await api("GET", "/api/meta")).data;
      if (role === "student") await loadStudent();
      else if (role === "recruiter") await loadRecruiter();
      else await loadOfficer();
      await loadNotifications(live === true);
    } finally {
      document.body.dataset.busy = "0";
    }
  }

  // Every open page asks the server every 2 s whether any data changed and redraws itself if so,
  // e.g. a job posted by a recruiter appears in the officer's pending list without reloading.
  async function poll() {
    if (document.body.dataset.busy === "1") return;
    try {
      const r = await api("GET", "/api/version");
      setLive(true);
      if (r.data.version !== seenVersion) await refresh(true);
    } catch (e) {
      setLive(false);
    }
  }

  function setLive(on) {
    $("liveDot").className = on ? "on" : "";
    $("liveText").textContent = on ? "Live" : "Server not reachable";
  }

  function showToast(message) {
    const t = $("toast");
    t.innerHTML = "<b>New notification</b>";
    t.appendChild(document.createTextNode(message));
    t.hidden = false;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(function () { t.hidden = true; }, 6000);
  }

  // ---------------- student: profile, job board, apply, my applications ----------------
  function student() {
    return meta.students.find(function (s) { return String(s.student_id) === String(actorId); });
  }

  async function loadStudent() {
    const s = student();
    $("pfName").textContent = s.name;
    $("pfPlaced").textContent = s.is_placed ? "Placed" : "Not placed";
    $("pfPlaced").className = "badge " + (s.is_placed ? "placed" : "not-placed");
    $("pfRoll").textContent = s.roll_no;
    $("pfBranch").textContent = s.department;
    $("pfBatch").textContent = s.batch;
    $("pfCgpa").textContent = s.cgpa.toFixed(2);
    $("pfBacklogs").textContent = s.backlogs;
    await searchJobs();
    await fillApplyForm();
    await loadMyApplications();
  }

  async function searchJobs() {
    const q = new URLSearchParams({ student_id: actorId });
    if ($("fKeyword").value.trim()) q.set("q", $("fKeyword").value.trim());
    if ($("fLocation").value.trim()) q.set("location", $("fLocation").value.trim());
    if ($("fMinCtc").value.trim()) q.set("min_ctc", $("fMinCtc").value.trim());
    if ($("fEligible").checked) q.set("eligible_only", "1");
    q.set("page", page);
    const r = await api("GET", "/api/jobs?" + q.toString());
    const body = $("jobRows");
    body.innerHTML = "";
    if (!r.ok) {
      showResult($("searchResult"), false, r.data.error);
      $("jobCount").textContent = "";
      $("pgInfo").textContent = "";
      $("pgPrev").disabled = $("pgNext").disabled = true;
      emptyRow(body, 7, "Fix the search filters and try again.");
      return;
    }
    clearResult($("searchResult"));
    const d = r.data;
    $("jobCount").textContent = "(" + d.total + (d.total === 1 ? " job)" : " jobs)");
    $("pgInfo").textContent = "Page " + d.page + " of " + d.pages;
    $("pgPrev").disabled = d.page <= 1;
    $("pgNext").disabled = d.page >= d.pages;
    if (d.jobs.length === 0) emptyRow(body, 7, "No jobs match the filters.");
    d.jobs.forEach(function (j) {
      const tr = document.createElement("tr");
      tr.dataset.job = j.job_id;
      const title = document.createElement("div");
      title.innerHTML = "<strong></strong><br><span class='muted small'></span>";
      title.querySelector("strong").textContent = j.title;
      title.querySelector("span").textContent = jobKey(j.job_id) + " · " + criteriaText(j.criteria);
      cell(tr, title);
      cell(tr, j.company);
      cell(tr, j.ctc + " LPA");
      cell(tr, j.location);
      const dl = cell(tr, fmt(j.deadline));
      if (!j.open) { dl.appendChild(document.createElement("br")); dl.appendChild(badge("Closed", "closed")); }
      const el = cell(tr, badge(j.eligible ? "Eligible" : "Not eligible", j.eligible ? "eligible" : "not-eligible"));
      if (!j.eligible) {
        const ul = document.createElement("ul");
        ul.className = "reasons";
        j.reasons.forEach(function (x) { const li = document.createElement("li"); li.textContent = x; ul.appendChild(li); });
        el.appendChild(ul);
      }
      const apply = button("Apply", "", function () {
        $("apJob").value = String(j.job_id);
        $("apJob").dispatchEvent(new Event("change"));
        $("applyCard").scrollIntoView({ behavior: "smooth" });
      });
      apply.disabled = !(j.eligible && j.open);
      apply.title = apply.disabled ? (j.open ? "You are not eligible for this job" : "Deadline has passed") : "";
      cell(tr, apply);
      body.appendChild(tr);
    });
  }

  async function fillApplyForm() {
    const keepJob = $("apJob").value;
    const jobs = boardJobs = (await api("GET", "/api/jobs?per_page=50&student_id=" + actorId)).data.jobs;
    $("apJob").innerHTML = '<option value="">-- Select a job --</option>';
    jobs.forEach(function (j) {
      const o = document.createElement("option");
      o.value = String(j.job_id);
      o.textContent = jobKey(j.job_id) + " " + j.title + " - " + j.company +
        (!j.open ? " (closed)" : !j.eligible ? " (not eligible)" : "");
      $("apJob").appendChild(o);
    });
    if (jobs.some(function (j) { return String(j.job_id) === keepJob; })) $("apJob").value = keepJob;
    const keepResume = $("apResume").value;
    $("apResume").innerHTML = '<option value="">-- Select a resume --</option>';
    meta.resumes.filter(function (r) { return String(r.student_id) === String(actorId); }).forEach(function (r) {
      const o = document.createElement("option");
      o.value = String(r.resume_id);
      o.textContent = r.file_name + (r.is_active ? "" : " (inactive)");
      $("apResume").appendChild(o);
    });
    // BUG-01 fix: the placeholder option also has the value "", so an empty choice must not count as "keep"
    if (keepResume && [...$("apResume").options].some(function (o) { return o.value === keepResume; })) {
      $("apResume").value = keepResume;
    } else {
      // UC-1 step 4: the student's active resume is pre-selected
      const active = meta.resumes.find(function (r) { return String(r.student_id) === String(actorId) && r.is_active; });
      if (active) $("apResume").value = String(active.resume_id);
    }
    await previewEligibility();
  }

  // UC-1 E1 / E2: submission is disabled and the unmet criteria (or the passed deadline) are listed.
  async function previewEligibility() {
    const box = $("apElig");
    box.textContent = "";
    box.className = "elig-preview";
    $("apSubmit").disabled = false;
    if (!$("apJob").value) return;
    const job = boardJobs.find(function (j) { return String(j.job_id) === $("apJob").value; });
    if (job && !job.open) {
      box.className = "elig-preview no";
      box.textContent = "The application deadline for " + jobKey(job.job_id) + " has passed.";
      $("apSubmit").disabled = true;
      return;
    }
    const r = await api("GET", "/api/jobs/" + $("apJob").value + "/eligibility?student_id=" + actorId);
    if (!r.ok) return;
    box.className = "elig-preview " + (r.data.eligible ? "ok" : "no");
    box.textContent = r.data.eligible ? "You meet the eligibility criteria for this job."
      : "Not eligible: " + r.data.reasons.join(" ");
    $("apSubmit").disabled = !r.data.eligible;
  }

  async function loadMyApplications() {
    const apps = (await api("GET", "/api/applications?student_id=" + actorId)).data;
    const body = $("myAppRows");
    body.innerHTML = "";
    if (apps.length === 0) emptyRow(body, 6, "You have not applied to any job yet.");
    apps.forEach(function (a) {
      const tr = document.createElement("tr");
      tr.dataset.app = a.app_id;
      cell(tr, a.tracking_id);
      cell(tr, jobKey(a.job_id) + " " + a.title);
      cell(tr, a.company);
      cell(tr, fmt(a.applied_on));
      cell(tr, badge(a.status));
      const actions = cell(tr, button("Timeline", "secondary", function () { showTimeline(a.app_id); }));
      if (a.status === "Applied") {
        actions.appendChild(button("Withdraw", "danger", async function () {
          if (!confirm("Withdraw application " + a.tracking_id + "? This cannot be undone.")) return;
          const r = await api("POST", "/api/applications/" + a.app_id + "/withdraw", { student_id: Number(actorId) });
          afterStatusChange(r, a.app_id);
        }));
      }
      if (a.status === "Offer Issued") {
        ["accept_offer", "reject_offer"].forEach(function (ev) {
          actions.appendChild(button(EVENT_LABELS[ev], ev === "reject_offer" ? "danger" : "", async function () {
            if (!confirm(EVENT_LABELS[ev] + " for " + a.tracking_id + "?")) return;
            const r = await api("POST", "/api/applications/" + a.app_id + "/events",
                                { event: ev, actor_role: "student", actor_id: Number(actorId) });
            afterStatusChange(r, a.app_id);
          }));
        });
      }
      body.appendChild(tr);
    });
    if (timelineApp && apps.some(function (a) { return a.app_id === timelineApp; })) await showTimeline(timelineApp);
    else $("timelineBox").hidden = true;
  }

  async function afterStatusChange(r, appId) {
    showResult($("appResult"), r.ok, r.ok ? r.data.message : r.data.error);
    timelineApp = appId;
    await refresh();
  }

  async function showTimeline(appId) {
    const r = await api("GET", "/api/applications/" + appId);
    if (!r.ok) return;
    const a = r.data;
    timelineApp = appId;
    $("timelineBox").hidden = false;
    $("tlTracking").textContent = a.tracking_id + " (" + a.status + ")";
    const reached = a.history.map(function (h) { return h.to_state; });
    const stepper = $("stepper");
    stepper.innerHTML = "";
    PATH.forEach(function (st) {
      const li = document.createElement("li");
      li.textContent = st;
      if (st === a.status) li.className = "current";
      else if (reached.includes(st)) li.className = "done";
      stepper.appendChild(li);
    });
    if (a.status === "Rejected" || a.status === "Withdrawn") {
      const li = document.createElement("li");
      li.className = "end-bad";
      li.textContent = a.status;
      stepper.appendChild(li);
    }
    const list = $("historyList");
    list.innerHTML = "";
    a.history.forEach(function (h) {
      const li = document.createElement("li");
      const t = document.createElement("time");
      t.textContent = fmt(h.at);
      li.appendChild(t);
      li.appendChild(document.createTextNode((h.from_state ? h.from_state + " → " : "") + h.to_state +
        " (" + (EVENT_LABELS[h.event] || h.event) + " by " + h.actor + ")"));
      list.appendChild(li);
    });
  }

  // ---------------- recruiter: post job, own postings, own applicants ----------------
  async function loadRecruiter() {
    const rec = meta.recruiters.find(function (r) { return String(r.recruiter_id) === String(actorId); });
    $("companyNote").hidden = !!rec.is_approved;
    $("companyNote").textContent = rec.is_approved ? "" :
      rec.company + " is not yet approved by the placement cell, so it cannot post jobs.";
    if (!$("jbBranches").children.length) {
      meta.branches.forEach(function (b) {
        const l = document.createElement("label");
        l.innerHTML = '<input type="checkbox" name="jbBranch"> ';
        l.querySelector("input").value = b;
        l.appendChild(document.createTextNode(b));
        $("jbBranches").appendChild(l);
      });
    }
    const jobs = (await api("GET", "/api/jobs/manage?recruiter_id=" + actorId)).data;
    const body = $("myJobRows");
    body.innerHTML = "";
    if (jobs.length === 0) emptyRow(body, 5, "No job postings yet.");
    jobs.forEach(function (j) {
      const tr = document.createElement("tr");
      tr.dataset.job = j.job_id;
      cell(tr, jobKey(j.job_id));
      cell(tr, j.title);
      cell(tr, badge(j.status.charAt(0).toUpperCase() + j.status.slice(1)));
      cell(tr, fmt(j.deadline));
      cell(tr, j.remarks || "-");
      cell(tr, j.status === "returned" ? button("Edit & resubmit", "secondary", function () { startEdit(j); }) : "");
      body.appendChild(tr);
    });
    $("applicantsTitle").textContent = "Applicants for my jobs";
    await loadApplicants("/api/applications?recruiter_id=" + actorId);
  }

  function startEdit(j) {
    editingJob = j.job_id;
    $("jbTitle").value = j.title;
    $("jbDescription").value = j.description;
    $("jbCtc").value = j.ctc;
    $("jbLocation").value = j.location;
    $("jbDeadline").value = j.deadline;
    $("jbMinCgpa").value = j.criteria.min_cgpa === null ? "" : j.criteria.min_cgpa;
    $("jbMaxBacklogs").value = j.criteria.max_backlogs === null ? "" : j.criteria.max_backlogs;
    $("jbBatch").value = j.criteria.batch || "";
    document.querySelectorAll('input[name="jbBranch"]').forEach(function (b) {
      b.checked = j.criteria.allowed_branches.includes(b.value);
    });
    $("jbSubmit").textContent = "Resubmit " + jobKey(j.job_id);
    $("jbCancel").hidden = false;
    clearResult($("jbResult"));
    $("postCard").scrollIntoView({ behavior: "smooth" });
  }

  function stopEdit() {
    editingJob = null;
    $("jobForm").reset();
    $("jbSubmit").textContent = "Submit for approval";
    $("jbCancel").hidden = true;
  }

  async function loadApplicants(path) {
    const apps = (await api("GET", path)).data;
    const body = $("applicantRows");
    const picked = {};   // keep a half-chosen next step when the list is redrawn
    body.querySelectorAll("tr[data-app] select").forEach(function (s) { picked[s.closest("tr").dataset.app] = s.value; });
    body.innerHTML = "";
    if (apps.length === 0) emptyRow(body, 7, "No applications yet.");
    apps.forEach(function (a) {
      const tr = document.createElement("tr");
      tr.dataset.app = a.app_id;
      cell(tr, a.tracking_id);
      cell(tr, a.student_name);
      cell(tr, a.roll_no);
      cell(tr, jobKey(a.job_id) + " " + a.title);
      cell(tr, a.resume);
      cell(tr, badge(a.status));
      const events = staffEvents(a.status);
      if (events.length === 0) { cell(tr, "-"); body.appendChild(tr); return; }
      const sel = document.createElement("select");
      sel.innerHTML = '<option value="">-- Select --</option>';
      events.forEach(function (ev) {
        const o = document.createElement("option");
        o.value = ev;
        o.textContent = EVENT_LABELS[ev] || ev;
        sel.appendChild(o);
      });
      if (picked[a.app_id]) sel.value = picked[a.app_id];
      const td = cell(tr, sel);
      td.appendChild(button("Update", "", async function () {
        if (!sel.value) { showResult($("stResult"), false, "Select the next step for " + a.tracking_id + "."); return; }
        if (sel.value === "reject" && !confirm("Reject application " + a.tracking_id + "?")) return;
        const r = await api("POST", "/api/applications/" + a.app_id + "/events",
                            { event: sel.value, actor_role: role, actor_id: Number(actorId) });
        showResult($("stResult"), r.ok, r.ok ? r.data.message : r.data.error);
        await refresh();
      }));
      body.appendChild(tr);
    });
  }

  // ---------------- placement officer: approvals and overview ----------------
  async function loadOfficer() {
    const pending = (await api("GET", "/api/jobs/manage?status=pending")).data;
    const body = $("pendingRows");
    const keep = $("dcJob").value;
    body.innerHTML = "";
    $("dcJob").innerHTML = '<option value="">-- Select --</option>';
    if (pending.length === 0) emptyRow(body, 6, "No job postings are waiting for approval.");
    pending.forEach(function (j) {
      const tr = document.createElement("tr");
      tr.dataset.job = j.job_id;
      cell(tr, jobKey(j.job_id));
      cell(tr, j.company);
      cell(tr, j.title);
      cell(tr, j.ctc + " LPA");
      cell(tr, fmt(j.deadline));
      cell(tr, criteriaText(j.criteria));
      body.appendChild(tr);
      const o = document.createElement("option");
      o.value = String(j.job_id);
      o.textContent = jobKey(j.job_id) + " " + j.title + " - " + j.company;
      $("dcJob").appendChild(o);
    });
    if (pending.some(function (j) { return String(j.job_id) === keep; })) $("dcJob").value = keep;
    const all = (await api("GET", "/api/jobs/manage?status=all")).data;
    const allBody = $("allJobRows");
    allBody.innerHTML = "";
    all.forEach(function (j) {
      const tr = document.createElement("tr");
      tr.dataset.job = j.job_id;
      cell(tr, jobKey(j.job_id));
      cell(tr, j.company);
      cell(tr, j.title);
      cell(tr, badge(j.status.charAt(0).toUpperCase() + j.status.slice(1)));
      cell(tr, fmt(j.deadline));
      cell(tr, j.remarks || "-");
      allBody.appendChild(tr);
    });
    $("applicantsTitle").textContent = "All applications";
    await loadApplicants("/api/applications");
  }

  async function loadNotifications(live) {
    const list = (await api("GET", "/api/notifications?recipient_type=" + role + "&recipient_id=" + actorId)).data;
    const key = role + ":" + actorId;
    const newest = list.length ? list[0].notif_id : 0;
    if (live && key in lastNotif && newest > lastNotif[key]) showToast(list[0].message);
    lastNotif[key] = newest;
    const ul = $("notifList");
    ul.innerHTML = "";
    $("notifCount").textContent = "(" + list.length + ")";
    if (list.length === 0) ul.innerHTML = '<li class="muted">No notifications.</li>';
    list.slice(0, 12).forEach(function (n) {
      const li = document.createElement("li");
      const t = document.createElement("time");
      t.textContent = fmt(n.sent_at);
      li.appendChild(t);
      li.appendChild(document.createTextNode(n.message));
      ul.appendChild(li);
    });
  }

  // ---------------- form handlers ----------------
  $("role").addEventListener("change", async function () {
    role = $("role").value;
    actorId = null;
    timelineApp = null;
    page = 1;
    stopEdit();
    fillActors();
    await refresh();
  });

  $("actor").addEventListener("change", async function () {
    actorId = $("actor").value;
    timelineApp = null;
    page = 1;
    stopEdit();
    document.querySelectorAll(".result").forEach(clearResult);
    fillActors();
    await refresh();
  });

  $("searchForm").addEventListener("submit", function (e) {
    e.preventDefault();
    page = 1;
    searchJobs();
  });

  $("pgPrev").addEventListener("click", function () { page -= 1; searchJobs(); });
  $("pgNext").addEventListener("click", function () { page += 1; searchJobs(); });
  $("jbCancel").addEventListener("click", function () { stopEdit(); clearResult($("jbResult")); });

  $("apJob").addEventListener("change", previewEligibility);

  $("apNote").addEventListener("input", function () {
    const n = $("apNote").value.length;
    $("apCount").textContent = n + " / 500";
    $("apCount").className = n > 500 ? "over" : "";
  });

  $("applyForm").addEventListener("submit", async function (e) {
    e.preventDefault();
    if (!$("apJob").value) {
      showResult($("apResult"), false, "Select a job to apply for.");
      return;
    }
    const r = await api("POST", "/api/applications", {
      student_id: Number(actorId),
      job_id: Number($("apJob").value),
      resume_id: $("apResume").value ? Number($("apResume").value) : null,
      cover_note: $("apNote").value
    });
    showResult($("apResult"), r.ok, r.ok ? r.data.message : r.data.error);
    if (r.ok) {
      $("apNote").value = "";
      $("apCount").textContent = "0 / 500";
      timelineApp = r.data.app_id;
    }
    await refresh();
  });

  $("jobForm").addEventListener("submit", async function (e) {
    e.preventDefault();
    const branches = [...document.querySelectorAll('input[name="jbBranch"]:checked')].map(function (b) { return b.value; });
    const r = await api(editingJob ? "PUT" : "POST", editingJob ? "/api/jobs/" + editingJob : "/api/jobs", {
      recruiter_id: Number(actorId),
      title: $("jbTitle").value,
      description: $("jbDescription").value,
      ctc: numberOrText($("jbCtc").value),
      location: $("jbLocation").value,
      deadline: $("jbDeadline").value,
      min_cgpa: numberOrText($("jbMinCgpa").value),
      max_backlogs: numberOrText($("jbMaxBacklogs").value),
      allowed_branches: branches,
      batch: $("jbBatch").value
    });
    showResult($("jbResult"), r.ok, r.ok ? r.data.message : r.data.error);
    if (r.ok) stopEdit();
    await refresh();
  });

  $("decisionForm").addEventListener("submit", async function (e) {
    e.preventDefault();
    const decision = document.querySelector('input[name="dcDecision"]:checked');
    if (!$("dcJob").value) {
      showResult($("dcResult"), false, "Select a pending job posting.");
      return;
    }
    if (decision && decision.value === "reject" && !confirm("Reject job posting " + jobKey($("dcJob").value) + "?")) return;
    const r = await api("POST", "/api/jobs/" + $("dcJob").value + "/decision", {
      decision: decision ? decision.value : "",
      remarks: $("dcRemarks").value,
      actor_role: "officer",
      actor_id: Number(actorId)
    });
    showResult($("dcResult"), r.ok, r.ok ? r.data.message : r.data.error);
    if (r.ok) $("decisionForm").reset();
    await refresh();
  });

  (async function start() {
    meta = (await api("GET", "/api/meta")).data;
    fillActors();
    await refresh();
    setLive(true);
    document.body.dataset.ready = "1";
    setInterval(poll, 2000);
  })();
})();
