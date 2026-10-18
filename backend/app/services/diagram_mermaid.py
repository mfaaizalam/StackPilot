"""Deterministic converters: validated diagram model -> Mermaid text.
No AI involved. All user/AI text is scrubbed so it cannot break Mermaid syntax."""
import re
from app.schemas.diagrams import ActivityModel, ClassModel, DeploymentModel, SequenceModel, StateModel
_BAD = re.compile(r'[;#"`{}<>\\|~\n\r\t]')


def _txt(s: str) -> str:
    """Safe free text (labels, messages)."""
    return " ".join(_BAD.sub(" ", str(s or "")).split())


_RESERVED = {"class", "end", "style", "click", "link", "subgraph", "direction", "default", "note", "state",
             "participant", "actor", "namespace", "interface", "enum", "abstract", "service", "graph", "flowchart"}


def _lab(s: str) -> str:
    """Text after ' : ' in class/state diagrams: a further colon would end the statement."""
    return _txt(str(s or "").replace(":", " "))


def _ident(s: str, prefix: str = "x") -> str:
    """Safe identifier: ascii word chars only, never a Mermaid keyword, never starts with a digit."""
    t = re.sub(r"[^A-Za-z0-9_]+", "_", str(s or "")).strip("_")
    if not t:
        return prefix
    if t[0].isdigit() or t.lower() in _RESERVED:
        return f"{prefix}_{t}"
    return t


# ------------------------------------------------------------------ class
_ARROW = {"association": "-->", "aggregation": "o--", "composition": "*--", "inheritance": "<|--"}


def class_to_mermaid(m: ClassModel) -> str:
    ids: dict[str, str] = {}
    for c in m.classes:
        base = _ident(c.name, "C")
        ident, k = base, 2
        while ident in ids.values():  # two names that collapse to the same identifier
            ident, k = f"{base}_{k}", k + 1
        ids[c.name] = ident
    L = ["classDiagram", "  direction LR"]
    for c in m.classes:
        shown = _txt(c.name)
        label = f'["{shown}"]' if shown != ids[c.name] else ""
        L.append(f"  class {ids[c.name]}{label} {{")
        for a in c.attributes:
            L.append(f"    +{_txt(a).replace('(', '').replace(')', '')}")
        for x in c.methods:
            L.append(f"    +{_txt(x).replace('(', '').replace(')', '')}()")
        L.append("  }")
    for r in m.relations:
        a, b = ids[r.source], ids[r.target]
        label = f" : {_lab(r.label)}" if _lab(r.label) else ""
        if r.kind == "inheritance":
            L.append(f"  {b} <|-- {a}{label}")  # parent <|-- child
            continue
        ms = f' "{_txt(r.multiplicity_source)}"' if _txt(r.multiplicity_source) else ""
        mt = f' "{_txt(r.multiplicity_target)}"' if _txt(r.multiplicity_target) else ""
        L.append(f"  {a}{ms} {_ARROW[r.kind]}{mt} {b}{label}")
    return "\n".join(L)


# --------------------------------------------------------------- sequence
_SEQ_ARROW = {"sync": "->>", "return": "-->>", "async": "-)"}


def sequence_to_mermaid(m: SequenceModel, actors: set[str] | None = None) -> str:
    actors = {a.lower() for a in (actors or set())}
    pid = {p: f"p{i}" for i, p in enumerate(m.participants, start=1)}
    L = ["sequenceDiagram", "  autonumber"]
    for p in m.participants:
        kind = "actor" if p.lower() in actors else "participant"
        L.append(f"  {kind} {pid[p]} as {_txt(p)}")
    starts = {f.start: f for f in m.fragments}
    ends = {f.end for f in m.fragments}
    for i, x in enumerate(m.messages, start=1):
        if i in starts:
            f = starts[i]
            L.append(f"  {f.kind} {_txt(f.label)}")
        L.append(f"  {pid[x.source]}{_SEQ_ARROW[x.kind]}{pid[x.target]}: {_txt(x.text)}")
        if i in ends:
            L.append("  end")
    return "\n".join(L)


