// Form 3: Approve / Reject Leave Request (administrator).
(function () {
  const form = document.getElementById("approveForm");
  const box = document.getElementById("result");
  const rows = document.getElementById("requestRows");

  function renderRequests() {
    rows.innerHTML = "";
    Object.keys(LEAVE_REQUESTS).forEach(function (id) {
      const r = LEAVE_REQUESTS[id];
      const tr = document.createElement("tr");
      [id, r.facultyId, r.type, r.from, r.days, r.status].forEach(function (value) {
        const td = document.createElement("td");
        td.textContent = value;
        tr.appendChild(td);
      });
      rows.appendChild(tr);
    });
  }

  form.addEventListener("submit", function (event) {
    event.preventDefault();

    const errors = [];
    const id = document.getElementById("requestId").value.trim().toUpperCase();
    const decision = checkedValue("decision");
    const remarks = document.getElementById("remarks").value.trim();
    let request = null;

    if (id === "") errors.push("Request ID is required.");
    else if (!/^LR-\d{4}$/.test(id)) errors.push("Request ID must be LR- followed by 4 digits (e.g. LR-1001).");
    else if (!LEAVE_REQUESTS[id]) errors.push("Leave request " + id + " not found.");
    else if (LEAVE_REQUESTS[id].status !== "PENDING") {
      errors.push("Leave request " + id + " is already " + LEAVE_REQUESTS[id].status + " and cannot be changed.");
    } else request = LEAVE_REQUESTS[id];

    if (!decision) errors.push("Please select Approve or Reject.");

    if (remarks.length > 200) errors.push("Remarks cannot exceed 200 characters.");
    else if (decision === "Reject" && remarks.length < 10) {
      errors.push("Remarks of at least 10 characters are required when rejecting.");
    }

    if (errors.length > 0) {
      showResult(box, "error", errors);
      return;
    }

    request.status = decision === "Approve" ? "APPROVED" : "REJECTED";
    request.remarks = remarks;
    renderRequests();
    showResult(box, "success", [
      "Leave request " + id + " " + request.status + ". Status notification sent to " +
      request.facultyId + " via " + FACULTY[request.facultyId].channel + "."
    ]);
  });

  form.addEventListener("reset", function () {
    hideResult(box);
  });

  renderRequests();
})();
