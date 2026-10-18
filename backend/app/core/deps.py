"""Shared ownership checks. Every route that touches a board, column or task
must go through one of these so users can only reach their own data."""
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.board import Board
from app.models.column import BoardColumn
from app.models.task import Task


def get_owned_board(db: Session, board_id: int, user) -> Board:
    board = db.query(Board).filter(Board.id == board_id, Board.owner_id == user.id).first()
    if not board:
        # 404 (not 403) so we don't reveal that another user's board exists
        raise HTTPException(status_code=404, detail="Board not found")
    return board


def get_owned_column(db: Session, column_id: int, user) -> BoardColumn:
    column = (
        db.query(BoardColumn)
        .join(Board, Board.id == BoardColumn.board_id)
        .filter(BoardColumn.id == column_id, Board.owner_id == user.id)
        .first()
    )
    if not column:
        raise HTTPException(status_code=404, detail="Column not found")
    return column


def get_owned_task(db: Session, task_id: int, user) -> Task:
    task = (
        db.query(Task)
        .join(BoardColumn, BoardColumn.id == Task.column_id)
        .join(Board, Board.id == BoardColumn.board_id)
        .filter(Task.id == task_id, Board.owner_id == user.id)
        .first()
    )
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task
