// Module 2 user-interface test cases. They drive the real dashboard (loaded in an iframe from the same
// server) through its DOM only: click tabs, fill the forms, press the buttons, read what is displayed.
// Data loaded by run_tests.py before the run: LAB-1 has 2 occupied frames, then 5 vacant frames with
// 2 fans and 6 lights ON, and 60 s later all four regions at 24.0 deg C (start 25.0) -> 3 open alerts.
// CR-201 has no readings. Cases run in order on the same server.

const MODULE = "M2 Dashboard & Control (UI)";

function text(doc, id) { return doc.getElementById(id).textContent.trim(); }

const ROOM_NAMES = { "CR-201": "Classroom 201", "LAB-1": "Computer Lab 1 (10 m x 8 m)" };

async function openRoom(doc, roomId) {
  const tab = [...doc.querySelectorAll("#roomTabs button")].find((b) => b.textContent === roomId);
  tab.click();
  await waitFor(() => text(doc, "roomName") === ROOM_NAMES[roomId]);
  await sleep(400);   // alerts and commands are fetched right after the status
}

async function submit(doc, formId, resultId) {
  doc.querySelector("#" + formId + ' button[type="submit"]').click();
  await waitFor(() => /success|error/.test(doc.getElementById(resultId).className));
  return text(doc, resultId);
}

function fill(doc, values) {
  Object.entries(values).forEach(([id, v]) => {
    const radios = doc.querySelectorAll('input[type="radio"][name="' + id + '"]');
    if (radios.length) { radios.forEach((r) => { r.checked = r.value === v; }); return; }
    doc.getElementById(id).value = v;
  });
}

