from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import accessible_boards, get_board_and_role, get_owned_board
from app.models.board import Board
from app.models.rbac import BoardMember
from app.routes.auth import get_current_user
from app.schemas.board import BoardCreate
from app.services.activity_service import log_activity

router = APIRouter(prefix="/boards", tags=["Boards"])


def _out(board: Board, role: str) -> dict:
    return {"id": board.id, "name": board.name, "description": board.description,
            "owner_id": board.owner_id, "my_role": role}


# Create: the creator becomes the project admin
@router.post("/")
def create_board(
    board: BoardCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    new_board = Board(name=board.name, description=board.description, owner_id=current_user.id)
    db.add(new_board)
    db.flush()  # get new_board.id
    db.add(BoardMember(board_id=new_board.id, user_id=current_user.id, role="admin"))
    db.commit()
    db.refresh(new_board)
    log_activity(db, new_board.id, current_user.id, "board.created", f"created the project “{new_board.name}”",
                 "board", new_board.id)
    return _out(new_board, "admin")


# Read all boards I belong to (owned + shared), each with my role
@router.get("/")
def get_boards(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return [_out(b, role) for b, role in accessible_boards(db, current_user)]


# Read single board
@router.get("/{board_id}")
def get_board(
    board_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    board, role = get_board_and_role(db, board_id, current_user, "viewer")
    return _out(board, role)


# Rename / edit board (admin only)
@router.put("/{board_id}")
def update_board(
    board_id: int,
    board_data: BoardCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    board = get_owned_board(db, board_id, current_user, "admin")
    board.name = board_data.name
    board.description = board_data.description
    db.commit()
    db.refresh(board)
    log_activity(db, board.id, current_user.id, "board.updated", f"renamed the project to “{board.name}”",
                 "board", board.id)
    return _out(board, "admin")


# Delete board (admin only; project managers and editors cannot)
@router.delete("/{board_id}")
def delete_board(
    board_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    board = get_owned_board(db, board_id, current_user, "admin")
    db.delete(board)
    db.commit()
    return {"message": "Board deleted successfully"}