"""Diagram scene graph.

Every diagram (use case, class, ER, DFD, sequence, activity, state, deployment) is first turned
into a Scene: boxes, ellipses, actors and connectors with real coordinates. The same Scene is then
written out three ways, so the pictures always agree:

    diagram_drawio.py  -> native, fully editable draw.io (.drawio) with UML / ER shapes
    diagram_render.py  -> PNG (for the Word documents) and SVG (for the web app)

No AI is involved here. Input is an already validated diagram model.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

# ------------------------------------------------------------------ look
INK = "#1F2937"
HEAD = "#DCE6F2"      # table / class header
SOFT = "#F3F4F6"
WHITE = "#FFFFFF"
EXT = "#EDEDED"
DB = "#E2EFDA"
WARM = "#FFF2CC"
FS = 12               # base font size in scene units


def tw(text: str, size: float = FS, bold: bool = False) -> float:
    """Approximate text width. Deliberately a little generous so labels never overflow."""
    return len(str(text)) * size * (0.60 if bold else 0.56)


def wrap(text: str, width: float, size: float = FS, bold: bool = False) -> list[str]:
    maxc = max(4, int(width / (size * (0.60 if bold else 0.56))))
    lines: list[str] = []
    cur = ""
    for w in str(text).split():
        while len(w) > maxc:
            if cur:
                lines.append(cur)
                cur = ""
            lines.append(w[:maxc])
            w = w[maxc:]
        if not cur:
            cur = w
        elif len(cur) + 1 + len(w) <= maxc:
            cur += " " + w
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines or [""]


# ----------------------------------------------------------------- model
@dataclass
class Node:
    id: str
    kind: str                     # rect rounded ellipse actor dot end diamond cylinder cube artifact store
    #                               entity class boundary lifeline frame note text
    x: float = 0
    y: float = 0
    w: float = 120
    h: float = 44
    text: str = ""
    sub: str = ""                 # stereotype / technology line
    fill: str = WHITE
    bold: bool = False
    rows: list = field(default_factory=list)     # entity rows [(key,name,type)] | class attributes [str]
    rows2: list = field(default_factory=list)    # class methods
    parent: str | None = None
    meta: dict = field(default_factory=dict)

    @property
    def cx(self) -> float:
        return self.x + self.w / 2

    @property
    def cy(self) -> float:
        return self.y + self.h / 2


@dataclass
class Edge:
    id: str
    src: str
    dst: str
    label: str = ""
    dash: bool = False
    end: str = "arrow"            # none arrow open triangle diamond diamond_f | er:<one|zero_or_one|many|one_or_many>
    start: str = "none"
    via: list = field(default_factory=list)      # absolute waypoints [(x, y)]
    src_text: str = ""            # multiplicity near the source end
    dst_text: str = ""
    pts: list | None = None       # explicit absolute polyline (sequence diagrams)
    meta: dict = field(default_factory=dict)


@dataclass
class Scene:
    kind: str
    title: str
    w: float = 800
    h: float = 600
    nodes: list[Node] = field(default_factory=list)
    edges: list[Edge] = field(default_factory=list)

    def node(self, nid: str) -> Node:
        for n in self.nodes:
            if n.id == nid:
                return n
        raise KeyError(nid)

    def fit(self, margin: float = 30) -> None:
        """Shift everything so the content starts at `margin` and set the canvas size."""
        if not self.nodes:
            return
        xs0 = min(n.x for n in self.nodes)
        ys0 = min(n.y for n in self.nodes)
        dx, dy = margin - xs0, margin - ys0
        for n in self.nodes:
            n.x += dx
            n.y += dy
        for e in self.edges:
            e.via = [(x + dx, y + dy) for x, y in e.via]
            if e.pts:
                e.pts = [(x + dx, y + dy) for x, y in e.pts]
        self.w = max(n.x + n.w for n in self.nodes) + margin
        self.h = max(n.y + n.h for n in self.nodes) + margin


# --------------------------------------------------------------- geometry
def _clip(n: Node, tx: float, ty: float) -> tuple[float, float]:
    """Point where the line from the node centre towards (tx, ty) leaves the node outline."""
    cx, cy = n.cx, n.cy
    dx, dy = tx - cx, ty - cy
    if abs(dx) < 1e-6 and abs(dy) < 1e-6:
        return cx, cy
    hw, hh = n.w / 2, n.h / 2
    if n.kind in ("ellipse", "dot", "end"):
        t = 1 / math.sqrt((dx / hw) ** 2 + (dy / hh) ** 2)
    elif n.kind == "diamond":
        t = 1 / (abs(dx) / hw + abs(dy) / hh)
    elif n.kind == "actor":
        hh = n.h * 0.45
        t = min(hw / abs(dx) if dx else 1e9, hh / abs(dy) if dy else 1e9)
    else:
        t = min(hw / abs(dx) if dx else 1e9, hh / abs(dy) if dy else 1e9)
    return cx + dx * t, cy + dy * t


def edge_points(scene: Scene, e: Edge) -> list[tuple[float, float]]:
    """The full polyline of an edge: start on the source outline, waypoints, end on the target outline."""
    if e.pts:
        return list(e.pts)
    a, b = scene.node(e.src), scene.node(e.dst)
    via = list(e.via)
    if e.src == e.dst:  # self loop above the node
        x, y = a.x + a.w * 0.65, a.y
        return [(x, y), (x, y - 28), (x + 46, y - 28), (x + 46, a.y + a.h * 0.25), (a.x + a.w, a.y + a.h * 0.25)]
    first = via[0] if via else (b.cx, b.cy)
    last = via[-1] if via else (a.cx, a.cy)
    return [_clip(a, *first)] + via + [_clip(b, *last)]


def label_anchor(pts: list[tuple[float, float]]) -> tuple[float, float, float]:
    """Midpoint of the longest segment of a polyline, and that segment's angle."""
    best, seg = -1.0, (pts[0], pts[-1])
    for p, q in zip(pts, pts[1:]):
        d = math.hypot(q[0] - p[0], q[1] - p[1])
        if d > best:
            best, seg = d, (p, q)
    (x1, y1), (x2, y2) = seg
    return (x1 + x2) / 2, (y1 + y2) / 2, math.atan2(y2 - y1, x2 - x1)


