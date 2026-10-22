"""Pure-Python validation + sanitising of diagram models.

validate_*  -> list[Issue]; errors trigger ONE repair call to the AI.
sanitize_*  -> (clean_spec | None, warnings); ALWAYS returns something that
               satisfies every hard limit, so a bad AI answer can never produce
               an unreadable diagram.
"""
from collections import deque

from app.schemas.diagrams import (
    MAX_ACTIVITY_NODES, MAX_CLASSES, MAX_CLASS_MEMBERS, MAX_DEPLOY_ARTIFACTS, MAX_DEPLOY_LINKS,
    MAX_DEPLOY_NODES, MAX_FRAGMENTS, MAX_LABEL,
    MAX_MESSAGES, MAX_PARTICIPANTS, MAX_RELATIONS, MAX_STATES, MAX_TRANSITIONS,
    MAX_UC_RELATIONS, ActEdge, ActivityModel, ActNode, ClassModel, ClassNode,
    ClassRelation, DeploymentModel, DeployLink, DeployNode, Fragment, Message, Rel, SequenceModel,
    StateModel, Transition, UseCaseModel,
    MAX_DFD_EXTERNALS, MAX_DFD_FLOWS, MAX_DFD_PROCESSES, MAX_DFD_STORES, MAX_ER_ATTRS, MAX_ER_ENTITIES,
    MAX_ER_RELATIONS, DfdExternal, DfdFlow, DfdModel, DfdProcess, DfdStore, ErAttribute, ErEntity, ErModel,
    ErRelation,
)
from app.schemas.srs import Issue


def clip(text: str, n: int = MAX_LABEL) -> str:
    """Collapse whitespace and cut to n characters (ellipsis if cut)."""
    t = " ".join(str(text or "").split())
    return t if len(t) <= n else t[: n - 1].rstrip() + "…"


def _key(s: str) -> str:
    return " ".join(str(s or "").split()).lower()


def _err(code: str, msg: str) -> Issue:
    return Issue(level="error", code=code, message=msg)


def has_errors(issues: list[Issue]) -> bool:
    return any(i.level == "error" for i in issues)


# ============================================================ class diagram
def validate_class(m: ClassModel) -> list[Issue]:
    out: list[Issue] = []
    names = [_key(c.name) for c in m.classes]
    if len(m.classes) < 2:
        out.append(_err("TOO_FEW_CLASSES", "A class diagram needs at least 2 classes."))
    if len(m.classes) > MAX_CLASSES:
        out.append(_err("TOO_MANY_CLASSES", f"Use at most {MAX_CLASSES} classes (found {len(m.classes)})."))
    if len(set(names)) != len(names):
        out.append(_err("DUP_CLASS", "Class names must be unique."))
    known = set(names)
    for r in m.relations:
        for end in (r.source, r.target):
            if _key(end) not in known:
                out.append(_err("UNKNOWN_CLASS", f"Relation refers to class '{end}' which is not defined."))
    if len(m.relations) > MAX_RELATIONS:
        out.append(_err("TOO_MANY_RELATIONS", f"Use at most {MAX_RELATIONS} relations."))
    return out


def sanitize_class(m: ClassModel) -> tuple[ClassModel | None, list[str]]:
    warns: list[str] = []
    seen: dict[str, ClassNode] = {}
    for c in m.classes:
        k = _key(c.name)
        if not k or k in seen:
            continue
        seen[k] = ClassNode(
            name=clip(c.name, 24),
            attributes=[clip(a) for a in c.attributes if str(a).strip()][:MAX_CLASS_MEMBERS],
            methods=[clip(x) for x in c.methods if str(x).strip()][:MAX_CLASS_MEMBERS],
        )
    # canonical name lookup for relation endpoints (case/space-insensitive)
    canon = {k: v.name for k, v in seen.items()}

    rels: list[ClassRelation] = []
    dedupe: set[tuple] = set()
    dropped = 0
    for r in m.relations:
        s, t = _key(r.source), _key(r.target)
        if s not in canon or t not in canon or s == t or (r.kind, s, t) in dedupe:
            dropped += 1
            continue
        dedupe.add((r.kind, s, t))
        rels.append(ClassRelation(kind=r.kind, source=canon[s], target=canon[t],
                                  multiplicity_source=clip(r.multiplicity_source, 6),
                                  multiplicity_target=clip(r.multiplicity_target, 6),
                                  label=clip(r.label, 20)))
    if dropped:
        warns.append(f"Removed {dropped} invalid or duplicate relation(s).")

    classes = list(seen.values())
    if len(classes) > MAX_CLASSES:
        degree = {c.name: 0 for c in classes}
        for r in rels:
            degree[r.source] += 1
            degree[r.target] += 1
        keep = sorted(classes, key=lambda c: -degree[c.name])[:MAX_CLASSES]  # stable
        keep_names = {c.name for c in keep}
        classes = [c for c in classes if c.name in keep_names]
        rels = [r for r in rels if r.source in keep_names and r.target in keep_names]
        warns.append(f"Reduced to the {MAX_CLASSES} most connected classes to keep the diagram readable.")
    if len(rels) > MAX_RELATIONS:
        rels = rels[:MAX_RELATIONS]
        warns.append(f"Showing the first {MAX_RELATIONS} relations only.")
    if len(classes) < 2:
        return None, warns
    return ClassModel(classes=classes, relations=rels), warns


