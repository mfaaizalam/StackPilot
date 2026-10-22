"""Scene -> PNG and SVG.

A Scene is first flattened into a few drawing primitives; the PNG (Pillow) and SVG writers only have
to know how to draw those. The PNG carries the draw.io source inside it (tEXt chunk "mxfile"), so the
picture that is pasted into a Word file can be dragged into draw.io and edited.
"""
from __future__ import annotations

import io
import math
import os
from urllib.parse import quote
from xml.sax.saxutils import escape

from app.services.diagram_scene import (
    HEAD, INK, SOFT, WHITE, Edge, Node, Scene, edge_points, label_anchor,
)

Prim = tuple


# ============================================================ primitives
def _t(x, y, text, size=12, bold=False, italic=False, color=INK, anchor="middle") -> Prim:
    return ("text", x, y, str(text), size, bold, italic, color, anchor)


def _lines(cx: float, top: float, lines: list[str], size=12, bold=False, step=16, anchor="middle") -> list[Prim]:
    return [_t(cx, top + i * step + step / 2, ln, size, bold, anchor=anchor) for i, ln in enumerate(lines)]


def _node_prims(n: Node) -> list[Prim]:
    P: list[Prim] = []
    x, y, w, h = n.x, n.y, n.w, n.h
    k = n.kind
    lines = [l for l in n.text.split("\n")] if n.text else []
    mid = lambda ls, step=16: y + (h - step * len(ls)) / 2

    if k in ("rect", "rounded"):
        P.append(("rect", x, y, w, h, n.fill, INK, 1.4, 10 if k == "rounded" else 0, False))
        ls = ([n.sub] if n.sub else []) + lines
        top = mid(ls)
        if n.sub:
            P.append(_t(x + w / 2, top + 8, n.sub, 10, False, True, "#4B5563"))
            top += 14
        P += _lines(x + w / 2, mid(lines) + (7 if n.sub else 0), lines, 12, n.bold)
    elif k == "ellipse":
        P.append(("ell", x + w / 2, y + h / 2, w / 2, h / 2, n.fill, INK, 1.4))
        P += _lines(x + w / 2, mid(lines), lines, 12, False)
    elif k == "diamond":
        P.append(("poly", [(x + w / 2, y), (x + w, y + h / 2), (x + w / 2, y + h), (x, y + h / 2)], n.fill, INK, 1.4, True))
        P += _lines(x + w / 2, mid(lines), lines, 11)
    elif k == "dot":
        P.append(("ell", x + w / 2, y + h / 2, w / 2, h / 2, INK, INK, 1))
    elif k == "end":
        P.append(("ell", x + w / 2, y + h / 2, w / 2, h / 2, WHITE, INK, 2))
        P.append(("ell", x + w / 2, y + h / 2, w / 2 - 6, h / 2 - 6, INK, INK, 1))
    elif k == "actor":
        cx = x + w / 2
        P.append(("ell", cx, y + 9, 9, 9, WHITE, INK, 1.6))
        P.append(("line", [(cx, y + 18), (cx, y + 44)], INK, 1.6, False))
        P.append(("line", [(cx - 16, y + 28), (cx + 16, y + 28)], INK, 1.6, False))
        P.append(("line", [(cx, y + 44), (cx - 14, y + 62)], INK, 1.6, False))
        P.append(("line", [(cx, y + 44), (cx + 14, y + 62)], INK, 1.6, False))
        P += _lines(cx, y + 66, lines, 12, False, 15)
    elif k == "boundary":
        P.append(("rect", x, y, w, h, WHITE, INK, 1.6, 0, False))
        P.append(_t(x + w / 2, y + 20, n.text, 13, True))
    elif k == "cylinder":
        ry = 11
        P.append(("ell", x + w / 2, y + h - ry, w / 2, ry, n.fill, INK, 1.4))
        P.append(("rect", x, y + ry, w, h - 2 * ry, n.fill, n.fill, 0, 0, False))
        P.append(("line", [(x, y + ry), (x, y + h - ry)], INK, 1.4, False))
        P.append(("line", [(x + w, y + ry), (x + w, y + h - ry)], INK, 1.4, False))
        P.append(("ell", x + w / 2, y + ry, w / 2, ry, n.fill, INK, 1.4))
        P.append(_t(x + w / 2, y + 26, n.sub, 10, False, True, "#4B5563"))
        P.append(_t(x + w / 2, y + 41, n.text, 13, True))
        if n.meta.get("tech"):
            P.append(_t(x + w / 2, y + 56, n.meta["tech"], 11, False, True))
    elif k == "cube":
        d = 12
        P.append(("poly", [(x, y + d), (x + d, y), (x + w, y), (x + w - d, y + d)], "#F9FAFB", INK, 1.4, True))
        P.append(("poly", [(x + w - d, y + d), (x + w, y), (x + w, y + h - d), (x + w - d, y + h)], "#D1D5DB", INK, 1.4, True))
        P.append(("rect", x, y + d, w - d, h - d, n.fill, INK, 1.4, 0, False))
        cx = x + (w - d) / 2
        P.append(_t(cx, y + d + 12, n.sub, 10, False, True, "#4B5563"))
        P.append(_t(cx, y + d + 28, n.text, 13, True))
        if n.meta.get("tech"):
            P.append(_t(cx, y + d + 44, n.meta["tech"], 11, False, True))
    elif k == "artifact":
        P.append(("rect", x, y, w, h, n.fill, INK, 1.2, 0, False))
        P.append(("rect", x - 6, y + 6, 12, 6, WHITE, INK, 1, 0, False))
        P.append(("rect", x - 6, y + 17, 12, 6, WHITE, INK, 1, 0, False))
        P.append(_t(x + w / 2 + 4, y + h / 2, n.text, 12))
    elif k == "store":
        P.append(("rect", x, y, w, h, WHITE, WHITE, 0, 0, False))
        P.append(("line", [(x, y), (x + w, y)], INK, 1.6, False))
        P.append(("line", [(x, y + h), (x + w, y + h)], INK, 1.6, False))
        P.append(("rect", x, y, 38, h, SOFT, INK, 1.4, 0, False))
        P.append(_t(x + 19, y + h / 2, n.meta.get("tag", ""), 12, True))
        P += _lines(x + 38 + (w - 38) / 2, mid(lines), lines, 12)
    elif k == "entity":
        P.append(("rect", x, y, w, h, WHITE, INK, 1.4, 0, False))
        P.append(("rect", x, y, w, 30, HEAD, INK, 1.4, 0, False))
        P.append(_t(x + w / 2, y + 15, n.text, 13, True))
        for i, (key, name, typ) in enumerate(n.rows):
            ry = y + 30 + i * 22
            if i:
                P.append(("line", [(x, ry), (x + w, ry)], "#D1D5DB", 0.8, False))
            P.append(_t(x + 8, ry + 11, key, 10, True, False, "#1D4ED8" if key == "PK" else "#6B7280", "start"))
            P.append(_t(x + 34, ry + 11, name, 12, key == "PK", anchor="start"))
            P.append(_t(x + w - 8, ry + 11, typ, 11, False, True, "#6B7280", "end"))
        P.append(("line", [(x + 28, y + 30), (x + 28, y + h)], "#D1D5DB", 0.8, False))
    elif k == "class":
        P.append(("rect", x, y, w, h, WHITE, INK, 1.4, 0, False))
        P.append(("rect", x, y, w, 28, HEAD, INK, 1.4, 0, False))
        P.append(_t(x + w / 2, y + 14, n.text, 13, True))
        ah = 18 * max(len(n.rows), 1)
        for i, r in enumerate(n.rows):
            P.append(_t(x + 10, y + 28 + i * 18 + 10, r, 11.5, anchor="start"))
        P.append(("line", [(x, y + 28 + ah + 4), (x + w, y + 28 + ah + 4)], INK, 1.2, False))
        for i, r in enumerate(n.rows2):
            P.append(_t(x + 10, y + 28 + ah + 8 + i * 18 + 10, r, 11.5, anchor="start"))
    elif k == "lifeline":
        cx = x + w / 2
        head = n.meta.get("head", 40)
        if n.meta.get("actor"):
            P.append(("ell", cx, y + 9, 9, 9, WHITE, INK, 1.6))
            P.append(("line", [(cx, y + 18), (cx, y + 44)], INK, 1.6, False))
            P.append(("line", [(cx - 16, y + 28), (cx + 16, y + 28)], INK, 1.6, False))
            P.append(("line", [(cx, y + 44), (cx - 14, y + 62)], INK, 1.6, False))
            P.append(("line", [(cx, y + 44), (cx + 14, y + 62)], INK, 1.6, False))
            P.append(_t(cx, y + 72, n.text, 12, True))
        else:
            P.append(("rect", x, y, w, head, n.fill, INK, 1.4, 0, False))
            P += _lines(cx, y + (head - 16 * len(lines)) / 2, lines, 12, True)
        P.append(("line", [(cx, y + head + 2), (cx, y + h)], "#6B7280", 1.2, True))
    elif k == "frame":
        P.append(("rect", x, y, w, h, None, "#6B7280", 1.2, 0, True))
        P.append(("poly", [(x, y), (x + 54, y), (x + 54, y + 12), (x + 46, y + 20), (x, y + 20)], WHITE, "#6B7280", 1.2, True))
        P.append(_t(x + 6, y + 10, n.text, 11, True, anchor="start"))
        P.append(_t(x + 62, y + 10, n.sub, 11, False, True, "#4B5563", "start"))
    return P