def spread_parallel(edges: list[Edge], scene: Scene, step: float = 34) -> None:
    """Two or more edges between the same pair of nodes would overlap: bend them apart."""
    groups: dict[frozenset, list[Edge]] = {}
    for e in edges:
        if e.src != e.dst and not e.via and not e.pts:
            groups.setdefault(frozenset((e.src, e.dst)), []).append(e)
    for key, grp in groups.items():
        if len(grp) < 2:
            continue
        a, b = scene.node(grp[0].src), scene.node(grp[0].dst)
        mx, my = (a.cx + b.cx) / 2, (a.cy + b.cy) / 2
        ang = math.atan2(b.cy - a.cy, b.cx - a.cx)
        nx, ny = -math.sin(ang), math.cos(ang)
        for k, e in enumerate(grp):
            off = (k - (len(grp) - 1) / 2) * step
            e.via = [(mx + nx * off, my + ny * off)]


# ------------------------------------------------------------ layered layout
def layered(sizes: dict[str, tuple[float, float]], edges: list[tuple[str, str]], direction: str = "LR",
            gap_layer: float = 90, gap_node: float = 34, rank: dict[str, int] | None = None):
    """Compact Sugiyama-style layout.

    Returns (pos, routes, width, height): pos[id] = (x, y) top-left; routes[(a, b)] = waypoints for
    edges that skip layers (so they run around boxes instead of through them)."""
    ids = list(sizes)
    out: dict[str, list[str]] = {i: [] for i in ids}
    for a, b in edges:
        if a != b and a in sizes and b in sizes and b not in out[a]:
            out[a].append(b)

    state: dict[str, int] = {}
    dag: list[tuple[str, str]] = []

    def dfs(u: str) -> None:
        state[u] = 1
        for v in out[u]:
            if state.get(v) == 1:
                continue            # back edge: dropped for ranking, still drawn
            dag.append((u, v))
            if v not in state:
                dfs(v)
        state[u] = 2

    for i in ids:
        if i not in state:
            dfs(i)

    preds: dict[str, list[str]] = {i: [] for i in ids}
    for a, b in dag:
        preds[b].append(a)
    layer: dict[str, int] = {}

    def L(i: str) -> int:
        if i not in layer:
            layer[i] = 0 if not preds[i] else 1 + max(L(p) for p in preds[i])
        return layer[i]

    for i in ids:
        L(i)
    if rank:
        for i, r in rank.items():
            if i in layer:
                layer[i] = r

    # chains with dummy nodes for edges that skip layers
    nlayers = max(layer.values(), default=0) + 1
    dsize: dict[str, tuple[float, float]] = dict(sizes)
    chains: dict[tuple[str, str], list[str]] = {}
    layer_of = dict(layer)
    for a, b in edges:
        if a == b or a not in sizes or b not in sizes or (a, b) in chains:
            continue
        la, lb = layer[a], layer[b]
        if abs(la - lb) <= 1:
            chains[(a, b)] = [a, b]
            continue
        step = 1 if lb > la else -1
        chain = [a]
        for k, l in enumerate(range(la + step, lb, step)):
            d = f"~{a}>{b}#{k}"
            layer_of[d] = l
            dsize[d] = (1, 16) if direction == "LR" else (16, 1)
            chain.append(d)
        chain.append(b)
        chains[(a, b)] = chain

    layers: list[list[str]] = [[] for _ in range(nlayers)]
    for n, l in layer_of.items():
        layers[l].append(n)

    up: dict[str, list[str]] = {n: [] for n in layer_of}
    down: dict[str, list[str]] = {n: [] for n in layer_of}
    for chain in chains.values():
        for p, q in zip(chain, chain[1:]):
            if layer_of[p] == layer_of[q]:
                continue
            lo, hi = (p, q) if layer_of[p] < layer_of[q] else (q, p)
            down[lo].append(hi)
            up[hi].append(lo)

    pos: dict[str, float] = {}
    for l in layers:
        for k, n in enumerate(l):
            pos[n] = k

    def sweep(down_pass: bool) -> None:
        rng = range(1, nlayers) if down_pass else range(nlayers - 2, -1, -1)
        for li in rng:
            nb = up if down_pass else down
            keyed = []
            for n in layers[li]:
                ns = nb[n]
                keyed.append((sum(pos[m] for m in ns) / len(ns) if ns else pos[n], pos[n], n))
            keyed.sort()
            layers[li] = [n for _, _, n in keyed]
            for k, n in enumerate(layers[li]):
                pos[n] = k

    for _ in range(6):
        sweep(True)
        sweep(False)

    # coordinates: `main` runs along the layers, `cross` across them
    lr = direction == "LR"
    msize = {n: (s[0] if lr else s[1]) for n, s in dsize.items()}
    csize = {n: (s[1] if lr else s[0]) for n, s in dsize.items()}
    main: dict[str, float] = {}
    cur = 0.0
    lw: list[float] = []
    for l in layers:
        w = max((msize[n] for n in l), default=0)
        lw.append(w)
        for n in l:
            main[n] = cur + (w - msize[n]) / 2
        cur += w + gap_layer

    cross: dict[str, float] = {}
    for l in layers:
        y = 0.0
        for n in l:
            cross[n] = y
            y += csize[n] + gap_node

    def recentre(li: int, nb: dict[str, list[str]]) -> None:
        l = layers[li]
        want = {}
        for n in l:
            ns = nb[n]
            want[n] = (sum(cross[m] + csize[m] / 2 for m in ns) / len(ns) - csize[n] / 2) if ns else cross[n]
        prev = None
        for n in l:
            lo = want[n] if prev is None else max(want[n], cross[prev] + csize[prev] + gap_node)
            cross[n] = lo
            prev = n
        # pull the layer back towards what its neighbours asked for, without breaking the order
        shift = sum(want[n] - cross[n] for n in l) / max(len(l), 1)
        for n in l:
            cross[n] += shift
        prev = None
        for n in l:
            if prev is not None and cross[n] < cross[prev] + csize[prev] + gap_node:
                cross[n] = cross[prev] + csize[prev] + gap_node
            prev = n

    for _ in range(5):
        for li in range(1, nlayers):
            recentre(li, up)
        for li in range(nlayers - 2, -1, -1):
            recentre(li, down)

    cmin = min(cross.values(), default=0)
    for n in cross:
        cross[n] -= cmin

    P: dict[str, tuple[float, float]] = {}
    for n in layer_of:
        P[n] = (main[n], cross[n]) if lr else (cross[n], main[n])
    centre = {n: (P[n][0] + dsize[n][0] / 2, P[n][1] + dsize[n][1] / 2) for n in P}

    routes: dict[tuple[str, str], list[tuple[float, float]]] = {}
    for (a, b), chain in chains.items():
        if len(chain) > 2:
            routes[(a, b)] = [centre[d] for d in chain[1:-1]]
    width = max((P[n][0] + dsize[n][0] for n in P), default=0)
    height = max((P[n][1] + dsize[n][1] for n in P), default=0)
    return {n: P[n] for n in sizes}, routes, width, height


