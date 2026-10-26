"""Executes every PBL test case and records the actual result of each one.

    python -m tests.run_tests run1          (label is used in the output file names)

Writes results/<label>.json and results/<label>-console.txt. Module 1, Module 2 API and integration cases
run in Python; the dashboard UI cases run in headless Microsoft Edge against a seeded server.
"""
import html
import json
import re
import subprocess
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path

from . import api_cases, engine_cases
from .helpers import TestServer

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "results"
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"


def run_python_cases(cases):
    out = []
    for c in cases:
        try:
            actual = c["run"]()
        except Exception as e:  # a crash is recorded as the actual result, never hidden
            actual = "ERROR: %s: %s" % (type(e).__name__, e)
        out.append({k: c[k] for k in ("id", "module", "technique", "scenario", "data", "expected")}
                   | {"actual": actual, "status": "PASS" if actual == c["expected"] else "FAIL"})
    return out


def run_ui_cases():
    srv = TestServer(extra_static={"ui-tests": ROOT / "tests" / "ui"})
    try:
        api_cases.seed_vacancy(srv)
        with tempfile.TemporaryDirectory() as profile:
            proc = subprocess.run(
                [EDGE, "--headless=new", "--disable-gpu", "--no-first-run", "--user-data-dir=" + profile,
                 "--virtual-time-budget=120000", "--dump-dom", srv.base + "/ui-tests/run.html"],
                capture_output=True, text=True, encoding="utf-8", timeout=300)
        m = re.search(r'<pre id="results-json" hidden="">(.*?)</pre>', proc.stdout, re.S)
        if not m:
            raise RuntimeError("UI run did not finish; Edge output: %s" % proc.stdout[-500:])
        return json.loads(html.unescape(m.group(1)))
    finally:
        srv.stop()


def main():
    label = sys.argv[1] if len(sys.argv) > 1 else "run"
    sys.stdout.reconfigure(encoding="utf-8")
    RESULTS.mkdir(exist_ok=True)
    started = datetime.now()
    t0 = time.time()
    results = run_python_cases(engine_cases.CASES) + run_python_cases(api_cases.CASES) + run_ui_cases()
    lines = ["PBL test run '%s' - %s" % (label, started.strftime("%d-%m-%Y %H:%M:%S")), ""]
    for r in results:
        lines.append("%-10s %-4s  %s" % (r["id"], r["status"], r["scenario"]))
        if r["status"] == "FAIL":
            lines.append("           expected: %s" % r["expected"])
            lines.append("           actual  : %s" % r["actual"])
    passed = sum(r["status"] == "PASS" for r in results)
    lines += ["", "%d test cases executed, %d passed, %d failed (%.1f s)"
              % (len(results), passed, len(results) - passed, time.time() - t0)]
    console = "\n".join(lines)
    print(console)
    (RESULTS / (label + "-console.txt")).write_text(console + "\n", encoding="utf-8")
    (RESULTS / (label + ".json")).write_text(json.dumps(
        {"label": label, "executed_at": started.isoformat(timespec="seconds"), "results": results},
        indent=2, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
