"""Draws the control flow graphs (CFGs) used in the Expt-9 report and checks V(G) = E - N + 2 for each.

Each node is a circle with its number; decision nodes are shaded blue, return/exit nodes orange.
Edges may pass through waypoints so that no edge runs through a node.
"""
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Circle, FancyArrowPatch  # noqa: E402

HERE = Path(__file__).resolve().parent
R = 0.3
INK = "#1f2d3d"
FILL = {"decision": "#dce6f2", "stmt": "#ffffff", "return": "#fde9d9", "exit": "#f4c7a1"}


def _toward(p, q, dist):
    dx, dy = q[0] - p[0], q[1] - p[1]
    d = math.hypot(dx, dy)
    return (p[0] + dx * dist / d, p[1] + dy * dist / d)


def draw(name, title, nodes, edges, figsize):
    fig, ax = plt.subplots(figsize=figsize)
    for nid, (x, y, kind) in nodes.items():
        ax.add_patch(Circle((x, y), R, facecolor=FILL[kind], edgecolor=INK, linewidth=1.4, zorder=3))
        ax.text(x, y, str(nid), ha="center", va="center", fontsize=11, fontweight="bold", color=INK, zorder=4)

    for src, dst, label, via in edges:
        pts = [nodes[src][:2]] + list(via) + [nodes[dst][:2]]
        pts[0] = _toward(pts[0], pts[1], R)
        pts[-1] = _toward(pts[-1], pts[-2], R)
        for a, b in zip(pts[:-2], pts[1:-1]):
            ax.plot([a[0], b[0]], [a[1], b[1]], color=INK, linewidth=1.2, zorder=1, solid_capstyle="round")
        ax.add_patch(FancyArrowPatch(pts[-2], pts[-1], arrowstyle="-|>", mutation_scale=13, color=INK,
                                     linewidth=1.2, shrinkA=0, shrinkB=0, zorder=2))
        if label:
            (x0, y0), (x1, y1) = pts[0], pts[1]
            seg = math.hypot(x1 - x0, y1 - y0)
            t = min(0.42, 0.42 / seg) if seg > 1 else 0.45
            mx, my = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t
            nx, ny = -(y1 - y0) / seg, (x1 - x0) / seg  # unit normal (left of direction)
            ax.text(mx + nx * 0.17, my + ny * 0.17, label, ha="center", va="center", fontsize=9,
                    fontweight="bold", color="#a32020" if label == "F" else "#17663a", zorder=5)

    xs = [p[0] for p in nodes.values()] + [w[0] for e in edges for w in e[3]]
    ys = [p[1] for p in nodes.values()] + [w[1] for e in edges for w in e[3]]
    ax.set_xlim(min(xs) - 0.6, max(xs) + 0.6)
    ax.set_ylim(min(ys) - 0.6, max(ys) + 0.9)
    ax.text((min(xs) + max(xs)) / 2, max(ys) + 0.6, title, ha="center", va="center", fontsize=11, color=INK)
    ax.set_aspect("equal")
    ax.axis("off")
    out = HERE / (name + ".png")
    fig.savefig(out, dpi=220, bbox_inches="tight", facecolor="white")
    plt.close(fig)

    n, e = len(nodes), len(edges)
    decisions = sum(1 for v in nodes.values() if v[2] == "decision")
    print("%s: N=%d E=%d V(G)=E-N+2=%d, predicate nodes P=%d -> P+1=%d" % (name, n, e, e - n + 2, decisions, decisions + 1))


