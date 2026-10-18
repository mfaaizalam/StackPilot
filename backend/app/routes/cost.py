from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_owned_board
from app.models.srs import CostEstimate
from app.routes.auth import get_current_user
from app.schemas.cost import CostRequest
from app.services import cost_service
from app.services.cost_rates import RatesError, load_rates, unverified_items

router = APIRouter(prefix="/boards/{board_id}/srs/cost", tags=["Cost estimation"])


def _get_row(db: Session, board_id: int, estimate_id: int) -> CostEstimate:
    row = db.query(CostEstimate).filter(CostEstimate.id == estimate_id, CostEstimate.board_id == board_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Estimate not found")
    return row


@router.get("/rates")
def rates(board_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    """The rate table the engine uses (shown in the UI so assumptions are visible)."""
    get_owned_board(db, board_id, current_user)
    try:
        t = load_rates()
    except RatesError as e:
        raise HTTPException(status_code=503, detail=str(e))
    return {**t.model_dump(), "unverified_items": unverified_items(t)}


@router.post("/estimate")
def estimate(board_id: int, body: CostRequest, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    """Deterministic and instant (no AI), so it runs inside the request."""
    get_owned_board(db, board_id, current_user)
    return cost_service.create_estimate(db, board_id, current_user.id, body)


@router.get("/")
def latest(board_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    get_owned_board(db, board_id, current_user)
    row = (db.query(CostEstimate).filter(CostEstimate.board_id == board_id)
           .order_by(CostEstimate.id.desc()).first())
    if not row:
        raise HTTPException(status_code=404, detail="No cost estimate has been made for this board yet.")
    return cost_service.row_out(db, row)


@router.post("/{estimate_id}/explain")
def explain(board_id: int, estimate_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    get_owned_board(db, board_id, current_user)
    return cost_service.explain(db, _get_row(db, board_id, estimate_id), current_user.id)
