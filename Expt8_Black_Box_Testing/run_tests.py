"""Executes the Expt-8 black box test cases through the USPS website and records the actual outputs.

    python run_tests.py              -> evidence/test-results.json, evidence/console.txt
    python run_tests.py --shots      -> also evidence/screenshots/<TC>.png for the cases in SHOTS

Every test case gets its own server with the pre-loaded data (clock fixed at 26-10-2026 10:00) and its own
headless Microsoft Edge, which opens harness/case.html?tc=<id>. The website is the PBL prototype in
../PBL_Student_Placement.
"""
import html
import json
import re
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
USPS = HERE.parent / "PBL_Student_Placement"
sys.path.insert(0, str(USPS))
from tests.helpers import TestServer  # noqa: E402  (the USPS test server: fresh database, fixed clock)

EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
EVIDENCE = HERE / "evidence"
SHOTS = {"TC_PJ_01": "postCard", "TC_PJ_05": "postCard", "TC_PJ_21": "postCard", "TC_JD_01": "approvalCard",
         "TC_JD_07": "approvalCard", "TC_AJ_01": "applyCard", "TC_AJ_04": "applyCard", "TC_AJ_10": "applyCard",
         "TC_JS_03": "jobsCard", "TC_JS_09": "jobsCard"}


def case_ids():
    return re.findall(r'^\s+\w+\("(TC_\w+)"', (HERE / "harness" / "testcases.js").read_text(encoding="utf-8"), re.M)


def edge(args, timeout=120):
    with tempfile.TemporaryDirectory() as profile:
        return subprocess.run([EDGE, "--headless=new", "--disable-gpu", "--no-first-run", "--hide-scrollbars",
                               "--user-data-dir=" + profile] + args,
                              capture_output=True, text=True, encoding="utf-8", timeout=timeout)


def run_case(tc):
    srv = TestServer(extra_static={"bbt": HERE / "harness"})
    try:
        out = edge(["--virtual-time-budget=60000", "--dump-dom", srv.base + "/bbt/case.html?tc=" + tc])
        m = re.search(r'<pre id="result" hidden="">(.*?)</pre>', out.stdout, re.S)
        if not m:
            return {"id": tc, "status": "FAIL", "actual": "ERROR: test page did not finish"}
        return json.loads(html.unescape(m.group(1)))
    finally:
        srv.stop()


def screenshot(tc, scroll):
    srv = TestServer(extra_static={"bbt": HERE / "harness"})
    try:
        target = EVIDENCE / "screenshots" / (tc + ".png")
        edge(["--virtual-time-budget=60000", "--window-size=1280,900", "--screenshot=" + str(target),
              srv.base + "/bbt/case.html?tc=%s&scroll=%s" % (tc, scroll)])
        return target
    finally:
        srv.stop()


def summary_image():
    """Screenshot of the console summary of the run (evidence/run-summary.png)."""
    text = (EVIDENCE / "console.txt").read_text(encoding="utf-8").rstrip("\n")
    rows = text.count("\n") + 1
    page = EVIDENCE / "run-summary.html"
    page.write_text('<!doctype html><meta charset="utf-8"><body style="margin:0;padding:14px 18px;background:#0f172a;'
                    'color:#e2e8f0;font:13px Consolas,monospace"><pre style="margin:0">%s</pre>'
                    % html.escape(text).replace(" PASS ", ' <b style="color:#4ade80">PASS</b> ')
                    .replace(" FAIL ", ' <b style="color:#f87171">FAIL</b> '), encoding="utf-8")
    edge(["--window-size=760,%d" % (30 + rows * 17), "--screenshot=" + str(EVIDENCE / "run-summary.png"),
          page.as_uri()])
    page.unlink()


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    if "--summary-only" in sys.argv:
        return summary_image()
    started = datetime.now()
    ids = case_ids()
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(run_case, ids))
    passed = sum(r["status"] == "PASS" for r in results)
    lines = ["Expt-8 black box test run - %s" % started.strftime("%d-%m-%Y %H:%M:%S"), ""]
    for r in results:
        lines.append("%-9s %-4s  %s" % (r["id"], r["status"], r.get("scenario", "")))
        if r["status"] == "FAIL":
            lines += ["          expected: %s" % r.get("expected"), "          actual  : %s" % r["actual"]]
    lines += ["", "%d test cases executed, %d passed, %d failed" % (len(results), passed, len(results) - passed)]
    print("\n".join(lines))
    EVIDENCE.mkdir(exist_ok=True)
    (EVIDENCE / "console.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (EVIDENCE / "test-results.json").write_text(json.dumps(
        {"executedAt": started.strftime("%d-%m-%Y %H:%M:%S"), "serverDate": "26-10-2026 10:00",
         "userAgent": next((r["userAgent"] for r in results if "userAgent" in r), ""), "results": results},
        indent=2, ensure_ascii=False), encoding="utf-8")
    summary_image()
    if "--shots" in sys.argv:
        (EVIDENCE / "screenshots").mkdir(parents=True, exist_ok=True)
        with ThreadPoolExecutor(max_workers=4) as pool:
            for path in pool.map(lambda kv: screenshot(*kv), SHOTS.items()):
                print("saved", path)


if __name__ == "__main__":
    main()
