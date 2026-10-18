from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import accessible_board_ids, get_owned_board, get_owned_column
from app.models.column import BoardColumn
from app.routes.auth import get_current_user
from app.schemas.column import ColumnCreate
from app.services.activity_service import log_activity

router = APIRouter(
    prefix="/columns",
    tags=["Columns"]
)


# Create (editor and above)
@router.post("/")
def create_column(
    column: ColumnCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    get_owned_board(db, column.board_id, current_user, "editor")
    new_column = BoardColumn(name=column.name, board_id=column.board_id)
    db.add(new_column)
    db.commit()
    db.refresh(new_column)
    log_activity(db, new_column.board_id, current_user.id, "column.created",
                 f"added the column “{new_column.name}”", "column", new_column.id)
    return new_column


# Read: columns of every board I belong to
@router.get("/")
def get_columns(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    ids = accessible_board_ids(db, current_user)
    if not ids:
        return []
    return db.query(BoardColumn).filter(BoardColumn.board_id.in_(ids)).all()


@router.get("/{column_id}")
def get_column(
    column_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    return get_owned_column(db, column_id, current_user, "viewer")


@router.put("/{column_id}")
def update_column(
    column_id: int,
    column_data: ColumnCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    column = get_owned_column(db, column_id, current_user, "editor")
    # moving a column to another board also needs editor rights on that board
    get_owned_board(db, column_data.board_id, current_user, "editor")
    old_name, board_id = column.name, column.board_id
    column.name = column_data.name
    column.board_id = column_data.board_id
    db.commit()
    db.refresh(column)
    if old_name != column.name:
        log_activity(db, board_id, current_user.id, "column.updated",
                     f"renamed the column “{old_name}” to “{column.name}”", "column", column.id)
    return column


# Deleting a column also deletes its tasks, so it needs project_manager
@router.delete("/{column_id}")
def delete_column(
    column_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    column = get_owned_column(db, column_id, current_user, "project_manager")
    board_id, name, cid = column.board_id, column.name, column.id
    db.delete(column)
    db.commit()
    log_activity(db, board_id, current_user.id, "column.deleted",
                 f"deleted the column “{name}”", "column", cid)
    return {"message": "Column deleted successfully"}