# ========================================================== sequence diagram
def validate_sequence(m: SequenceModel) -> list[Issue]:
    out: list[Issue] = []
    parts = [_key(p) for p in m.participants]
    if len(parts) < 2 or len(m.messages) < 2:
        out.append(_err("SEQ_TOO_SMALL", "Need at least 2 participants and 2 messages."))
    if len(m.participants) > MAX_PARTICIPANTS:
        out.append(_err("TOO_MANY_PARTICIPANTS", f"Use at most {MAX_PARTICIPANTS} participants."))
    if len(m.messages) > MAX_MESSAGES:
        out.append(_err("TOO_MANY_MESSAGES", f"Use at most {MAX_MESSAGES} messages (found {len(m.messages)})."))
    if len(set(parts)) != len(parts):
        out.append(_err("DUP_PARTICIPANT", "Participant names must be unique."))
    known = set(parts)
    for msg in m.messages:
        for end in (msg.source, msg.target):
            if _key(end) not in known:
                out.append(_err("UNKNOWN_PARTICIPANT", f"Message uses '{end}' which is not in the participants list."))
    return out


def sanitize_sequence(m: SequenceModel) -> tuple[SequenceModel | None, list[str]]:
    warns: list[str] = []
    names: dict[str, str] = {}
    for p in m.participants:
        k = _key(p)
        if k and k not in names:
            names[k] = clip(p, 20)
    if len(names) > MAX_PARTICIPANTS:
        names = dict(list(names.items())[:MAX_PARTICIPANTS])
        warns.append(f"Showing the first {MAX_PARTICIPANTS} participants only.")

    msgs: list[Message] = []
    dropped = 0
    for x in m.messages:
        s, t = _key(x.source), _key(x.target)
        if s not in names or t not in names or not str(x.text).strip():
            dropped += 1
            continue
        msgs.append(Message(source=names[s], target=names[t], text=clip(x.text), kind=x.kind))
    if dropped:
        warns.append(f"Removed {dropped} message(s) that referred to unknown participants.")
    if len(msgs) > MAX_MESSAGES:
        msgs = msgs[:MAX_MESSAGES]
        warns.append(f"Showing the first {MAX_MESSAGES} messages only.")

    # keep only participants that actually talk
    used = {x.source for x in msgs} | {x.target for x in msgs}
    parts = [n for n in names.values() if n in used]

    # fragments: valid range, disjoint, capped
    frags: list[Fragment] = []
    last_end = 0
    for f in sorted(m.fragments, key=lambda f: f.start):
        if 1 <= f.start <= f.end <= len(msgs) and f.start > last_end and len(frags) < MAX_FRAGMENTS:
            frags.append(Fragment(kind=f.kind, label=clip(f.label, 24), start=f.start, end=f.end))
            last_end = f.end
    if len(parts) < 2 or len(msgs) < 2:
        return None, warns
    return SequenceModel(participants=parts, messages=msgs, fragments=frags), warns


# =========================================================== activity diagram
def _reachable(nodes: dict[str, ActNode], edges: list[ActEdge], start: str) -> list[str]:
    adj: dict[str, list[str]] = {}
    for e in edges:
        adj.setdefault(e.source, []).append(e.target)
    order, seen, q = [], {start}, deque([start])
    while q:
        n = q.popleft()
        order.append(n)
        for nxt in adj.get(n, []):
            if nxt in nodes and nxt not in seen:
                seen.add(nxt)
                q.append(nxt)
    return order


