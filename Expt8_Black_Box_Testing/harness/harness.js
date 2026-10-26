// Helpers used by the black box test cases: they only use what a user can do on the page - choose values,
// type, press buttons - and read what the page displays.
function sleep(ms) { return new Promise((r) => setTimeout(r, ms)); }

async function waitFor(cond, timeout = 6000) {
  const start = Date.now();
  while (Date.now() - start < timeout) {
    try { if (cond()) return; } catch (e) { /* page still loading */ }
    await sleep(50);
  }
  throw new Error("timed out waiting for the page");
}

// Loads the USPS page as the case's user; a confirmation dialog is answered OK.
function openPage(frame, tc) {
  return new Promise((resolve, reject) => {
    frame.onload = async () => {
      try {
        frame.contentWindow.confirm = () => true;
        const doc = frame.contentDocument;
        await waitFor(() => doc.body.dataset.ready === "1" && doc.body.dataset.busy === "0", 8000);
        resolve(doc);
      } catch (e) {
        reject(e);
      }
    };
    frame.src = "/" + tc.page + "&t=" + Date.now();
  });
}

function text(doc, id) { return doc.getElementById(id).textContent.trim(); }

async function idle(doc) { await sleep(60); await waitFor(() => doc.body.dataset.busy !== "1"); }

function setValue(doc, id, v) {
  const el = doc.getElementById(id);
  el.value = v;
  el.dispatchEvent(new Event("input"));
  el.dispatchEvent(new Event("change"));
}

async function submit(doc, formId, resultId) {
  const res = doc.getElementById(resultId);
  res.className = "result";
  res.textContent = "";
  doc.querySelector("#" + formId + ' button[type="submit"]').click();
  await waitFor(() => /success|error/.test(res.className));
  await idle(doc);
  return text(doc, resultId);
}