# --------------------------------------------------------------- arrows
def _end_marker(p: tuple[float, float], u: tuple[float, float], kind: str) -> list[Prim]:
    """Draw a marker at point p. u is the unit vector pointing AWAY from the shape along the line."""
    if kind == "none":
        return []
    ux, uy = u
    nx, ny = -uy, ux
    at = lambda d, s=0.0: (p[0] + ux * d + nx * s, p[1] + uy * d + ny * s)
    if kind == "arrow":
        return [("poly", [p, at(12, 5.5), at(12, -5.5)], INK, INK, 1, True)]
    if kind == "open":
        return [("line", [at(11, 5.5), p, at(11, -5.5)], INK, 1.4, False)]
    if kind == "triangle":
        return [("poly", [p, at(15, 8), at(15, -8)], WHITE, INK, 1.4, True)]
    if kind in ("diamond", "diamond_f"):
        return [("poly", [p, at(10, 6), at(20, 0), at(10, -6)], INK if kind == "diamond_f" else WHITE, INK, 1.4, True)]
    if kind.startswith("er:"):
        c = kind[3:]
        M: list[Prim] = []
        bar = lambda d: M.append(("line", [at(d, 8), at(d, -8)], INK, 1.5, False))
        circ = lambda d: M.append(("ell", *at(d, 0), 5, 5, WHITE, INK, 1.4))
        foot = lambda: [M.append(("line", [at(14, 0), at(0, s)], INK, 1.5, False)) for s in (-8, 0, 8)]
        if c == "one":
            bar(9)
            bar(15)
        elif c == "zero_or_one":
            bar(9)
            circ(19)
        elif c == "many":
            foot()
            circ(22)
        elif c == "one_or_many":
            foot()
            bar(19)
        return M
    return []


