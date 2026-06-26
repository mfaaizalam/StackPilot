from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.column import BoardColumn
from app.models.board import Board
from app.schemas.column import ColumnCreate

router = APIRouter(
    prefix="/columns",
    tags =["Columns"]
)

# Create 
@router.post("/")
def create_column(
    column:ColumnCreate,
    db:Session =Depends(get_db)
):
    board= (
        db.query(Board).filter(Board.id ==column.board_id ).first()
    )
    if not board:
        raise HTTPException(
            status_code=404,
            detail="Board not found"
        )
    new_column = BoardColumn(
        name = column.name,
        board_id = column.board_id
    )
    db.add(new_column)
    db.commit()
    db.refresh(new_column)
    return new_column


#read 
@router.get("/")
def get_columns(
    db: Session = Depends(get_db)
):
    return db.query(BoardColumn).all()

@router.get('/{column_id}')
def get_column(
    column_id:int,
    db:Session =Depends(get_db)
):
    column =(
        db.query(BoardColumn).filter(BoardColumn.id ==column_id).first()

    )
    if not column :
        raise HTTPException(
            status_code=404,
            detail="Column not found"
        )
    return column

@router.put("/{column_id}")
def update_column(
    column_id : int,
    column_data:ColumnCreate,
    db:Session =Depends(get_db)
):
    column = (
        db.query(BoardColumn).filter(BoardColumn.id == column_id).first()
    )
    if not column:
        raise HTTPException(
            status_code=404,
            detail="Column not found"
        )
    column.name = column_data.name
    column.board_id = column_data.board_id
    db.commit()
    db.refresh(column)

    return column

@router.delete("/{column_id}")
def delete_column(
    column_id:int,
    db:Session = Depends(get_db)
):
    column = (
        db.query(BoardColumn).filter(BoardColumn.id==column_id).first()
    )
    if not column:
        raise HTTPException(
            status_code=404,
            detail="column not found"
        )
    db.delete(column)
    db.commit()
    return {
        "message":"Column deleted successfully"
    }