def _apply_layout(scene: Scene, nodes: list[Node], edges: list[Edge], direction: str = "LR",
                  gap_layer: float = 90, gap_node: float = 34, rank: dict[str, int] | None = None,
                  auto: bool = True) -> None:
    sizes = {n.id: (n.w, n.h) for n in nodes}
    pairs = [(e.src, e.dst) for e in edges]
    pos, routes, W, H = layered(sizes, pairs, direction, gap_layer, gap_node, rank)
    if auto and direction == "LR" and len(nodes) > 4:
        # a long single row is unreadable on a page: take the top-down layout if its shape is closer to a page
        pos2, routes2, W2, H2 = layered(sizes, pairs, "TB", gap_node, gap_layer, rank)
        score = lambda w, h: abs(math.log((w / max(h, 1)) / 1.5))
        if score(W2, H2) + 0.05 < score(W, H):
            pos, routes = pos2, routes2
    for n in nodes:
        n.x, n.y = pos[n.id]
    scene.nodes += nodes
    for e in edges:
        if (e.src, e.dst) in routes:
            e.via = routes[(e.src, e.dst)]
    scene.edges += edges
    spread_parallel(scene.edges, scene)
    scene.fit()


# ================================================================== builders
def _box(nid: str, text: str, kind: str = "rounded", min_w: float = 130, max_w: float = 190, fill: str = WHITE,
         sub: str = "", bold: bool = False, pad: float = 18) -> Node:
    lines = wrap(text, max_w - pad, FS, bold)
    w = max(min_w, min(max_w, max(tw(l, FS, bold) for l in lines) + pad + 6))
    if sub:
        w = max(w, min(max_w + 40, tw(sub, 11) + pad))
    lines = wrap(text, w - pad, FS, bold)
    h = 16 * len(lines) + (14 if sub else 0) + 26
    return Node(nid, kind, 0, 0, w, h, "\n".join(lines), sub, fill, bold)


