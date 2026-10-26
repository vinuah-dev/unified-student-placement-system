// Drives a form page loaded in an iframe exactly as a user would: fill fields, press submit, read the message shown.
// It only touches the page through its DOM, never through the page's own scripts (black-box).

function shiftedDate(days) {
  const d = new Date();
  d.setDate(d.getDate() + days);
  return d.getFullYear() + "-" + String(d.getMonth() + 1).padStart(2, "0") + "-" + String(d.getDate()).padStart(2, "0");
}

function resolveValue(value) {
  const m = /^today([+-]\d+)?$/.exec(value);
  return m ? shiftedDate(m[1] ? parseInt(m[1], 10) : 0) : value;
}

function resolveInputs(inputs) {
  const out = {};
  Object.keys(inputs).forEach(function (k) { out[k] = resolveValue(inputs[k]); });
  return out;
}

function loadPage(frame, src) {
  return new Promise(function (resolve) {
    frame.onload = function () { resolve(frame.contentDocument); };
    frame.src = src + "?run=" + Date.now();
  });
}

function fillForm(doc, inputs) {
  Object.keys(inputs).forEach(function (name) {
    const value = inputs[name];
    const radios = doc.querySelectorAll('input[type="radio"][name="' + name + '"]');
    if (radios.length > 0) {
      radios.forEach(function (r) { r.checked = r.value === value; });
      return;
    }
    const el = doc.getElementById(name);
    if (!el) throw new Error("Field not found on page: " + name);
    el.value = value;
    el.dispatchEvent(new Event("input", { bubbles: true }));
    el.dispatchEvent(new Event("change", { bubbles: true }));
  });
}

function readResult(doc) {
  const box = doc.getElementById("result");
  const items = box.querySelectorAll("li");
  const text = items.length > 0
    ? Array.prototype.map.call(items, function (li) { return li.textContent.trim(); }).join(" | ")
    : box.textContent.trim();
  return { text: text, kind: box.className.replace("result", "").trim() || "none" };
}

async function executeCase(frame, tc) {
  const form = FORMS[tc.form];
  const doc = await loadPage(frame, "../" + form.page);
  const inputs = resolveInputs(tc.inputs);
  fillForm(doc, inputs);
  doc.querySelector("#" + form.formId + ' button[type="submit"]').click();
  const actual = readResult(doc);
  return {
    id: tc.id,
    form: form.name,
    page: form.page,
    submit: form.submit,
    technique: tc.technique,
    scenario: tc.scenario,
    inputs: inputs,
    expected: tc.expected,
    actual: actual.text,
    outputKind: actual.kind,
    status: actual.text === tc.expected ? "PASS" : "FAIL"
  };
}
