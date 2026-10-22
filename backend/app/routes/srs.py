import json
from datetime import datetime, timedelta

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_owned_board
from app.core.llm import LLMError
from app.models.srs import SRSDocument, SRSJob
from app.routes.auth import get_current_user
from app.schemas.srs import GenerateRequest, Issue, QuestionsRequest, Requirements
from app.services.srs_docx import build_docx
from app.services import srs_service
from app.services.activity_service import log_activity
from app.services.srs_validator import validate_requirements

router = APIRouter(prefix="/boards/{board_id}/srs", tags=["SRS"])

MAX_JOBS_PER_HOUR = 5


def _doc_out(d: SRSDocument) -> dict:
    return {
        "id": d.id, "version": d.version, "description": d.description,
        "requirements": d.requirements, "issues": d.issues, "markdown": d.markdown,
        "created_at": d.created_at,
    }


def _get_doc(db: Session, board_id: int, version: int | None) -> SRSDocument:
    q = db.query(SRSDocument).filter(SRSDocument.board_id == board_id)
    doc = q.filter(SRSDocument.version == version).first() if version else q.order_by(SRSDocument.version.desc()).first()
    if not doc:
        raise HTTPException(status_code=404, detail="No SRS has been generated for this board yet.")
    return doc


@router.post("/questions")
def questions(board_id: int, body: QuestionsRequest, db: Session = Depends(get_db),
              current_user=Depends(get_current_user)):
    get_owned_board(db, board_id, current_user, "project_manager")
    try:
        return srs_service.generate_questions(body.description)
    except LLMError as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.post("/generate", status_code=202)
def generate(board_id: int, body: GenerateRequest, background: BackgroundTasks,
             db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    get_owned_board(db, board_id, current_user, "project_manager")

    active = db.query(SRSJob).filter(SRSJob.board_id == board_id,
                                     SRSJob.status.in_(["queued", "running"]),
                                     SRSJob.created_at > datetime.utcnow() - timedelta(minutes=10)).first()
    if active:
        return {"job_id": active.id}  # reuse the running job instead of paying twice

    recent = db.query(SRSJob).filter(SRSJob.user_id == current_user.id,
                                     SRSJob.created_at > datetime.utcnow() - timedelta(hours=1)).count()
    if recent >= MAX_JOBS_PER_HOUR:
        raise HTTPException(status_code=429, detail="Generation limit reached. Please try again later.")

    job = srs_service.create_job(db, board_id, current_user.id, body.description,
                                 [a.model_dump() for a in body.answers])
    background.add_task(srs_service.run_srs_job, job.id)
    log_activity(db, board_id, current_user.id, "srs.generated", "started generating the SRS", "srs_job")
    return {"job_id": job.id}


@router.get("/jobs/{job_id}")
def job_status(board_id: int, job_id: str, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    get_owned_board(db, board_id, current_user, "viewer")
    job = db.query(SRSJob).filter(SRSJob.id == job_id, SRSJob.board_id == board_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"job_id": job.id, "status": job.status, "stage": job.stage, "error": job.error, "srs_id": job.srs_id}


@router.get("/versions")
def versions(board_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    get_owned_board(db, board_id, current_user, "viewer")
    rows = (db.query(SRSDocument).filter(SRSDocument.board_id == board_id)
            .order_by(SRSDocument.version.desc()).all())
    return [{"id": r.id, "version": r.version, "created_at": r.created_at} for r in rows]


@router.get("/export.md")
def export_md(board_id: int, version: int | None = None, db: Session = Depends(get_db),
              current_user=Depends(get_current_user)):
    board = get_owned_board(db, board_id, current_user, "viewer")
    doc = _get_doc(db, board_id, version)
    name = "".join(c if c.isalnum() else "_" for c in board.name)[:40] or "srs"
    return Response(doc.markdown, media_type="text/markdown",
                    headers={"Content-Disposition": f'attachment; filename="SRS_{name}_v{doc.version}.md"'})


@router.get("/export.docx")
def export_docx(board_id: int, version: int | None = None, db: Session = Depends(get_db),
                current_user=Depends(get_current_user)):
    board = get_owned_board(db, board_id, current_user, "viewer")
    doc = _get_doc(db, board_id, version)
    from app.services import diagram_service  # local import: keeps module start-up light
    data = build_docx(Requirements.model_validate(doc.requirements),
                      [Issue.model_validate(i) for i in (doc.issues or [])], doc.version,
                      diagram_service.figures(db, doc.id))
    name = "".join(c if c.isalnum() else "_" for c in board.name)[:40] or "srs"
    return Response(data,
                    media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    headers={"Content-Disposition": f'attachment; filename="SRS_{name}_v{doc.version}.docx"'})


@router.get("/")
def latest(board_id: int, version: int | None = None, db: Session = Depends(get_db),
           current_user=Depends(get_current_user)):
    get_owned_board(db, board_id, current_user, "viewer")
    return _doc_out(_get_doc(db, board_id, version))


@router.patch("/requirements")
def edit_requirements(board_id: int, body: Requirements, db: Session = Depends(get_db),
                      current_user=Depends(get_current_user)):
    """User edited the requirements: re-validate, re-render and store as a new version."""
    get_owned_board(db, board_id, current_user, "project_manager")
    base = _get_doc(db, board_id, None)
    issues = validate_requirements(body)
    doc = srs_service.save_srs(db, board_id, base.description, base.answers or [], body, issues)
    log_activity(db, board_id, current_user.id, "srs.edited", f"edited the requirements (SRS v{doc.version})", "srs", doc.id)
    return _doc_out(doc)