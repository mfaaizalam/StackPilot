from datetime import datetime, timedelta

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_owned_board
from app.models.srs import DiagramJob, SRSDocument
from app.routes.auth import get_current_user
from app.schemas.diagrams import DIAGRAM_TYPES, DiagramGenerateRequest
from app.services import diagram_service

router = APIRouter(prefix="/boards/{board_id}/srs/diagrams", tags=["Diagrams"])

MAX_JOBS_PER_HOUR = 5


def _get_srs(db: Session, board_id: int, srs_id: int | None) -> SRSDocument:
    q = db.query(SRSDocument).filter(SRSDocument.board_id == board_id)
    doc = q.filter(SRSDocument.id == srs_id).first() if srs_id else q.order_by(SRSDocument.version.desc()).first()
    if not doc:
        raise HTTPException(status_code=404, detail="No SRS found. Generate the SRS first.")
    return doc


@router.post("/generate", status_code=202)
def generate(board_id: int, body: DiagramGenerateRequest, background: BackgroundTasks,
             db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    get_owned_board(db, board_id, current_user)
    doc = _get_srs(db, board_id, body.srs_id)

    active = db.query(DiagramJob).filter(DiagramJob.board_id == board_id, DiagramJob.srs_id == doc.id,
                                         DiagramJob.status.in_(["queued", "running"]),
                                         DiagramJob.created_at > datetime.utcnow() - timedelta(minutes=10)).first()
    if active:
        return {"job_id": active.id, "srs_id": doc.id}  # reuse the running job instead of paying twice

    recent = db.query(DiagramJob).filter(DiagramJob.user_id == current_user.id,
                                         DiagramJob.created_at > datetime.utcnow() - timedelta(hours=1)).count()
    if recent >= MAX_JOBS_PER_HOUR:
        raise HTTPException(status_code=429, detail="Generation limit reached. Please try again later.")

    job = diagram_service.create_job(db, board_id, current_user.id, doc.id, body.types or list(DIAGRAM_TYPES))
    background.add_task(diagram_service.run_diagram_job, job.id)
    return {"job_id": job.id, "srs_id": doc.id}


@router.get("/jobs/{job_id}")
def job_status(board_id: int, job_id: str, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    get_owned_board(db, board_id, current_user)
    job = db.query(DiagramJob).filter(DiagramJob.id == job_id, DiagramJob.board_id == board_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"job_id": job.id, "status": job.status, "stage": job.stage, "error": job.error, "srs_id": job.srs_id}


@router.get("")
def list_for_srs(board_id: int, srs_id: int | None = None, db: Session = Depends(get_db),
                 current_user=Depends(get_current_user)):
    get_owned_board(db, board_id, current_user)
    doc = _get_srs(db, board_id, srs_id)
    return {"srs_id": doc.id, "version": doc.version, "diagrams": diagram_service.list_diagrams(db, doc.id)}