def _unit(a: tuple[float, float], b: tuple[float, float]) -> tuple[float, float]:
    d = math.hypot(b[0] - a[0], b[1] - a[1]) or 1
    return (b[0] - a[0]) / d, (b[1] - a[1]) / d


def _edge_prims(sc: Scene, e: Edge) -> list[Prim]:
    pts = edge_points(sc, e)
    if len(pts) < 2:
        return []
    P: list[Prim] = []
    # trim the line so it does not poke through hollow / filled markers
    P.append(("line", pts, INK, 1.4, e.dash))
    P += _end_marker(pts[-1], _unit(pts[-1], pts[-2]), e.end)
    P += _end_marker(pts[0], _unit(pts[0], pts[1]), e.start)
    if e.label:
        if e.meta.get("y") is not None:
            if e.meta.get("self"):
                P.append(_t(pts[1][0] + 8, (pts[1][1] + pts[2][1]) / 2, e.label, 11, anchor="start"))
            else:
                P.append(_t((pts[0][0] + pts[-1][0]) / 2, pts[0][1] - 9, e.label, 11))
        else:
            mx, my, _ = label_anchor(pts)
            if len(e.via) == 1:               # two flows between the same pair: label each at its own bend
                mx, my = e.via[0]
            w = len(e.label) * 6.4 + 8
            P.append(("rect", mx - w / 2, my - 9, w, 18, WHITE, WHITE, 0, 3, False))
            P.append(_t(mx, my, e.label, 11, False, True))
    for txt, i, j in ((e.src_text, 0, 1), (e.dst_text, -1, -2)):
        if txt:
            a, b = pts[i], pts[j]
            u = _unit(a, b)
            P.append(_t(a[0] + u[0] * 22 - u[1] * 12, a[1] + u[1] * 22 + u[0] * 12, txt, 11))
    return P