def validate_activity(m: ActivityModel) -> list[Issue]:
    out: list[Issue] = []
    ids = [n.id for n in m.nodes]
    if len(set(ids)) != len(ids):
        out.append(_err("DUP_NODE", "Node ids must be unique."))
    kinds = [n.kind for n in m.nodes]
    if kinds.count("start") != 1:
        out.append(_err("START_COUNT", "There must be exactly one start node."))
    if "end" not in kinds:
        out.append(_err("NO_END", "There must be at least one end node."))
    if len(m.nodes) > MAX_ACTIVITY_NODES:
        out.append(_err("TOO_MANY_NODES", f"Use at most {MAX_ACTIVITY_NODES} nodes (found {len(m.nodes)})."))
    known = set(ids)
    for e in m.edges:
        if e.source not in known or e.target not in known:
            out.append(_err("UNKNOWN_NODE", f"Edge {e.source} -> {e.target} refers to a node that does not exist."))
    for n in m.nodes:
        if n.kind == "decision" and sum(1 for e in m.edges if e.source == n.id) < 2:
            out.append(_err("DECISION_BRANCHES", f"Decision '{n.label}' needs at least 2 outgoing edges."))
    return out


def sanitize_activity(m: ActivityModel) -> tuple[ActivityModel | None, list[str]]:
    warns: list[str] = []
    nodes: dict[str, ActNode] = {}
    for n in m.nodes:
        if n.id in nodes:
            continue
        if n.kind == "start" and any(x.kind == "start" for x in nodes.values()):
            continue  # only one start
        nodes[n.id] = ActNode(id=n.id, kind=n.kind, label=clip(n.label) if n.kind in ("action", "decision") else "")
    start = next((i for i, n in nodes.items() if n.kind == "start"), None)
    if start is None:
        return None, warns

    edges: list[ActEdge] = []
    seen_e: set[tuple] = set()
    for e in m.edges:
        if e.source in nodes and e.target in nodes and e.source != e.target and (e.source, e.target) not in seen_e:
            seen_e.add((e.source, e.target))
            edges.append(ActEdge(source=e.source, target=e.target, label=clip(e.label, 16)))

    order = _reachable(nodes, edges, start)  # drops unreachable nodes
    if len(order) < len(nodes):
        warns.append(f"Removed {len(nodes) - len(order)} unreachable step(s).")
    if len(order) > MAX_ACTIVITY_NODES:
        order = order[:MAX_ACTIVITY_NODES]
        warns.append(f"Showing the first {MAX_ACTIVITY_NODES} steps only.")
    keep = set(order)
    nodes = {i: nodes[i] for i in order}
    edges = [e for e in edges if e.source in keep and e.target in keep]

    # every non-end node must lead somewhere: connect dead ends to an end node
    end_id = next((i for i, n in nodes.items() if n.kind == "end"), None)
    out_deg = {i: 0 for i in nodes}
    for e in edges:
        out_deg[e.source] += 1
    dead = [i for i, d in out_deg.items() if d == 0 and nodes[i].kind != "end"]
    if dead:
        if end_id is None:
            end_id = "n_end"
            while end_id in nodes:
                end_id += "_"
            nodes[end_id] = ActNode(id=end_id, kind="end", label="")
        for i in dead:
            edges.append(ActEdge(source=i, target=end_id, label=""))
        warns.append("Connected open-ended steps to the end node.")
    elif end_id is None:
        return None, warns
    if sum(1 for n in nodes.values() if n.kind == "action") < 1:
        return None, warns
    return ActivityModel(nodes=list(nodes.values()), edges=edges), warns


# ============================================================ state diagram
def validate_state(m: StateModel) -> list[Issue]:
    out: list[Issue] = []
    states = [_key(s) for s in m.states]
    if len(states) < 2:
        out.append(_err("STATE_TOO_SMALL", f"'{m.entity}' needs at least 2 states."))
    if len(states) > MAX_STATES:
        out.append(_err("TOO_MANY_STATES", f"Use at most {MAX_STATES} states for '{m.entity}'."))
    if len(m.transitions) > MAX_TRANSITIONS:
        out.append(_err("TOO_MANY_TRANSITIONS", f"Use at most {MAX_TRANSITIONS} transitions."))
    known = set(states)
    if _key(m.initial) not in known:
        out.append(_err("BAD_INITIAL", f"Initial state '{m.initial}' is not in the states list."))
    for t in m.transitions:
        for end in (t.source, t.target):
            if _key(end) not in known:
                out.append(_err("UNKNOWN_STATE", f"Transition uses state '{end}' which is not defined."))
    return out


