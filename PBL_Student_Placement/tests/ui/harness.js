// Shared by run.html (all UI cases) and show.html (evidence screenshot of one case).
function sleep(ms) { return new Promise((r) => setTimeout(r, ms)); }

async function waitFor(cond, timeout = 5000) {
  const start = Date.now();
  while (Date.now() - start < timeout) {
    try { if (cond()) return; } catch (e) { /* page still loading */ }
    await sleep(50);
  }
  throw new Error("timed out waiting for the page");
}

// Loads the page as the case's acting user; window.confirm answers as the case says and is recorded.
function openPage(frame, tc) {
  return new Promise((resolve, reject) => {
    frame.style.width = (tc.width || 1200) + "px";
    frame.onload = async () => {
      try {
        const win = frame.contentWindow;
        win.__confirms = [];
        win.confirm = (msg) => { win.__confirms.push(msg); return tc.confirm !== false; };
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
