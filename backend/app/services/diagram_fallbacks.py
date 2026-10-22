"""Deterministic diagram builders that need NO AI.
Used (a) for the use-case diagram itself, (b) as a safety net when the AI is
unavailable or returns something unusable, so the demo never shows an empty tab."""
import re

from app.schemas.diagrams import (
    MAX_CLASSES, ActEdge, ActivityModel, ActNode, ClassModel, ClassNode, ClassRelation,
    DeploymentModel, DeployLink, DeployNode, DfdExternal, DfdFlow, DfdModel, DfdProcess, DfdStore, ErAttribute,
    ErEntity, ErModel, ErRelation, Message, SequenceModel, UCActor, UCNode, UseCaseModel,
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

# ------------------------------------------------------------ deployment
def deployment_from_requirements(req: Requirements) -> DeploymentModel:
    """Generic 3-tier layout plus one external node per named external interface."""
    nodes = [
        DeployNode(id="d1", name="Client Device", kind="client", technology="Web browser",
                   artifacts=["Web UI"]),
        DeployNode(id="d2", name="Application Server", kind="server", technology="",
                   artifacts=["Web App", "REST API"]),
        DeployNode(id="d3", name="Database Server", kind="database", technology="",
                   artifacts=["Database"]),
    ]
    links = [DeployLink(source="d1", target="d2", protocol="HTTPS"),
             DeployLink(source="d2", target="d3", protocol="SQL/TCP")]
    for i, text in enumerate(req.external_interfaces[:3], start=4):
        name = clip(re.split(r"\s[-–—:(]|[:(]", str(text), maxsplit=1)[0].strip() or str(text))
        nodes.append(DeployNode(id=f"d{i}", name=name, kind="external", technology="",
                                artifacts=["External API"]))
        links.append(DeployLink(source="d2", target=f"d{i}", protocol="HTTPS"))
    return DeploymentModel(nodes=nodes, links=links)

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



# ====================================================== entity-relationship
_COL_STOP = re.compile(r"\s+(NOT\s+NULL|NULL|UNIQUE|PRIMARY|REFERENCES|DEFAULT|CHECK)\b", re.I)
_TYPE_ALIAS = {"SERIAL": "INT", "INTEGER": "INT", "BIGSERIAL": "BIGINT", "NUMERIC": "DECIMAL", "TIMESTAMP": "TIMESTAMP"}


def er_from_tables(tables) -> ErModel:
    """ER model from the SDD table designs (TableDesign list): the picture always matches the data dictionary."""
    from app.services.sdd_fallbacks import pascal, singular

    by_table = {t.table.lower(): pascal(t.entity) for t in tables}
    by_single = {singular(t.table).lower(): pascal(t.entity) for t in tables}
    ents, rels, seen = [], [], set()
    for t in tables:
        me = pascal(t.entity)
        attrs = []
        for raw in t.columns:
            name, _, spec = raw.partition(":")
            name, spec = name.strip(), spec.strip()
            if not name:
                continue
            m = _COL_STOP.search(spec)
            typ = (spec[: m.start()] if m else spec).strip().upper() or "VARCHAR(255)"
            typ = _TYPE_ALIAS.get(typ, typ)
            up = spec.upper()
            ref = re.search(r"REFERENCES\s+(\w+)", spec, re.I)
            parent = by_table.get(ref.group(1).lower()) if ref else None
            if not parent and name.lower().endswith("_id") and name.lower() != "id":
                parent = by_single.get(name[:-3].lower())
            key = "PK" if "PRIMARY KEY" in up else "FK" if (ref or parent) else "UK" if "UNIQUE" in up else ""
            attrs.append(ErAttribute(name=name, type=typ, key=key))
            if parent and parent != me and (parent, me) not in seen:
                seen.add((parent, me))
                one_to_one = "UNIQUE" in up
                rels.append(ErRelation(source=parent, target=me, cardinality_source="one" if "NOT NULL" in up else "zero_or_one",
                                       cardinality_target="zero_or_one" if one_to_one else "many", label="has"))
        ents.append(ErEntity(name=me, attributes=attrs))
    return ErModel(entities=ents, relations=rels)


def er_from_requirements(req: Requirements) -> ErModel:
    from app.services.sdd_fallbacks import table_from_entity
    return er_from_tables([table_from_entity(e, req.entities) for e in req.entities])


# ================================================================= data flow
_READ_VERBS = {"view", "search", "list", "browse", "track", "read", "check", "display", "show", "see", "find", "export", "download", "report"}


def _noun(name: str) -> str:
    words = re.findall(r"[A-Za-z]+", name)
    return words[-1].capitalize() if words else "Data"


def _process_name(uc_name: str) -> str:
    return clip(" ".join(w if i else w.capitalize() for i, w in enumerate(uc_name.split())), 28)


def dfd_level1_from_requirements(req: Requirements) -> tuple[DfdModel, dict[str, UseCase]]:
    """Deterministic Level 1: one process per important use case, one store per entity."""
    ucs = rank_use_cases(req)[:6]
    used = {u.actor for u in ucs}
    ext = [DfdExternal(id=f"e{i}", name=clip(a.name)) for i, a in enumerate([a for a in req.actors if a.name in used], start=1)]
    by_actor = {x.name: x.id for x in ext}
    k = len(ext)
    for text in req.external_interfaces[:3]:
        if len(ext) >= 6:
            break
        k += 1
        ext.append(DfdExternal(id=f"e{k}", name=clip(re.split(r"\s[-–—:(]|[:(]", str(text), maxsplit=1)[0].strip() or str(text))))
    ents = req.entities[:5]
    sto = [DfdStore(id=f"D{i}", name=clip(e.name)) for i, e in enumerate(ents, start=1)]
    procs, flows, mapping = [], [], {}
    fr_text = {f.id: f"{f.title} {f.statement}" for f in req.functional_requirements}
    for i, u in enumerate(ucs, start=1):
        pid = str(i)
        procs.append(DfdProcess(id=pid, name=_process_name(u.name)))
        mapping[pid] = u
        noun = _noun(u.name)
        actor_id = by_actor.get(u.actor)
        if actor_id:
            flows.append(DfdFlow(source=actor_id, target=pid, label=clip(f"{noun} request")))
            flows.append(DfdFlow(source=pid, target=actor_id, label=clip(f"{noun} result")))
        blob = " ".join([u.name, u.description, *u.main_flow, *(fr_text.get(f, "") for f in u.fr_ids)]).lower()
        hits = [(j, e) for j, e in enumerate(ents, start=1) if re.search(rf"\b{re.escape(e.name.lower())}s?\b", blob)]
        if not hits and sto:
            hits = [(((i - 1) % len(ents)) + 1, ents[(i - 1) % len(ents)])]
        read_only = u.name.lower().split()[0] in _READ_VERBS if u.name.split() else False
        for n, (j, e) in enumerate(hits[:1]):
            flows.append(DfdFlow(source=f"D{j}", target=pid, label=clip(f"{e.name} data")))
            if not read_only:
                flows.append(DfdFlow(source=pid, target=f"D{j}", label=clip(f"{e.name} record")))
    for x in ext[len(by_actor):]:  # external systems: attach to the process whose text mentions them, else the first
        key = x.name.lower().split()[0]
        pid = next((p for p, u in mapping.items() if key in (u.name + " " + u.description + " ".join(u.main_flow)).lower()), "1")
        flows.append(DfdFlow(source=pid, target=x.id, label="Service request"))
        flows.append(DfdFlow(source=x.id, target=pid, label="Service response"))
    return DfdModel(level=1, title=clip(f"Level 1 DFD: {req.title}", 60), parent="", externals=ext,
                    processes=procs, stores=sto, flows=flows), mapping


def dfd_context_from_level1(l1: DfdModel, req: Requirements) -> DfdModel:
    """Level 0 is the Level 1 diagram folded into one process, so the two always balance."""
    flows = []
    ids = {p.id for p in l1.processes}
    for x in l1.externals:
        ins = list(dict.fromkeys(f.label for f in l1.flows if f.source == x.id and f.target in ids))
        outs = list(dict.fromkeys(f.label for f in l1.flows if f.target == x.id and f.source in ids))
        if ins:
            flows.append(DfdFlow(source=x.id, target="0", label=clip(" / ".join(ins[:2]), 40)))
        if outs:
            flows.append(DfdFlow(source="0", target=x.id, label=clip(" / ".join(outs[:2]), 40)))
    return DfdModel(level=0, title=clip(f"Level 0 DFD: {req.title}", 60), parent="", externals=list(l1.externals),
                    processes=[DfdProcess(id="0", name=clip(req.title))], stores=[], flows=flows)


def dfd_level2_from_level1(l1: DfdModel, mapping: dict[str, UseCase], max_diagrams: int = 3) -> list[DfdModel]:
    out: list[DfdModel] = []
    pool = sorted((p for p in l1.processes if mapping.get(p.id) and len(mapping[p.id].main_flow) >= 3),
                  key=lambda p: -len(mapping[p.id].main_flow))[:max_diagrams]
    for p in sorted(pool, key=lambda p: int(p.id)):
        uc = mapping[p.id]
        steps = [_short(s, uc.actor) for s in uc.main_flow[:5]][:4]
        subs = [DfdProcess(id=f"{p.id}.{i}", name=st) for i, st in enumerate(steps, start=1)]
        mid = ["Validated input", "Processed data", "Result data"]
        flows = [DfdFlow(source=subs[i].id, target=subs[i + 1].id, label=mid[min(i, 2)]) for i in range(len(subs) - 1)]
        ext_ids, sto_ids = set(), set()
        for f in l1.flows:
            if f.target == p.id and f.source.startswith("e"):
                flows.append(DfdFlow(source=f.source, target=subs[0].id, label=f.label)); ext_ids.add(f.source)
            elif f.source == p.id and f.target.startswith("e"):
                flows.append(DfdFlow(source=subs[-1].id, target=f.target, label=f.label)); ext_ids.add(f.target)
            elif f.target == p.id and f.source.startswith("D"):
                flows.append(DfdFlow(source=f.source, target=subs[min(1, len(subs) - 1)].id, label=f.label)); sto_ids.add(f.source)
            elif f.source == p.id and f.target.startswith("D"):
                flows.append(DfdFlow(source=subs[-1].id, target=f.target, label=f.label)); sto_ids.add(f.target)
        out.append(DfdModel(level=2, title=clip(f"Level 2 DFD: {p.id} {p.name}", 60), parent=p.id,
                            externals=[x for x in l1.externals if x.id in ext_ids], processes=subs,
                            stores=[s for s in l1.stores if s.id in sto_ids], flows=flows))
    return out
