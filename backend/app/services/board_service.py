"""Stores a BoardPlan in the database, keeps it in sync with the SRS, and builds the
traceability story for one task. The decisions themselves live in board_planner.py."""
import logging

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.board import Board
from app.models.column import BoardColumn
from app.models.srs import SRSDocument
from app.models.task import Task
from app.schemas.srs import Requirements
from app.services.board_planner import BoardPlan, STANDARD_COLUMNS, plan_board

log = logging.getLogger("stackpilot.board")


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------
def get_srs(db: Session, board_id: int, srs_id: int | None) -> SRSDocument:
    q = db.query(SRSDocument).filter(SRSDocument.board_id == board_id)
    doc = q.filter(SRSDocument.id == srs_id).first() if srs_id else q.order_by(SRSDocument.version.desc()).first()
    if not doc:
        raise HTTPException(status_code=404, detail="No SRS found. Generate the SRS first.")
    return doc


def load_requirements(doc: SRSDocument) -> Requirements:
    try:
        return Requirements.model_validate(doc.requirements)
    except ValidationError:
        raise HTTPException(status_code=422, detail="This SRS version is damaged and cannot be turned into a board. "
                                                    "Regenerate the SRS and try again.")


def _board_tasks(db: Session, board_id: int) -> list[Task]:
    return (db.query(Task).join(BoardColumn, BoardColumn.id == Task.column_id)
            .filter(BoardColumn.board_id == board_id).order_by(Task.id).all())


# --------------------------------------------------------------------------
# generate
# --------------------------------------------------------------------------
def generate_board(db: Session, board_id: int, user_id: int, srs_id: int | None,
                   mode: str, include_nfr: bool) -> dict:
    """One transaction: either the whole board is written or nothing is.

    Returns the summary for the client plus the private keys `_new_task_ids` and
    `_removed_task_ids` that the route hands to the background vector indexer.
    """
    # Lock the board row so a double click cannot create the board twice (PostgreSQL;
    # SQLite ignores FOR UPDATE, which is fine for tests).
    board = db.query(Board).filter(Board.id == board_id).with_for_update().first()
    if board is None:  # route already checked ownership; this only guards a race with delete
        raise HTTPException(status_code=404, detail="Board not found")

    doc = get_srs(db, board_id, srs_id)
    plan: BoardPlan = plan_board(load_requirements(doc), include_nfr=include_nfr)
    if not plan.tasks:
        raise HTTPException(status_code=422, detail="This SRS has no requirements to turn into tasks.")

    columns = db.query(BoardColumn).filter(BoardColumn.board_id == board_id).order_by(BoardColumn.id).all()
    removed_ids: list[int] = []
    skipped = 0
    tasks_to_make = plan.tasks

    try:
        if mode == "create" and columns:
            raise HTTPException(
                status_code=409,
                detail="This board already has columns. Choose 'Add missing' to keep your work, "
                       "or 'Replace' to start over.")

        if mode == "replace":
            removed_ids = [t.id for t in _board_tasks(db, board_id)]
            for c in columns:
                db.delete(c)          # ORM cascade removes their tasks
            db.flush()
            columns = []

        if mode == "sync":
            have = {t.requirement_id for t in _board_tasks(db, board_id) if t.requirement_id}
            tasks_to_make = [t for t in plan.tasks if t.requirement_id not in have]
            skipped = len(plan.tasks) - len(tasks_to_make)

        # name (case-insensitive) -> column; create only the standard columns we actually need
        by_name = {c.name.strip().lower(): c for c in columns}
        created_columns: list[str] = []
        needed = list(STANDARD_COLUMNS) if mode != "sync" else \
            [n for n in STANDARD_COLUMNS if n in {t.column for t in tasks_to_make}]
        for name in needed:
            if name.lower() not in by_name:
                col = BoardColumn(name=name, board_id=board_id)
                db.add(col)
                db.flush()
                by_name[name.lower()] = col
                created_columns.append(name)

        new_tasks: list[Task] = []
        for t in tasks_to_make:
            task = Task(
                title=t.title, description=t.description, priority=t.priority,
                column_id=by_name[t.column.lower()].id, created_by=user_id,
                requirement_id=t.requirement_id, estimate_points=t.estimate_points,
                depends_on=list(t.depends_on), srs_id=doc.id,
            )
            db.add(task)
            new_tasks.append(task)
        db.flush()
        new_ids = [t.id for t in new_tasks]
        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        log.exception("generate_board failed")
        raise HTTPException(status_code=500, detail="Could not build the board. Nothing was changed; please try again.")

    return {
        "board_id": board_id, "srs_id": doc.id, "version": doc.version, "mode": mode,
        "columns_created": created_columns,
        "tasks_created": len(new_ids), "tasks_skipped": skipped,
        "points_total": sum(t.estimate_points for t in tasks_to_make),
        "warnings": plan.warnings,
        "_new_task_ids": new_ids, "_removed_task_ids": removed_ids,
    }


