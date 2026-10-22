"""Database side of Issue #9. Maths lives in gantt_calculator.py; routes stay thin.

Every function takes a `board_id` and filters by it, so an id from another board is
a 404, never a leak. Money leaves this module as strings (no float drift in JSON)."""
from datetime import date
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.column import BoardColumn
from app.models.expense import Expense
from app.models.gantt import Activity, BoardBudget, FinanceIncrement
from app.models.srs import CostEstimate
from app.models.task import Task
from app.schemas.gantt import (ActivityCreate, ActivityUpdate, BudgetUpdate, IncrementCreate,
                               IncrementUpdate)
from app.services import costing_calculator as K
from app.services import gantt_calculator as C

D = Decimal


# ---------------------------------------------------------------- serialisers
def _s(v) -> str | None:
    return None if v is None else str(C.q2(C.dec(v)))


def activity_out(a: Activity, metrics: dict, conflicts: list[int]) -> dict:
    m = dict(metrics)
    m["cost_variance"] = _s(m["cost_variance"])
    m["hours_variance"] = _s(m["hours_variance"])
    flags = list(m["flags"]) + (["dependency_conflict"] if conflicts else [])
    return {"id": a.id, "task_id": a.task_id, "name": a.name, "phase": a.phase,
            "start_date": a.start_date.isoformat(), "end_date": a.end_date.isoformat(),
            "planned_hours": _s(a.planned_hours), "actual_hours": _s(a.actual_hours),
            "progress_pct": a.progress_pct, "estimated_cost": _s(a.estimated_cost),
            "actual_cost": _s(a.actual_cost), "depends_on": list(a.depends_on or []),
            "position": a.position, "conflicting_dependencies": conflicts,
            "cost_source": getattr(a, "cost_source", "manual"), "expense_count": getattr(a, "expense_count", 0),
            **m, "flags": flags}


def increment_out(i: FinanceIncrement) -> dict:
    return {"id": i.id, "activity_id": i.activity_id, "phase": i.phase, "amount": _s(i.amount),
            "effective_date": i.effective_date.isoformat(), "status": i.status, "note": i.note}


def _money_dict(d: dict, skip=()) -> dict:
    out = {}
    for k, v in d.items():
        if k in skip:
            out[k] = v
        elif isinstance(v, Decimal):
            out[k] = _s(v)
        else:
            out[k] = v
    return out


def summary_out(s: dict) -> dict:
    out = _money_dict(s, skip=("timeline", "alerts"))
    out["timeline"] = [{**t, "date": t["date"].isoformat(), "amount": _s(t["amount"]),
                        "cumulative_budget": _s(t["cumulative_budget"]),
                        "cumulative_committed": _s(t["cumulative_committed"])} for t in s["timeline"]]
    out["alerts"] = [{**a, "amount": _s(a["amount"])} for a in s["alerts"]]
    return out


# ---------------------------------------------------------------- reads
def _activities(db: Session, board_id: int) -> list[Activity]:
    return (db.query(Activity).filter(Activity.board_id == board_id)
            .order_by(Activity.position, Activity.start_date, Activity.id).all())


def _increments(db: Session, board_id: int) -> list[FinanceIncrement]:
    return (db.query(FinanceIncrement).filter(FinanceIncrement.board_id == board_id)
            .order_by(FinanceIncrement.effective_date, FinanceIncrement.id).all())


def base_budget(db: Session, board_id: int) -> Decimal:
    row = db.query(BoardBudget).filter(BoardBudget.board_id == board_id).first()
    return C.dec(row.base_budget) if row else D(0)


def expense_out(e: Expense) -> dict:
    return {"id": e.id, "activity_id": e.activity_id, "category": e.category, "description": e.description,
            "estimated_amount": _s(e.estimated_amount), "actual_amount": _s(e.actual_amount),
            "variance": _s(C.dec(e.actual_amount) - C.dec(e.estimated_amount)),
            "incurred_on": e.incurred_on.isoformat() if e.incurred_on else None}


def _expenses(db: Session, board_id: int) -> list[Expense]:
    return db.query(Expense).filter(Expense.board_id == board_id).order_by(Expense.id).all()


