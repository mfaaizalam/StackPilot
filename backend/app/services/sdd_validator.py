"""Pure-Python checks and clean-up for a DesignModel. No AI involved.

validate_design()  -> list[Issue]. Errors trigger the single repair call; warnings are shown to the user.
sanitize_design()  -> (clean DesignModel, warnings). Deterministic: drops dangling references, breaks
                      dependency cycles, trims to hard limits. It NEVER invents design content,
                      except tables for SRS entities the AI forgot (built mechanically from the entity).
Coverage gaps (an FR with no component, an NFR with no tactic) are reported, never silently patched."""
import re

from app.schemas.sdd import (
    MAX_COMPONENTS, MAX_DECISIONS, MAX_ENDPOINTS, MAX_NAME, MAX_TABLES, MAX_TECH, DesignModel,
)
from app.schemas.srs import Issue, Requirements
from app.services import sdd_fallbacks as F

# Layers that take part in the strict top-down rule. integration/infrastructure are ignored.
_RANK = {"presentation": 0, "api": 1, "service": 2, "data": 3}


def _err(code, msg):
    return Issue(level="error", code=code, message=msg)


def _warn(code, msg):
    return Issue(level="warning", code=code, message=msg)


def has_errors(issues: list[Issue]) -> bool:
    return any(i.level == "error" for i in issues)


def _norm(x: str) -> str:
    return (x or "").strip().upper()


def _clip(s: str, n: int) -> str:
    s = (s or "").strip()
    return s if len(s) <= n else s[: n - 1].rstrip() + "…"


def _find_cycle(graph: dict[str, list[str]]) -> list[str] | None:
    """Return one dependency cycle as a list of ids, or None. Deterministic (insertion order)."""
    WHITE, GREY, BLACK = 0, 1, 2
    color = {n: WHITE for n in graph}
    stack: list[str] = []

    def visit(n: str):
        color[n] = GREY
        stack.append(n)
        for m in graph.get(n, []):
            if m not in color:
                continue
            if color[m] == GREY:
                return stack[stack.index(m):] + [m]
            if color[m] == WHITE:
                found = visit(m)
                if found:
                    return found
        stack.pop()
        color[n] = BLACK
        return None

    for n in list(graph):
        if color[n] == WHITE:
            found = visit(n)
            if found:
                return found
    return None


