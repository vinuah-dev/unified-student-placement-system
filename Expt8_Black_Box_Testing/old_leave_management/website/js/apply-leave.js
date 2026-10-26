// Form 1: Apply for Leave.
(function () {
  const form = document.getElementById("applyForm");
  const box = document.getElementById("result");
  const fromEl = document.getElementById("fromDate");
  const toEl = document.getElementById("toDate");
  const daysEl = document.getElementById("days");
  let nextRequestNo = 2001;

  function updateDays() {
    const days = daysBetween(fromEl.value, toEl.value);
    daysEl.value = days > 0 ? days + " day(s)" : "";
  }

  fromEl.addEventListener("change", updateDays);
  toEl.addEventListener("change", updateDays);

  form.addEventListener("submit", function (event) {
    event.preventDefault();
    updateDays();

    const errors = [];
    const id = readFacultyId(document.getElementById("facultyId").value, errors);
    const type = document.getElementById("leaveType").value;
    const from = fromEl.value;
    const to = toEl.value;
    const reason = document.getElementById("reason").value.trim();
    const channel = checkedValue("channel");

    if (!type) errors.push("Please select a leave type.");

    if (!from) errors.push("From date is required.");
    else if (from < todayISO()) errors.push("From date cannot be in the past.");

    if (!to) errors.push("To date is required.");
    else if (from && to < from) errors.push("To date cannot be before From date.");

    if (reason.length < 10 || reason.length > 200) errors.push("Reason must be 10 to 200 characters.");
    if (!channel) errors.push("Please select a notification channel.");

    // Leave-policy rules are applied only once every field is individually valid.
    const days = daysBetween(from, to);
    if (errors.length === 0) {
      const faculty = FACULTY[id];
      const balance = faculty.balance[type];
      if (balance === null) {
        errors.push(faculty.category + " faculty are not eligible for " + LEAVE_NAMES[type] + ".");
      } else if (days > MAX_DAYS[type]) {
        errors.push(LEAVE_NAMES[type] + " cannot exceed " + MAX_DAYS[type] + " days per request.");
      } else if (days > balance.available) {
        errors.push("Insufficient " + type + " balance (available: " + balance.available + " day(s)).");
      }
    }

    if (errors.length > 0) {
      showResult(box, "error", errors);
      return;
    }

    const requestId = "LR-" + nextRequestNo++;
    LEAVE_REQUESTS[requestId] = { facultyId: id, type: type, from: from, days: days, status: "PENDING" };
    showResult(box, "success", [
      "Leave request " + requestId + " submitted successfully (" + type + ", " + days +
      " day(s), status PENDING, notification via " + channel + ")."
    ]);
  });

  form.addEventListener("reset", function () {
    hideResult(box);
    daysEl.value = "";
  });
})();
