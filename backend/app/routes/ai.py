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
    request:ProjectGenerateRequest
):
    try:
        project = generate_project(
            project_name=request.project_name,
            requirements=request.requirements,
            project_type=request.project_type
        )
        return project
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

@router.post("/save-project")
def save_project_route(
    request: SaveProjectRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:

        result = save_project(
            db=db,
            data=request,
            user_id=current_user.id      # Temporary
        )

        return result

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )