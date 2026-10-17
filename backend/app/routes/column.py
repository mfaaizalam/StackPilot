from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.column import BoardColumn
from app.models.board import Board
from app.schemas.column import ColumnCreate
from app.routes.auth import get_current_user
from app.core.deps import get_owned_board, get_owned_column

router = APIRouter(
    prefix="/columns",
    tags =["Columns"]
)

# Create 
@router.post("/")
def create_column(
    column:ColumnCreate,
    db:Session =Depends(get_db),
    current_user = Depends(get_current_user)
):
    board = get_owned_board(db, column.board_id, current_user)
    new_column = BoardColumn(
        name = column.name,
        board_id = column.board_id
    )
    db.add(new_column)
    db.commit()
    db.refresh(new_column)
    return new_column


#read 
#read 
@router.get("/")
def get_columns(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    column = db.query(BoardColumn).filter(BoardColumn.board.has(owner_id=current_user.id)).all()
    return column 

@router.get('/{column_id}')
def get_column(
    column_id:int,
    db:Session =Depends(get_db),
    current_user = Depends(get_current_user)
):
    return get_owned_column(db, column_id, current_user)

@router.put("/{column_id}")
def update_column(
    column_id : int,
    column_data:ColumnCreate,
    db:Session =Depends(get_db),
    current_user = Depends(get_current_user)
):
    column = get_owned_column(db, column_id, current_user)
    # moving a column to another board also requires owning that board
    get_owned_board(db, column_data.board_id, current_user)
    column.name = column_data.name
    column.board_id = column_data.board_id
    db.commit()
    db.refresh(column)

    return column

@router.delete("/{column_id}")
def delete_column(
    column_id:int,
    db:Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    column = get_owned_column(db, column_id, current_user)
    db.delete(column)
    db.commit()
    return {
        "message":"Column deleted successfully"
    }