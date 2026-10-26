// Dashboard: polls the API, renders room status, heatmap, alerts and commands, and submits the three forms.
(function () {
  let rooms = [];
  let currentRoom = new URLSearchParams(location.search).get("room");   // e.g. /?room=LAB-1

  const $ = (id) => document.getElementById(id);

  async function api(method, path, body) {
    const res = await fetch(path, {
      method: method,
      headers: body ? { "Content-Type": "application/json" } : {},
      body: body ? JSON.stringify(body) : undefined
    });
    const data = await res.json();
    return { ok: res.ok, data: data };
  }

  function showResult(el, ok, text) {
    el.className = "result " + (ok ? "success" : "error");
    el.textContent = text;
  }

  function fmtTime(ts) {
    if (ts === null || ts === undefined) return "-";
    return new Date(ts * 1000).toLocaleString("en-IN");
  }

  // 20 deg C -> blue, 35 deg C -> red
  function tempColour(t) {
    const x = Math.max(0, Math.min(1, (t - 20) / 15));
    return "hsl(" + Math.round(220 - 220 * x) + ", 75%, " + Math.round(80 - 18 * x) + "%)";
  }

  function acText(s) {
    if (s.state === "CHECKING_AC") return "Checking… " + s.ac_check_seconds_left + " s left";
    if (s.ac_inferred_on === true) return "AC likely ON (mean drop " + s.mean_temp_drop.toFixed(2) + " °C)";
    if (s.ac_inferred_on === false) return "AC OFF (mean drop " + s.mean_temp_drop.toFixed(2) + " °C)";
    return "Not checked yet (room not vacant)";
  }

  function renderTabs() {
    const nav = $("roomTabs");
    nav.innerHTML = "";
    rooms.forEach(function (r) {
      const b = document.createElement("button");
      b.type = "button";
      b.textContent = r.id;
      b.className = r.id === currentRoom ? "active" : "";
      b.addEventListener("click", function () { currentRoom = r.id; refresh(); });
      nav.appendChild(b);
    });
  }

  function renderStatus(room) {
    const s = room.status;
    $("stateBadge").textContent = s.state.replace("_", " ");
    $("stateBadge").className = "badge " + s.state;
    $("roomName").textContent = room.name;
    $("people").textContent = s.people ?? "-";
    $("fans").textContent = s.fans_on ?? "-";
    $("lights").textContent = s.lights_on ?? "-";
    $("openAlerts").textContent = room.open_alerts;
    $("acCheck").textContent = s.last_timestamp === null ? "-" : acText(s);
    $("lastUpdate").textContent = fmtTime(s.last_timestamp);
    for (let i = 0; i < 4; i++) {
      const cell = $("region" + (i + 1));
      const t = s.temps ? s.temps[i] : null;
      cell.querySelector("b").textContent = t === null ? "-" : t.toFixed(1) + " °C";
      cell.style.background = t === null ? "#e5e7eb" : tempColour(t);
    }
  }

  function renderAlerts(alerts) {
    const body = $("alertRows");
    const select = $("ackAlert");
    const keep = select.value;
    body.innerHTML = "";
    select.innerHTML = '<option value="">-- Select --</option>';
    if (alerts.length === 0) {
      body.innerHTML = '<tr><td colspan="5" class="muted">No open alerts.</td></tr>';
    }
    alerts.forEach(function (a) {
      const tr = document.createElement("tr");
      [a.id, fmtTime(a.ts), a.type.replaceAll("_", " "), a.message].forEach(function (v) {
        const td = document.createElement("td");
        td.textContent = v;
        tr.appendChild(td);
      });
      const td = document.createElement("td");
      const btn = document.createElement("button");
      btn.type = "button";
      btn.textContent = "Acknowledge";
      btn.addEventListener("click", function () { select.value = String(a.id); $("ackOperator").focus(); });
      td.appendChild(btn);
      tr.appendChild(td);
      body.appendChild(tr);
      const opt = document.createElement("option");
      opt.value = String(a.id);
      opt.textContent = "#" + a.id + " " + a.type.replaceAll("_", " ");
      select.appendChild(opt);
    });
    if ([...select.options].some(function (o) { return o.value === keep; })) select.value = keep;
  }

  function renderCommands(cmds) {
    const list = $("commandList");
    list.innerHTML = "";
    if (cmds.length === 0) {
      list.innerHTML = '<li class="muted">No commands yet.</li>';
      return;
    }
    cmds.slice(0, 6).forEach(function (c) {
      const li = document.createElement("li");
      const tag = document.createElement("span");
      tag.className = "tag " + c.status;
      tag.textContent = c.status;
      li.textContent = "#" + c.id + " " + c.appliance + " " + c.action + " by " + c.operator + " - " + c.reason + " ";
      li.appendChild(tag);
      list.appendChild(li);
    });
  }

  async function refresh() {
    try {
      const r = await api("GET", "/api/rooms");
      rooms = r.data;
      if (!rooms.some(function (x) { return x.id === currentRoom; })) currentRoom = rooms[0].id;
      renderTabs();
      const room = rooms.find(function (x) { return x.id === currentRoom; });
      renderStatus(room);
      renderAlerts((await api("GET", "/api/alerts?status=OPEN&room=" + currentRoom)).data);
      renderCommands((await api("GET", "/api/commands?room=" + currentRoom)).data);
      $("liveDot").className = "on";
      $("liveText").textContent = "Live";
    } catch (e) {
      $("liveDot").className = "";
      $("liveText").textContent = "Server not reachable";
    }
  }

  async function loadSettings() {
    const s = (await api("GET", "/api/settings")).data;
    $("setFrames").value = s.vacancy_frames;
    $("setWait").value = s.wait_seconds;
    $("setThreshold").value = s.delta_t_threshold;
  }

  // The API names settings by their JSON keys; the form shows them by their labels.
  const SETTING_LABELS = {
    vacancy_frames: "Empty frames to confirm vacancy",
    wait_seconds: "Wait before final temperature",
    delta_t_threshold: "Mean ΔT threshold"
  };

  function withLabel(message) {
    const key = Object.keys(SETTING_LABELS).find(function (k) { return message.startsWith(k + " "); });
    return key ? SETTING_LABELS[key] + message.slice(key.length) : message;
  }

  // Numbers are sent as numbers; anything else is sent as typed so the server can reject it.
  function numberOrText(value) {
    const v = value.trim();
    return v !== "" && !isNaN(Number(v)) ? Number(v) : v;
  }

  $("ackForm").addEventListener("submit", async function (e) {
    e.preventDefault();
    const id = $("ackAlert").value;
    if (!id) {
      showResult($("ackResult"), false, "Please select an alert.");
      return;
    }
    const r = await api("POST", "/api/alerts/" + id + "/ack", { operator: $("ackOperator").value, remarks: $("ackRemarks").value });
    showResult($("ackResult"), r.ok, r.ok ? r.data.message : r.data.error);
    refresh();
  });

  $("overrideForm").addEventListener("submit", async function (e) {
    e.preventDefault();
    const action = document.querySelector('input[name="ovAction"]:checked');
    const r = await api("POST", "/api/override", {
      room_id: currentRoom,
      appliance: $("ovAppliance").value,
      action: action ? action.value : "",
      operator: $("ovOperator").value,
      reason: $("ovReason").value
    });
    showResult($("ovResult"), r.ok, r.ok ? r.data.message : r.data.error);
    refresh();
  });

  $("settingsForm").addEventListener("submit", async function (e) {
    e.preventDefault();
    const r = await api("PUT", "/api/settings", {
      vacancy_frames: numberOrText($("setFrames").value),
      wait_seconds: numberOrText($("setWait").value),
      delta_t_threshold: numberOrText($("setThreshold").value)
    });
    showResult($("setResult"), r.ok, r.ok ? r.data.message : withLabel(r.data.error));
  });

  loadSettings();
  refresh();
  setInterval(refresh, 2000);
})();
