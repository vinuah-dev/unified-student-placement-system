// Form 2: Update Faculty Profile.
(function () {
  const form = document.getElementById("profileForm");
  const box = document.getElementById("result");

  form.addEventListener("submit", function (event) {
    event.preventDefault();

    const errors = [];
    const id = readFacultyId(document.getElementById("facultyId").value, errors);
    const name = document.getElementById("fullName").value.trim();
    const email = document.getElementById("email").value.trim();
    const mobile = document.getElementById("mobile").value.trim();
    const dept = document.getElementById("department").value;

    if (!/^[A-Za-z. ]{3,50}$/.test(name)) {
      errors.push("Name must be 3 to 50 characters (letters, spaces and dots only).");
    }
    if (!/^[^\s@]+@[^\s@]+\.[A-Za-z]{2,}$/.test(email)) {
      errors.push("Enter a valid email address (e.g. name@college.edu).");
    }
    if (!/^[6-9]\d{9}$/.test(mobile)) {
      errors.push("Mobile number must be 10 digits starting with 6, 7, 8 or 9.");
    }
    if (!dept) errors.push("Please select a department.");

    if (errors.length > 0) {
      showResult(box, "error", errors);
      return;
    }

    const faculty = FACULTY[id];
    faculty.name = name;
    faculty.email = email;
    faculty.mobile = mobile;
    faculty.dept = dept;
    showResult(box, "success", ["Profile updated successfully for " + id + " (" + name + ", " + dept + ")."]);
  });

  form.addEventListener("reset", function () {
    hideResult(box);
  });
})();
