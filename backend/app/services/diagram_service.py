"""Diagram generation: requirements JSON -> validated diagram models -> stored rows.

Each diagram follows the same safe pipeline (Golden rules 1 and 2):
    AI -> validate (code) -> ONE repair call if errors -> sanitize (code, hard limits)
and falls back to a deterministic, AI-free builder if the AI is unavailable."""
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Callable

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.llm import LLMError, llm_json
from app.models.srs import Diagram, DiagramJob, SRSDocument
from app.prompts import diagram_prompt as P
from app.schemas.diagrams import (
        DIAGRAM_TYPES, ActivityModel, ClassModel, DeploymentModel, SequenceModel, StateModelSet,
    UseCaseRelations,
)
import logging
from app.schemas.srs import Requirements
from app.services import diagram_fallbacks as F
from app.services import diagram_validator as V
from app.services.diagram_mermaid import to_mermaid
from app.services.diagram_usecase_svg import render_usecase_svg
from app.schemas.diagrams import UseCaseModel

log = logging.getLogger("stackpilot.diagrams")
TYPE_ORDER = {t: i for i, t in enumerate(DIAGRAM_TYPES)}
N_SEQUENCE = 4   # top use cases that get a sequence diagram (plan: 3-5)
N_ACTIVITY = 3   # major workflows that get an activity diagram
AI_DOWN = "The AI service was unavailable, so this diagram was drawn directly from the requirements."

# (spec_dict | None, warnings, source)
Result = tuple[dict | None, list[str], str]


@dataclass
class Task:
    type: str
    title: str
    run: Callable[[], Result]


def _ai_model(prompt, schema, system, validate, sanitize):
    """AI call -> validate -> one repair -> sanitize. Raises LLMError if the AI fails outright."""
    spec = llm_json(prompt, schema, system=system, temperature=0.2)
    errors = [i.message for i in validate(spec) if i.level == "error"]
    if errors:
        try:
            spec = llm_json(P.repair_prompt(spec.model_dump_json(), errors), schema,
                            system=P.REPAIR_SYSTEM, temperature=0.1)
        except LLMError:
            pass  # keep the first draft; sanitize will trim it
    return sanitize(spec)


# --------------------------------------------------------------- builders
def make_usecase(req: Requirements) -> Result:
    model = F.build_usecase_model(req)
    warns: list[str] = []
    source = "rules"
    try:
        rel = llm_json(P.usecase_rel_prompt(req), UseCaseRelations, system=P.USECASE_REL_SYSTEM, temperature=0.1)
        model.includes, model.extends = V.sanitize_uc_relations(rel.includes, rel.extends, model)
        source = "ai"
    except LLMError:
        pass  # the diagram is complete without include/extend arcs
    return model.model_dump(), warns, source


def make_class(req: Requirements, entities, part: int, parts: int) -> Result:
    fallback = F.class_from_entities(entities)
    try:
        spec, warns = _ai_model(P.class_prompt(req, entities), ClassModel, P.CLASS_SYSTEM,
                                V.validate_class, V.sanitize_class)
        if spec:
            return spec.model_dump(), warns, "ai"
    except LLMError:
        pass
    spec, warns = V.sanitize_class(fallback)
    return (spec.model_dump() if spec else None), [AI_DOWN] + warns, "fallback"


def make_sequence(req: Requirements, uc) -> Result:
    try:
        spec, warns = _ai_model(P.sequence_prompt(req, uc), SequenceModel, P.SEQUENCE_SYSTEM,
                                V.validate_sequence, V.sanitize_sequence)
        if spec:
            return spec.model_dump(), warns, "ai"
    except LLMError:
        pass
    spec, warns = V.sanitize_sequence(F.sequence_from_usecase(uc))
    return (spec.model_dump() if spec else None), [AI_DOWN] + warns, "fallback"


def make_activity(req: Requirements, uc) -> Result:
    try:
        spec, warns = _ai_model(P.activity_prompt(req, uc), ActivityModel, P.ACTIVITY_SYSTEM,
                                V.validate_activity, V.sanitize_activity)
        if spec:
            return spec.model_dump(), warns, "ai"
    except LLMError:
        pass
    spec, warns = V.sanitize_activity(F.activity_from_usecase(uc))
    return (spec.model_dump() if spec else None), [AI_DOWN] + warns, "fallback"

def make_deployment(req: Requirements) -> Result:
    reason = AI_DOWN
    try:
        spec, warns = _ai_model(P.deployment_prompt(req), DeploymentModel, P.DEPLOYMENT_SYSTEM,
                                V.validate_deployment, V.sanitize_deployment)
        if spec:
            return spec.model_dump(), warns, "ai"
        log.warning("Deployment diagram: the AI answered but nothing usable was left after cleanup: %s", warns)
        reason = "The AI's answer could not be used, so this diagram was drawn directly from the requirements."
    except LLMError as e:
        log.warning("Deployment diagram: AI call failed: %s", e)
    spec, warns = V.sanitize_deployment(F.deployment_from_requirements(req))
    return (spec.model_dump() if spec else None), [reason] + warns, "fallback"

def make_state_set(req: Requirements) -> list[tuple[str, Result]]:
    """May yield 0..3 diagrams (only entities with a lifecycle). Returns [(title, result)]."""
    try:
        sset = llm_json(P.state_prompt(req), StateModelSet, system=P.STATE_SYSTEM, temperature=0.2)
    except LLMError:
        return []  # no honest deterministic fallback for lifecycles: skip silently
    out = []
    for m in sset.machines[:3]:
        errors = [i.message for i in V.validate_state(m) if i.level == "error"]
        spec, warns = V.sanitize_state(m)  # state machines are small: trim instead of re-asking
        if spec:
            out.append((f"{spec.entity} lifecycle", (spec.model_dump(), warns + (errors and ["Some states or transitions were trimmed."] or []), "ai")))
    return out


