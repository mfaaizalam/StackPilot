"""Scene -> draw.io (.drawio) XML.

Everything is written with NATIVE draw.io shapes (UML actor, lifeline, component, node, cylinder,
swimlane tables, ER crow's-foot arrows ...), never as pictures. In draw.io (app.diagrams.net or the
desktop app) every element can be moved, restyled, renamed or replaced from the full shape library.
"""
from __future__ import annotations

import re
from xml.sax.saxutils import escape

from app.services.diagram_scene import HEAD, INK, Edge, Node, Scene

_Q = {'"': "&quot;"}
INKC = INK


def _a(s) -> str:
    """XML attribute escape."""
    return escape(str(s), _Q)


def _html(lines: list[str]) -> str:
    return "<br>".join(escape(l) for l in lines)


def _geo(x, y, w, h) -> str:
    return f'<mxGeometry x="{x:.0f}" y="{y:.0f}" width="{w:.0f}" height="{h:.0f}" as="geometry"/>'


_END = {
    "none": ("none", 0, ""),
    "arrow": ("block", 1, "endSize=8;"),
    "open": ("open", 0, "endSize=8;"),
    "triangle": ("block", 0, "endSize=14;"),
    "diamond": ("diamondThin", 0, "endSize=18;"),
    "diamond_f": ("diamondThin", 1, "endSize=18;"),
    "er:one": ("ERmandOne", 0, "endSize=14;"),
    "er:zero_or_one": ("ERzeroToOne", 0, "endSize=14;"),
    "er:many": ("ERzeroToMany", 0, "endSize=14;"),
    "er:one_or_many": ("ERoneToMany", 0, "endSize=14;"),
}


def _edge_style(e: Edge, extra: str = "") -> str:
    ea, ef, ex = _END.get(e.end, _END["arrow"])
    sa, sf, sx = _END.get(e.start, _END["none"])
    s = (f"html=1;rounded=0;strokeColor={INKC};strokeWidth=1.5;fontSize=11;fontColor={INKC};"
         f"labelBackgroundColor=#FFFFFF;endArrow={ea};endFill={ef};startArrow={sa};startFill={sf};{ex}"
         f"{sx.replace('endSize', 'startSize')}")
    if e.dash:
        s += "dashed=1;"
    return s + extra


def _fill(fill: str, stroke: str = INKC) -> str:
    return f"fillColor={fill};strokeColor={stroke};fontColor={INKC};"