def primitives(sc: Scene) -> list[Prim]:
    P: list[Prim] = []
    order = {"boundary": 0, "frame": 0, "lifeline": 1}
    for n in sorted(sc.nodes, key=lambda n: (order.get(n.kind, 2), 1 if n.parent else 0)):
        P += _node_prims(n)
    for e in sc.edges:
        P += _edge_prims(sc, e)
    return P


# ================================================================== SVG
_DASH = ' stroke-dasharray="6 4"'
_BOLD = ' font-weight="bold"'
_ITAL = ' font-style="italic"'


def to_svg(sc: Scene, title: bool = False) -> str:
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {sc.w:.0f} {sc.h:.0f}" width="{sc.w:.0f}" '
           f'height="{sc.h:.0f}" font-family="Arial, Helvetica, sans-serif">',
           f'<rect width="100%" height="100%" fill="#ffffff"/>']
    for p in primitives(sc):
        k = p[0]
        if k == "rect":
            _, x, y, w, h, fill, stroke, sw, r, dash = p
            out.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{r}" '
                       f'fill="{fill or "none"}" stroke="{stroke}" stroke-width="{sw}"'
                       f'{_DASH if dash else ""}/>')
        elif k == "ell":
            _, cx, cy, rx, ry, fill, stroke, sw = p
            out.append(f'<ellipse cx="{cx:.1f}" cy="{cy:.1f}" rx="{rx:.1f}" ry="{ry:.1f}" fill="{fill}" '
                       f'stroke="{stroke}" stroke-width="{sw}"/>')
        elif k == "poly":
            _, pts, fill, stroke, sw, close = p
            s = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
            out.append(f'<polygon points="{s}" fill="{fill or "none"}" stroke="{stroke}" stroke-width="{sw}" stroke-linejoin="round"/>')
        elif k == "line":
            _, pts, stroke, sw, dash = p
            s = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
            out.append(f'<polyline points="{s}" fill="none" stroke="{stroke}" stroke-width="{sw}" '
                       f'stroke-linejoin="round"{_DASH if dash else ""}/>')
        elif k == "text":
            _, x, y, text, size, bold, italic, color, anchor = p
            out.append(f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" fill="{color}" text-anchor="{anchor}" '
                       f'dominant-baseline="central"{_BOLD if bold else ""}'
                       f'{_ITAL if italic else ""}>{escape(text)}</text>')
    out.append("</svg>")
    return "\n".join(out)


