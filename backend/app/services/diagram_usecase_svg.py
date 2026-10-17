"""Use-case diagram renderer: pure Python -> SVG string.

Mermaid has no real use-case diagram, so we lay it out ourselves:
  * internal actors on the left, external systems on the right
  * one system boundary in the middle with one ellipse per use case
  * use cases are ordered by actor, and each actor sits at the vertical centre
    of its own use cases, so association lines are short and rarely cross
  * include / extend relations are dashed arcs on the right side of the boundary
Deterministic: same model in -> same SVG out."""
import math
import textwrap
from html import escape

from app.schemas.diagrams import UseCaseModel

ELL_W, ELL_H, PITCH = 230, 54, 78
SIDE = 170            # width reserved for actors on each side
BOX_W = 400           # system boundary width
TOP = 50
MIN_ACTOR_GAP = 125
INK, SOFT, FILL = "#262626", "#a3a3a3", "#fafafa"


def _lines(text: str, width: int = 22, max_lines: int = 2) -> list[str]:
    parts = textwrap.wrap(text, width=width) or [""]
    if len(parts) > max_lines:
        parts = parts[:max_lines]
        parts[-1] = parts[-1][: width - 1].rstrip() + "…"
    return parts


def _text(x: float, y: float, lines: list[str], size: int = 13, weight: str = "400", anchor: str = "middle") -> str:
    lh = size + 3
    y0 = y - (len(lines) - 1) * lh / 2
    spans = "".join(f'<tspan x="{x:.1f}" y="{y0 + i * lh:.1f}">{escape(l)}</tspan>' for i, l in enumerate(lines))
    return (f'<text text-anchor="{anchor}" dominant-baseline="middle" font-size="{size}" '
            f'font-weight="{weight}" fill="{INK}">{spans}</text>')


def _ellipse_edge(cx: float, cy: float, rx: float, ry: float, px: float, py: float) -> tuple[float, float]:
    """Point on the ellipse border in the direction of (px, py)."""
    dx, dy = px - cx, py - cy
    k = math.sqrt((dx / rx) ** 2 + (dy / ry) ** 2) or 1
    return cx + dx / k, cy + dy / k


def layout(m: UseCaseModel) -> dict:
    """Return positions. Separated from drawing so tests can check geometry."""
    left = [a for a in m.actors if not a.external]
    right = [a for a in m.actors if a.external]
    order = {a.name: i for i, a in enumerate(left + right)}
    ucs = sorted(m.use_cases, key=lambda u: order.get(u.actor, 99))  # stable within an actor

    x0 = SIDE
    cx = x0 + 50 + ELL_W / 2
    rows = {}
    for i, u in enumerate(ucs):
        rows[u.id] = (cx, TOP + 64 + i * PITCH + ELL_H / 2)
    box_h = 64 + max(len(ucs), 1) * PITCH + 6

    def place(actors, x):
        want = []
        for a in actors:
            ys = [rows[u.id][1] for u in ucs if u.actor == a.name]
            want.append([a, sum(ys) / len(ys) if ys else TOP + 90])
        want.sort(key=lambda w: w[1])
        pos, prev = {}, None
        for a, y in want:
            y = max(y, TOP + 50)
            if prev is not None:
                y = max(y, prev + MIN_ACTOR_GAP)
            pos[a.name] = (x, y)
            prev = y
        return pos

    actors_pos = {}
    actors_pos.update(place(left, SIDE / 2))
    actors_pos.update(place(right, SIDE + BOX_W + SIDE / 2))
    height = max(TOP + box_h + 40, max((p[1] for p in actors_pos.values()), default=0) + 90)
    return {"ucs": ucs, "rows": rows, "actors": actors_pos, "box": (x0, TOP, BOX_W, box_h),
            "width": 2 * SIDE + BOX_W, "height": height}


