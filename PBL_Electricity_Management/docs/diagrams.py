"""Draws the architecture and state-transition diagrams used in the PBL report and presentation."""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch  # noqa: E402

OUT = Path(__file__).resolve().parent / "figures"
INK = "#1b2430"


def box(ax, x, y, w, h, title, lines=(), fill="#ffffff", edge=INK, title_size=10.5):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.12",
                                facecolor=fill, edgecolor=edge, linewidth=1.3, zorder=2))
    ax.text(x + w / 2, y + h - 0.28, title, ha="center", va="top", fontsize=title_size, fontweight="bold",
            color=INK, zorder=3)
    for i, line in enumerate(lines):
        ax.text(x + w / 2, y + h - 0.68 - i * 0.34, line, ha="center", va="top", fontsize=8.6, color="#3b4352",
                zorder=3)


def arrow(ax, p, q, label="", offset=(0, 0.16), both=False, rad=0.0):
    ax.add_patch(FancyArrowPatch(p, q, arrowstyle="<|-|>" if both else "-|>", mutation_scale=13, color=INK,
                                 linewidth=1.2, connectionstyle="arc3,rad=%s" % rad, zorder=1))
    if label:
        ax.text((p[0] + q[0]) / 2 + offset[0], (p[1] + q[1]) / 2 + offset[1], label, ha="center", va="center",
                fontsize=8.3, color="#14532d", fontweight="bold", zorder=4,
                bbox=dict(boxstyle="round,pad=0.15", facecolor="white", edgecolor="none"))


