"""Turns the recorded result of chosen test cases in one run into a screenshot (for API-level bugs, which have no
page to photograph).

    python -m tests.console_evidence run3 evidence/bugs/BUG-02_before.png TC_INT_10
"""
import html
import json
import sys
from pathlib import Path

from .run_tests import RESULTS, edge


def main():
    label, out, ids = sys.argv[1], Path(sys.argv[2]).resolve(), sys.argv[3:]
    run = json.loads((RESULTS / (label + ".json")).read_text(encoding="utf-8"))
    rows = [r for r in run["results"] if r["id"] in ids]
    blocks = []
    for r in rows:
        blocks.append(
            '<div class="tc"><b>%s</b> <span class="%s">%s</span> - %s<br>'
            '<span class="k">technique</span> %s<br><span class="k">test data</span> %s<br>'
            '<span class="k">expected </span> %s<br><span class="k">actual   </span> %s</div>'
            % tuple(html.escape(x) for x in (r["id"], r["status"], r["status"], r["scenario"], r["technique"],
                                              r["data"], r["expected"], r["actual"])))
    page = """<!doctype html><meta charset="utf-8"><style>
      body { margin: 0; padding: 14px 18px; background: #0f172a; color: #e2e8f0; font: 14px Consolas, monospace; }
      .head { color: #94a3b8; margin-bottom: 10px; } .tc { margin-bottom: 14px; line-height: 1.5; }
      .k { color: #94a3b8; } .PASS { color: #4ade80; font-weight: 700; } .FAIL { color: #f87171; font-weight: 700; }
      b { color: #fff; }</style>
      <div class="head">&gt; python -m tests.run_tests %s &nbsp;&nbsp;(executed %s)</div>%s""" % (
        html.escape(label), html.escape(run["executed_at"].replace("T", " ")), "".join(blocks))
    tmp = out.with_suffix(".html")
    tmp.write_text(page, encoding="utf-8")
    edge(["--hide-scrollbars", "--window-size=1100,%d" % (60 + 130 * len(rows)), "--screenshot=" + str(out),
          tmp.as_uri()], 120)
    tmp.unlink()
    print("saved", out)


if __name__ == "__main__":
    main()