const UI_CASES = [
  { id: "TC_UI_01", technique: "Functional (UI)", scenario: "Room that has sent no readings yet",
    data: "Open dashboard, room CR-201 (no readings)", expected: "NO DATA",
    run: async (doc) => { await openRoom(doc, "CR-201"); return text(doc, "stateBadge"); } },
  { id: "TC_UI_02", technique: "Functional (UI)", scenario: "Status card after the room becomes vacant",
    data: "Open room LAB-1", expected: "VACANT | people 0 | fans 2 | lights 6 | AC likely ON (mean drop 1.00 °C)",
    run: async (doc) => {
      await openRoom(doc, "LAB-1");
      return [text(doc, "stateBadge"), "people " + text(doc, "people"), "fans " + text(doc, "fans"),
              "lights " + text(doc, "lights"), text(doc, "acCheck")].join(" | ");
    } },
  { id: "TC_UI_03", technique: "Functional (UI)", scenario: "Heatmap shows the four region temperatures",
    data: "Open room LAB-1", expected: "24.0 °C, 24.0 °C, 24.0 °C, 24.0 °C",
    run: async (doc) => {
      await openRoom(doc, "LAB-1");
      return [1, 2, 3, 4].map((i) => doc.querySelector("#region" + i + " b").textContent).join(", ");
    } },
  { id: "TC_UI_04", technique: "Functional (UI)", scenario: "Open alerts table",
    data: "Open room LAB-1", expected: "3 rows: AC ON VACANT, LIGHT ON VACANT, FAN ON VACANT",
    run: async (doc) => {
      await openRoom(doc, "LAB-1");
      const rows = [...doc.querySelectorAll("#alertRows tr")].map((tr) => tr.children[2].textContent);
      return rows.length + " rows: " + rows.join(", ");
    } },
  { id: "TC_UI_05", technique: "Validation (UI)", scenario: "Acknowledge without selecting an alert",
    data: "Alert: -- Select --, operator 'R. Kulkarni'", expected: "Please select an alert.",
    run: async (doc) => {
      await openRoom(doc, "LAB-1");
      fill(doc, { ackAlert: "", ackOperator: "R. Kulkarni", ackRemarks: "" });
      return submit(doc, "ackForm", "ackResult");
    } },
  { id: "TC_UI_06", technique: "Validation / BVA (UI)", scenario: "Operator name of 1 character",
    data: "Alert #1, operator 'R'",
    expected: "Operator name must be 3 to 40 characters (letters, spaces and dots only).",
    run: async (doc) => {
      await openRoom(doc, "LAB-1");
      fill(doc, { ackAlert: "1", ackOperator: "R", ackRemarks: "" });
      return submit(doc, "ackForm", "ackResult");
    } },
  { id: "TC_UI_07", technique: "Functional (UI)", scenario: "Acknowledge alert #1",
    data: "Alert #1, operator 'R. Kulkarni', remarks 'Fans switched off'",
    expected: "Alert 1 acknowledged by R. Kulkarni.",
    run: async (doc) => {
      await openRoom(doc, "LAB-1");
      fill(doc, { ackAlert: "1", ackOperator: "R. Kulkarni", ackRemarks: "Fans switched off" });
      return submit(doc, "ackForm", "ackResult");
    } },
  { id: "TC_UI_08", technique: "Integration (UI)", scenario: "Acknowledged alert leaves the open list",
    data: "Reload dashboard, room LAB-1", expected: "2 rows; open alerts card shows 2",
    run: async (doc) => {
      await openRoom(doc, "LAB-1");
      return doc.querySelectorAll("#alertRows tr").length + " rows; open alerts card shows " + text(doc, "openAlerts");
    } },
  { id: "TC_UI_09", technique: "Functional (UI)", scenario: "Send manual override fan OFF",
    data: "Fan, Switch OFF, 'R. Kulkarni', 'Room empty after lecture'",
    expected: "Command 1 queued: switch fan OFF in LAB-1.",
    run: async (doc) => {
      await openRoom(doc, "LAB-1");
      fill(doc, { ovAppliance: "fan", ovAction: "OFF", ovOperator: "R. Kulkarni", ovReason: "Room empty after lecture" });
      return submit(doc, "overrideForm", "ovResult");
    } },
  { id: "TC_UI_10", technique: "Validation (UI)", scenario: "Override without choosing an appliance",
    data: "Appliance: -- Select --, Switch OFF", expected: "Appliance must be fan or light.",
    run: async (doc) => {
      await openRoom(doc, "LAB-1");
      fill(doc, { ovAppliance: "", ovAction: "OFF", ovOperator: "R. Kulkarni", ovReason: "Room empty after lecture" });
      return submit(doc, "overrideForm", "ovResult");
    } },
  { id: "TC_UI_11", technique: "Validation (UI)", scenario: "Override without choosing ON or OFF",
    data: "Light, no action selected", expected: "Action must be ON or OFF.",
    run: async (doc) => {
      await openRoom(doc, "LAB-1");
      fill(doc, { ovAppliance: "light", ovAction: "", ovOperator: "R. Kulkarni", ovReason: "Room empty after lecture" });
      return submit(doc, "overrideForm", "ovResult");
    } },
  { id: "TC_UI_12", technique: "Validation / BVA (UI)", scenario: "Override reason of 3 characters",
    data: "Light, Switch OFF, reason 'abc'", expected: "Reason must be 5 to 100 characters.",
    run: async (doc) => {
      await openRoom(doc, "LAB-1");
      fill(doc, { ovAppliance: "light", ovAction: "OFF", ovOperator: "R. Kulkarni", ovReason: "abc" });
      return submit(doc, "overrideForm", "ovResult");
    } },
  { id: "TC_UI_13", technique: "Functional (UI)", scenario: "Save valid settings",
    data: "frames 5, wait 60, threshold 0.5", expected: "Settings saved.",
    run: async (doc) => {
      fill(doc, { setFrames: "5", setWait: "60", setThreshold: "0.5" });
      return submit(doc, "settingsForm", "setResult");
    } },
  { id: "TC_UI_14", technique: "Validation / BVA (UI)", scenario: "Empty frames = 301",
    data: "frames 301, wait 60, threshold 0.5",
    expected: "Empty frames to confirm vacancy must be between 1 and 300.",
    run: async (doc) => {
      fill(doc, { setFrames: "301", setWait: "60", setThreshold: "0.5" });
      return submit(doc, "settingsForm", "setResult");
    } },
  { id: "TC_UI_15", technique: "Validation (UI)", scenario: "Threshold is not a number",
    data: "frames 5, wait 60, threshold 'abc'", expected: "Mean ΔT threshold must be a number.",
    run: async (doc) => {
      fill(doc, { setFrames: "5", setWait: "60", setThreshold: "abc" });
      return submit(doc, "settingsForm", "setResult");
    } },
];
UI_CASES.forEach((c) => { c.module = MODULE; });
