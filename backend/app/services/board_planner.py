"""Requirements -> Kanban plan. PURE PYTHON: no AI, no database, fully deterministic.

Same Requirements in -> byte-identical plan out. The database layer (board_service.py)
only stores what this module decided.

Rules (all documented so nothing is a hidden assumption):
  * Columns: Backlog, Ready, In Progress, Testing, Done. A new project has nothing done,
    so no task is ever planned into In Progress / Testing / Done.
  * One task per functional requirement (FR) and, optionally, one per non-functional
    requirement (NFR). Title is "[FR-004] Return book".
  * Priority from MoSCoW: must -> high, should -> medium, could -> low.
  * Ready  = a MUST task with no dependencies. Everything else starts in Backlog.
  * Tasks are ordered by the use case that covers them, then by requirement ID.
  * Dependencies (suggestions, never invented from keywords):
      1. EXPLICIT: the requirement's own text names another FR ("after FR-002 ...").
      2. FLOW ORDER: inside one use case, an FR comes after the FR listed just before it.
    Edges that would make a cycle are dropped, and a derived edge is dropped when it would
    make an important task wait for a less important one (must waiting for could).
  * Story points: 1 + acceptance criteria + 0.5 per dependency + 1 for a long statement,
    snapped to 1/2/3/5/8. They are relative sizes to edit, not a promise.
"""
import re
from dataclasses import dataclass, field

from app.schemas.srs import FR, NFR, Requirements

STANDARD_COLUMNS = ["Backlog", "Ready", "In Progress", "Testing", "Done"]
PRIORITY_MAP = {"must": "high", "should": "medium", "could": "low"}
NFR_PRIORITY = {"security": "high", "reliability": "high"}  # everything else: medium
FIB = [1, 2, 3, 5, 8]
NFR_POINTS = 3
TITLE_MAX = 150
ID_MAX = 40
UNASSIGNED = "Unassigned"
CROSS_CUTTING = "Cross-cutting (NFR)"

_FR_REF = re.compile(r"\bFR-\d{3}\b")
_RANK = {"must": 0, "should": 1, "could": 2}


@dataclass
class PlannedTask:
    requirement_id: str
    title: str
    description: str
    priority: str                 # high | medium | low
    column: str                   # Backlog | Ready
    estimate_points: int
    depends_on: list[str] = field(default_factory=list)
    group: str = ""               # use case label, "Unassigned" or "Cross-cutting (NFR)"


@dataclass
class BoardPlan:
    columns: list[str]
    tasks: list[PlannedTask]
    warnings: list[str]


# --------------------------------------------------------------------------
# dependency graph helpers
# --------------------------------------------------------------------------
def has_cycle(deps: dict[str, list[str]]) -> bool:
    """True if the dependency map (task -> tasks it waits for) contains a cycle (Kahn's algorithm)."""
    nodes = set(deps) | {d for v in deps.values() for d in v}
    waiting = {n: len(set(deps.get(n, []))) for n in nodes}  # a self-dependency never reaches 0 -> cycle
    dependents: dict[str, list[str]] = {n: [] for n in nodes}
    for n, ds in deps.items():
        for d in set(ds):
            dependents[d].append(n)
    ready = [n for n in nodes if waiting[n] == 0]
    seen = 0
    while ready:
        n = ready.pop()
        seen += 1
        for m in dependents[n]:
            waiting[m] -= 1
            if waiting[m] == 0:
                ready.append(m)
    return seen != len(nodes)


def _reaches(deps: dict[str, list[str]], start: str, target: str) -> bool:
    """Can we get from `start` to `target` by following 'depends on' edges?"""
    stack, seen = [start], set()
    while stack:
        n = stack.pop()
        if n == target:
            return True
        if n in seen:
            continue
        seen.add(n)
        stack.extend(deps.get(n, []))
    return False


def plan_dependencies(req: Requirements) -> tuple[dict[str, list[str]], list[str]]:
    """Return ({fr_id: [fr_ids it depends on]}, warnings). Always acyclic."""
    frs: dict[str, FR] = {}
    for f in req.functional_requirements:
        if f.id and f.id not in frs:
            frs[f.id] = f
    deps: dict[str, list[str]] = {fid: [] for fid in frs}
    warnings: list[str] = []

    # candidate edges: (dependent, dependency, explicit?)
    candidates: list[tuple[str, str, bool]] = []
    for fid in sorted(frs):
        f = frs[fid]
        text = " ".join([f.title, f.statement, *f.acceptance_criteria])
        for ref in sorted(set(_FR_REF.findall(text))):
            if ref != fid and ref in frs:
                candidates.append((fid, ref, True))
    for uc in req.use_cases:
        seq: list[str] = []
        for x in uc.fr_ids:
            if x in frs and x not in seq:
                seq.append(x)
        for prev, cur in zip(seq, seq[1:]):
            candidates.append((cur, prev, False))

    for dependent, dependency, explicit in candidates:
        if dependency in deps[dependent]:
            continue
        rank_dep, rank_cur = _RANK[frs[dependency].priority], _RANK[frs[dependent].priority]
        if rank_dep > rank_cur:  # dependency is LESS important than the task waiting for it
            if explicit:
                warnings.append(
                    f"{dependent} ({frs[dependent].priority}) depends on {dependency} "
                    f"({frs[dependency].priority}); review the priorities.")
            else:
                continue  # never invent an edge that blocks an important task behind an optional one
        if _reaches(deps, dependency, dependent):  # adding the edge would close a loop
            if explicit:
                warnings.append(f"Ignored dependency {dependent} -> {dependency}: it would create a circular wait.")
            continue
        deps[dependent].append(dependency)

    for fid in deps:
        deps[fid].sort()
    # belt and braces: the guard above makes this impossible, but a cycle must never reach the database
    if has_cycle(deps):
        warnings.append("Dependencies were removed because they formed a cycle.")
        deps = {fid: [] for fid in frs}
    return deps, warnings