# ============================================================== validate
def validate_design(d: DesignModel, req: Requirements) -> list[Issue]:
    issues: list[Issue] = []
    fr_ids = {_norm(f.id) for f in req.functional_requirements}
    nfr_ids = {_norm(n.id) for n in req.non_functional_requirements}
    actor_names = {a.name.strip().lower() for a in req.actors}
    entity_names = {e.name.strip().lower() for e in req.entities}

    # ---- components -----------------------------------------------------
    if not d.components:
        issues.append(_err("NO_COMPONENTS", "The design has no components."))
        return issues
    ids = [_norm(c.id) for c in d.components]
    comp_ids = set(ids)
    for dup in sorted({i for i in ids if ids.count(i) > 1}):
        issues.append(_err("DUP_COMPONENT_ID", f"Component id {dup} is used more than once."))
    names = [c.name.strip().lower() for c in d.components]
    for dup in sorted({n for n in names if names.count(n) > 1}):
        issues.append(_warn("DUP_COMPONENT_NAME", f"Two components are both named '{dup}'."))
    if len(d.components) > MAX_COMPONENTS:
        issues.append(_warn("TOO_MANY_COMPONENTS", f"{len(d.components)} components; only {MAX_COMPONENTS} are kept."))
    if not any(c.layer == "service" for c in d.components):
        issues.append(_err("NO_SERVICE_LAYER", "No component sits in the service (business logic) layer."))

    by_id = {_norm(c.id): c for c in d.components}
    graph: dict[str, list[str]] = {}
    for c in d.components:
        cid = _norm(c.id)
        for fr in c.fr_ids:
            if _norm(fr) not in fr_ids:
                issues.append(_err("UNKNOWN_FR", f"{c.name} references {fr}, which is not in the SRS."))
        for dep in c.depends_on:
            if _norm(dep) not in comp_ids:
                issues.append(_err("UNKNOWN_COMPONENT", f"{c.name} depends on {dep}, which does not exist."))
            elif _norm(dep) == cid:
                issues.append(_err("SELF_DEPENDENCY", f"{c.name} depends on itself."))
        graph[cid] = [_norm(x) for x in c.depends_on if _norm(x) in comp_ids and _norm(x) != cid]

    cycle = _find_cycle(graph)
    if cycle:
        issues.append(_err("COMPONENT_CYCLE", "Circular dependency between components: " + " -> ".join(cycle) + "."))

    for c in d.components:  # layering rule: calls go down, never up, and never skip the service layer
        for dep in c.depends_on:
            t = by_id.get(_norm(dep))
            if not t or c.layer not in _RANK or t.layer not in _RANK:
                continue
            if _RANK[t.layer] < _RANK[c.layer]:
                issues.append(_warn("LAYER_VIOLATION", f"{c.name} ({c.layer}) calls upward to {t.name} ({t.layer})."))
            elif _RANK[c.layer] <= 1 and t.layer == "data":
                issues.append(_warn("LAYER_VIOLATION", f"{c.name} ({c.layer}) reaches the data layer directly, skipping the service layer."))

    # ---- traceability: every FR must be allocated -------------------------
    allocated = {_norm(fr) for c in d.components for fr in c.fr_ids}
    for f in req.functional_requirements:
        if _norm(f.id) not in allocated:
            issues.append(_err("FR_NOT_ALLOCATED", f"{f.id} ({f.title}) is not allocated to any component."))

    # ---- endpoints --------------------------------------------------------
    seen: set[tuple[str, str]] = set()
    for e in d.endpoints:
        if _norm(e.component_id) not in comp_ids:
            issues.append(_err("ENDPOINT_UNKNOWN_COMPONENT", f"{e.method} {e.path} points to unknown component {e.component_id}."))
        if not e.path.startswith("/"):
            issues.append(_warn("BAD_PATH", f"Endpoint path '{e.path}' must start with '/'."))
        key = (e.method, e.path.strip().lower())
        if key in seen:
            issues.append(_warn("DUP_ENDPOINT", f"{e.method} {e.path} is defined twice."))
        seen.add(key)
        for fr in e.fr_ids:
            if _norm(fr) not in fr_ids:
                issues.append(_err("UNKNOWN_FR", f"{e.method} {e.path} references {fr}, which is not in the SRS."))
        if e.actor.strip() and e.actor.strip().lower() not in actor_names:
            issues.append(_warn("UNKNOWN_ACTOR", f"{e.method} {e.path} names actor '{e.actor}', which is not in the SRS."))
    if len(d.endpoints) > MAX_ENDPOINTS:
        issues.append(_warn("TOO_MANY_ENDPOINTS", f"{len(d.endpoints)} endpoints; only {MAX_ENDPOINTS} are kept."))

    # ---- data design -------------------------------------------------------
    stored = {t.entity.strip().lower() for t in d.tables}
    for e in req.entities:
        if e.name.strip().lower() not in stored:
            issues.append(_warn("ENTITY_NO_TABLE", f"Entity {e.name} has no table design."))
    for t in d.tables:
        if not t.columns:
            issues.append(_warn("EMPTY_TABLE", f"Table {t.table} has no columns."))
        if t.entity.strip().lower() not in entity_names and t.entity.strip():
            issues.append(_warn("EXTRA_TABLE", f"Table {t.table} stores '{t.entity}', which is not an SRS entity (helper table?)."))

    # ---- quality attributes -------------------------------------------------
    covered = set()
    for q in d.quality_tactics:
        if _norm(q.nfr_id) not in nfr_ids:
            issues.append(_err("UNKNOWN_NFR", f"A tactic references {q.nfr_id}, which is not in the SRS."))
        else:
            covered.add(_norm(q.nfr_id))
        for cid in q.realized_by:
            if _norm(cid) not in comp_ids:
                issues.append(_err("UNKNOWN_COMPONENT", f"The tactic for {q.nfr_id} names unknown component {cid}."))
    for n in req.non_functional_requirements:
        if _norm(n.id) not in covered:
            issues.append(_err("NFR_NO_TACTIC", f"{n.id} ({n.category}) has no design tactic."))

    if not d.decisions:
        issues.append(_warn("NO_DECISIONS", "No design decisions were recorded."))
    return issues