def architecture():
    fig, ax = plt.subplots(figsize=(11, 6.2))
    # region labels
    ax.add_patch(FancyBboxPatch((0.2, 0.3), 3.5, 7.0, boxstyle="round,pad=0.02,rounding_size=0.15",
                                facecolor="#f4f6f9", edgecolor="#9aa3b2", linewidth=1, linestyle="--", zorder=0))
    ax.text(1.95, 7.05, "Classroom node (simulated in this PBL)", ha="center", fontsize=9.5, color="#5d6676")
    ax.add_patch(FancyBboxPatch((4.4, 0.3), 9.3, 7.0, boxstyle="round,pad=0.02,rounding_size=0.15",
                                facecolor="#f2f8f4", edgecolor="#86b49a", linewidth=1, linestyle="--", zorder=0))
    ax.text(9.05, 7.05, "Server - Python 3.11 (implemented modules)", ha="center", fontsize=9.5, color="#14532d")

    box(ax, 0.5, 5.0, 2.9, 1.6, "CCTV + YOLOv8", ["people, fans ON,", "lights ON per frame"])
    box(ax, 0.5, 2.95, 2.9, 1.6, "4 x DHT11 sensors", ["one per room region", "0 - 50 deg C"])
    box(ax, 0.5, 0.75, 2.9, 1.7, "ESP32 controller", ["polls pending commands,", "relays for fans / lights"])

    box(ax, 4.8, 3.2, 3.0, 2.6, "REST API", ["app/server.py", "/api/readings", "/api/alerts, /api/override", "/api/commands, /api/settings"],
        fill="#ffffff")
    box(ax, 8.6, 4.6, 4.7, 2.0, "Module 1: Detection Engine", ["app/engine.py - frame validation,", "vacancy, wastage alerts, Delta T"],
        fill="#dcfce7", edge="#166534")
    box(ax, 8.6, 2.2, 4.7, 1.9, "SQLite database", ["rooms, readings, alerts,", "commands, settings  (app/db.py)"],
        fill="#ffffff")
    box(ax, 4.8, 0.6, 8.5, 1.3, "Module 2: Web Dashboard  (app/static)",
        ["status + heatmap · acknowledge alerts · manual override · settings"], fill="#dcfce7", edge="#166534")

    arrow(ax, (3.4, 5.8), (4.8, 5.0), "frames", offset=(0, 0.3))
    arrow(ax, (3.4, 3.75), (4.8, 4.2), "temps", offset=(0, -0.28))
    arrow(ax, (3.4, 1.6), (4.8, 3.4), "commands", offset=(-0.15, 0.1), both=True)
    arrow(ax, (7.8, 5.2), (8.6, 5.6), "", both=True)
    arrow(ax, (7.8, 3.8), (8.6, 3.4), "", both=True)
    arrow(ax, (6.3, 3.2), (6.3, 1.9), "HTTP + JSON", offset=(0.75, 0), both=True)
    ax.set_xlim(0, 13.9)
    ax.set_ylim(0.1, 7.5)
    ax.set_aspect("equal")
    ax.axis("off")
    fig.savefig(OUT / "architecture.png", dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def polyline_arrow(ax, points, label, label_at):
    xs, ys = zip(*points)
    ax.plot(xs[:-1], ys[:-1], color=INK, linewidth=1.2, zorder=1)
    ax.add_patch(FancyArrowPatch(points[-2], points[-1], arrowstyle="-|>", mutation_scale=13, color=INK,
                                 linewidth=1.2, zorder=1))
    ax.text(label_at[0], label_at[1] - 0.12, label, ha="center", va="top", fontsize=8.6, color="#14532d",
            fontweight="bold", zorder=4)


def states():
    fig, ax = plt.subplots(figsize=(13, 4.8))
    w, h, y = 2.5, 1.0, 3.0
    xs = {"NO_DATA": 0.2, "OCCUPIED": 4.6, "CHECKING_AC": 9.0, "VACANT": 13.4}
    fills = {"NO_DATA": "#e5e7eb", "OCCUPIED": "#dcfce7", "CHECKING_AC": "#fef3c7", "VACANT": "#e0e7ff"}
    for name, x in xs.items():
        box(ax, x, y, w, h, name.replace("_", " "), fill=fills[name], title_size=11)
    ax.text(xs["CHECKING_AC"] + w / 2, y + h + 0.95, "FAN_ON / LIGHT_ON_VACANT alerts while vacant",
            ha="center", fontsize=8.6, color="#a31f1f")
    ax.text(xs["VACANT"] + w / 2, y + h + 0.45, "AC_ON_VACANT if mean drop >= threshold",
            ha="center", fontsize=8.6, color="#a31f1f")
    cy = y + h / 2
    for a, b, label in (("NO_DATA", "OCCUPIED", "first frame"), ("OCCUPIED", "CHECKING_AC", "N empty\nframes"),
                        ("CHECKING_AC", "VACANT", "wait_seconds\npassed")):
        x0, x1 = xs[a] + w, xs[b]
        arrow(ax, (x0 + 0.05, cy), (x1 - 0.05, cy))
        ax.text((x0 + x1) / 2, cy + 0.12, label, ha="center", va="bottom", fontsize=8.6, color="#14532d",
                fontweight="bold", linespacing=1.1)
    occ = xs["OCCUPIED"]
    chk = xs["CHECKING_AC"] + w / 2
    vac = xs["VACANT"] + w / 2
    polyline_arrow(ax, [(chk, y), (chk, 2.0), (occ + 1.6, 2.0), (occ + 1.6, y - 0.03)],
                   "people > 0 (AC check cancelled)", ((chk + occ + 1.6) / 2, 2.0))
    polyline_arrow(ax, [(vac, y), (vac, 1.0), (occ + 0.9, 1.0), (occ + 0.9, y - 0.03)],
                   "people > 0", ((vac + occ + 0.9) / 2, 1.0))
    ax.set_xlim(0, 16.1)
    ax.set_ylim(0.4, 5.2)
    ax.set_aspect("equal")
    ax.axis("off")
    fig.savefig(OUT / "state_diagram.png", dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    architecture()
    states()
    print("saved", sorted(p.name for p in OUT.glob("*.png")))