# ---------------------------------------------------------------- use case
def usecase_scene(spec: dict, title: str) -> Scene:
    sc = Scene("usecase", title)
    actors = spec.get("actors", [])
    ucs = spec.get("use_cases", [])
    cols = 1 if len(ucs) <= 6 else 2
    uw, uh, gy, gx = 220, 58, 26, 40
    rows = math.ceil(len(ucs) / cols) if ucs else 1
    bw = cols * uw + (cols - 1) * gx + 80
    bh = rows * (uh + gy) + 60
    left = [a for a in actors if not a.get("external")]
    right = [a for a in actors if a.get("external")]
    bx = 180
    sc.nodes.append(Node("sys", "boundary", bx, 0, bw, bh, spec.get("system", "System"), bold=True))
    place: dict[str, Node] = {}
    for i, u in enumerate(ucs):
        c, r = i // rows, i % rows
        n = Node(u["id"], "ellipse", bx + 40 + c * (uw + gx), 52 + r * (uh + gy), uw, uh,
                 "\n".join(wrap(f'{u["name"]}', uw - 50)[:2]), parent="sys")
        sc.nodes.append(n)
        place[u["id"]] = n
    by_actor: dict[str, list[Node]] = {}
    for u in ucs:
        by_actor.setdefault(u["actor"], []).append(place[u["id"]])

    def put(group: list[dict], x: float) -> None:
        ys: list[tuple[float, dict]] = []
        for a in group:
            mine = by_actor.get(a["name"], [])
            ys.append((sum(n.cy for n in mine) / len(mine) if mine else bh / 2, a))
        ys.sort(key=lambda t: t[0])
        last = -1e9
        for y, a in ys:
            y = max(y, last + 110)
            last = y
            sc.nodes.append(Node("a:" + a["name"], "actor", x, y - 40, 44, 80, a["name"]))

    put(left, 60)
    put(right, bx + bw + 70)
    k = 0
    for a in actors:
        for n in by_actor.get(a["name"], []):
            k += 1
            sc.edges.append(Edge(f"e{k}", "a:" + a["name"], n.id, end="none"))
    for kind, lab in (("includes", "«include»"), ("extends", "«extend»")):
        for r in spec.get(kind, []):
            if r["source"] in place and r["target"] in place:
                k += 1
                sc.edges.append(Edge(f"e{k}", r["source"], r["target"], label=lab, dash=True, end="open"))
    # actors keep their own y; boundary height may need to grow for tall actor columns
    sc.nodes[0].h = max(bh, max((n.y + n.h for n in sc.nodes if n.kind == "actor"), default=0) + 10)
    spread_parallel(sc.edges, sc)
    sc.fit()
    return sc


