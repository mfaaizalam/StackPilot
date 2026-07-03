from fastapi import APIRouter,HTTPException,Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.chat import ChatResponse,ChatRequest
from app.routes.auth import get_current_user
from app.services.chat_service import save_message
from app.services.gemini_chat_service import ask_ai
router = APIRouter(
    prefix="/boards",
    tags=["Chat"]
)

@router.post(
    "/{board_id}/chat",
    response_model=ChatResponse
)
def chat(
    board_id: int,
    request: ChatRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    try:
        ai_response = ask_ai(
            db=db,
            board_id=board_id,
            user_id=current_user.id,
            user_message=request.message
        )

        return ChatResponse(
            role="assistant",
            message=ai_response
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )