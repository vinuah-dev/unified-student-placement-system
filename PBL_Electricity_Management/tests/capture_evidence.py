"""Captures dashboard screenshots for the report: each shot starts a fresh seeded server, runs one UI test
case through tests/ui/show.html in headless Edge and saves the page.

    python -m tests.capture_evidence evidence/bugs BUG-01_before:TC_UI_01 BUG-04_before:TC_UI_14:settingsCard
    (each item is  file_name:test_case[:element_to_scroll_to[:WIDTHxHEIGHT]])
"""
import subprocess
import sys
import tempfile
from pathlib import Path

from . import api_cases
from .helpers import TestServer
from .run_tests import EDGE, ROOT


def capture(out_dir, name, case_id, scroll=None, size="1280,900"):
    srv = TestServer(extra_static={"ui-tests": ROOT / "tests" / "ui"})
    try:
        api_cases.seed_vacancy(srv)
        url = srv.base + "/ui-tests/show.html?tc=" + case_id + ("&scroll=" + scroll if scroll else "")
        out = (Path(out_dir) / (name + ".png")).resolve()
        with tempfile.TemporaryDirectory() as profile:
            subprocess.run([EDGE, "--headless=new", "--disable-gpu", "--no-first-run", "--hide-scrollbars",
                            "--user-data-dir=" + profile, "--virtual-time-budget=20000", "--window-size=" + size,
                            "--screenshot=" + str(out), url], capture_output=True, timeout=120)
        print("saved", out)
    finally:
        srv.stop()


def main():
    out_dir = Path(sys.argv[1])
    out_dir.mkdir(parents=True, exist_ok=True)
    for item in sys.argv[2:]:
        parts = item.split(":")
        capture(out_dir, parts[0], parts[1], (parts[2] if len(parts) > 2 else "") or None,
                parts[3].replace("x", ",") if len(parts) > 3 else "1280,900")


if __name__ == "__main__":
    main()