# ------------------------------------------------------------------- class
_CARD = {"": ""}


def class_scene(spec: dict, title: str) -> Scene:
    sc = Scene("class", title)
    nodes: list[Node] = []
    for c in spec.get("classes", []):
        attrs = [str(a) for a in c.get("attributes", [])]
        meths = [str(m) + "()" for m in c.get("methods", [])]
        w = max(150, max([tw(c["name"], 13, True) + 24] + [tw(r) + 20 for r in attrs + meths]))
        h = 28 + 18 * max(len(attrs), 1) + 8 + (18 * len(meths) + 8 if meths else 0)
        nodes.append(Node(c["name"], "class", 0, 0, w, h, c["name"], rows=attrs, rows2=meths, fill=HEAD, bold=True))
    edges: list[Edge] = []
    for i, r in enumerate(spec.get("relations", []), start=1):
        e = Edge(f"r{i}", r["source"], r["target"], label=r.get("label", ""),
                 src_text=r.get("multiplicity_source", ""), dst_text=r.get("multiplicity_target", ""))
        k = r["kind"]
        if k == "inheritance":
            e.end = "triangle"
        elif k == "aggregation":
            e.start = "diamond"
            e.end = "none"
        elif k == "composition":
            e.start = "diamond_f"
            e.end = "none"
        else:
            e.end = "none"
        edges.append(e)
    _apply_layout(sc, nodes, edges, "LR", gap_layer=110, gap_node=40)
    return sc


# ---------------------------------------------------------------------- ER
def er_scene(spec: dict, title: str) -> Scene:
    sc = Scene("er", title)
    nodes: list[Node] = []
    for ent in spec.get("entities", []):
        rows = [(a.get("key", ""), a["name"], a.get("type", "")) for a in ent.get("attributes", [])]
        kw = 28
        nw = max([tw(r[1]) for r in rows] + [0]) + 10
        tyw = max([tw(r[2], 11) for r in rows] + [0]) + 10
        w = max(170, tw(ent["name"], 13, True) + 30, kw + nw + tyw + 16)
        h = 30 + 22 * max(len(rows), 1)
        nodes.append(Node(ent["name"], "entity", 0, 0, w, h, ent["name"], rows=rows, fill=HEAD, bold=True))
    edges: list[Edge] = []
    for i, r in enumerate(spec.get("relations", []), start=1):
        edges.append(Edge(f"r{i}", r["source"], r["target"], label=r.get("label", ""),
                          start="er:" + r["cardinality_source"], end="er:" + r["cardinality_target"]))
    _apply_layout(sc, nodes, edges, "LR", gap_layer=130, gap_node=44)
    return sc


# --------------------------------------------------------------------- DFD
def dfd_scene(spec: dict, title: str) -> Scene:
    sc = Scene("dfd", title)
    nodes: list[Node] = []
    level = spec.get("level", 1)
    for x in spec.get("externals", []):
        n = _box(x["id"], x["name"], "rect", 120, 170, EXT, bold=True)
        n.meta["role"] = "external"
        nodes.append(n)
    for p in spec.get("processes", []):
        lines = wrap(p["name"], 130, 12, False)
        d = 118 if level == 0 else 128
        h = max(d, 40 + 16 * len(lines) + 20)
        w = max(d, h) if level != 0 else 160
        n = Node(p["id"], "ellipse", 0, 0, w if level != 0 else 170, max(h, 120) if level != 0 else 170,
                 f'{p["id"]}\n' + "\n".join(lines), fill=WHITE)
        n.meta["role"] = "process"
        nodes.append(n)
    for s in spec.get("stores", []):
        lines = wrap(s["name"], 120, 12)
        n = Node(s["id"], "store", 0, 0, 190, 30 + 16 * len(lines), "\n".join(lines), fill=WHITE)
        n.meta["role"] = "store"
        n.meta["tag"] = s["id"]
        nodes.append(n)
    edges = [Edge(f"f{i}", f["source"], f["target"], label=f.get("label", ""))
             for i, f in enumerate(spec.get("flows", []), start=1)]
    if level == 0 and len(nodes) <= 9:
        _star(sc, nodes, edges)
    else:
        _radial(sc, nodes, edges)
    return sc


