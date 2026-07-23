from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.board import Board
from app.schemas.board import BoardCreate
from app.routes.auth import get_current_user
router = APIRouter(prefix="/boards",tags = ["Boards"])

# Create
@router.post("/")
def create_board(
    board:BoardCreate,
    db:Session =Depends(get_db),
    current_user = Depends(get_current_user)
):
    new_board =Board(
        name = board.name,
        description=board.description,
        owner_id=current_user.id
    )
    db.add(new_board)
    db.commit()
    db.refresh(new_board)
    return new_board
# Readb all board
@router.get("/")
def get_boards(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    boards = (
        db.query(Board)
        .filter(Board.owner_id == current_user.id)
        .all()
    )
    return boards

# Read Single Board
@router.get("/{board_id}")
def get_board(
    board_id: int,
    db: Session = Depends(get_db)
):
    board = (
        db.query(Board)
        .filter(Board.id == board_id)
        .first()
    )

    if not board:
        raise HTTPException(
            status_code=404,
            detail="Board not found"
        )

    return board

# Upade boared
@router.put("/{board_id}")
def update_board(
    board_id:int,
    board_data:BoardCreate,
    db: Session = Depends(get_db)
):
    board = (
        db.query(Board).filter(Board.id == board_id).first()
    )
    if not board:
        raise HTTPException(
            status_code=404,
            detail="Board not Found"
        )
    board.name = board_data.name
    board.description = board_data.description
    db.commit()
    db.refresh(board)
    return board

@router.delete("/{board_id}")
def delete_board(
     board_id: int,
     db: Session = Depends(get_db)
):
    board = (
        db.query(Board)
        .filter(Board.id == board_id)
        .first()
    )
    if not board:
        raise HTTPException(
            status_code=404,
            detail="Board not found"
        )
    db.delete(board)
    db.commit()

    return {
        "message": "Board deleted successfully"
    }