# --------------------------------------------------------------------------
# task content
# --------------------------------------------------------------------------
def estimate_points(f: FR, n_deps: int) -> int:
    score = 1 + len(f.acceptance_criteria) + 0.5 * n_deps + (1 if len(f.statement) > 140 else 0)
    return min(FIB, key=lambda p: (abs(p - score), p))


def _clip(text: str, n: int) -> str:
    text = " ".join(str(text).split())
    return text if len(text) <= n else text[: n - 1].rstrip() + "…"


def _fr_description(f: FR, group: str, dep_labels: list[str]) -> str:
    parts = [f.statement.strip(), "", f"Actor: {f.actor}", f"Use case: {group}"]
    if f.acceptance_criteria:
        parts += ["", "Acceptance criteria:"] + [f"- {c}" for c in f.acceptance_criteria]
    if dep_labels:
        parts += ["", "Suggested to start after: " + "; ".join(dep_labels)]
    return "\n".join(parts)


def _nfr_description(n: NFR) -> str:
    return "\n".join([n.statement.strip(), "", f"Category: {n.category}",
                      f"Measurable target: {n.metric.strip() or 'not specified'}",
                      "", "Applies to the whole system (not tied to one use case)."])


# --------------------------------------------------------------------------
# the plan
# --------------------------------------------------------------------------
def plan_board(req: Requirements, include_nfr: bool = True) -> BoardPlan:
    deps, warnings = plan_dependencies(req)

    # first use case that covers each FR = its group ("epic")
    uc_index: dict[str, int] = {}
    uc_label: dict[str, str] = {}
    for i, uc in enumerate(req.use_cases):
        for fid in uc.fr_ids:
            if fid not in uc_index:
                uc_index[fid] = i
                uc_label[fid] = f"{uc.id} {uc.name}".strip()

    seen_ids: set[str] = set()
    titles = {f.id: f.title for f in req.functional_requirements if f.id}
    drafts: list[tuple[tuple[int, str], PlannedTask]] = []

    for f in req.functional_requirements:
        rid = f.id.strip()[:ID_MAX]
        if not rid:
            warnings.append(f"A requirement titled '{_clip(f.title, 40)}' has no ID and was skipped.")
            continue
        if rid in seen_ids:
            warnings.append(f"{rid} appears more than once in the SRS; only the first one became a task.")
            continue
        seen_ids.add(rid)

        group = uc_label.get(rid)
        if group is None:
            group = UNASSIGNED
            warnings.append(f"{rid} is not covered by any use case; it is listed under '{UNASSIGNED}'.")
        my_deps = deps.get(rid, [])
        dep_labels = [f"{d} {titles.get(d, '')}".strip() for d in my_deps]
        priority = PRIORITY_MAP[f.priority]
        task = PlannedTask(
            requirement_id=rid,
            title=_clip(f"[{rid}] {f.title}", TITLE_MAX),
            description=_fr_description(f, group, dep_labels),
            priority=priority,
            column="Ready" if (f.priority == "must" and not my_deps) else "Backlog",
            estimate_points=estimate_points(f, len(my_deps)),
            depends_on=list(my_deps),
            group=group,
        )
        drafts.append(((uc_index.get(rid, 10_000), rid), task))

    drafts.sort(key=lambda d: d[0])
    tasks = [t for _, t in drafts]

    if include_nfr:
        for n in sorted(req.non_functional_requirements, key=lambda x: x.id):
            rid = n.id.strip()[:ID_MAX]
            if not rid or rid in seen_ids:
                if rid:
                    warnings.append(f"{rid} appears more than once in the SRS; only the first one became a task.")
                continue
            seen_ids.add(rid)
            tasks.append(PlannedTask(
                requirement_id=rid,
                title=_clip(f"[{rid}] {n.category.capitalize()}: {n.statement}", TITLE_MAX),
                description=_nfr_description(n),
                priority=NFR_PRIORITY.get(n.category, "medium"),
                column="Backlog",
                estimate_points=NFR_POINTS,
                depends_on=[],
                group=CROSS_CUTTING,
            ))

    return BoardPlan(columns=list(STANDARD_COLUMNS), tasks=tasks, warnings=warnings)