def payload(db: Session, board_id: int, role: str, today: date | None = None) -> dict:
    """Everything the Timeline and Costing pages need, in one round trip.
    Activity costs are the EFFECTIVE costs (expense lines when present, else the manual fields),
    so both pages always show the same totals."""
    today = today or date.today()
    raw, incs, exps = _activities(db, board_id), _increments(db, board_id), _expenses(db, board_id)
    acts, x_est, x_act, x_count = K.apply_expenses(raw, exps)
    conflicts = C.schedule_conflicts(acts)
    summary = C.finance_summary(base_budget(db, board_id), incs, acts, x_est, x_act)
    proj = C.project_summary(acts, today)
    proj_out = {**_money_dict(proj), "start_date": proj["start_date"].isoformat() if proj["start_date"] else None,
                "end_date": proj["end_date"].isoformat() if proj["end_date"] else None}
    phases = [_money_dict(p) for p in C.phase_summary(incs, acts)]
    cats = [{**_money_dict(r), "variance_pct": r["variance_pct"], "share_pct": r["share_pct"], "overrun": r["overrun"]}
            for r in K.category_breakdown(raw, exps)]
    return {"today": today.isoformat(), "role": role, "can_edit": role in ("editor", "project_manager", "admin"),
            "can_manage_finance": role in ("project_manager", "admin"),
            "project": proj_out,
            "activities": [activity_out(a, C.activity_metrics(a, today), conflicts.get(a.id, [])) for a in acts],
            "increments": [increment_out(i) for i in incs],
            "expenses": [expense_out(e) for e in exps],
            "categories": cats,
            "project_level": {"estimated": _s(x_est), "actual": _s(x_act), "count": x_count},
            "summary": summary_out(summary), "phases": phases}


# ---------------------------------------------------------------- activities
def _check_dependencies(db: Session, board_id: int, activity_id: int, deps: list[int]) -> list[int]:
    deps = list(dict.fromkeys(deps))                       # de-duplicate, keep order
    graph = {a.id: list(a.depends_on or []) for a in _activities(db, board_id)}
    graph[activity_id] = deps
    try:
        C.validate_dependencies(graph)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return deps


def _get_activity(db: Session, board_id: int, activity_id: int) -> Activity:
    a = db.query(Activity).filter(Activity.id == activity_id, Activity.board_id == board_id).first()
    if not a:
        raise HTTPException(status_code=404, detail="Activity not found")
    return a


def create_activity(db: Session, board_id: int, body: ActivityCreate) -> Activity:
    if body.task_id is not None:
        t = db.get(Task, body.task_id)
        if not t or not t.column or t.column.board_id != board_id:
            raise HTTPException(status_code=404, detail="Task not found")
    count = db.query(Activity).filter(Activity.board_id == board_id).count()
    a = Activity(board_id=board_id, position=count, depends_on=[],
                 **body.model_dump(exclude={"depends_on"}))
    db.add(a)
    db.flush()
    try:
        a.depends_on = _check_dependencies(db, board_id, a.id, body.depends_on)
        db.commit()
    except HTTPException:
        db.rollback()
        raise
    db.refresh(a)
    return a


def update_activity(db: Session, board_id: int, activity_id: int, body: ActivityUpdate) -> Activity:
    a = _get_activity(db, board_id, activity_id)
    data = body.model_dump(exclude_unset=True)
    start, end = data.get("start_date", a.start_date), data.get("end_date", a.end_date)
    if start is None or end is None or end < start:
        raise HTTPException(status_code=422, detail="End date cannot be before the start date.")
    if "depends_on" in data:
        data["depends_on"] = _check_dependencies(db, board_id, a.id, data["depends_on"] or [])
    for k in ("name", "start_date", "end_date", "planned_hours", "actual_hours", "progress_pct",
              "estimated_cost", "actual_cost"):
        if k in data and data[k] is None:
            raise HTTPException(status_code=422, detail=f"{k} cannot be empty.")
    for k, v in data.items():
        setattr(a, k, v)
    db.commit()
    db.refresh(a)
    return a


def delete_activity(db: Session, board_id: int, activity_id: int) -> None:
    a = _get_activity(db, board_id, activity_id)
    for other in _activities(db, board_id):                 # nobody may keep depending on a deleted row
        if activity_id in (other.depends_on or []):
            other.depends_on = [d for d in other.depends_on if d != activity_id]
    db.query(Expense).filter(Expense.activity_id == activity_id).update({"activity_id": None})
    db.query(FinanceIncrement).filter(FinanceIncrement.activity_id == activity_id).update({"activity_id": None})
    db.delete(a)
    db.commit()


# ---------------------------------------------------------------- finance
def _check_target(db: Session, board_id: int, activity_id: int | None) -> None:
    if activity_id is not None:
        _get_activity(db, board_id, activity_id)            # 404 if it is not on this board


def create_increment(db: Session, board_id: int, body: IncrementCreate) -> FinanceIncrement:
    _check_target(db, board_id, body.activity_id)
    i = FinanceIncrement(board_id=board_id, **body.model_dump())
    db.add(i)
    db.commit()
    db.refresh(i)
    return i


def _get_increment(db: Session, board_id: int, inc_id: int) -> FinanceIncrement:
    i = db.query(FinanceIncrement).filter(FinanceIncrement.id == inc_id,
                                          FinanceIncrement.board_id == board_id).first()
    if not i:
        raise HTTPException(status_code=404, detail="Finance increment not found")
    return i


