"""Deterministic diagram builders that need NO AI.
Used (a) for the use-case diagram itself, (b) as a safety net when the AI is
unavailable or returns something unusable, so the demo never shows an empty tab."""
import re

from app.schemas.diagrams import (
    MAX_CLASSES, ActEdge, ActivityModel, ActNode, ClassModel, ClassNode, ClassRelation,
    Message, SequenceModel, UCActor, UCNode, UseCaseModel,
)
from app.schemas.srs import Entity, Requirements, UseCase
from app.services.diagram_validator import clip

_EXTERNAL_NAME = re.compile(r"(system|service|gateway|api|server|bank|provider|sms|email|payment|third)", re.I)
_EXTERNAL_DESC = re.compile(r"\bexternal\b|third[- ]party", re.I)
_PRIORITY_WEIGHT = {"must": 3, "should": 2, "could": 1}


def _short(step: str, actor: str = "") -> str:
    """'The system validates the input.' -> 'Validates the input' (readable at 28 chars)."""
    who = "|".join(re.escape(w) for w in ("system", "actor", "user", actor) if w)
    t = re.sub(rf"^\s*(the\s+)?({who})\s+(?=[a-z])", "", step.strip().rstrip("."), count=1, flags=re.I)
    t = t.split(":")[0].strip() or step
    return clip(t[:1].upper() + t[1:])


# ------------------------------------------------------------- use case
def build_usecase_model(req: Requirements) -> UseCaseModel:
    names = [a.name for a in req.actors]
    extra = [u.actor for u in req.use_cases if u.actor not in names]
    actors = []
    for a in req.actors:
        ext = bool(_EXTERNAL_NAME.search(a.name) or _EXTERNAL_DESC.search(a.description or ""))
        actors.append(UCActor(name=a.name, external=ext))
    actors += [UCActor(name=n, external=False) for n in dict.fromkeys(extra)]
    used = {u.actor for u in req.use_cases}
    actors = [a for a in actors if a.name in used]  # no floating actors
    return UseCaseModel(
        system=clip(req.title, 40),
        actors=actors,
        use_cases=[UCNode(id=u.id, name=clip(u.name), actor=u.actor) for u in req.use_cases],
    )


def rank_use_cases(req: Requirements) -> list[UseCase]:
    """Most important first: more / higher-priority requirements, richer flow."""
    prio = {f.id: _PRIORITY_WEIGHT[f.priority] for f in req.functional_requirements}

    def score(u: UseCase) -> float:
        return sum(prio.get(i, 1) for i in u.fr_ids) + 0.1 * len(u.main_flow)

    return sorted(req.use_cases, key=lambda u: -score(u))  # stable


# ---------------------------------------------------------------- class
_REL = re.compile(r"^\s*(?P<a>[\w ]+?)\s+(?P<verb>has many|has one|has a|has|belongs to|contains|is a|extends|owns|places|manages|references)\s+(?P<b>[\w ]+?)\s*$", re.I)


def _find(name: str, known: dict[str, str]) -> str | None:
    n = name.strip().lower()
    if n in known:
        return known[n]
    if n.endswith("s") and n[:-1] in known:
        return known[n[:-1]]
    return None


def class_from_entities(entities: list[Entity]) -> ClassModel:
    classes = [ClassNode(name=re.sub(r"\W+", "", e.name.title()) or "Entity",
                         attributes=list(e.attributes), methods=[]) for e in entities]
    known = {e.name.strip().lower(): c.name for e, c in zip(entities, classes)}
    rels, seen = [], set()
    for e, c in zip(entities, classes):
        for text in e.relations:
            m = _REL.match(text)
            if not m:
                continue
            a, b = _find(m["a"], known), _find(m["b"], known)
            if not a or not b or a == b:
                continue
            verb = m["verb"].lower()
            if verb in ("is a", "extends"):
                r = ClassRelation(kind="inheritance", source=a, target=b, multiplicity_source="", multiplicity_target="", label="")
            elif verb == "belongs to":
                r = ClassRelation(kind="association", source=a, target=b, multiplicity_source="*", multiplicity_target="1", label="belongs to")
            elif verb in ("has one", "has a"):
                r = ClassRelation(kind="association", source=a, target=b, multiplicity_source="1", multiplicity_target="1", label="has")
            else:
                r = ClassRelation(kind="association", source=a, target=b, multiplicity_source="1",
                                  multiplicity_target="*", label=verb.replace("has many", "has"))
            pair = frozenset((a, b))
            if pair in seen:
                continue
            seen.add(pair)
            rels.append(r)
    return ClassModel(classes=classes, relations=rels)