def sanitize_state(m: StateModel) -> tuple[StateModel | None, list[str]]:
    warns: list[str] = []
    names: dict[str, str] = {}
    for s in m.states:
        k = _key(s)
        if k and k not in names:
            names[k] = clip(s, 22)
    if len(names) > MAX_STATES:
        names = dict(list(names.items())[:MAX_STATES])
        warns.append(f"Showing the first {MAX_STATES} states only.")
    trans, seen = [], set()
    for t in m.transitions:
        s, d = _key(t.source), _key(t.target)
        if s in names and d in names and (s, d, _key(t.label)) not in seen:
            seen.add((s, d, _key(t.label)))
            trans.append(Transition(source=names[s], target=names[d], label=clip(t.label)))
    trans = trans[:MAX_TRANSITIONS]
    initial = names.get(_key(m.initial)) or next(iter(names.values()), "")
    finals = [names[k] for k in (_key(f) for f in m.finals) if k in names]
    if len(names) < 2 or not trans:
        return None, warns
    return StateModel(entity=clip(m.entity, 24), states=list(names.values()), initial=initial,
                      finals=finals, transitions=trans), warns
# ========================================================= deployment diagram
def validate_deployment(m: DeploymentModel) -> list[Issue]:
    out: list[Issue] = []
    ids = [n.id for n in m.nodes]
    if len(m.nodes) < 2 or not m.links:
        out.append(_err("DEPLOY_TOO_SMALL", "Need at least 2 nodes and 1 link."))
    if len(m.nodes) > MAX_DEPLOY_NODES:
        out.append(_err("TOO_MANY_DEPLOY_NODES", f"Use at most {MAX_DEPLOY_NODES} nodes (found {len(m.nodes)})."))
    if len(set(ids)) != len(ids):
        out.append(_err("DUP_DEPLOY_NODE", "Node ids must be unique."))
    if len(m.links) > MAX_DEPLOY_LINKS:
        out.append(_err("TOO_MANY_DEPLOY_LINKS", f"Use at most {MAX_DEPLOY_LINKS} links."))
    known = set(ids)
    for l in m.links:
        for end in (l.source, l.target):
            if end not in known:
                out.append(_err("UNKNOWN_DEPLOY_NODE", f"Link refers to node '{end}' which is not defined."))
    linked = {l.source for l in m.links} | {l.target for l in m.links}
    for n in m.nodes:
        if n.id not in linked:
            out.append(_err("DEPLOY_ISOLATED", f"Node '{n.name}' is not connected to anything."))
    return out


def sanitize_deployment(m: DeploymentModel) -> tuple[DeploymentModel | None, list[str]]:
    warns: list[str] = []
    nodes: dict[str, DeployNode] = {}
    for n in m.nodes:
        if not n.id or n.id in nodes or not str(n.name).strip():
            continue
        arts = [clip(a, 24) for a in n.artifacts if str(a).strip()][:MAX_DEPLOY_ARTIFACTS]
        nodes[n.id] = DeployNode(id=n.id, name=clip(n.name), kind=n.kind,
                                 technology=clip(n.technology), artifacts=arts or [clip(n.name, 24)])
    if len(nodes) > MAX_DEPLOY_NODES:
        nodes = dict(list(nodes.items())[:MAX_DEPLOY_NODES])
        warns.append(f"Showing the first {MAX_DEPLOY_NODES} nodes only.")

    links: list[DeployLink] = []
    seen: set[frozenset] = set()
    dropped = 0
    for l in m.links:
        pair = frozenset((l.source, l.target))
        if l.source not in nodes or l.target not in nodes or l.source == l.target or pair in seen:
            dropped += 1
            continue
        seen.add(pair)
        links.append(DeployLink(source=l.source, target=l.target, protocol=clip(l.protocol, 20)))
    if dropped:
        warns.append(f"Removed {dropped} invalid or duplicate link(s).")
    if len(links) > MAX_DEPLOY_LINKS:
        links = links[:MAX_DEPLOY_LINKS]
        warns.append(f"Showing the first {MAX_DEPLOY_LINKS} links only.")

    linked = {l.source for l in links} | {l.target for l in links}  # drop nodes that float alone
    if len(linked) < len(nodes):
        warns.append(f"Removed {len(nodes) - len(linked)} unconnected node(s).")
    nodes = {i: n for i, n in nodes.items() if i in linked}
    if len(nodes) < 2 or not links:
        return None, warns
    return DeploymentModel(nodes=list(nodes.values()), links=links), warns

