"""SDD generation: SRS requirements + generated UML diagrams -> validated design -> stored document.

Same safe pipeline as the SRS and diagram engines (Golden rules 1 and 2):
    AI -> validate (code) -> ONE repair call if errors -> sanitize (code) -> validate again -> render (code)
and a deterministic, AI-free design if the AI is unavailable."""
import json
import logging
import uuid

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.llm import LLMError, llm_json
from app.models.srs import Diagram, SRSDocument
from app.models.sdd import SDDDocument, SDDJob
from app.prompts import sdd_prompt as P
from app.schemas.sdd import DesignModel
from app.schemas.srs import Issue, Requirements
from app.services import diagram_service
from app.services import sdd_fallbacks as F
from app.services.sdd_renderer import render_sdd_markdown
from app.services.sdd_validator import has_errors, sanitize_design, validate_design

log = logging.getLogger("stackpilot.sdd")


# ------------------------------------------------------------ 1. context
def collect_context(db: Session, srs_id: int) -> tuple[list[dict], dict, list[Issue]]:
    """Rendered diagrams (for the document), a compact summary (for the AI) and diagram-related findings."""
    diagrams = diagram_service.list_diagrams(db, srs_id)
    classes: dict[str, dict] = {}
    relations: list[str] = []
    deployment: list[dict] = []
    for row in db.query(Diagram).filter(Diagram.srs_id == srs_id).order_by(Diagram.id).all():
        spec = (row.model or {}).get("spec") or {}
        if row.type == "class":
            for c in spec.get("classes", []):
                classes.setdefault(c["name"], {"name": c["name"], "methods": c.get("methods", [])[:6]})
            for r in spec.get("relations", []):
                relations.append(f"{r['source']} {r.get('multiplicity_source', '')} -> {r.get('multiplicity_target', '')} {r['target']} ({r['kind']})")
        elif row.type == "deployment":
            deployment = [{"name": n["name"], "kind": n["kind"], "technology": n.get("technology", ""),
                           "artifacts": n.get("artifacts", [])} for n in spec.get("nodes", [])]
    ctx = {"classes": list(classes.values()), "class_relations": relations[:30], "deployment": deployment}

    findings: list[Issue] = []
    if not diagrams:
        findings.append(Issue(level="warning", code="NO_DIAGRAMS",
                              message="No UML diagrams exist for this SRS version, so the design sections that embed diagrams are empty. Generate the diagrams and regenerate the SDD."))
    elif any(d["stale"] for d in diagrams):
        findings.append(Issue(level="warning", code="STALE_DIAGRAMS",
                              message="Some diagrams were generated from an earlier SRS version and may not match the requirements. Regenerate the diagrams, then the SDD."))
    return diagrams, ctx, findings


# ------------------------------------------------------------ 2. design
def build_design(req: Requirements, ctx: dict, on_stage=lambda s: None) -> tuple[DesignModel, list[Issue], str]:
    on_stage("designing")
    source = "ai"
    try:
        draft = llm_json(P.design_prompt(req, ctx), DesignModel, system=P.DESIGN_SYSTEM, temperature=0.2)
    except LLMError as e:
        log.warning("SDD: AI unavailable, using the rule-based design: %s", e)
        draft, source = F.build_design(req, ctx), "fallback"

    on_stage("validating")
    issues = validate_design(draft, req)
    if source == "ai" and has_errors(issues):
        on_stage("repairing")
        problems = [i.message for i in issues if i.level == "error"]
        try:
            draft = llm_json(P.repair_prompt(draft.model_dump_json(), problems), DesignModel,
                             system=P.REPAIR_SYSTEM, temperature=0.1)
        except LLMError:
            pass  # keep the first draft; remaining gaps are reported to the user, never hidden

    design, cleaned = sanitize_design(draft, req)
    issues = validate_design(design, req)  # what the user sees = the state of the FINAL design
    if source == "fallback":
        issues.insert(0, Issue(level="warning", code="AI_UNAVAILABLE",
                               message="The AI service was unavailable, so this design was derived directly from the requirements. Endpoints and component allocation are indicative; review them."))
    issues += [Issue(level="warning", code="CLEANED", message=m) for m in cleaned]
    return design, issues, source


# ------------------------------------------------------------ 3. saving
def save_sdd(db: Session, srs: SRSDocument, design: DesignModel, issues: list[Issue],
             diagrams: list[dict], source: str) -> SDDDocument:
    last = (db.query(SDDDocument).filter(SDDDocument.board_id == srs.board_id)
            .order_by(SDDDocument.version.desc()).first())
    version = (last.version + 1) if last else 1
    req = Requirements.model_validate(srs.requirements)
    doc = SDDDocument(
        board_id=srs.board_id, srs_id=srs.id, srs_version=srs.version, version=version, source=source,
        design=json.loads(design.model_dump_json()),
        issues=[i.model_dump() for i in issues],
        diagrams=[{"id": d["id"], "type": d["type"], "title": d["title"], "stale": d["stale"]} for d in diagrams],
        markdown=render_sdd_markdown(design, req, issues, diagrams, version, srs.version),
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


# ------------------------------------------------------------ 4. job
def create_job(db: Session, board_id: int, user_id: int, srs_id: int) -> SDDJob:
    job = SDDJob(id=str(uuid.uuid4()), board_id=board_id, user_id=user_id, srs_id=srs_id,
                 status="queued", stage="queued")
    db.add(job)
    db.commit()
    return job


def run_sdd_job(job_id: str) -> None:
    """Runs in a background thread with its OWN db session."""
    db = SessionLocal()
    try:
        job = db.query(SDDJob).filter(SDDJob.id == job_id).first()
        if not job:
            return

        def stage(name: str):
            job.stage = name
            db.commit()

        job.status = "running"
        db.commit()
        try:
            stage("collecting")
            srs = db.query(SRSDocument).filter(SRSDocument.id == job.srs_id, SRSDocument.board_id == job.board_id).first()
            if not srs:
                raise ValueError("The SRS for this job no longer exists.")
            req = Requirements.model_validate(srs.requirements)
            diagrams, ctx, findings = collect_context(db, srs.id)
            design, issues, source = build_design(req, ctx, on_stage=stage)
            stage("saving")
            doc = save_sdd(db, srs, design, findings + issues, diagrams, source)
            job.sdd_id, job.status, job.stage = doc.id, "done", "done"
        except Exception as e:  # never leave a job stuck in "running"
            db.rollback()
            log.exception("SDD job %s failed", job_id)
            job = db.query(SDDJob).filter(SDDJob.id == job_id).first()
            job.status, job.stage = "failed", "failed"
            job.error = "The design could not be generated. Please try again." if not isinstance(e, ValueError) else str(e)[:200]
        db.commit()
    finally:
        db.close()
        