def chunk_entities(entities: list[Entity], size: int = MAX_CLASSES, max_parts: int = 2) -> list[list[Entity]]:
    """Split a large domain into <= `size` entities per diagram, keeping connected
    entities together where possible (so each diagram tells a coherent story)."""
    if len(entities) <= size:
        return [entities]
    by_name = {e.name.strip().lower(): e for e in entities}
    adj: dict[str, set[str]] = {k: set() for k in by_name}
    for e in entities:
        for text in e.relations:
            m = _REL.match(text)
            if m:
                a, b = _find(m["a"], {k: k for k in by_name}), _find(m["b"], {k: k for k in by_name})
                if a and b and a != b:
                    adj[a].add(b)
                    adj[b].add(a)
    seen, comps = set(), []
    for k in by_name:
        if k in seen:
            continue
        comp, stack = [], [k]
        seen.add(k)
        while stack:
            n = stack.pop()
            comp.append(n)
            for nxt in sorted(adj[n]):
                if nxt not in seen:
                    seen.add(nxt)
                    stack.append(nxt)
        comps.append(comp)
    bins: list[list[str]] = []
    for comp in sorted(comps, key=len, reverse=True):
        comp = sorted(comp, key=lambda n: -len(adj[n]))[:size]
        for b in bins:
            if len(b) + len(comp) <= size:
                b.extend(comp)
                break
        else:
            bins.append(list(comp))
    order = {e.name.strip().lower(): i for i, e in enumerate(entities)}
    return [[by_name[n] for n in sorted(b, key=order.get)] for b in bins[:max_parts]]


# -------------------------------------------------------------- sequence
def sequence_from_usecase(uc: UseCase) -> SequenceModel:
    actor = clip(uc.actor, 20)
    parts = [actor, "System"] if actor.lower() != "system" else ["User", "System"]
    msgs = []
    for step in uc.main_flow[:14]:
        system_acts = re.match(r"^\s*(the\s+)?system\b", step, re.I)
        a, b = (parts[1], parts[0]) if system_acts else (parts[0], parts[1])
        msgs.append(Message(source=a, target=b, text=_short(step, uc.actor),
                            kind="return" if system_acts else "sync"))
    return SequenceModel(participants=parts, messages=msgs, fragments=[])


# -------------------------------------------------------------- activity
def activity_from_usecase(uc: UseCase) -> ActivityModel:
    steps = [_short(s, uc.actor) for s in uc.main_flow[:10]] or [clip(uc.name)]
    nodes = [ActNode(id="n0", kind="start", label="")]
    edges: list[ActEdge] = []
    prev, prev_label = "n0", ""
    for i, step in enumerate(steps, start=1):
        nodes.append(ActNode(id=f"a{i}", kind="action", label=step))
        edges.append(ActEdge(source=prev, target=f"a{i}", label=prev_label))
        prev, prev_label = f"a{i}", ""
        if i == 2 and uc.alternate_flows and len(steps) >= 3:  # show the alternate path as a decision
            nodes.append(ActNode(id="d1", kind="decision", label="Input valid?"))
            nodes.append(ActNode(id="a_err", kind="action", label=_short(uc.alternate_flows[0], uc.actor)))
            edges.append(ActEdge(source=prev, target="d1", label=""))
            edges.append(ActEdge(source="d1", target="a_err", label="No"))
            edges.append(ActEdge(source="a_err", target="a1", label="Retry"))
            prev, prev_label = "d1", "Yes"
    nodes.append(ActNode(id="n_end", kind="end", label=""))
    edges.append(ActEdge(source=prev, target="n_end", label=prev_label))
    return ActivityModel(nodes=nodes, edges=edges)