# ============================================== use-case include / extend
def sanitize_uc_relations(includes: list[Rel], extends: list[Rel], model: UseCaseModel) -> tuple[list[Rel], list[Rel]]:
    ids = {u.id for u in model.use_cases}
    used: set[tuple] = set()

    def clean(rels: list[Rel]) -> list[Rel]:
        out: list[Rel] = []
        for r in rels:
            pair = tuple(sorted((r.source, r.target)))
            if r.source in ids and r.target in ids and r.source != r.target and pair not in used:
                used.add(pair)  # one relation per pair keeps the picture clean
                out.append(Rel(source=r.source, target=r.target))
        return out[:MAX_UC_RELATIONS]

    inc = clean(includes)
    ext = clean(extends)
    return inc, ext



# ======================================================== entity-relationship
def validate_er(m: ErModel) -> list[Issue]:
    out: list[Issue] = []
    names = [_key(e.name) for e in m.entities]
    if len(names) < 2:
        out.append(_err("ER_TOO_SMALL", "Need at least 2 entities."))
    if len(m.entities) > MAX_ER_ENTITIES:
        out.append(_err("TOO_MANY_ENTITIES", f"Use at most {MAX_ER_ENTITIES} entities."))
    if len(set(names)) != len(names):
        out.append(_err("DUP_ENTITY", "Entity names must be unique."))
    known = set(names)
    for r in m.relations:
        for end in (r.source, r.target):
            if _key(end) not in known:
                out.append(_err("UNKNOWN_ENTITY", f"Relation refers to entity '{end}' which is not defined."))
    for e in m.entities:
        if not any(a.key == "PK" for a in e.attributes):
            out.append(_err("NO_PK", f"Entity '{e.name}' has no primary key."))
    return out


def sanitize_er(m: ErModel) -> tuple[ErModel | None, list[str]]:
    warns: list[str] = []
    ents: dict[str, ErEntity] = {}
    for e in m.entities:
        k = _key(e.name)
        if not k or k in ents:
            continue
        attrs, seen = [], set()
        for a in e.attributes:
            n = _key(a.name).replace(" ", "_")
            if not n or n in seen:
                continue
            seen.add(n)
            attrs.append(ErAttribute(name=clip(n, 30), type=clip(a.type, 16).upper(), key=a.key))
        if not any(a.key == "PK" for a in attrs):
            attrs.insert(0, ErAttribute(name="id", type="INT", key="PK"))
        if len(attrs) > MAX_ER_ATTRS:
            attrs = attrs[:MAX_ER_ATTRS]
            warns.append(f"'{e.name}' shows its first {MAX_ER_ATTRS} attributes only.")
        ents[k] = ErEntity(name=clip(e.name.replace(" ", ""), 28), attributes=attrs)
    if len(ents) > MAX_ER_ENTITIES:
        ents = dict(list(ents.items())[:MAX_ER_ENTITIES])
        warns.append(f"Showing the first {MAX_ER_ENTITIES} entities only.")
    rels, seen_pairs = [], set()
    for r in m.relations:
        s_, t_ = _key(r.source), _key(r.target)
        if s_ in ents and t_ in ents and s_ != t_ and (s_, t_, _key(r.label)) not in seen_pairs:
            seen_pairs.add((s_, t_, _key(r.label)))
            rels.append(ErRelation(source=ents[s_].name, target=ents[t_].name, cardinality_source=r.cardinality_source,
                                   cardinality_target=r.cardinality_target, label=clip(r.label, 20)))
    rels = rels[:MAX_ER_RELATIONS]
    linked = {r.source for r in rels} | {r.target for r in rels}
    if len(ents) < 2:
        return None, warns
    if rels and len(linked) < len(ents):
        gone = [n for n in (e.name for e in ents.values()) if n not in linked]
        if gone and len(gone) < len(ents):
            warns.append(f"Entities with no relationship are shown on their own: {', '.join(gone)}.")
    return ErModel(entities=list(ents.values()), relations=rels), warns