# ================================================================== PNG
_FONT_CACHE: dict = {}
_REG = ["arial.ttf", "Arial.ttf", "LiberationSans-Regular.ttf", "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]
_BLD = ["arialbd.ttf", "Arial Bold.ttf", "LiberationSans-Bold.ttf", "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "DejaVuSans-Bold.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]
_ITA = ["ariali.ttf", "LiberationSans-Italic.ttf", "/usr/share/fonts/truetype/liberation/LiberationSans-Italic.ttf",
        "DejaVuSans-Oblique.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Oblique.ttf"]


def _font(size: float, bold: bool, italic: bool):
    from PIL import ImageFont
    key = (round(size * 2), bold, italic)
    if key not in _FONT_CACHE:
        font = None
        for name in (_BLD if bold else _ITA if italic else _REG):
            try:
                font = ImageFont.truetype(name, int(round(size)))
                break
            except Exception:
                continue
        _FONT_CACHE[key] = font or ImageFont.load_default(int(round(size)))
    return _FONT_CACHE[key]


def _dashed(draw, pts, color, width, S):
    on, off = 6 * S, 4 * S
    for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
        d = math.hypot(x2 - x1, y2 - y1)
        if d == 0:
            continue
        ux, uy = (x2 - x1) / d, (y2 - y1) / d
        t = 0.0
        while t < d:
            e = min(t + on, d)
            draw.line([(x1 + ux * t, y1 + uy * t), (x1 + ux * e, y1 + uy * e)], fill=color, width=width)
            t += on + off


def to_png(sc: Scene, drawio_xml: str | None = None, scale: float = 2.0) -> bytes:
    from PIL import Image, ImageDraw
    from PIL.PngImagePlugin import PngInfo

    S = scale * 2  # draw at 2x the output size, then shrink: smooth edges without anti-aliased primitives
    W, H = int(sc.w * S), int(sc.h * S)
    img = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(img)
    sx = lambda v: v * S
    for p in primitives(sc):
        k = p[0]
        if k == "rect":
            _, x, y, w, h, fill, stroke, sw, r, dash = p
            if dash:
                _dashed(d, [(sx(x), sx(y)), (sx(x + w), sx(y)), (sx(x + w), sx(y + h)), (sx(x), sx(y + h)), (sx(x), sx(y))],
                        stroke, max(1, int(sw * S)), S)
            else:
                box = [sx(x), sx(y), sx(x + w), sx(y + h)]
                width = int(sw * S) if sw else 0
                if r:
                    d.rounded_rectangle(box, radius=sx(r), fill=fill, outline=stroke if width else None, width=width)
                else:
                    d.rectangle(box, fill=fill, outline=stroke if width else None, width=width)
        elif k == "ell":
            _, cx, cy, rx, ry, fill, stroke, sw = p
            d.ellipse([sx(cx - rx), sx(cy - ry), sx(cx + rx), sx(cy + ry)], fill=fill, outline=stroke,
                      width=max(1, int(sw * S)))
        elif k == "poly":
            _, pts, fill, stroke, sw, close = p
            q = [(sx(x), sx(y)) for x, y in pts]
            if fill:
                d.polygon(q, fill=fill)
            d.line(q + [q[0]], fill=stroke, width=max(1, int(sw * S)), joint="curve")
        elif k == "line":
            _, pts, stroke, sw, dash = p
            q = [(sx(x), sx(y)) for x, y in pts]
            if dash:
                _dashed(d, q, stroke, max(1, int(sw * S)), S)
            else:
                d.line(q, fill=stroke, width=max(1, int(sw * S)), joint="curve")
        elif k == "text":
            _, x, y, text, size, bold, italic, color, anchor = p
            d.text((sx(x), sx(y)), text, font=_font(size * S, bold, italic), fill=color,
                   anchor={"start": "lm", "middle": "mm", "end": "rm"}[anchor])
    out = img.resize((int(sc.w * scale), int(sc.h * scale)), Image.LANCZOS)
    meta = PngInfo()
    meta.add_text("Title", sc.title)
    meta.add_text("Software", "StackPilot")
    if drawio_xml:
        meta.add_text("mxfile", quote(drawio_xml, safe=""))  # draw.io opens this PNG as an editable diagram
    buf = io.BytesIO()
    out.save(buf, "PNG", pnginfo=meta, dpi=(192, 192))
    return buf.getvalue()