def _radial(sc: Scene, nodes: list[Node], edges: list[Edge]) -> None:
    """Processes on a ring, stores on a second ring, external entities on the outside, each one placed
    at the average direction of the processes it talks to. Keeps flows short and mostly uncrossed."""
    procs = [n for n in nodes if n.meta.get("role") == "process"]
    outer = [n for n in nodes if n.meta.get("role") != "process"]
    byid = {n.id: n for n in nodes}
    n = max(len(procs), 1)
    rp = max(210.0, n * 52.0)
    rx, ry = rp * 1.3, rp
    ang: dict[str, float] = {}

    def ring_radius(t: float) -> float:       # polar radius of the process ellipse at polar angle t
        return (rx * ry) / math.sqrt((ry * math.cos(t)) ** 2 + (rx * math.sin(t)) ** 2)

    for i, p in enumerate(procs):
        ang[p.id] = -math.pi / 2 + 2 * math.pi * i / n
        r = ring_radius(ang[p.id])
        p.x, p.y = r * math.cos(ang[p.id]) - p.w / 2, r * math.sin(ang[p.id]) - p.h / 2
    nbr: dict[str, list[str]] = {o.id: [] for o in outer}
    for e in edges:
        for a, b in ((e.src, e.dst), (e.dst, e.src)):
            if a in nbr and b in ang:
                nbr[a].append(b)
    for k, o in enumerate(outer):
        ns = nbr[o.id]
        if ns:
            sx = sum(math.cos(ang[m]) for m in ns)
            sy = sum(math.sin(ang[m]) for m in ns)
            ang[o.id] = math.atan2(sy, sx) if abs(sx) + abs(sy) > 1e-6 else -math.pi / 2 + k
        else:
            ang[o.id] = -math.pi / 2 + 2 * math.pi * k / max(len(outer), 1)
    pmax = max((max(p.w, p.h) for p in procs), default=130) / 2
    has_store = any(o.meta.get("role") == "store" for o in outer)

    def reach(o: Node, t: float, extra: float) -> float:
        ux, uy = abs(math.cos(t)), abs(math.sin(t))
        return ring_radius(t) + pmax + (ux * o.w / 2 + uy * o.h / 2) + extra

    extras = {"store": 70.0, "external": 90.0 + (150.0 if has_store else 0.0)}
    ring = sorted(outer, key=lambda o: ang[o.id])
    for _ in range(6):  # stores and externals share one angular order, so no flow runs through a store
        for a, b in zip(ring, ring[1:] + ring[:1]):
            if a is b:
                continue
            ra = min(reach(a, ang[a.id], extras[a.meta["role"]]), reach(b, ang[b.id], extras[b.meta["role"]]))
            need = (max(a.w, a.h) / 2 + max(b.w, b.h) / 2 + 40) / ra
            gap = (ang[b.id] - ang[a.id]) % (2 * math.pi)
            if gap < need and len(ring) > 1:
                push = (need - gap) / 2
                ang[a.id] -= push
                ang[b.id] += push
    for o in ring:
        d = reach(o, ang[o.id], extras[o.meta["role"]])
        o.x = d * math.cos(ang[o.id]) - o.w / 2
        o.y = d * math.sin(ang[o.id]) - o.h / 2
    sc.nodes += nodes
    sc.edges += edges
    spread_parallel(sc.edges, sc, step=52)
    sc.fit()


