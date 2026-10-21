"""Issue #9 routes. Thin on purpose: access check, call the service, log, return.
Roles: viewers read; editors change activities; project managers/admins manage money."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_board_and_role, get_owned_board
from app.routes.auth import get_current_user
from app.schemas.gantt import (ActivityCreate, ActivityUpdate, BudgetUpdate, IncrementCreate,
                               IncrementUpdate, SeedRequest)
from app.services import gantt_service as S
from app.services.activity_service import log_activity

router = APIRouter(prefix="/boards/{board_id}", tags=["Gantt and finance"])


@router.get("/gantt")
def get_gantt(board_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    _, role = get_board_and_role(db, board_id, current_user, "viewer")
    return S.payload(db, board_id, role)


# ---- activities
@router.post("/activities", status_code=201)
def add_activity(board_id: int, body: ActivityCreate, db: Session = Depends(get_db),
                 current_user=Depends(get_current_user)):
    get_owned_board(db, board_id, current_user, "editor")
    a = S.create_activity(db, board_id, body)
    log_activity(db, board_id, current_user.id, "gantt.activity_created", f"added the activity “{a.name}”", "activity", a.id)
    return {"id": a.id}


@router.patch("/activities/{activity_id}")
def edit_activity(board_id: int, activity_id: int, body: ActivityUpdate, db: Session = Depends(get_db),
                  current_user=Depends(get_current_user)):
    get_owned_board(db, board_id, current_user, "editor")
    a = S.update_activity(db, board_id, activity_id, body)
    log_activity(db, board_id, current_user.id, "gantt.activity_updated", f"updated the activity “{a.name}”", "activity", a.id)
    return {"id": a.id}


@router.delete("/activities/{activity_id}", status_code=204)
def remove_activity(board_id: int, activity_id: int, db: Session = Depends(get_db),
                    current_user=Depends(get_current_user)):
    get_owned_board(db, board_id, current_user, "editor")
    S.delete_activity(db, board_id, activity_id)
    log_activity(db, board_id, current_user.id, "gantt.activity_deleted", "deleted an activity", "activity", activity_id)


@router.post("/activities/seed")
def seed(board_id: int, body: SeedRequest, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    get_owned_board(db, board_id, current_user, "project_manager")
    result = S.seed_from_board(db, board_id, body.mode)
    log_activity(db, board_id, current_user.id, "gantt.seeded", f"generated the Gantt activities from the board ({body.mode})", "board", board_id)
    return result


# ---- finance
@router.put("/budget")
def put_budget(board_id: int, body: BudgetUpdate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    get_owned_board(db, board_id, current_user, "project_manager")
    value = S.set_base_budget(db, board_id, body)
    log_activity(db, board_id, current_user.id, "finance.budget_set", "set the base budget", "board", board_id)
    return {"base_budget": str(value)}


@router.post("/finance-increments", status_code=201)
def add_increment(board_id: int, body: IncrementCreate, db: Session = Depends(get_db),
                  current_user=Depends(get_current_user)):
    get_owned_board(db, board_id, current_user, "project_manager")
    i = S.create_increment(db, board_id, body)
    log_activity(db, board_id, current_user.id, "finance.increment_created", f"added a {i.status} finance increment", "increment", i.id)
    return S.increment_out(i)


@router.patch("/finance-increments/{inc_id}")
def edit_increment(board_id: int, inc_id: int, body: IncrementUpdate, db: Session = Depends(get_db),
                   current_user=Depends(get_current_user)):
    get_owned_board(db, board_id, current_user, "project_manager")
    i = S.update_increment(db, board_id, inc_id, body)
    log_activity(db, board_id, current_user.id, "finance.increment_updated", f"updated a finance increment (now {i.status})", "increment", i.id)
    return S.increment_out(i)


@router.delete("/finance-increments/{inc_id}", status_code=204)
def remove_increment(board_id: int, inc_id: int, db: Session = Depends(get_db),
                     current_user=Depends(get_current_user)):
    get_owned_board(db, board_id, current_user, "project_manager")
    S.delete_increment(db, board_id, inc_id)
    log_activity(db, board_id, current_user.id, "finance.increment_deleted", "deleted a finance increment", "increment", inc_id)