def build_cells(sc: Scene, p: str = "") -> list[str]:
    """All mxCell elements of a scene. Ids are prefixed with `p` so several diagrams can share a file."""
    ids = {n.id: f"{p}n{i}" for i, n in enumerate(sc.nodes, start=2)}
    nodes = {n.id: n for n in sc.nodes}
    X: list[str] = []

    def vertex(cid, value, style, x, y, w, h, parent="1"):
        X.append(f'<mxCell id="{cid}" value="{_a(value)}" style="{_a(style)}" vertex="1" parent="{parent}">{_geo(x, y, w, h)}</mxCell>')

    def rel(n: Node):
        par = nodes.get(n.parent) if n.parent else None
        return (n.x - par.x, n.y - par.y, ids[par.id]) if par else (n.x, n.y, "1")

    # containers first so children can reference them
    ordered = sorted(sc.nodes, key=lambda n: (0 if n.kind in ("boundary", "frame", "lifeline") else 1, 1 if n.parent else 0))
    for n in ordered:
        cid = ids[n.id]
        x, y, par = rel(n)
        w, h, k = n.w, n.h, n.kind
        lines = n.text.split("\n") if n.text else []
        if k == "rect":
            v = (f"<i>{escape(n.sub)}</i><br>" if n.sub else "") + (f"<b>{_html(lines)}</b>" if n.bold else _html(lines))
            vertex(cid, v, f"rounded=0;whiteSpace=wrap;html=1;{_fill(n.fill)}", x, y, w, h, par)
        elif k == "rounded":
            vertex(cid, _html(lines), f"rounded=1;arcSize=22;whiteSpace=wrap;html=1;{_fill(n.fill)}", x, y, w, h, par)
        elif k == "ellipse":
            if n.meta.get("role") == "process":
                v = f"<b>{escape(lines[0])}</b><br>" + _html(lines[1:])
            else:
                v = _html(lines)
            vertex(cid, v, f"ellipse;whiteSpace=wrap;html=1;{_fill(n.fill)}", x, y, w, h, par)
        elif k == "diamond":
            vertex(cid, _html(lines), f"rhombus;whiteSpace=wrap;html=1;{_fill(n.fill)}", x, y, w, h, par)
        elif k == "dot":
            vertex(cid, "", f"ellipse;html=1;shape=startState;fillColor={INKC};strokeColor={INKC};", x, y, w, h, par)
        elif k == "end":
            vertex(cid, "", f"ellipse;html=1;shape=endState;fillColor={INKC};strokeColor={INKC};", x, y, w, h, par)
        elif k == "actor":
            vertex(cid, _html(lines), f"shape=umlActor;verticalLabelPosition=bottom;verticalAlign=top;html=1;outlineConnect=0;{_fill('#FFFFFF')}", x, y, w, h, par)
        elif k == "boundary":
            vertex(cid, f"<b>{escape(n.text)}</b>", f"rounded=0;whiteSpace=wrap;html=1;container=1;collapsible=0;verticalAlign=top;{_fill('#FFFFFF')}", x, y, w, h, par)
        elif k == "cylinder":
            v = f"<i>{escape(n.sub)}</i><br><b>{escape(n.text)}</b>" + (f"<br><i>{escape(n.meta['tech'])}</i>" if n.meta.get("tech") else "")
            vertex(cid, v, f"shape=cylinder3;whiteSpace=wrap;html=1;boundedLbl=1;backgroundOutline=1;size=12;container=1;collapsible=0;verticalAlign=top;spacingTop=14;{_fill(n.fill)}", x, y, w, h, par)
        elif k == "cube":
            v = f"<i>{escape(n.sub)}</i><br><b>{escape(n.text)}</b>" + (f"<br><i>{escape(n.meta['tech'])}</i>" if n.meta.get("tech") else "")
            vertex(cid, v, f"shape=cube;size=12;whiteSpace=wrap;html=1;container=1;collapsible=0;verticalAlign=top;align=center;spacingTop=10;spacingRight=12;{_fill(n.fill)}", x, y, w, h, par)
        elif k == "artifact":
            vertex(cid, escape(n.text), f"html=1;dropTarget=0;whiteSpace=wrap;shape=module;align=center;spacingLeft=10;jettyWidth=14;jettyHeight=8;{_fill('#FFFFFF')}", x, y, w, h, par)
        elif k == "store":
            vertex(cid, _html(lines), f"shape=partialRectangle;whiteSpace=wrap;html=1;left=0;right=0;spacingLeft=38;container=1;collapsible=0;{_fill('#FFFFFF')}strokeWidth=2;", x, y, w, h, par)
            vertex(f"{cid}t", f"<b>{escape(n.meta.get('tag', ''))}</b>", f"rounded=0;whiteSpace=wrap;html=1;{_fill('#F3F4F6')}", 0, 0, 38, h, cid)
        elif k == "entity":
            vertex(cid, f"<b>{escape(n.text)}</b>",
                   f"swimlane;fontStyle=1;childLayout=stackLayout;horizontal=1;startSize=30;horizontalStack=0;resizeParent=1;"
                   f"resizeParentMax=0;resizeLast=0;collapsible=0;marginBottom=0;whiteSpace=wrap;html=1;{_fill(HEAD)}", x, y, w, h, par)
            for i, (key, name, typ) in enumerate(n.rows):
                lab = (f"<b>{escape(key)}</b>&nbsp;&nbsp;" if key else "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;") + \
                      (f"<u>{escape(name)}</u>" if key == "PK" else escape(name)) + (f" : <i>{escape(typ)}</i>" if typ else "")
                vertex(f"{cid}r{i}", lab,
                       "text;strokeColor=none;fillColor=none;align=left;verticalAlign=middle;spacingLeft=6;spacingRight=6;"
                       "overflow=hidden;points=[[0,0.5],[1,0.5]];portConstraint=eastwest;rotatable=0;whiteSpace=wrap;html=1;",
                       0, 30 + 22 * i, w, 22, cid)
        elif k == "class":
            vertex(cid, f"<b>{escape(n.text)}</b>",
                   f"swimlane;fontStyle=1;align=center;verticalAlign=top;childLayout=stackLayout;horizontal=1;startSize=28;"
                   f"horizontalStack=0;resizeParent=1;resizeParentMax=0;resizeLast=0;collapsible=0;marginBottom=0;html=1;{_fill(HEAD)}",
                   x, y, w, h, par)
            ah = 18 * max(len(n.rows), 1)
            cell = ("text;strokeColor=none;fillColor=none;align=left;verticalAlign=top;spacingLeft=6;spacingRight=6;"
                    "overflow=hidden;rotatable=0;points=[[0,0.5],[1,0.5]];portConstraint=eastwest;whiteSpace=wrap;html=1;")
            vertex(f"{cid}a", "<br>".join("+ " + escape(r) for r in n.rows), cell, 0, 28, w, ah + 4, cid)
            vertex(f"{cid}s", "", "line;strokeWidth=1;fillColor=none;align=left;verticalAlign=middle;spacingTop=-1;spacingLeft=3;spacingRight=3;rotatable=0;labelPosition=right;points=[];portConstraint=eastwest;strokeColor=inherit;", 0, 28 + ah + 4, w, 8, cid)
            if n.rows2:
                vertex(f"{cid}m", "<br>".join("+ " + escape(r) for r in n.rows2), cell, 0, 28 + ah + 12, w, 18 * len(n.rows2) + 2, cid)
        elif k == "lifeline":
            head = n.meta.get("head", 40)
            actor = "participant=umlActor;verticalAlign=top;spacingTop=36;" if n.meta.get("actor") else ""
            vertex(cid, escape(n.text),
                   f"shape=umlLifeline;perimeter=lifelinePerimeter;whiteSpace=wrap;html=1;container=1;dropTarget=0;collapsible=0;"
                   f"recursiveResize=0;outlineConnect=0;portConstraint=eastwest;size={head};{actor}{_fill(n.fill)}", x, y, w, h, par)
        elif k == "frame":
            vertex(cid, escape(n.text), f"shape=umlFrame;whiteSpace=wrap;html=1;pointerEvents=0;width=54;height=20;dashed=1;fillColor=none;strokeColor=#6B7280;fontSize=11;", x, y, w, h, par)
            vertex(f"{cid}c", f"<i>{escape(n.sub)}</i>", "text;html=1;align=left;verticalAlign=middle;fontSize=11;strokeColor=none;fillColor=none;", 60, 0, max(w - 70, 40), 20, cid)

    # edges
    for i, e in enumerate(sc.edges):
        eid = f"{p}e{i}"
        extra = ""
        src, dst = ids[e.src], ids[e.dst]
        pts = ""
        if e.pts is not None:                      # sequence diagrams: ride on the lifelines
            a, b = nodes[e.src], nodes[e.dst]
            y = e.meta["y"]
            fa, fb = (y - a.y) / a.h, (y - b.y) / b.h
            extra = f"exitX=0.5;exitY={fa:.4f};exitDx=0;exitDy=0;entryX=0.5;entryY={fb:.4f};entryDx=0;entryDy=0;verticalAlign=bottom;"
            if e.meta.get("self"):
                inner = e.pts[1:-1]
                pts = "<Array as=\"points\">" + "".join(f'<mxPoint x="{x:.0f}" y="{yy:.0f}"/>' for x, yy in inner) + "</Array>"
        elif e.via:
            pts = "<Array as=\"points\">" + "".join(f'<mxPoint x="{x:.0f}" y="{yy:.0f}"/>' for x, yy in e.via) + "</Array>"
        X.append(f'<mxCell id="{eid}" value="{_a(e.label)}" style="{_a(_edge_style(e, extra))}" edge="1" parent="1" '
                 f'source="{src}" target="{dst}"><mxGeometry relative="1" as="geometry">{pts}</mxGeometry></mxCell>')
        for k, (txt, pos) in enumerate(((e.src_text, -0.82), (e.dst_text, 0.82))):
            if txt:
                X.append(f'<mxCell id="{eid}c{k}" value="{_a(txt)}" style="edgeLabel;html=1;align=center;verticalAlign=middle;'
                         f'resizable=0;points=[];fontSize=11;" vertex="1" connectable="0" parent="{eid}">'
                         f'<mxGeometry x="{pos}" relative="1" as="geometry"><mxPoint y="-12" as="offset"/></mxGeometry></mxCell>')
    return X


def to_model(sc: Scene, p: str = "") -> str:
    pw, ph = max(int(sc.w) + 40, 827), max(int(sc.h) + 40, 583)
    return (f'<mxGraphModel dx="{int(sc.w)}" dy="{int(sc.h)}" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" '
            f'arrows="1" fold="1" page="1" pageScale="1" pageWidth="{pw}" pageHeight="{ph}" math="0" shadow="0">'
            f'<root><mxCell id="0"/><mxCell id="1" parent="0"/>{"".join(build_cells(sc, p))}</root></mxGraphModel>')


def _safe(s: str) -> str:
    return re.sub(r"\s+", " ", s or "Diagram").strip()[:60]


def to_mxfile(scenes: list[Scene]) -> str:
    """One .drawio file. Each diagram is its own page (tab) at the bottom of draw.io."""
    pages = "".join(f'<diagram id="sp-{i}" name="{_a(_safe(s.title))}">{to_model(s)}</diagram>'
                    for i, s in enumerate(scenes, start=1))
    return f'<mxfile host="app.diagrams.net" agent="StackPilot" version="24.7.0" type="device">{pages}</mxfile>'
