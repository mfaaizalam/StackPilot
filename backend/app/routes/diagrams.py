from datetime import datetime, timedelta

import base64
import re
import xml.etree.ElementTree as ET

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_owned_board
from app.models.srs import DiagramJob, SRSDocument
from app.routes.auth import get_current_user
from app.schemas.diagrams import DIAGRAM_TYPES, DiagramGenerateRequest
from app.models.srs import Diagram
from app.services import diagram_service
from app.services.diagram_drawio import to_model, to_mxfile
from app.services.diagram_render import to_png
from app.services.activity_service import log_activity

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
    get_owned_board(db, board_id, current_user, "project_manager")
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
    log_activity(db, board_id, current_user.id, "diagrams.generated", "started generating UML diagrams", "diagram_job")
    return {"job_id": job.id, "srs_id": doc.id}


@router.get("/jobs/{job_id}")
def job_status(board_id: int, job_id: str, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    get_owned_board(db, board_id, current_user, "viewer")
    job = db.query(DiagramJob).filter(DiagramJob.id == job_id, DiagramJob.board_id == board_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"job_id": job.id, "status": job.status, "stage": job.stage, "error": job.error, "srs_id": job.srs_id}


@router.get("")
def list_for_srs(board_id: int, srs_id: int | None = None, db: Session = Depends(get_db),
                 current_user=Depends(get_current_user)):
    get_owned_board(db, board_id, current_user, "viewer")
    doc = _get_srs(db, board_id, srs_id)
    return {"srs_id": doc.id, "version": doc.version, "diagrams": diagram_service.list_diagrams(db, doc.id)}


# ------------------------------------------------------------------ exports
def _combined(figs: list[dict]) -> str:
    """One .drawio with a page per diagram; a diagram edited in the app keeps the user's edited pages."""
    pages = []
    for i, f in enumerate(figs, start=1):
        src = f.get("xml")
        if src:
            try:
                root = ET.fromstring(src)
                for dg in root.iter("diagram"):
                    dg.set("name", f["title"][:60])
                    dg.set("id", f"sp-{i}")
                    pages.append(ET.tostring(dg, encoding="unicode"))
                    break
                else:
                    raise ValueError("no page")
                continue
            except Exception:
                pass
        pages.append(re.search(r"<diagram .*</diagram>", to_mxfile([f["scene"]]), re.S).group(0).replace('id="sp-1"', f'id="sp-{i}"', 1))
        pages[-1] = re.sub(r'name="[^"]*"', 'name="' + f["title"][:60].replace('"', "'").replace("&", "and").replace("<", "") + '"', pages[-1], count=1)
    return f'<mxfile host="app.diagrams.net" agent="StackPilot" type="device">{"".join(pages)}</mxfile>'


def _safe(name: str, fallback: str = "diagrams") -> str:
    return "".join(c if c.isalnum() else "_" for c in (name or ""))[:60].strip("_") or fallback


@router.get("/export.drawio")
def export_all_drawio(board_id: int, srs_id: int | None = None, db: Session = Depends(get_db),
                      current_user=Depends(get_current_user)):
    """Every diagram of the SRS in ONE draw.io file (one page per diagram). Opens in app.diagrams.net or the
    draw.io desktop app; all shapes are native draw.io shapes, so everything can be edited."""
    board = get_owned_board(db, board_id, current_user, "viewer")
    doc = _get_srs(db, board_id, srs_id)
    figs = diagram_service.figures(db, doc.id)
    if not figs:
        raise HTTPException(status_code=404, detail="No diagrams have been generated yet.")
    xml = _combined(figs)
    return Response(xml, media_type="application/vnd.jgraph.mxfile",
                    headers={"Content-Disposition": f'attachment; filename="Diagrams_{_safe(board.name)}_v{doc.version}.drawio"'})


def _one(db: Session, board_id: int, diagram_id: int) -> tuple[Diagram, object]:
    row = (db.query(Diagram).join(SRSDocument, SRSDocument.id == Diagram.srs_id)
           .filter(Diagram.id == diagram_id, SRSDocument.board_id == board_id).first())
    sc = diagram_service.row_scene(row) if row else None
    if not row or not sc:
        raise HTTPException(status_code=404, detail="Diagram not found")
    return row, sc


@router.get("/{diagram_id}/export.drawio")
def export_drawio(board_id: int, diagram_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    get_owned_board(db, board_id, current_user, "viewer")
    row, sc = _one(db, board_id, diagram_id)
    ed = (row.model or {}).get("edited") or {}
    return Response(ed.get("xml") or to_mxfile([sc]), media_type="application/vnd.jgraph.mxfile",
                    headers={"Content-Disposition": f'attachment; filename="{_safe(row.title, "diagram")}.drawio"'})


@router.get("/{diagram_id}/export.png")
def export_png(board_id: int, diagram_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    """PNG that also carries its draw.io source: drag it into draw.io to edit it again."""
    get_owned_board(db, board_id, current_user, "viewer")
    row, sc = _one(db, board_id, diagram_id)
    ed = (row.model or {}).get("edited") or {}
    png = base64.b64decode(ed["png"]) if ed.get("png") else to_png(sc, to_model(sc))
    return Response(png, media_type="image/png",
                    headers={"Content-Disposition": f'attachment; filename="{_safe(row.title, "diagram")}.png"'})



# ------------------------------------------------------- in-app draw.io editing
class DrawioSave(BaseModel):
    xml: str
    png: str | None = None  # base64 PNG exported by the editor (used in the Word documents)


@router.get("/{diagram_id}/drawio")
def get_drawio(board_id: int, diagram_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    """The diagram as draw.io XML for the in-app editor: the user's saved version, else the generated one."""
    get_owned_board(db, board_id, current_user, "viewer")
    row, sc = _one(db, board_id, diagram_id)
    ed = (row.model or {}).get("edited") or {}
    return {"xml": ed.get("xml") or to_mxfile([sc]), "edited": bool(ed)}


@router.put("/{diagram_id}/drawio")
def save_drawio(board_id: int, diagram_id: int, body: DrawioSave, db: Session = Depends(get_db),
                current_user=Depends(get_current_user)):
    get_owned_board(db, board_id, current_user, "editor")
    row, _ = _one(db, board_id, diagram_id)
    if len(body.xml) > 3_000_000 or not re.match(r"\s*<(\?xml[^>]*\?>\s*)?<?(mxfile|mxGraphModel)", body.xml):
        raise HTTPException(status_code=422, detail="That is not a valid draw.io diagram.")
    try:
        ET.fromstring(body.xml)
    except ET.ParseError:
        raise HTTPException(status_code=422, detail="The diagram file is damaged.")
    png = None
    if body.png:
        png = body.png.split(",", 1)[-1]
        if len(png) > 8_000_000:
            raise HTTPException(status_code=413, detail="The diagram image is too large.")
        try:
            base64.b64decode(png, validate=True)
        except Exception:
            raise HTTPException(status_code=422, detail="The diagram image is damaged.")
    row.model = {**(row.model or {}), "edited": {"xml": body.xml, "png": png}}
    row.stale = False
    db.commit()
    return {"ok": True}


@router.delete("/{diagram_id}/drawio")
def reset_drawio(board_id: int, diagram_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    """Throw away the manual edits and go back to the generated diagram."""
    get_owned_board(db, board_id, current_user, "editor")
    row, _ = _one(db, board_id, diagram_id)
    m = dict(row.model or {})
    m.pop("edited", None)
    row.model = m
    db.commit()
    return {"ok": True}