def update_increment(db: Session, board_id: int, inc_id: int, body: IncrementUpdate) -> FinanceIncrement:
    i = _get_increment(db, board_id, inc_id)
    data = body.model_dump(exclude_unset=True)
    clear = data.pop("clear_target", False)
    for k in ("amount", "effective_date", "status"):
        if k in data and data[k] is None:
            raise HTTPException(status_code=422, detail=f"{k} cannot be empty.")
    if "activity_id" in data:
        _check_target(db, board_id, data["activity_id"])
    if clear:
        data["activity_id"], data["phase"] = None, None
    for k, v in data.items():
        setattr(i, k, v)
    db.commit()
    db.refresh(i)
    return i


def delete_increment(db: Session, board_id: int, inc_id: int) -> None:
    db.delete(_get_increment(db, board_id, inc_id))
    db.commit()


def set_base_budget(db: Session, board_id: int, body: BudgetUpdate) -> Decimal:
    row = db.query(BoardBudget).filter(BoardBudget.board_id == board_id).first()
    if row:
        row.base_budget = body.base_budget
    else:
        db.add(BoardBudget(board_id=board_id, base_budget=body.base_budget))
    db.commit()
    return body.base_budget


# ---------------------------------------------------------------- seed from the Kanban board
def _latest_estimate(db: Session, board_id: int) -> dict | None:
    row = (db.query(CostEstimate).filter(CostEstimate.board_id == board_id)
           .order_by(CostEstimate.id.desc()).first())
    return row.result if row else None


def seed_from_board(db: Session, board_id: int, mode: str, today: date | None = None) -> dict:
    """One activity per Kanban task. Cost and hours are shared out of the latest PKR cost estimate
    in proportion to story points; dates follow the task dependency order. `create` refuses if
    activities exist (409); `sync` adds only tasks that have no activity yet."""
    today = today or date.today()
    existing = _activities(db, board_id)
    if mode == "create" and existing:
        raise HTTPException(status_code=409, detail="This board already has activities. "
                                                    "Choose 'Add missing' to keep your work.")
    rows = (db.query(Task, BoardColumn.name).join(BoardColumn, BoardColumn.id == Task.column_id)
            .filter(BoardColumn.board_id == board_id).order_by(Task.id).all())
    if not rows:
        raise HTTPException(status_code=422, detail="This board has no tasks yet. "
                                                    "Generate the Kanban board from the SRS first.")
    have = {a.task_id for a in existing if a.task_id}
    new = [(t, col) for t, col in rows if t.id not in have]
    if not new:
        return {"added": 0, "skipped": len(rows), "used_cost_estimate": False}

    est = _latest_estimate(db, board_id)
    pert = (est or {}).get("pert") or {}
    total_cost = C.dec(pert.get("total")) if est else D(0)
    pm = C.dec(pert.get("pm"))
    total_points = sum((t.estimate_points or 1) for t, _ in rows)
    total_hours = (pm * C.HOURS_PER_PERSON_MONTH) if pm > 0 else D(total_points * C.HOURS_PER_POINT)

    by_req = {t.requirement_id: t.id for t, _ in rows if t.requirement_id}
    start = min((a.start_date for a in existing), default=today)
    ends = {a.task_id: a.end_date for a in existing if a.task_id}
    items = [{"key": t.id, "days": C.days_for_points(t.estimate_points),
              "deps": [by_req[r] for r in (t.depends_on or []) if r in by_req]} for t, _ in new]
    plan = C.plan_schedule(items, start, ends)

    created: dict[int, Activity] = {}
    pos = len(existing)
    for t, col in new:
        share = D(t.estimate_points or 1) / D(total_points)
        s, e = plan[t.id]
        kind = "Non-functional" if (t.requirement_id or "").startswith("NFR") else "Functional"
        a = Activity(board_id=board_id, task_id=t.id, name=(t.title or "Task")[:200], phase=kind,
                     start_date=s, end_date=e, position=pos,
                     planned_hours=C.q2(total_hours * share), estimated_cost=C.q2(total_cost * share),
                     progress_pct=100 if (col or "").strip().lower() == "done" else 0, depends_on=[])
        db.add(a)
        created[t.id] = a
        pos += 1
    db.flush()
    existing_by_task = {a.task_id: a.id for a in existing if a.task_id}
    deps_by_key = {i["key"]: i["deps"] for i in items}
    for t, _ in new:
        deps = [created[d].id if d in created else existing_by_task[d]
                for d in deps_by_key[t.id] if d in created or d in existing_by_task]
        created[t.id].depends_on = list(dict.fromkeys(deps))
    db.commit()
    return {"added": len(new), "skipped": len(rows) - len(new), "used_cost_estimate": bool(est)}