# ---------- Part 1: Triangle.classify() ----------
TRIANGLE_NODES = {
    1: (0, 0, "decision"), 2: (0, -1.2, "decision"), 3: (0, -2.4, "decision"), 4: (2.4, -1.2, "return"),
    5: (0, -3.6, "decision"), 6: (0, -4.8, "decision"), 7: (0, -6.0, "decision"), 8: (2.4, -4.8, "return"),
    9: (0, -7.2, "decision"), 10: (-1.6, -8.4, "decision"), 11: (-2.4, -9.6, "return"),
    12: (-0.8, -9.6, "return"), 13: (1.6, -8.4, "decision"), 14: (2.4, -9.6, "decision"),
    15: (1.2, -10.8, "return"), 16: (3.4, -10.8, "return"), 17: (0, -12.2, "exit"),
}
TRIANGLE_EDGES = [
    (1, 4, "T", []), (1, 2, "F", []), (2, 4, "T", []), (2, 3, "F", []), (3, 4, "T", []), (3, 5, "F", []),
    (5, 8, "T", []), (5, 6, "F", []), (6, 8, "T", []), (6, 7, "F", []), (7, 8, "T", []), (7, 9, "F", []),
    (9, 10, "T", []), (9, 13, "F", []), (10, 11, "T", []), (10, 12, "F", []),
    (13, 15, "T", []), (13, 14, "F", []), (14, 15, "T", []), (14, 16, "F", []),
    (4, 17, "", [(4.4, -1.2), (4.4, -12.2)]), (8, 17, "", [(3.9, -4.8), (3.9, -11.6)]),
    (11, 17, "", []), (12, 17, "", []), (15, 17, "", []), (16, 17, "", []),
]

# ---------- Part 2: EligibilityCriteria.parseBranches() ----------
PARSE_NODES = {
    1: (0, 0, "stmt"), 2: (0, -1.3, "decision"), 3: (2.6, -1.3, "return"), 4: (0, -2.6, "decision"),
    5: (0, -3.9, "stmt"), 6: (0, -5.2, "decision"), 7: (0, -6.5, "decision"), 8: (1.6, -6.5, "return"),
    9: (0, -7.8, "decision"), 10: (0, -9.1, "stmt"), 11: (-2.6, -2.6, "return"), 12: (0, -11.4, "exit"),
}
PARSE_EDGES = [
    (1, 2, "", []), (2, 3, "T", []), (2, 4, "F", []), (3, 12, "", [(2.6, -11.4)]),
    (4, 5, "T", []), (4, 11, "F", []), (5, 6, "", []),
    (6, 4, "T", [(-0.9, -5.2), (-0.9, -3.2)]), (6, 7, "F", []),
    (7, 8, "T", []), (7, 9, "F", []), (8, 12, "", []),
    (9, 10, "T", []), (9, 4, "F", [(-1.3, -7.8), (-1.3, -3.0)]),
    (10, 4, "", [(-1.7, -9.1), (-1.7, -2.85)]), (11, 12, "", [(-2.6, -11.4)]),
]

# ---------- Part 2: EligibilityCriteria.getReasons() ----------
REASONS_NODES = {1: (0, 1.3, "stmt"), 14: (0, -10.4, "exit")}
REASONS_EDGES = [(1, 2, "", [])]
for k, (d1, d2, add, nxt) in enumerate([(2, 3, 4, 5), (5, 6, 7, 8), (8, 9, 10, 11), (11, 12, 13, 14)]):
    y0 = -k * 2.6
    REASONS_NODES[d1] = (0, y0, "decision")
    REASONS_NODES[d2] = (1.3, y0 - 0.8, "decision")
    REASONS_NODES[add] = (2.6, y0 - 1.6, "stmt")
    REASONS_EDGES += [(d1, d2, "T", []), (d1, nxt, "F", []), (d2, add, "T", []), (d2, nxt, "F", []),
                      (add, nxt, "", [])]

if __name__ == "__main__":
    draw("cfg_triangle_classify", "CFG of Triangle.classify()", TRIANGLE_NODES, TRIANGLE_EDGES, (6.2, 10.5))
    draw("cfg_eligibility_parseBranches", "CFG of EligibilityCriteria.parseBranches()", PARSE_NODES, PARSE_EDGES,
         (6.0, 9.5))
    draw("cfg_eligibility_getReasons", "CFG of EligibilityCriteria.getReasons()", REASONS_NODES, REASONS_EDGES,
         (5.0, 10.5))