# --------------------------------------------------------------- activity
def activity_to_mermaid(m: ActivityModel) -> str:
    nid = {n.id: f"n{i}" for i, n in enumerate(m.nodes, start=1)}
    L = ["flowchart TD"]
    for n in m.nodes:
        i, label = nid[n.id], _txt(n.label)
        if n.kind == "start":
            L.append(f'  {i}(("Start")):::startNode')
        elif n.kind == "end":
            L.append(f'  {i}((("End"))):::endNode')
        elif n.kind == "decision":
            L.append(f'  {i}{{"{label or "?"}"}}:::decisionNode')
        elif n.kind == "merge":
            L.append(f'  {i}{{" "}}:::mergeNode')
        else:
            L.append(f'  {i}("{label}"):::actionNode')
    for e in m.edges:
        lab = _txt(e.label)
        L.append(f'  {nid[e.source]} -->|"{lab}"| {nid[e.target]}' if lab else f"  {nid[e.source]} --> {nid[e.target]}")
    L += [
        "  classDef startNode fill:#171717,stroke:#171717,color:#ffffff",
        "  classDef endNode fill:#ffffff,stroke:#171717,stroke-width:3px,color:#171717",
        "  classDef actionNode fill:#f5f5f5,stroke:#737373,color:#171717",
        "  classDef decisionNode fill:#fef3c7,stroke:#d97706,color:#171717",
        "  classDef mergeNode fill:#fef3c7,stroke:#d97706,color:#171717",
    ]
    return "\n".join(L)


# ------------------------------------------------------------------ state
def state_to_mermaid(m: StateModel) -> str:
    sid = {s: f"s{i}" for i, s in enumerate(m.states, start=1)}
    L = ["stateDiagram-v2", "  direction LR"]
    for s in m.states:
        L.append(f'  state "{_txt(s)}" as {sid[s]}')
    L.append(f"  [*] --> {sid[m.initial]}")
    for t in m.transitions:
        lab = _lab(t.label)
        L.append(f"  {sid[t.source]} --> {sid[t.target]}" + (f" : {lab}" if lab else ""))
    for f in m.finals:
        L.append(f"  {sid[f]} --> [*]")
    return "\n".join(L)

# ------------------------------------------------------------- deployment
_STEREO = {"client": "device", "server": "server", "database": "database", "external": "external"}
_NODE_STYLE = {
    "client": "fill:#eff6ff,stroke:#3b82f6,color:#171717",
    "server": "fill:#f5f5f5,stroke:#737373,color:#171717",
    "database": "fill:#ecfdf5,stroke:#10b981,color:#171717",
    "external": "fill:#fef3c7,stroke:#d97706,color:#171717",
}


def deployment_to_mermaid(m: DeploymentModel) -> str:
    nid = {n.id: f"d{i}" for i, n in enumerate(m.nodes, start=1)}
    L = ["flowchart LR"]
    for n in m.nodes:
        i = nid[n.id]
        tech = f" ({_txt(n.technology)})" if _txt(n.technology) else ""
        L.append(f'  subgraph {i}["«{_STEREO[n.kind]}» {_txt(n.name)}{tech}"]')
        for k, a in enumerate(n.artifacts, start=1):
            L.append(f'    {i}_a{k}["{_txt(a)}"]:::artifactNode')
        L.append("  end")
    for l in m.links:
        lab = _txt(l.protocol)
        L.append(f'  {nid[l.source]} ---|"{lab}"| {nid[l.target]}' if lab else f"  {nid[l.source]} --- {nid[l.target]}")
    for n in m.nodes:
        L.append(f"  style {nid[n.id]} {_NODE_STYLE[n.kind]}")
    L.append("  classDef artifactNode fill:#ffffff,stroke:#737373,color:#171717")
    return "\n".join(L)

def to_mermaid(dtype: str, spec: dict, actors: set[str] | None = None) -> str | None:
    if dtype == "class":
        return class_to_mermaid(ClassModel.model_validate(spec))
    if dtype == "sequence":
        return sequence_to_mermaid(SequenceModel.model_validate(spec), actors)
    if dtype == "activity":
        return activity_to_mermaid(ActivityModel.model_validate(spec))
    if dtype == "state":
        return state_to_mermaid(StateModel.model_validate(spec))
    if dtype == "deployment":
        return deployment_to_mermaid(DeploymentModel.model_validate(spec))
    return None  # use-case diagrams are drawn by diagram_usecase_svg