def render_usecase_svg(m: UseCaseModel) -> str:
    lay = layout(m)
    W, H = lay["width"], lay["height"]
    bx, by, bw, bh = lay["box"]
    rx, ry = ELL_W / 2, ELL_H / 2
    ext = {a.name for a in m.actors if a.external}
    out: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H:.0f}" width="{W}" height="{H:.0f}" '
        f'font-family="Inter, Segoe UI, Helvetica, Arial, sans-serif">',
        '<defs><marker id="arr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto">'
        f'<path d="M0,0 L10,5 L0,10 z" fill="{INK}"/></marker></defs>',
        f'<rect width="{W}" height="{H:.0f}" fill="#ffffff"/>',
        f'<rect x="{bx}" y="{by}" width="{bw}" height="{bh}" rx="18" fill="#ffffff" stroke="{SOFT}" stroke-width="1.5"/>',
        _text(bx + bw / 2, by + 28, _lines(m.system, 40, 1), 15, "600"),
    ]

    # associations (drawn first so ellipses sit on top)
    for u in lay["ucs"]:
        if u.actor not in lay["actors"]:
            continue
        ax, ay = lay["actors"][u.actor]
        ux, uy = lay["rows"][u.id]
        hand = (ax - 55, ay) if u.actor in ext else (ax + 16, ay - 14)
        ex, ey = _ellipse_edge(ux, uy, rx, ry, *hand)
        out.append(f'<line x1="{hand[0]:.1f}" y1="{hand[1]:.1f}" x2="{ex:.1f}" y2="{ey:.1f}" stroke="{INK}" stroke-width="1.3"/>')

    # include / extend arcs on the right
    def arc(a_id: str, b_id: str, label: str):
        (x1, y1), (x2, y2) = lay["rows"][a_id], lay["rows"][b_id]
        sx = x1 + rx
        ctrl = sx + 40 + min(30, abs(y2 - y1) * 0.15)
        out.append(f'<path d="M{sx:.1f},{y1:.1f} Q{ctrl:.1f},{(y1 + y2) / 2:.1f} {x2 + rx:.1f},{y2:.1f}" fill="none" '
                   f'stroke="{INK}" stroke-width="1.2" stroke-dasharray="6 4" marker-end="url(#arr)"/>')
        apex = sx + (ctrl - sx) / 2
        out.append(f'<text x="{apex + 5:.1f}" y="{(y1 + y2) / 2:.1f}" font-size="11" font-style="italic" fill="{INK}" '
                   f'dominant-baseline="middle">{escape(label)}</text>')

    for r in m.includes:
        if r.source in lay["rows"] and r.target in lay["rows"]:
            arc(r.source, r.target, "«include»")
    for r in m.extends:
        if r.source in lay["rows"] and r.target in lay["rows"]:
            arc(r.source, r.target, "«extend»")

    for u in lay["ucs"]:
        ux, uy = lay["rows"][u.id]
        out.append(f'<ellipse cx="{ux:.1f}" cy="{uy:.1f}" rx="{rx}" ry="{ry}" fill="{FILL}" stroke="{INK}" stroke-width="1.4"/>')
        out.append(_text(ux, uy, _lines(u.name)))

    for name, (ax, ay) in lay["actors"].items():
        if name in ext:  # external system: «system» box
            out.append(f'<rect x="{ax - 55:.1f}" y="{ay - 26:.1f}" width="110" height="52" rx="6" fill="{FILL}" stroke="{INK}" stroke-width="1.4"/>')
            out.append(_text(ax, ay - 9, ["«system»"], 10, "400"))
            out.append(_text(ax, ay + 8, _lines(name, 14, 1), 12, "600"))
        else:  # stick figure
            out.append(f'<g stroke="{INK}" stroke-width="1.6" fill="#ffffff" stroke-linecap="round">'
                       f'<circle cx="{ax:.1f}" cy="{ay - 34:.1f}" r="11"/>'
                       f'<line x1="{ax:.1f}" y1="{ay - 23:.1f}" x2="{ax:.1f}" y2="{ay + 8:.1f}"/>'
                       f'<line x1="{ax - 16:.1f}" y1="{ay - 14:.1f}" x2="{ax + 16:.1f}" y2="{ay - 14:.1f}"/>'
                       f'<line x1="{ax:.1f}" y1="{ay + 8:.1f}" x2="{ax - 14:.1f}" y2="{ay + 30:.1f}"/>'
                       f'<line x1="{ax:.1f}" y1="{ay + 8:.1f}" x2="{ax + 14:.1f}" y2="{ay + 30:.1f}"/></g>')
            out.append(_text(ax, ay + 46, _lines(name, 18, 2), 12, "600"))
    out.append("</svg>")
    return "".join(out)
