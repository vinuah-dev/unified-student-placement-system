// Shared data and helpers for the Online Leave Management System demo.
// Data is held in memory and re-seeded on every page load, so each test starts from the same state.

const DATA_YEAR = "2026-27";

const LEAVE_NAMES = { CL: "Casual Leave", ML: "Medical Leave", OD: "On-Duty Leave" };

// Maximum number of days allowed in a single request, per leave type.
const MAX_DAYS = { CL: 3, ML: 15, OD: 10 };

// balance[type] = { available, total }; null means the faculty category is not eligible.
const FACULTY = {
  FAC101: {
    name: "Dr. Anita Deshmukh", category: "Permanent", dept: "CSE", channel: "Email",
    balance: { CL: { available: 8, total: 12 }, ML: { available: 10, total: 10 }, OD: { available: 5, total: 7 } }
  },
  FAC102: {
    name: "Mr. Rahul Patil", category: "Contract", dept: "CSE", channel: "SMS",
    balance: { CL: { available: 5, total: 8 }, ML: null, OD: { available: 3, total: 5 } }
  },
  FAC103: {
    name: "Dr. Sneha Kulkarni", category: "Permanent", dept: "IT", channel: "Mobile App",
    balance: { CL: { available: 12, total: 12 }, ML: { available: 2, total: 10 }, OD: { available: 7, total: 7 } }
  }
};

const LEAVE_REQUESTS = {
  "LR-1001": { facultyId: "FAC101", type: "CL", from: "2026-11-02", days: 2, status: "PENDING" },
  "LR-1002": { facultyId: "FAC102", type: "OD", from: "2026-11-05", days: 3, status: "PENDING" },
  "LR-1003": { facultyId: "FAC103", type: "ML", from: "2026-10-20", days: 1, status: "APPROVED" }
};

// Faculty ID is trimmed and upper-cased, then checked for format and registration.
function readFacultyId(raw, errors) {
  const id = raw.trim().toUpperCase();
  if (id === "") {
    errors.push("Faculty ID is required.");
    return null;
  }
  if (!/^FAC\d{3}$/.test(id)) {
    errors.push("Faculty ID must be FAC followed by 3 digits (e.g. FAC101).");
    return null;
  }
  if (!FACULTY[id]) {
    errors.push("Faculty ID " + id + " is not registered.");
    return null;
  }
  return id;
}

function checkedValue(name) {
  const checked = document.querySelector('input[name="' + name + '"]:checked');
  return checked ? checked.value : "";
}

function todayISO() {
  const d = new Date();
  return d.getFullYear() + "-" + String(d.getMonth() + 1).padStart(2, "0") + "-" + String(d.getDate()).padStart(2, "0");
}

// Inclusive number of days between two yyyy-mm-dd dates; 0 if either is missing.
function daysBetween(from, to) {
  if (!from || !to) return 0;
  return Math.round((Date.parse(to) - Date.parse(from)) / 86400000) + 1;
}

function showResult(box, kind, messages) {
  box.className = "result " + kind;
  box.innerHTML = "";
  if (messages.length === 1) {
    box.textContent = messages[0];
    return;
  }
  const list = document.createElement("ul");
  messages.forEach(function (m) {
    const item = document.createElement("li");
    item.textContent = m;
    list.appendChild(item);
  });
  box.appendChild(list);
}

function hideResult(box) {
  box.className = "result";
  box.innerHTML = "";
}
