from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.chat import ChatResponse, ChatRequest
from app.routes.auth import get_current_user
from app.services.gemini_chat_service import ask_ai
from app.core.deps import get_owned_board

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
    get_owned_board(db, board_id, current_user)
    try:
        result = ask_ai(
            db=db,
            board_id=board_id,
            user_id=current_user.id,
            user_message=request.message,
            pending_tasks=request.pending_tasks
        )

        return ChatResponse(
            role="assistant",
            message=result["message"],
            action=result["action"]
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail="Chat assistance is temporarily unavailable. Please try again."
        )