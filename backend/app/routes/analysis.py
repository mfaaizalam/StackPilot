from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.routes.auth import get_current_user
from app.schemas.analysis import ProjectInsightsResponse
from app.services.analysis_service import analyze_project
from app.core.deps import get_owned_board

router = APIRouter(
    prefix="/boards",
    tags=["Analysis"]
)


@router.get(
    "/{board_id}/analyze",
    response_model=ProjectInsightsResponse
)
def analyze_board(
    board_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    get_owned_board(db, board_id, current_user)
    try:
        return analyze_project(db=db, board_id=board_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Project analysis is temporarily unavailable. Please try again.")