# --------------------------------------------------------------------------
# best-effort vector indexing so the RAG chat knows the new tasks
# --------------------------------------------------------------------------
def index_tasks(new_ids: list[int], removed_ids: list[int], *, embedder=None, store=None) -> None:
    """Runs AFTER the response is sent. Never raises: the board is already saved and the
    chat index is a bonus. Heavy imports (Qdrant connects on import) are lazy on purpose."""
    if not new_ids and not removed_ids:
        return
    try:
        if embedder is None:
            from app.rag.embedding_service import create_embedding as embedder
        if store is None:
            from app.rag.qdrant_service import qdrant as store
    except Exception:
        log.exception("Vector index unavailable; the chat will not know the new tasks yet")
        return

    for tid in removed_ids:
        try:
            store.delete_vector(tid)
        except Exception:
            log.warning("Could not delete vector for task %s", tid)

    db = SessionLocal()
    try:
        rows = (db.query(Task, BoardColumn).join(BoardColumn, BoardColumn.id == Task.column_id)
                .filter(Task.id.in_(new_ids)).all()) if new_ids else []
        for task, column in rows:
            try:
                text = f"""
        Title:{task.title}
        Description:{task.description}
        Priority: {task.priority}
    """
                store.insert_vector(
                    embedding=embedder(text), point_id=task.id,
                    payload={"type": "task", "board_id": column.board_id, "task_id": task.id,
                             "column_id": task.column_id, "priority": task.priority,
                             "title": task.title, "text": text})
            except Exception:
                log.warning("Could not index task %s", task.id)
    finally:
        db.close()


# --------------------------------------------------------------------------
# traceability story for one task
# --------------------------------------------------------------------------
def task_trace(db: Session, board_id: int, task: Task) -> dict:
    if not task.requirement_id:
        return {"linked": False, "reason": "This task was created by hand, not from the SRS."}

    latest = (db.query(SRSDocument).filter(SRSDocument.board_id == board_id)
              .order_by(SRSDocument.version.desc()).first())
    doc = None
    if task.srs_id:
        doc = db.query(SRSDocument).filter(SRSDocument.id == task.srs_id, SRSDocument.board_id == board_id).first()
    doc = doc or latest
    if doc is None:
        return {"linked": False, "reason": "The SRS this task came from no longer exists."}

    try:
        req = Requirements.model_validate(doc.requirements)
    except ValidationError:
        return {"linked": False, "reason": "The SRS this task came from is unreadable."}

    rid = task.requirement_id
    fr = next((f for f in req.functional_requirements if f.id == rid), None)
    nfr = next((n for n in req.non_functional_requirements if n.id == rid), None)

    by_req = {t.requirement_id: t for t in _board_tasks(db, board_id) if t.requirement_id}
    names = {c.id: c.name for c in db.query(BoardColumn).filter(BoardColumn.board_id == board_id).all()}
    titles = {f.id: f.title for f in req.functional_requirements}

    def ref(r: str) -> dict:
        t = by_req.get(r)
        return {"requirement_id": r, "title": titles.get(r, ""), "task_id": t.id if t else None,
                "column": names.get(t.column_id) if t else None}

    out: dict = {
        "linked": True, "requirement_id": rid, "srs_id": doc.id, "srs_version": doc.version,
        "srs_is_latest": bool(latest and latest.id == doc.id),
        "depends_on": [ref(r) for r in (task.depends_on or [])],
        "blocks": [ref(r) for r, t in sorted(by_req.items()) if rid in (t.depends_on or [])],
    }
    if fr:
        out["kind"] = "functional"
        out["requirement"] = {"id": fr.id, "title": fr.title, "statement": fr.statement,
                              "priority": fr.priority, "actor": fr.actor,
                              "acceptance_criteria": fr.acceptance_criteria}
        out["use_cases"] = [{"id": u.id, "name": u.name, "actor": u.actor, "description": u.description,
                             "main_flow": u.main_flow} for u in req.use_cases if rid in u.fr_ids]
    elif nfr:
        out["kind"] = "non-functional"
        out["requirement"] = {"id": nfr.id, "category": nfr.category, "statement": nfr.statement, "metric": nfr.metric}
        out["use_cases"] = []
    else:
        out["kind"] = "missing"
        out["requirement"] = None
        out["use_cases"] = []
        out["note"] = f"{rid} is no longer in SRS version {doc.version}."
    return out