# ================================================================== data flow
def _dfd_kind(m: DfdModel) -> dict[str, str]:
    kinds = {x.id: "external" for x in m.externals}
    kinds.update({p.id: "process" for p in m.processes})
    kinds.update({s.id: "store" for s in m.stores})
    return kinds


def validate_dfd(m: DfdModel) -> list[Issue]:
    out: list[Issue] = []
    kinds = _dfd_kind(m)
    ids = [x.id for x in m.externals] + [p.id for p in m.processes] + [s.id for s in m.stores]
    if len(set(ids)) != len(ids):
        out.append(_err("DUP_DFD_ID", "Every external, process and store needs a unique id."))
    if not m.processes:
        out.append(_err("DFD_NO_PROCESS", "A data flow diagram needs at least one process."))
    if len(m.processes) > MAX_DFD_PROCESSES:
        out.append(_err("TOO_MANY_PROCESSES", f"Use at most {MAX_DFD_PROCESSES} processes."))
    if len(m.flows) > MAX_DFD_FLOWS:
        out.append(_err("TOO_MANY_FLOWS", f"Use at most {MAX_DFD_FLOWS} data flows."))
    for f in m.flows:
        a, b = kinds.get(f.source), kinds.get(f.target)
        if not a or not b:
            out.append(_err("UNKNOWN_DFD_ID", f"Flow '{f.label}' refers to an id that does not exist."))
        elif a != "process" and b != "process":
            out.append(_err("FLOW_NEEDS_PROCESS", f"Flow '{f.label}' joins two non-process items: every data flow must start or end at a process."))
    ins = {f.target for f in m.flows}
    outs = {f.source for f in m.flows}
    for p in m.processes:
        if p.id not in ins:
            out.append(_err("PROCESS_NO_INPUT", f"Process '{p.name}' has no incoming data flow (a 'miracle')."))
        if p.id not in outs:
            out.append(_err("PROCESS_NO_OUTPUT", f"Process '{p.name}' has no outgoing data flow (a 'black hole')."))
    return out


def sanitize_dfd(m: DfdModel) -> tuple[DfdModel | None, list[str]]:
    warns: list[str] = []
    ext = [DfdExternal(id=x.id, name=clip(x.name)) for x in m.externals if x.id and str(x.name).strip()][:MAX_DFD_EXTERNALS]
    pro = [DfdProcess(id=p.id, name=clip(p.name)) for p in m.processes if p.id and str(p.name).strip()][:MAX_DFD_PROCESSES]
    sto = [DfdStore(id=s.id, name=clip(s.name)) for s in m.stores if s.id and str(s.name).strip()][:MAX_DFD_STORES]
    seen_ids: set[str] = set()
    for lst in (ext, pro, sto):
        for item in list(lst):
            if item.id in seen_ids:
                lst.remove(item)
            seen_ids.add(item.id)
    kinds = {**{x.id: "external" for x in ext}, **{p.id: "process" for p in pro}, **{s.id: "store" for s in sto}}
    flows, seen, dropped = [], set(), 0
    for f in m.flows:
        a, b = kinds.get(f.source), kinds.get(f.target)
        key = (f.source, f.target, _key(f.label))
        if not a or not b or (a != "process" and b != "process") or f.source == f.target or key in seen:
            dropped += 1
            continue
        seen.add(key)
        flows.append(DfdFlow(source=f.source, target=f.target, label=clip(f.label or "data")))
    if dropped:
        warns.append(f"Removed {dropped} invalid or duplicate data flow(s).")
    flows = flows[:MAX_DFD_FLOWS]
    used = {f.source for f in flows} | {f.target for f in flows}
    if len(used) < len(kinds):
        warns.append(f"Removed {len(kinds) - len(used)} item(s) that had no data flow.")
    ext = [x for x in ext if x.id in used]
    pro = [p for p in pro if p.id in used]
    sto = [s for s in sto if s.id in used]
    if not pro or not flows:
        return None, warns
    return DfdModel(level=m.level, title=clip(m.title, 60), parent=m.parent, externals=ext, processes=pro,
                    stores=sto, flows=flows), warns