def _star(sc: Scene, nodes: list[Node], edges: list[Edge]) -> None:
    """Level 0 context diagram: one process in the middle, external entities left and right."""
    proc = next(n for n in nodes if n.meta.get("role") == "process")
    ext = [n for n in nodes if n is not proc]
    left, right = ext[0::2], ext[1::2]
    gap = 130
    colh = lambda col: sum(n.h for n in col) + gap * max(len(col) - 1, 0)
    H = max(colh(left), colh(right), proc.h)
    px = 330
    proc.x, proc.y = px, (H - proc.h) / 2
    for col, x in ((left, 0), (right, px + proc.w + 330 - 120)):
        y = (H - colh(col)) / 2
        for n in col:
            n.x, n.y = x + (120 - n.w) / 2 if x == 0 else x, y
            y += n.h + gap
    sc.nodes += nodes
    sc.edges += edges
    spread_parallel(sc.edges, sc, step=46)
    sc.fit()


# ---------------------------------------------------------------- sequence
def sequence_scene(spec: dict, title: str, actors: set[str] | None = None) -> Scene:
    sc = Scene("sequence", title)
    actors = {a.lower() for a in (actors or set())}
    parts = spec.get("participants", [])
    msgs = spec.get("messages", [])
    colw = max(170, max([tw(p) for p in parts] + [0]) + 50)
    top, step = 24, 46
    llen = 80 + step * (len(msgs) + 1)
    pid = {}
    for i, p in enumerate(parts):
        is_actor = p.lower() in actors
        n = Node(f"p{i}", "lifeline", 30 + i * colw, top, 120, llen, p, fill=HEAD if not is_actor else WHITE,
                 meta={"actor": is_actor, "head": 80 if is_actor else 40})
        sc.nodes.append(n)
        pid[p] = n
    y0 = top + 80 + 18
    ys = []
    for i, m in enumerate(msgs):
        y = y0 + i * step
        ys.append(y)
        a, b = pid[m["source"]], pid[m["target"]]
        if a is b:
            pts = [(a.cx, y - 10), (a.cx + 46, y - 10), (a.cx + 46, y + 12), (a.cx, y + 12)]
        else:
            pts = [(a.cx, y), (b.cx, y)]
        kind = m["kind"]
        e = Edge(f"m{i + 1}", a.id, b.id, label=f"{i + 1}. {m['text']}", dash=(kind == "return"),
                 end="open" if kind in ("return", "async") else "arrow", pts=pts,
                 meta={"y": y, "self": a is b})
        sc.edges.append(e)
    for j, f in enumerate(spec.get("fragments", [])):
        s, e_ = max(f["start"], 1), min(f["end"], len(msgs))
        if s > e_:
            continue
        x1 = min(n.x for n in pid.values()) - 14
        x2 = max(n.x + n.w for n in pid.values()) + 14
        y1, y2 = ys[s - 1] - 30, ys[e_ - 1] + 22
        sc.nodes.append(Node(f"f{j}", "frame", x1, y1, x2 - x1, y2 - y1, f["kind"], sub=f"[{f['label']}]"))
    sc.fit()
    return sc


# ---------------------------------------------------------------- activity
def activity_scene(spec: dict, title: str) -> Scene:
    sc = Scene("activity", title)
    nodes: list[Node] = []
    for n in spec.get("nodes", []):
        k = n["kind"]
        if k == "start":
            nodes.append(Node(n["id"], "dot", 0, 0, 24, 24))
        elif k == "end":
            nodes.append(Node(n["id"], "end", 0, 0, 28, 28))
        elif k == "decision":
            lines = wrap(n["label"] or "?", 120)
            nodes.append(Node(n["id"], "diamond", 0, 0, 170, 40 + 16 * len(lines), "\n".join(lines), fill=WARM))
        elif k == "merge":
            nodes.append(Node(n["id"], "diamond", 0, 0, 30, 30, fill=WARM))
        else:
            nodes.append(_box(n["id"], n["label"], "rounded", 150, 200, SOFT))
    edges = [Edge(f"t{i}", e["source"], e["target"], label=e.get("label", ""))
             for i, e in enumerate(spec.get("edges", []), start=1)]
    _apply_layout(sc, nodes, edges, "TB", gap_layer=52, gap_node=60, auto=False)
    return sc


