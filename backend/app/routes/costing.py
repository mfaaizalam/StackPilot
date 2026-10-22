"""Issue #7 routes: expense lines for the Costing tab. Money = project_manager and above.
Reading everything (activities, increments, expenses, categories, alerts) is GET /boards/{id}/gantt."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_owned_board
from app.routes.auth import get_current_user
from app.schemas.expense import ExpenseCreate, ExpenseUpdate
from app.services import costing_service as S
from app.services import gantt_service as G
from app.services.activity_service import log_activity

router = APIRouter(prefix="/boards/{board_id}/expenses", tags=["Costing"])


@router.post("", status_code=201)
def add_expense(board_id: int, body: ExpenseCreate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    get_owned_board(db, board_id, current_user, "project_manager")
    e = S.create_expense(db, board_id, body)
    log_activity(db, board_id, current_user.id, "cost.expense_created", f"added an expense “{e.description[:60]}”", "expense", e.id)
    return G.expense_out(e)


@router.patch("/{expense_id}")
def edit_expense(board_id: int, expense_id: int, body: ExpenseUpdate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    get_owned_board(db, board_id, current_user, "project_manager")
    e = S.update_expense(db, board_id, expense_id, body)
    log_activity(db, board_id, current_user.id, "cost.expense_updated", f"updated an expense “{e.description[:60]}”", "expense", e.id)
    return G.expense_out(e)


@router.delete("/{expense_id}", status_code=204)
def remove_expense(board_id: int, expense_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    get_owned_board(db, board_id, current_user, "project_manager")
    S.delete_expense(db, board_id, expense_id)
    log_activity(db, board_id, current_user.id, "cost.expense_deleted", "deleted an expense", "expense", expense_id)
