// Form 4: Leave Balance Enquiry.
(function () {
  const form = document.getElementById("balanceForm");
  const box = document.getElementById("result");
  const table = document.getElementById("balanceTable");
  const rows = document.getElementById("balanceRows");

  function renderBalance(faculty, types) {
    rows.innerHTML = "";
    types.forEach(function (type) {
      const b = faculty.balance[type];
      const cells = b === null
        ? [LEAVE_NAMES[type], "-", "-", "Not eligible"]
        : [LEAVE_NAMES[type], b.total, b.total - b.available, b.available];
      const tr = document.createElement("tr");
      cells.forEach(function (value) {
        const td = document.createElement("td");
        td.textContent = value;
        tr.appendChild(td);
      });
      rows.appendChild(tr);
    });
    table.hidden = false;
  }

  form.addEventListener("submit", function (event) {
    event.preventDefault();
    table.hidden = true;

    const errors = [];
    const id = readFacultyId(document.getElementById("facultyId").value, errors);
    const year = document.getElementById("academicYear").value;
    const type = document.getElementById("leaveType").value;

    if (!year) errors.push("Please select an academic year.");

    if (errors.length > 0) {
      showResult(box, "error", errors);
      return;
    }

    if (year !== DATA_YEAR) {
      showResult(box, "info", ["No leave records found for " + id + " in " + year + "."]);
      return;
    }

    const faculty = FACULTY[id];
    const types = type === "ALL" ? ["CL", "ML", "OD"] : [type];
    const parts = types.map(function (t) {
      const b = faculty.balance[t];
      return b === null ? t + " Not eligible" : t + " " + b.available + "/" + b.total;
    });
    showResult(box, "success", ["Leave balance for " + id + " (" + year + "): " + parts.join(", ")]);
    renderBalance(faculty, types);
  });

  form.addEventListener("reset", function () {
    hideResult(box);
    table.hidden = true;
  });
})();
