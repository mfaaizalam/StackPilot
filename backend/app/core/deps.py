"""Shared access checks. Every route that touches a board, column or task must go
through one of these, so users only reach boards they belong to AND only do what
their role allows.

Roles (low -> high): viewer < editor < project_manager < admin.
Rules:
  * not a member            -> 404 (never reveal that the board exists)
  * member, role too low    -> 403 (so the UI can say "you don't have permission")
  * the board owner (boards.owner_id) is always admin.

The function names are unchanged (get_owned_*) but they now take a `min_role`.
The default is "admin" on purpose: a route you forgot to update fails closed.
"""
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.board import Board
from app.models.column import BoardColumn
from app.models.rbac import BoardMember
from app.models.task import Task

ROLE_RANK = {"viewer": 1, "editor": 2, "project_manager": 3, "admin": 4}
ASSIGNABLE_ROLES = ("project_manager", "editor", "viewer")  # "admin" is never invited


def role_can(role: str | None, min_role: str) -> bool:
    return ROLE_RANK.get(role or "", 0) >= ROLE_RANK[min_role]


def _role_in_board(db: Session, board: Board, user) -> str | None:
    """The user's role on this board, or None if they are not a member."""
    if board.owner_id == user.id:
        # The owner is always admin. Also self-heals boards created before RBAC
        # existed (no board_members row yet) so nobody is ever locked out.
        if not db.query(BoardMember.id).filter_by(board_id=board.id, user_id=user.id).first():
            try:
                db.add(BoardMember(board_id=board.id, user_id=user.id, role="admin"))
                db.commit()
            except IntegrityError:  # two requests healed at once: fine
                db.rollback()
        return "admin"
    m = db.query(BoardMember).filter_by(board_id=board.id, user_id=user.id).first()
    return m.role if m else None


def get_board_and_role(db: Session, board_id: int, user, min_role: str = "admin") -> tuple[Board, str]:
    board = db.get(Board, board_id)
    role = _role_in_board(db, board, user) if board else None
    if role is None:
        raise HTTPException(status_code=404, detail="Board not found")
    if not role_can(role, min_role):
        raise HTTPException(status_code=403, detail="Your role does not allow this action")
    return board, role


def get_owned_board(db: Session, board_id: int, user, min_role: str = "admin") -> Board:
    return get_board_and_role(db, board_id, user, min_role)[0]


def get_owned_column(db: Session, column_id: int, user, min_role: str = "admin") -> BoardColumn:
    column = db.get(BoardColumn, column_id)
    if not column:
        raise HTTPException(status_code=404, detail="Column not found")
    try:
        get_board_and_role(db, column.board_id, user, min_role)
    except HTTPException as e:
        if e.status_code == 404:
            raise HTTPException(status_code=404, detail="Column not found")
        raise
    return column


def get_owned_task(db: Session, task_id: int, user, min_role: str = "admin") -> Task:
    task = db.get(Task, task_id)
    if not task or not task.column:
        raise HTTPException(status_code=404, detail="Task not found")
    try:
        get_board_and_role(db, task.column.board_id, user, min_role)
    except HTTPException as e:
        if e.status_code == 404:
            raise HTTPException(status_code=404, detail="Task not found")
        raise
    return task


def accessible_boards(db: Session, user) -> list[tuple[Board, str]]:
    """Every board the user belongs to (or owns), with their role."""
    out: dict[int, tuple[Board, str]] = {}
    rows = (db.query(Board, BoardMember.role)
              .join(BoardMember, BoardMember.board_id == Board.id)
              .filter(BoardMember.user_id == user.id).all())
    for b, role in rows:
        out[b.id] = (b, "admin" if b.owner_id == user.id else role)
    for b in db.query(Board).filter(Board.owner_id == user.id).all():
        out.setdefault(b.id, (b, "admin"))
    return sorted(out.values(), key=lambda x: x[0].id)


def accessible_board_ids(db: Session, user) -> list[int]:
    return [b.id for b, _ in accessible_boards(db, user)]