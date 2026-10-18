from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_owned_board, get_owned_task
from app.routes.auth import get_current_user
from app.schemas.board_gen import GenerateBoardRequest
from app.services import board_service
from app.services.activity_service import log_activity

router = APIRouter(prefix="/boards/{board_id}", tags=["SRS to Kanban"])


@router.post("/srs/generate-board")
def generate_board(board_id: int, body: GenerateBoardRequest, background: BackgroundTasks,
                   db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    """Deterministic (no AI, milliseconds), so it runs inside the request instead of a job."""
    get_owned_board(db, board_id, current_user, "project_manager")
    result = board_service.generate_board(db, board_id, current_user.id, body.srs_id, body.mode, body.include_nfr)
    background.add_task(board_service.index_tasks, result.pop("_new_task_ids"), result.pop("_removed_task_ids"))
    log_activity(db, board_id, current_user.id, "board.generated", f"generated the Kanban board from the SRS ({body.mode})", "board", board_id)
    return result


@router.get("/tasks/{task_id}/trace")
def task_trace(board_id: int, task_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    get_owned_board(db, board_id, current_user, "viewer")
    task = get_owned_task(db, task_id, current_user, "viewer")
    if task.column.board_id != board_id:  # task exists but belongs to another of the user's boards
        raise HTTPException(status_code=404, detail="Task not found")
    return board_service.task_trace(db, board_id, task)