# ============================================================== sanitize
def sanitize_design(d: DesignModel, req: Requirements) -> tuple[DesignModel, list[str]]:
    d = d.model_copy(deep=True)
    warns: list[str] = []
    fr_ids = {_norm(f.id): f.id for f in req.functional_requirements}
    nfr_ids = {_norm(n.id): n.id for n in req.non_functional_requirements}
    entity_by_lc = {e.name.strip().lower(): e.name for e in req.entities}
    actor_by_lc = {a.name.strip().lower(): a.name for a in req.actors}

    # ---- components: unique ids, hard limit, tidy references ---------------
    seen, unique = set(), []
    for c in d.components:
        cid = _norm(c.id)
        if cid in seen or not cid:
            warns.append(f"Duplicate component '{c.name}' ({c.id}) was removed.")
            continue
        seen.add(cid)
        c.id = cid
        unique.append(c)
    if len(unique) > MAX_COMPONENTS:
        ref_count = {c.id: sum(1 for o in unique if c.id in {_norm(x) for x in o.depends_on}) for c in unique}
        ranked = sorted(unique, key=lambda c: -(len(c.fr_ids) + ref_count[c.id]))[:MAX_COMPONENTS]
        keep = {c.id for c in ranked}
        warns.append(f"Only the {MAX_COMPONENTS} most connected components were kept.")
        unique = [c for c in unique if c.id in keep]
    comp_ids = {c.id for c in unique}

    for c in unique:
        c.name = _clip(c.name, MAX_NAME)
        c.responsibility = _clip(c.responsibility, 400)
        c.fr_ids = list(dict.fromkeys(fr_ids[_norm(x)] for x in c.fr_ids if _norm(x) in fr_ids))
        c.entities = list(dict.fromkeys(entity_by_lc[x.strip().lower()] for x in c.entities if x.strip().lower() in entity_by_lc))
        deps = [_norm(x) for x in c.depends_on]
        c.depends_on = list(dict.fromkeys(x for x in deps if x in comp_ids and x != c.id))
        if len(c.depends_on) != len(deps):
            warns.append(f"Invalid or repeated dependencies of {c.name} were removed.")

    # ---- break dependency cycles by dropping the edge that closes each one ---
    by_id = {c.id: c for c in unique}
    for _ in range(len(unique) * len(unique) + 1):  # hard bound: cannot loop forever
        cycle = _find_cycle({c.id: list(c.depends_on) for c in unique})
        if not cycle:
            break
        src, dst = cycle[-2], cycle[-1]
        by_id[src].depends_on.remove(dst)
        warns.append(f"Circular dependency {src} -> {dst} was removed.")
    d.components = unique

    # ---- endpoints ------------------------------------------------------------
    clean, taken = [], set()
    for e in d.endpoints:
        cid = _norm(e.component_id)
        if cid not in comp_ids:
            warns.append(f"Endpoint {e.method} {e.path} was dropped: its component does not exist.")
            continue
        e.component_id = cid
        path = e.path.strip() or "/"
        e.path = path if path.startswith("/") else "/" + path
        key = (e.method, e.path.lower())
        if key in taken:
            warns.append(f"Duplicate endpoint {e.method} {e.path} was removed.")
            continue
        taken.add(key)
        e.summary = _clip(e.summary, 80)
        e.fr_ids = list(dict.fromkeys(fr_ids[_norm(x)] for x in e.fr_ids if _norm(x) in fr_ids))
        e.actor = actor_by_lc.get(e.actor.strip().lower(), e.actor.strip())
        clean.append(e)
    if len(clean) > MAX_ENDPOINTS:
        warns.append(f"Only the first {MAX_ENDPOINTS} endpoints were kept.")
        clean = clean[:MAX_ENDPOINTS]
    for n, e in enumerate(clean, start=1):
        e.id = f"API-{n:03d}"
    d.endpoints = clean

    # ---- tables: one per SRS entity (missing ones are built mechanically) ----
    tables = [t for t in d.tables if t.table.strip()][:MAX_TABLES]
    stored = {t.entity.strip().lower() for t in tables}
    all_entities = {e.name.strip().lower(): e for e in req.entities}
    for t in tables:
        t.entity = entity_by_lc.get(t.entity.strip().lower(), t.entity.strip())
    for lc, ent in all_entities.items():
        if lc not in stored and len(tables) < MAX_TABLES:
            tables.append(F.table_from_entity(ent, req.entities))
            warns.append(f"A table for {ent.name} was added from the SRS entity definition.")
    d.tables = tables

    # ---- quality tactics: known NFR only, one per NFR ---------------------------
    seen_nfr, tactics = set(), []
    for q in d.quality_tactics:
        key = _norm(q.nfr_id)
        if key not in nfr_ids or key in seen_nfr:
            continue
        seen_nfr.add(key)
        q.nfr_id = nfr_ids[key]
        q.realized_by = list(dict.fromkeys(_norm(x) for x in q.realized_by if _norm(x) in comp_ids))
        tactics.append(q)
    d.quality_tactics = tactics

    # ---- decisions / stack / text -----------------------------------------------
    decisions = d.decisions[:MAX_DECISIONS]
    for n, dd in enumerate(decisions, start=1):
        dd.id = f"DD-{n:03d}"
        dd.nfr_ids = list(dict.fromkeys(nfr_ids[_norm(x)] for x in dd.nfr_ids if _norm(x) in nfr_ids))
        dd.alternatives = dd.alternatives[:4]
    d.decisions = decisions
    d.technology_stack = d.technology_stack[:MAX_TECH]
    d.error_handling = [x.strip() for x in d.error_handling if x.strip()][:8]
    d.design_risks = [x.strip() for x in d.design_risks if x.strip()][:8]
    return d, warns