# ------------------------------------------------------------------ plan
def plan_tasks(req: Requirements, types: list[str]) -> list[Task]:
    tasks: list[Task] = []
    ranked = F.rank_use_cases(req)
    if "usecase" in types:
        tasks.append(Task("usecase", "Use case diagram", lambda: make_usecase(req)))
    if "class" in types and req.entities:
        parts = F.chunk_entities(req.entities)
        for i, ents in enumerate(parts, start=1):
            title = "Class diagram" if len(parts) == 1 else f"Class diagram (part {i} of {len(parts)})"
            tasks.append(Task("class", title, lambda e=ents, i=i, n=len(parts): make_class(req, e, i, n)))
    if "sequence" in types:
        for uc in ranked[:N_SEQUENCE]:
            tasks.append(Task("sequence", f"Sequence: {uc.name}", lambda uc=uc: make_sequence(req, uc)))
    if "activity" in types:
        for uc in ranked[:N_ACTIVITY]:
            tasks.append(Task("activity", f"Activity: {uc.name}", lambda uc=uc: make_activity(req, uc)))
    if "deployment" in types:
        tasks.append(Task("deployment", "Deployment diagram", lambda: make_deployment(req)))
    return tasks


# ------------------------------------------------------------ rendering
def diagram_out(d: Diagram, req_actors: set[str] | None = None) -> dict:
    m = d.model or {}
    out = {"id": d.id, "type": d.type, "title": d.title, "stale": bool(d.stale),
           "warnings": m.get("warnings", []), "source": m.get("source", "ai")}
    try:
        if d.type == "usecase":
            out["svg"] = render_usecase_svg(UseCaseModel.model_validate(m["spec"]))
        else:
            out["mermaid"] = to_mermaid(d.type, m["spec"], set(m.get("actors", [])))
    except Exception:  # a corrupt row must never break the whole list
        out["error"] = "This diagram could not be rendered."
    return out


def list_diagrams(db: Session, srs_id: int) -> list[dict]:
    rows = db.query(Diagram).filter(Diagram.srs_id == srs_id).all()
    rows.sort(key=lambda d: (TYPE_ORDER.get(d.type, 99), (d.model or {}).get("order", 0), d.id))
    return [diagram_out(d) for d in rows]


# ------------------------------------------------------------------- job
def create_job(db: Session, board_id: int, user_id: int, srs_id: int, types: list[str]) -> DiagramJob:
    job = DiagramJob(id=str(uuid.uuid4()), board_id=board_id, user_id=user_id, srs_id=srs_id,
                     status="queued", stage="queued", payload={"types": types})
    db.add(job)
    db.commit()
    return job


def run_diagram_job(job_id: str) -> None:
    """Runs in a background thread with its OWN db session. LLM calls run in a small
    thread pool; ALL database writes stay on this thread."""
    db = SessionLocal()
    try:
        job = db.query(DiagramJob).filter(DiagramJob.id == job_id).first()
        if not job:
            return
        try:
            doc = db.query(SRSDocument).filter(SRSDocument.id == job.srs_id).first()
            req = Requirements.model_validate(doc.requirements)
            types = job.payload.get("types") or list(DIAGRAM_TYPES)
            actors = [a.name for a in req.actors]
            tasks = plan_tasks(req, types)
            want_state = "state" in types
            total = len(tasks) + (1 if want_state else 0)

            job.status, job.stage = "running", f"0/{total}"
            db.commit()

            cleared: set[str] = set()
            done = produced = 0

            def store(dtype: str, title: str, order: int, res: Result):
                nonlocal produced
                spec, warns, source = res
                if not spec:
                    return
                if dtype not in cleared:  # replace old diagrams of this type only once we have a new one
                    db.query(Diagram).filter(Diagram.srs_id == job.srs_id, Diagram.type == dtype).delete()
                    cleared.add(dtype)
                db.add(Diagram(srs_id=job.srs_id, type=dtype, title=title, stale=False,
                               model={"spec": spec, "warnings": warns, "source": source, "actors": actors, "order": order}))
                db.commit()
                produced += 1

            jobs: list[tuple[str, int, Callable]] = [(t.type, i, t) for i, t in enumerate(tasks)]
            with ThreadPoolExecutor(max_workers=4) as pool:
                futures = {pool.submit(t.run): (t, i) for _, i, t in jobs}
                if want_state:
                    futures[pool.submit(make_state_set, req)] = (None, 0)
                for fut in as_completed(futures):
                    task, order = futures[fut]
                    try:
                        res = fut.result()
                    except Exception:
                        res = None
                    if task is None:  # state machines: a list of (title, result)
                        for k, (title, r) in enumerate(res or []):
                            store("state", title, k, r)
                    elif res:
                        store(task.type, task.title, order, res)
                    done += 1
                    job.stage = f"{done}/{total}"
                    db.commit()

            if produced:
                job.status, job.stage = "done", "done"
            else:
                job.status, job.stage, job.error = "failed", "failed", "No diagrams could be generated. Please try again."
        except Exception as e:  # never leave a job stuck in "running"
            db.rollback()
            job = db.query(DiagramJob).filter(DiagramJob.id == job_id).first()
            job.status, job.stage, job.error = "failed", "failed", f"Unexpected error: {str(e)[:200]}"
        db.commit()
    finally:
        db.close()
