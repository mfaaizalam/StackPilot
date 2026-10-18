from fastapi import APIRouter,HTTPException

from app.schemas.ai import (
    ProjectGenerateResponse,
    ProjectGenerateRequest,
)
from app.services.gemini_services import generate_project
from sqlalchemy.orm import Session
from app.core.database import get_db
from fastapi import Depends
from app.schemas.ai_save import SaveProjectRequest
from app.services.ai_save_service import save_project
from app.routes.auth import get_current_user
from app.models.user import User
from app.core.deps import get_owned_board
router = APIRouter(
    prefix="/ai",
    tags=["AI"]
)
# Generate Route
@router.post(
    "/generate-project",
    response_model=ProjectGenerateResponse
)
def generate_project_route(
    request:ProjectGenerateRequest,
    current_user: User = Depends(get_current_user)
):
    try:
        project = generate_project(
            project_name=request.project_name,
            requirements=request.requirements,
            project_type=request.project_type
        )
        return project
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail="AI generation is temporarily unavailable. Please try again or load an offline demo."
        )

@router.post("/boards/{board_id}/save-project")
def save_project_route(
    board_id: int,
    request: SaveProjectRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    get_owned_board(db, board_id, current_user)
    try:

        result = save_project(
        db=db,
        board_id=board_id,
        data=request,
        user_id=current_user.id
        )

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail="The project could not be saved. Please try again."
        )