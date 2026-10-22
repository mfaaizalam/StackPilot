"""Issue #7: expense CRUD. Every lookup filters by board_id, so an id from another board is a 404."""
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.expense import Expense
from app.models.gantt import Activity
from app.schemas.expense import ExpenseCreate, ExpenseUpdate


def _check_activity(db: Session, board_id: int, activity_id: int | None) -> None:
    if activity_id is not None and not db.query(Activity.id).filter(
            Activity.id == activity_id, Activity.board_id == board_id).first():
        raise HTTPException(status_code=404, detail="Activity not found")


def _get(db: Session, board_id: int, expense_id: int) -> Expense:
    e = db.query(Expense).filter(Expense.id == expense_id, Expense.board_id == board_id).first()
    if not e:
        raise HTTPException(status_code=404, detail="Expense not found")
    return e


def create_expense(db: Session, board_id: int, body: ExpenseCreate) -> Expense:
    _check_activity(db, board_id, body.activity_id)
    e = Expense(board_id=board_id, **body.model_dump())
    db.add(e)
    db.commit()
    db.refresh(e)
    return e


def update_expense(db: Session, board_id: int, expense_id: int, body: ExpenseUpdate) -> Expense:
    e = _get(db, board_id, expense_id)
    data = body.model_dump(exclude_unset=True)
    clear = data.pop("clear_activity", False)
    for k in ("category", "description", "estimated_amount", "actual_amount"):
        if k in data and data[k] is None:
            raise HTTPException(status_code=422, detail=f"{k} cannot be empty.")
    if "activity_id" in data:
        _check_activity(db, board_id, data["activity_id"])
    if clear:
        data["activity_id"] = None
    for k, v in data.items():
        setattr(e, k, v)
    db.commit()
    db.refresh(e)
    return e


def delete_expense(db: Session, board_id: int, expense_id: int) -> None:
    db.delete(_get(db, board_id, expense_id))
    db.commit()
