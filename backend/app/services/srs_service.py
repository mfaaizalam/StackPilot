import json
import uuid
from datetime import datetime

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.llm import LLMError, llm_json
from app.models.srs import Diagram, SRSDocument, SRSJob
from app.prompts.srs_prompt import (
    QUESTIONS_SYSTEM, REPAIR_SYSTEM, REQUIREMENTS_SYSTEM,
    questions_prompt, repair_prompt, requirements_prompt,
)
from app.schemas.srs import Issue, QuestionList, Requirements
from app.services.srs_validator import has_errors, validate_requirements


# --------------------------------------------------------------------------
# 1. Questions
# --------------------------------------------------------------------------
def generate_questions(description: str) -> QuestionList:
    result = llm_json(questions_prompt(description), QuestionList, system=QUESTIONS_SYSTEM, temperature=0.4)
    result.questions = result.questions[:8]
    return result


# --------------------------------------------------------------------------
# 2. Requirements (generate -> validate -> ONE repair -> validate)
# --------------------------------------------------------------------------
def build_requirements(description: str, answers: list[dict], on_stage=lambda s: None) -> tuple[Requirements, list[Issue]]:
    on_stage("requirements")
    req = llm_json(requirements_prompt(description, answers), Requirements, system=REQUIREMENTS_SYSTEM, temperature=0.2)

    on_stage("validating")
    issues = validate_requirements(req)
    if has_errors(issues):
        on_stage("repairing")
        problems = [i.message for i in issues if i.level == "error"]
        try:
            req = llm_json(repair_prompt(req.model_dump_json(), problems), Requirements,
                           system=REPAIR_SYSTEM, temperature=0.1)
            issues = validate_requirements(req)
        except LLMError:
            pass  # keep the first draft; the remaining issues are shown to the user
    return req, issues


# --------------------------------------------------------------------------
# 3. Deterministic Markdown renderer (no AI)
# --------------------------------------------------------------------------
def _cell(text: str) -> str:
    return str(text).replace("|", "\\|").replace("\n", " ").strip()


def _bullets(items: list[str], empty: str = "None.") -> str:
    return "\n".join(f"- {i}" for i in items) if items else empty


def render_srs_markdown(req: Requirements, issues: list[Issue], version: int = 1) -> str:
    L: list[str] = []
    a = L.append
    a(f"# Software Requirements Specification\n\n## {req.title}\n")
    a(f"*Version {version} · {datetime.utcnow():%Y-%m-%d} · Structure based on ISO/IEC/IEEE 29148*\n")

    a("## 1. Introduction\n")
    a(f"### 1.1 Purpose\n\n{req.purpose}\n")
    a(f"### 1.2 Scope\n\n{req.scope}\n")
    a("### 1.3 Definitions, Acronyms and Abbreviations\n")
    if req.definitions:
        a("| Term | Definition |\n|---|---|")
        L.extend(f"| {_cell(d.term)} | {_cell(d.definition)} |" for d in req.definitions)
        a("")
    else:
        a("None.\n")

    a("## 2. Overall Description\n")
    a(f"### 2.1 Product Perspective\n\n{req.product_perspective}\n")
    a("### 2.2 User Classes and Characteristics\n")
    a("| Actor | Description |\n|---|---|")
    L.extend(f"| {_cell(x.name)} | {_cell(x.description)} |" for x in req.actors)
    a("")
    a(f"### 2.3 Constraints\n\n{_bullets(req.constraints)}\n")
    a(f"### 2.4 Assumptions and Dependencies\n\n{_bullets(req.assumptions)}\n")

    a("## 3. Specific Requirements\n")
    a(f"### 3.1 External Interfaces\n\n{_bullets(req.external_interfaces)}\n")

    a("### 3.2 Functional Requirements\n")
    by_actor: dict[str, list] = {}
    for f in req.functional_requirements:
        by_actor.setdefault(f.actor, []).append(f)
    for n, (actor, frs) in enumerate(by_actor.items(), start=1):
        a(f"#### 3.2.{n} {actor}\n")
        for f in frs:
            a(f"**{f.id} · {f.title}** *(priority: {f.priority})*\n")
            a(f"{f.statement}\n")
            if f.acceptance_criteria:
                a("Acceptance criteria:\n")
                a(_bullets(f.acceptance_criteria) + "\n")

    a("### 3.3 Non-Functional Requirements\n")
    by_cat: dict[str, list] = {}
    for r in req.non_functional_requirements:
        by_cat.setdefault(r.category, []).append(r)
    for n, (cat, rs) in enumerate(by_cat.items(), start=1):
        a(f"#### 3.3.{n} {cat.capitalize()}\n")
        a("| ID | Requirement | Measurable target |\n|---|---|---|")
        L.extend(f"| {r.id} | {_cell(r.statement)} | {_cell(r.metric)} |" for r in rs)
        a("")

    a("## 4. Use Cases\n")
    for u in req.use_cases:
        a(f"### {u.id} · {u.name}\n")
        a(f"- **Primary actor:** {u.actor}")
        a(f"- **Description:** {u.description}")
        a(f"- **Related requirements:** {', '.join(u.fr_ids) or '—'}\n")
        if u.preconditions:
            a("**Preconditions**\n")
            a(_bullets(u.preconditions) + "\n")
        a("**Main flow**\n")
        a("\n".join(f"{i}. {s}" for i, s in enumerate(u.main_flow, start=1)) + "\n")
        if u.alternate_flows:
            a("**Alternate flows**\n")
            a(_bullets(u.alternate_flows) + "\n")

    a("## 5. Data Entities\n")
    for e in req.entities:
        a(f"### {e.name}\n")
        a(f"{e.description}\n")
        a(f"- **Attributes:** {', '.join(e.attributes) or '—'}")
        a(f"- **Relations:** {'; '.join(e.relations) or '—'}\n")

    a("## Appendix A: Traceability Matrix\n")
    a("| Requirement | Title | Priority | Covered by |\n|---|---|---|---|")
    for f in req.functional_requirements:
        ucs = ", ".join(u.id for u in req.use_cases if f.id in u.fr_ids) or "**NOT COVERED**"
        a(f"| {f.id} | {_cell(f.title)} | {f.priority} | {ucs} |")
    a("")

    a("## Appendix B: Open Issues\n")
    a(_bullets(req.open_issues) + "\n")

    warnings = [i for i in issues if i.level == "warning"]
    errors = [i for i in issues if i.level == "error"]
    if warnings or errors:
        a("## Appendix C: Quality Check Findings\n")
        a(_bullets([f"[{i.level.upper()}] {i.message}" for i in errors + warnings]) + "\n")
    return "\n".join(L)


