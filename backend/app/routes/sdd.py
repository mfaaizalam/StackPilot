"""SDD routes: thin HTTP layer. Ownership is checked on every route through core/deps.py."""
from datetime import datetime, timedelta

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_owned_board
from app.models.sdd import SDDDocument, SDDJob
from app.models.srs import SRSDocument
from app.routes.auth import get_current_user
from app.schemas.sdd import DesignModel, SDDGenerateRequest
from app.schemas.srs import Issue, Requirements
from app.services import diagram_service, sdd_service
from app.services.sdd_docx import build_docx

router = APIRouter(prefix="/boards/{board_id}/sdd", tags=["SDD"])

MAX_JOBS_PER_HOUR = 5
_DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def _get_srs(db: Session, board_id: int, srs_id: int | None) -> SRSDocument:
    q = db.query(SRSDocument).filter(SRSDocument.board_id == board_id)
    doc = q.filter(SRSDocument.id == srs_id).first() if srs_id else q.order_by(SRSDocument.version.desc()).first()
    if not doc:
        raise HTTPException(status_code=404, detail="No SRS found. Generate the SRS first.")
    return doc


def _get_sdd(db: Session, board_id: int, version: int | None) -> SDDDocument:
    q = db.query(SDDDocument).filter(SDDDocument.board_id == board_id)
    doc = q.filter(SDDDocument.version == version).first() if version else q.order_by(SDDDocument.version.desc()).first()
    if not doc:
        raise HTTPException(status_code=404, detail="No SDD has been generated for this board yet.")
    return doc


def _out(db: Session, d: SDDDocument) -> dict:
    latest = (db.query(SRSDocument).filter(SRSDocument.board_id == d.board_id)
              .order_by(SRSDocument.version.desc()).first())
    return {
        "id": d.id, "version": d.version, "srs_id": d.srs_id, "srs_version": d.srs_version, "source": d.source,
        "srs_outdated": bool(latest and latest.id != d.srs_id),  # the SRS changed after this SDD was made
        "design": d.design, "issues": d.issues, "diagrams": d.diagrams, "markdown": d.markdown,
        "created_at": d.created_at,
    }


def _filename(board, doc: SDDDocument, ext: str) -> str:
    name = "".join(c if c.isalnum() else "_" for c in board.name)[:40] or "sdd"
    return f'attachment; filename="SDD_{name}_v{doc.version}.{ext}"'


@router.post("/generate", status_code=202)
def generate(board_id: int, body: SDDGenerateRequest, background: BackgroundTasks,
             db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    get_owned_board(db, board_id, current_user, "editor")
    srs = _get_srs(db, board_id, body.srs_id)

    active = db.query(SDDJob).filter(SDDJob.board_id == board_id, SDDJob.status.in_(["queued", "running"]),
                                     SDDJob.created_at > datetime.utcnow() - timedelta(minutes=10)).first()
    if active:
        return {"job_id": active.id, "srs_id": active.srs_id}  # reuse the running job instead of paying twice

    recent = db.query(SDDJob).filter(SDDJob.user_id == current_user.id,
                                     SDDJob.created_at > datetime.utcnow() - timedelta(hours=1)).count()
    if recent >= MAX_JOBS_PER_HOUR:
        raise HTTPException(status_code=429, detail="Generation limit reached. Please try again later.")

    job = sdd_service.create_job(db, board_id, current_user.id, srs.id)
    background.add_task(sdd_service.run_sdd_job, job.id)
    return {"job_id": job.id, "srs_id": srs.id}


@router.get("/jobs/{job_id}")
def job_status(board_id: int, job_id: str, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    get_owned_board(db, board_id, current_user, "viewer")
    job = db.query(SDDJob).filter(SDDJob.id == job_id, SDDJob.board_id == board_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"job_id": job.id, "status": job.status, "stage": job.stage, "error": job.error, "sdd_id": job.sdd_id}


@router.get("/versions")
def versions(board_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    get_owned_board(db, board_id, current_user, "viewer")
    rows = db.query(SDDDocument).filter(SDDDocument.board_id == board_id).order_by(SDDDocument.version.desc()).all()
    return [{"id": r.id, "version": r.version, "srs_version": r.srs_version, "source": r.source,
             "created_at": r.created_at} for r in rows]


@router.get("/export.md")
def export_md(board_id: int, version: int | None = None, db: Session = Depends(get_db),
              current_user=Depends(get_current_user)):
    board = get_owned_board(db, board_id, current_user, "viewer")
    doc = _get_sdd(db, board_id, version)
    return Response(doc.markdown, media_type="text/markdown",
                    headers={"Content-Disposition": _filename(board, doc, "md")})


@router.get("/export.docx")
def export_docx(board_id: int, version: int | None = None, db: Session = Depends(get_db),
                current_user=Depends(get_current_user)):
    board = get_owned_board(db, board_id, current_user, "viewer")
    doc = _get_sdd(db, board_id, version)
    srs = db.query(SRSDocument).filter(SRSDocument.id == doc.srs_id).first()
    if not srs:
        raise HTTPException(status_code=404, detail="The SRS this SDD was based on no longer exists.")
    data = build_docx(DesignModel.model_validate(doc.design), Requirements.model_validate(srs.requirements),
                      [Issue.model_validate(i) for i in (doc.issues or [])],
                      diagram_service.figures(db, srs.id), doc.version, doc.srs_version or srs.version)
    return Response(data, media_type=_DOCX, headers={"Content-Disposition": _filename(board, doc, "docx")})


@router.get("")
def latest(board_id: int, version: int | None = None, db: Session = Depends(get_db),
           current_user=Depends(get_current_user)):
    get_owned_board(db, board_id, current_user, "viewer")
    return _out(db, _get_sdd(db, board_id, version))