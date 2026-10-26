"""Draws the architecture diagram of the PBL prototype used in the report and presentation.

    python docs/diagrams.py   -> docs/figures/architecture.png
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch  # noqa: E402

OUT = Path(__file__).resolve().parent / "figures"
INK = "#1b2430"
BRAND = "#1e3a8a"


def box(ax, x, y, w, h, title, lines=(), fill="#ffffff", edge=INK, title_size=10.5):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.12",
                                facecolor=fill, edgecolor=edge, linewidth=1.3, zorder=2))
    ax.text(x + w / 2, y + h - 0.25, title, ha="center", va="top", fontsize=title_size, fontweight="bold",
            color=INK, zorder=3)
    for i, line in enumerate(lines):
        ax.text(x + w / 2, y + h - 0.66 - i * 0.33, line, ha="center", va="top", fontsize=8.4, color="#3b4352",
                zorder=3)


def arrow(ax, p, q, label="", offset=(0, 0.16), both=False):
    ax.add_patch(FancyArrowPatch(p, q, arrowstyle="<|-|>" if both else "-|>", mutation_scale=13, color=INK,
                                 linewidth=1.2, zorder=1))
    if label:
        ax.text((p[0] + q[0]) / 2 + offset[0], (p[1] + q[1]) / 2 + offset[1], label, ha="center", va="center",
                fontsize=8.2, color=BRAND, fontweight="bold", zorder=4,
                bbox=dict(boxstyle="round,pad=0.15", facecolor="white", edgecolor="none"))


def architecture():
    fig, ax = plt.subplots(figsize=(11.5, 6.4))
    tiers = [(0.2, "Presentation tier (browser)", "#f4f6f9", "#9aa3b2"),
             (4.25, "Application tier (Python REST API)", "#eef2fb", "#8ea2d6"),
             (9.15, "Data tier", "#f4f6f9", "#9aa3b2")]
    widths = [3.6, 4.5, 2.65]
    for (x, label, fill, edge), w in zip(tiers, widths):
        ax.add_patch(FancyBboxPatch((x, 0.3), w, 6.9, boxstyle="round,pad=0.02,rounding_size=0.15",
                                    facecolor=fill, edgecolor=edge, linewidth=1, linestyle="--", zorder=0))
        ax.text(x + w / 2, 6.95, label, ha="center", fontsize=9.5, color="#5d6676")

    box(ax, 0.45, 4.65, 3.1, 1.9, "Student page", ["profile, job board + eligibility,", "apply form, my applications,",
                                                    "timeline, notifications"])
    box(ax, 0.45, 2.55, 3.1, 1.8, "Recruiter page", ["post / resubmit job,", "my postings, applicants",
                                                      "and next steps"])
    box(ax, 0.45, 0.55, 3.1, 1.7, "Placement Officer page", ["pending approvals, decision", "form, all postings"])

    box(ax, 4.5, 5.1, 4.0, 1.55, "server.py - REST API", ["routes, actor checks (BR-02, BR-07),",
                                                            "locking, /api/version for live updates"],
        fill="#ffffff", edge=BRAND)
    box(ax, 4.5, 2.75, 4.0, 2.0, "Module 1: Job Posting &", ["Eligibility Verification",
                                                              "validate_job_posting(), decision rules,",
                                                              "EligibilityCriteria.evaluate()", "job board search + paging"],
        fill="#dbe4fb", edge=BRAND, title_size=10)
    box(ax, 4.5, 0.55, 4.0, 1.9, "Module 2: Job Application &", ["Tracking",
                                                                  "apply checks + rollback, statechart",
                                                                  "next_state(), withdraw, offers,",
                                                                  "history and notifications"],
        fill="#dbe4fb", edge=BRAND, title_size=10)

    box(ax, 9.35, 1.2, 2.25, 4.9, "SQLite (db.py)", ["students", "companies", "recruiters", "placement_officers",
                                                     "resumes", "jobs", "applications", "application_history",
                                                     "eligibility_checks", "notifications"])

    arrow(ax, (3.55, 5.75), (4.5, 5.75), both=True)
    ax.text(4.02, 6.25, "JSON / HTTP", ha="center", fontsize=8.0, color=BRAND, fontweight="bold")
    ax.text(4.14, 5.45, "polls\nevery\n2 s", ha="center", va="top", fontsize=7.4, color="#5d6676")
    for y in (3.6, 1.4):   # each page also uses the API (one shared line, arrows drawn once above)
        ax.plot([3.55, 3.75], [y, y], color="#9aa3b2", linewidth=1, linestyle=":")
    ax.plot([3.75, 3.75], [1.4, 5.75], color="#9aa3b2", linewidth=1, linestyle=":")
    arrow(ax, (6.5, 5.1), (6.5, 4.75))
    arrow(ax, (6.5, 2.75), (6.5, 2.45))
    ax.text(6.62, 2.6, "eligibility check before apply", fontsize=7.6, color="#5d6676", va="center")
    arrow(ax, (8.5, 3.75), (9.35, 3.9), "SQL", both=True)
    arrow(ax, (8.5, 1.5), (9.35, 2.0), "SQL", both=True)

    ax.set_xlim(0, 12)
    ax.set_ylim(0, 7.4)
    ax.axis("off")
    fig.tight_layout()
    fig.savefig(OUT / "architecture.png", dpi=170)
    plt.close(fig)


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    architecture()
    print("saved", OUT / "architecture.png")
