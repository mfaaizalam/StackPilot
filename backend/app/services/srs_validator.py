"""Pure-Python checks on a Requirements object. No AI involved.

Errors  -> trigger the single repair call.
Warnings -> shown to the user, never block."""
import re

from app.schemas.srs import Issue, Requirements

VAGUE = ("fast", "quick", "user-friendly", "user friendly", "easy", "efficient",
         "robust", "scalable", "intuitive", "modern", "seamless", "flexible")
ID_PATTERNS = {"FR": r"^FR-\d{3}$", "NFR": r"^NFR-\d{3}$", "UC": r"^UC-\d{3}$"}


def _err(code, msg):
    return Issue(level="error", code=code, message=msg)


def _warn(code, msg):
    return Issue(level="warning", code=code, message=msg)


def validate_requirements(req: Requirements) -> list[Issue]:
    issues: list[Issue] = []
    actor_names = {a.name.strip().lower() for a in req.actors}
    fr_ids = [f.id for f in req.functional_requirements]
    uc_ids = [u.id for u in req.use_cases]
    nfr_ids = [n.id for n in req.non_functional_requirements]

    # ---- minimum size ---------------------------------------------------
    if len(req.functional_requirements) < 5:
        issues.append(_err("MIN_FR", "At least 5 functional requirements are needed."))
    if len(req.non_functional_requirements) < 3:
        issues.append(_err("MIN_NFR", "At least 3 non-functional requirements are needed."))
    if len(req.use_cases) < 3:
        issues.append(_err("MIN_UC", "At least 3 use cases are needed."))
    if not req.actors:
        issues.append(_err("NO_ACTORS", "At least one actor is needed."))

    # ---- ids ------------------------------------------------------------
    for kind, ids in (("FR", fr_ids), ("NFR", nfr_ids), ("UC", uc_ids)):
        for i in ids:
            if not re.match(ID_PATTERNS[kind], i or ""):
                issues.append(_err("BAD_ID", f"'{i}' is not a valid {kind} id (expected {kind}-001 format)."))
        dupes = {i for i in ids if ids.count(i) > 1}
        for d in sorted(dupes):
            issues.append(_err("DUP_ID", f"Duplicate id {d}."))

    # ---- references -----------------------------------------------------
    for f in req.functional_requirements:
        if f.actor.strip().lower() not in actor_names:
            issues.append(_err("UNKNOWN_ACTOR", f"{f.id} uses actor '{f.actor}' which is not in the actor list."))
    covered: set[str] = set()
    used_actors: set[str] = set()
    for u in req.use_cases:
        if u.actor.strip().lower() not in actor_names:
            issues.append(_err("UNKNOWN_ACTOR", f"{u.id} uses actor '{u.actor}' which is not in the actor list."))
        used_actors.add(u.actor.strip().lower())
        if not u.fr_ids:
            issues.append(_err("UC_NO_FR", f"{u.id} does not reference any functional requirement."))
        for r in u.fr_ids:
            if r not in fr_ids:
                issues.append(_err("UNKNOWN_FR", f"{u.id} references {r} which does not exist."))
            covered.add(r)

    # ---- traceability ---------------------------------------------------
    for f in req.functional_requirements:
        if f.id not in covered:
            issues.append(_err("FR_UNCOVERED", f"{f.id} is not covered by any use case."))
    for a in req.actors:
        if a.name.strip().lower() not in used_actors:
            issues.append(_err("ACTOR_UNUSED", f"Actor '{a.name}' has no use case."))

    # ---- warnings -------------------------------------------------------
    for f in req.functional_requirements:
        if "shall" not in f.statement.lower():
            issues.append(_warn("NO_SHALL", f"{f.id} should be written as 'The system shall ...'."))
        if not f.acceptance_criteria:
            issues.append(_warn("NO_CRITERIA", f"{f.id} has no acceptance criteria."))
    for n in req.non_functional_requirements:
        text = f"{n.statement} {n.metric}".lower()
        has_number = bool(re.search(r"\d", n.metric))
        if not n.metric.strip() or not has_number:
            issues.append(_warn("NFR_NOT_MEASURABLE", f"{n.id} has no measurable target (add a number)."))
        elif any(re.search(rf"\b{re.escape(w)}\b", n.statement.lower()) for w in VAGUE) and not has_number:
            issues.append(_warn("NFR_VAGUE", f"{n.id} uses a vague word."))
    entity_names = {e.name.strip().lower() for e in req.entities}
    for e in req.entities:
        for rel in e.relations:
            words = re.findall(r"[A-Za-z][A-Za-z0-9_]*", rel)
            mentioned = [w for w in words if w[0].isupper() and w.lower() != e.name.lower()]
            if mentioned and not any(w.lower() in entity_names for w in mentioned):
                issues.append(_warn("ENTITY_REF", f"Relation '{rel}' of {e.name} mentions an unknown entity."))
    return issues


def has_errors(issues: list[Issue]) -> bool:
    return any(i.level == "error" for i in issues)