# --------------------------------------------------------------------------
# 4. Saving + background job
# --------------------------------------------------------------------------
def save_srs(db: Session, board_id: int, description: str, answers: list[dict],
             req: Requirements, issues: list[Issue]) -> SRSDocument:
    last = (db.query(SRSDocument).filter(SRSDocument.board_id == board_id)
            .order_by(SRSDocument.version.desc()).first())
    version = (last.version + 1) if last else 1
    doc = SRSDocument(
        board_id=board_id, version=version, description=description, answers=answers,
        requirements=json.loads(req.model_dump_json()),
        issues=[i.model_dump() for i in issues],
        markdown=render_srs_markdown(req, issues, version),
    )
    db.add(doc)
    db.flush()
    if last:  # diagrams of the previous version carry over, flagged stale until regenerated
        for d in db.query(Diagram).filter(Diagram.srs_id == last.id).all():
            db.add(Diagram(srs_id=doc.id, type=d.type, title=d.title, model=d.model, stale=True))
    db.commit()
    db.refresh(doc)
    return doc


def create_job(db: Session, board_id: int, user_id: int, description: str, answers: list[dict]) -> SRSJob:
    job = SRSJob(id=str(uuid.uuid4()), board_id=board_id, user_id=user_id, status="queued",
                 stage="queued", payload={"description": description, "answers": answers})
    db.add(job)
    db.commit()
    return job


def run_srs_job(job_id: str) -> None:
    """Runs in a background thread with its OWN db session."""
    db = SessionLocal()
    try:
        job = db.query(SRSJob).filter(SRSJob.id == job_id).first()
        if not job:
            return

        def stage(name: str):
            job.stage = name
            db.commit()

        job.status = "running"
        db.commit()
        try:
            description = job.payload["description"]
            answers = job.payload.get("answers", [])
            req, issues = build_requirements(description, answers, on_stage=stage)
            stage("saving")
            doc = save_srs(db, job.board_id, description, answers, req, issues)
            job.srs_id = doc.id
            job.status = "done"
            job.stage = "done"
        except LLMError as e:
            job.status, job.stage, job.error = "failed", "failed", str(e)
        except Exception as e:  # never leave a job stuck in "running"
            job.status, job.stage, job.error = "failed", "failed", f"Unexpected error: {str(e)[:200]}"
        db.commit()
    finally:
        db.close()
