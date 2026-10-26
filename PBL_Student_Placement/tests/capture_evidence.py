"""Captures page screenshots for the report: each shot starts a fresh server with the demo data, replays the UI
cases up to the chosen one through tests/ui/show.html in headless Edge and saves the page.

    python -m tests.capture_evidence evidence/ui TC_UI_11:TC_UI_11 BUG-01_after:TC_UI_21:applicantsCard
    (each item is  file_name:test_case[:element_to_scroll_to[:WIDTHxHEIGHT]])
"""
import sys
from pathlib import Path

from .helpers import TestServer
from .run_tests import UI_STATIC, edge


def capture(out_dir, name, case_id, scroll=None, size="1280,900"):
    srv = TestServer(extra_static=UI_STATIC)
    try:
        url = srv.base + "/ui-tests/show.html?tc=" + case_id + ("&scroll=" + scroll if scroll else "")
        out = (Path(out_dir) / (name + ".png")).resolve()
        edge(["--hide-scrollbars", "--virtual-time-budget=300000", "--window-size=" + size, "--screenshot=" + str(out),
              url], 300)
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