# ------------------------------------------------------------------- state
def state_scene(spec: dict, title: str) -> Scene:
    sc = Scene("state", title)
    nodes: list[Node] = [Node("__i", "dot", 0, 0, 24, 24)]
    for s in spec.get("states", []):
        nodes.append(_box(s, s, "rounded", 120, 170, SOFT))
    edges = [Edge("t0", "__i", spec["initial"])]
    for i, t in enumerate(spec.get("transitions", []), start=1):
        edges.append(Edge(f"t{i}", t["source"], t["target"], label=t.get("label", "")))
    for j, f in enumerate(spec.get("finals", [])):
        nodes.append(Node(f"__f{j}", "end", 0, 0, 28, 28))
        edges.append(Edge(f"tf{j}", f, f"__f{j}"))
    _apply_layout(sc, nodes, edges, "LR", gap_layer=110, gap_node=48, auto=False)
    return sc


# -------------------------------------------------------------- deployment
_STEREO = {"client": "device", "server": "server", "database": "database", "external": "external"}
_FILL = {"client": "#EAF1FB", "server": SOFT, "database": DB, "external": WARM}


def deployment_scene(spec: dict, title: str) -> Scene:
    sc = Scene("deployment", title)
    nodes: list[Node] = []
    kids: list[Node] = []
    for n in spec.get("nodes", []):
        arts = n.get("artifacts", [])
        head = 52 + (16 if n.get("technology") else 0)
        w = max(190, tw(n["name"], 13, True) + 50, max([tw(a) for a in arts] + [0]) + 70)
        h = head + len(arts) * 40 + 16
        node = Node(n["id"], "cylinder" if n["kind"] == "database" else "cube", 0, 0, w, h, n["name"],
                    sub=f"«{_STEREO[n['kind']]}»", fill=_FILL[n["kind"]], bold=True,
                    meta={"tech": n.get("technology", ""), "head": head})
        nodes.append(node)
    edges = [Edge(f"l{i}", l["source"], l["target"], label=l.get("protocol", ""), end="none")
             for i, l in enumerate(spec.get("links", []), start=1)]
    _apply_layout(sc, nodes, edges, "LR", gap_layer=140, gap_node=50)
    byid = {n["id"]: n for n in spec.get("nodes", [])}
    for node in nodes:
        for k, a in enumerate(byid[node.id].get("artifacts", [])):
            kids.append(Node(f"{node.id}.a{k}", "artifact", node.x + 24, node.y + node.meta["head"] + k * 40,
                             node.w - 48, 30, a, parent=node.id, fill=WHITE))
    sc.nodes += kids
    return sc


def component_scene(components: list[dict], title: str) -> Scene:
    """SDD architecture figure: components grouped by layer, calls point down the layers."""
    sc = Scene("component", title)
    order = ["presentation", "api", "service", "data", "integration", "infrastructure"]
    layer_fill = {"presentation": "#EAF1FB", "api": "#EFE9F7", "service": "#E6F4EA", "data": WARM,
                  "integration": "#FBE9E7", "infrastructure": SOFT}
    nodes: list[Node] = []
    for c in components:
        n = _box(c["id"], c["name"], "rect", 140, 170, layer_fill.get(c["layer"], SOFT), sub=c["id"], bold=True)
        n.meta["layer"] = c["layer"]
        nodes.append(n)
    ids = {n.id for n in nodes}
    edges = [Edge(f"d{i}", c["id"], d, end="arrow") for i, (c, d) in enumerate(
        [(c, d) for c in components for d in c.get("depends_on", []) if d in ids], start=1)]
    rank = {n.id: order.index(n.meta["layer"]) if n.meta["layer"] in order else 5 for n in nodes}
    _apply_layout(sc, nodes, edges, "TB", gap_layer=60, gap_node=36, rank=rank, auto=False)
    return sc


def scene_for(dtype: str, spec: dict, title: str, actors: set[str] | None = None) -> Scene:
    if dtype == "usecase":
        return usecase_scene(spec, title)
    if dtype == "class":
        return class_scene(spec, title)
    if dtype == "er":
        return er_scene(spec, title)
    if dtype == "dfd":
        return dfd_scene(spec, title)
    if dtype == "sequence":
        return sequence_scene(spec, title, actors)
    if dtype == "activity":
        return activity_scene(spec, title)
    if dtype == "state":
        return state_scene(spec, title)
    if dtype == "deployment":
        return deployment_scene(spec, title)
    raise ValueError(f"unknown diagram type {dtype}")
