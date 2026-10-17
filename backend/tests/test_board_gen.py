"""Phase 4 tests: SRS -> Kanban. Fake LLM + SQLite, no keys, no network."""
import random

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect, text

from app.core.database import Base, SessionLocal, engine
from app.core.llm_fake import sample_requirements
from app.core.migrate import TASK_COLUMNS, ensure_task_columns
from app.models.board import Board
from app.models.column import BoardColumn
from app.models.otp import OTP  # noqa: F401  (register table)
from app.models.chat import Chat  # noqa: F401
from app.models.srs import Diagram, DiagramJob, SRSDocument, SRSJob  # noqa: F401
from app.models.task import Task
from app.models.user import User
from app.routes import srs as srs_routes
from app.routes import srs_board as board_routes
from app.routes.auth import get_current_user
from app.schemas.srs import FR, NFR, Requirements
from app.schemas.task import TaskResponse
from app.services import board_planner, board_service
from app.services.board_planner import STANDARD_COLUMNS, has_cycle, plan_board, plan_dependencies
from app.services.srs_service import save_srs
from app.services.srs_validator import validate_requirements

DESC = "A web system for a university library to manage books, members, loans and fines."


@pytest.fixture(autouse=True)
def fresh_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


# ------------------------------------------------------------------ helpers
def make_client(user_id):
    app = FastAPI()
    app.include_router(srs_routes.router)
    app.include_router(board_routes.router)
    app.dependency_overrides[get_current_user] = lambda: type("U", (), {"id": user_id})()
    return TestClient(app)


def seed(with_srs=True, req=None):
    db = SessionLocal()
    db.add_all([User(id=1, name="A", email="a@a.com"), User(id=2, name="B", email="b@b.com")])
    db.add_all([Board(id=1, name="Library", description="x", owner_id=1),
                Board(id=2, name="Other", description="y", owner_id=1)])
    db.commit()
    if with_srs:
        r = req or sample_requirements()
        save_srs(db, 1, DESC, [], r, validate_requirements(r))
    db.close()


def board_rows(board_id=1):
    db = SessionLocal()
    cols = db.query(BoardColumn).filter(BoardColumn.board_id == board_id).order_by(BoardColumn.id).all()
    names = {c.id: c.name for c in cols}
    tasks = db.query(Task).filter(Task.column_id.in_(names)).order_by(Task.id).all() if names else []
    cols_l = [c.name for c in cols]
    for t in tasks:
        db.expunge(t)
    db.close()
    return cols_l, tasks, names


def fr(i, title, priority="must", actor="Member", statement=None, ac=None):
    return FR(id=f"FR-{i:03d}", title=title, statement=statement or f"The system shall {title.lower()}.",
              priority=priority, actor=actor, acceptance_criteria=ac if ac is not None else ["It works."])


def req_with(frs, ucs=None, nfrs=()):
    r = sample_requirements()
    r.functional_requirements = frs
    r.non_functional_requirements = list(nfrs)
    if ucs is None:
        ucs = [(f"UC-{i + 1:03d}", [f.id]) for i, f in enumerate(frs)]
    base = r.use_cases[0]
    r.use_cases = [base.model_copy(update={"id": uid, "name": f"Case {uid}", "fr_ids": ids}) for uid, ids in ucs]
    return r


# ------------------------------------------------------------------ planner
def test_every_must_fr_has_a_task_and_nothing_starts_done():
    r = sample_requirements()
    plan = plan_board(r)
    ids = {t.requirement_id for t in plan.tasks}
    assert {f.id for f in r.functional_requirements if f.priority == "must"} <= ids
    assert {f.id for f in r.functional_requirements} <= ids          # all FRs, not just musts
    assert {n.id for n in r.non_functional_requirements} <= ids      # NFRs by default
    assert plan.columns == STANDARD_COLUMNS
    assert {t.column for t in plan.tasks} <= {"Backlog", "Ready"}    # nothing in Done/Testing/In Progress


def test_priority_title_and_description_content():
    plan = plan_board(sample_requirements())
    t = {x.requirement_id: x for x in plan.tasks}
    assert t["FR-001"].priority == "high" and t["FR-006"].priority == "medium" and t["FR-008"].priority == "low"
    assert t["FR-004"].title == "[FR-004] Return book"
    assert "Acceptance criteria:" in t["FR-004"].description and "- Return book succeeds with valid input." in t["FR-004"].description
    assert "Use case: UC-003 Process a return" in t["FR-004"].description
    assert t["NFR-002"].priority == "high" and t["NFR-001"].priority == "medium"
    assert "Measurable target:" in t["NFR-001"].description


def test_columns_ready_only_for_unblocked_musts():
    t = {x.requirement_id: x for x in plan_board(sample_requirements()).tasks}
    assert t["FR-001"].column == "Ready" and t["FR-002"].column == "Ready" and t["FR-004"].column == "Ready"
    assert t["FR-003"].column == "Backlog"     # waits for FR-002
    assert t["FR-006"].column == "Backlog"     # should, waits for FR-004
    assert t["FR-007"].column == "Backlog"     # should, no deps -> still not Ready
    assert t["NFR-001"].column == "Backlog"


def test_flow_order_dependencies():
    deps, warnings = plan_dependencies(sample_requirements())
    assert deps["FR-003"] == ["FR-002"] and deps["FR-008"] == ["FR-003"] and deps["FR-006"] == ["FR-004"]
    assert deps["FR-001"] == [] and not warnings and not has_cycle(deps)


def test_tasks_are_grouped_by_use_case_then_id_and_nfr_last():
    ids = [t.requirement_id for t in plan_board(sample_requirements()).tasks]
    assert ids == ["FR-001", "FR-002", "FR-003", "FR-008", "FR-004", "FR-006", "FR-005", "FR-007",
                   "NFR-001", "NFR-002", "NFR-003"]


def test_plan_is_deterministic():
    a, b = plan_board(sample_requirements()), plan_board(sample_requirements())
    assert a == b


def test_include_nfr_false():
    ids = {t.requirement_id for t in plan_board(sample_requirements(), include_nfr=False).tasks}
    assert not any(i.startswith("NFR") for i in ids)


def test_explicit_cycle_is_broken_with_warning():
    a = fr(1, "A", statement="The system shall do A after FR-002 is done.")
    b = fr(2, "B", statement="The system shall do B after FR-001 is done.")
    deps, warnings = plan_dependencies(req_with([a, b]))
    assert not has_cycle(deps)
    assert sum(len(v) for v in deps.values()) == 1                      # exactly one edge survives
    assert any("circular" in w for w in warnings)


def test_self_reference_ignored():
    a = fr(1, "A", statement="The system shall do A (see FR-001).")
    deps, _ = plan_dependencies(req_with([a]))
    assert deps["FR-001"] == []


def test_derived_edge_never_blocks_important_behind_optional():
    low, high = fr(1, "Optional thing", "could"), fr(2, "Core thing", "must")
    r = req_with([low, high], ucs=[("UC-001", ["FR-001", "FR-002"])])
    deps, warnings = plan_dependencies(r)
    assert deps["FR-002"] == [] and not warnings


def test_explicit_priority_inversion_is_kept_but_warned():
    low = fr(1, "Optional thing", "could")
    high = fr(2, "Core thing", "must", statement="The system shall do the core thing using FR-001.")
    deps, warnings = plan_dependencies(req_with([low, high]))
    assert deps["FR-002"] == ["FR-001"] and any("review the priorities" in w for w in warnings)


def test_random_reference_graphs_never_cycle():
    rnd = random.Random(7)
    for _ in range(200):
        n = rnd.randint(2, 12)
        frs = []
        for i in range(1, n + 1):
            refs = " ".join(f"FR-{rnd.randint(1, n):03d}" for _ in range(rnd.randint(0, 4)))
            frs.append(fr(i, f"T{i}", rnd.choice(["must", "should", "could"]),
                          statement=f"The system shall do {i} {refs}."))
        order = [f.id for f in frs]
        rnd.shuffle(order)
        deps, _ = plan_dependencies(req_with(frs, ucs=[("UC-001", order)]))
        assert not has_cycle(deps)
        plan = plan_board(req_with(frs, ucs=[("UC-001", order)]))
        assert {t.requirement_id for t in plan.tasks} == {f.id for f in frs}
        assert all(t.column in ("Backlog", "Ready") for t in plan.tasks)


def test_has_cycle_detector():
    assert has_cycle({"A": ["B"], "B": ["A"]})
    assert has_cycle({"A": ["A"]})
    assert has_cycle({"A": ["B"], "B": ["C"], "C": ["A"]})
    assert not has_cycle({"A": ["B"], "B": [], "C": ["A", "B"]})
    assert not has_cycle({})


def test_uncovered_fr_goes_to_unassigned():
    r = sample_requirements()
    for u in r.use_cases:
        u.fr_ids = [x for x in u.fr_ids if x != "FR-006"]
    plan = plan_board(r)
    t = next(x for x in plan.tasks if x.requirement_id == "FR-006")
    assert t.group == "Unassigned" and "Use case: Unassigned" in t.description
    assert any("FR-006" in w and "not covered" in w for w in plan.warnings)


def test_duplicate_and_blank_ids_are_skipped_with_warning():
    r = sample_requirements()
    r.functional_requirements[1].id = "FR-001"
    r.functional_requirements[2].id = "  "
    plan = plan_board(r)
    ids = [t.requirement_id for t in plan.tasks]
    assert ids.count("FR-001") == 1
    assert sum("more than once" in w for w in plan.warnings) == 1
    assert sum("no ID" in w for w in plan.warnings) == 1


def test_points_are_fibonacci_and_stable():
    for t in plan_board(sample_requirements()).tasks:
        assert t.estimate_points in (1, 2, 3, 5, 8)
    big = fr(1, "Big", statement="The system shall " + "do many things " * 20, ac=["a"] * 12)
    assert board_planner.estimate_points(big, 3) == 8
    assert board_planner.estimate_points(fr(2, "Tiny", ac=[]), 0) == 1


def test_long_titles_are_clipped():
    r = req_with([fr(1, "x" * 500)])
    assert len(plan_board(r).tasks[0].title) <= board_planner.TITLE_MAX


# ------------------------------------------------------------------ API
def test_generate_board_creates_everything():
    seed()
    c = make_client(1)
    r = c.post("/boards/1/srs/generate-board", json={})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["tasks_created"] == 11 and body["tasks_skipped"] == 0
    assert body["columns_created"] == STANDARD_COLUMNS and body["version"] == 1
    assert body["points_total"] == sum(t.estimate_points for t in board_rows()[1])
    assert "_new_task_ids" not in body

    cols, tasks, names = board_rows()
    assert cols == STANDARD_COLUMNS
    assert len(tasks) == 11
    assert {names[t.column_id] for t in tasks} <= {"Backlog", "Ready"}
    by = {t.requirement_id: t for t in tasks}
    assert by["FR-003"].depends_on == ["FR-002"] and by["FR-001"].depends_on == []
    assert by["FR-003"].srs_id == 1 and by["FR-003"].created_by == 1
    assert by["FR-004"].title == "[FR-004] Return book" and by["FR-004"].priority == "high"
    # every must FR is on the board
    musts = {f.id for f in sample_requirements().functional_requirements if f.priority == "must"}
    assert musts <= set(by)
    # task schema accepts the new fields
    TaskResponse.model_validate(tasks[0], from_attributes=True)


def test_create_on_nonempty_board_is_409_and_changes_nothing():
    seed()
    c = make_client(1)
    assert c.post("/boards/1/srs/generate-board", json={}).status_code == 200
    before = board_rows()[1]
    r = c.post("/boards/1/srs/generate-board", json={})
    assert r.status_code == 409 and "already has columns" in r.json()["detail"]
    assert len(board_rows()[1]) == len(before)


def test_manual_columns_also_block_create():
    seed()
    db = SessionLocal(); db.add(BoardColumn(name="Mine", board_id=1)); db.commit(); db.close()
    assert make_client(1).post("/boards/1/srs/generate-board", json={}).status_code == 409


def test_sync_adds_only_missing_and_never_touches_existing_work():
    seed()
    c = make_client(1)
    c.post("/boards/1/srs/generate-board", json={})
    # the user works on the board
    db = SessionLocal()
    t1 = db.query(Task).filter(Task.requirement_id == "FR-001").first()
    t1.title = "My own title"
    t1.column_id = db.query(BoardColumn).filter(BoardColumn.name == "Done", BoardColumn.board_id == 1).first().id
    db.add(Task(title="Hand made", description="x", priority="low", column_id=t1.column_id, created_by=1))
    db.commit(); db.close()

    # SRS gets a new requirement -> new version
    r = sample_requirements()
    new = fr(9, "Export reports", "should", actor="Librarian")
    r.functional_requirements.append(new)
    r.use_cases[3].fr_ids.append("FR-009")
    db = SessionLocal(); save_srs(db, 1, DESC, [], r, validate_requirements(r)); db.close()

    s = c.post("/boards/1/srs/generate-board", json={"mode": "sync"})
    assert s.status_code == 200, s.text
    j = s.json()
    assert j["tasks_created"] == 1 and j["tasks_skipped"] == 11 and j["version"] == 2
    assert j["columns_created"] == []                      # Backlog already exists
    _, tasks, names = board_rows()
    assert len(tasks) == 13                                # 11 + hand made + new
    by = {t.requirement_id: t for t in tasks if t.requirement_id}
    assert by["FR-001"].title == "My own title" and names[by["FR-001"].column_id] == "Done"
    assert by["FR-009"].srs_id == 2 and by["FR-009"].depends_on == ["FR-005"]   # flow order in UC-004
    assert any(t.title == "Hand made" for t in tasks)
    # a second sync is a no-op
    again = c.post("/boards/1/srs/generate-board", json={"mode": "sync"}).json()
    assert again["tasks_created"] == 0 and len(board_rows()[1]) == 13


def test_sync_on_empty_board_acts_like_create():
    seed()
    j = make_client(1).post("/boards/1/srs/generate-board", json={"mode": "sync"}).json()
    assert j["tasks_created"] == 11 and j["columns_created"] == ["Backlog", "Ready"]  # only what is needed


def test_sync_creates_a_missing_column_only_when_needed():
    seed()
    db = SessionLocal()
    for n in ("backlog", "READY"):                      # case-insensitive match, no duplicates
        db.add(BoardColumn(name=n, board_id=1))
    db.commit(); db.close()
    j = make_client(1).post("/boards/1/srs/generate-board", json={"mode": "sync"}).json()
    assert j["columns_created"] == [] and j["tasks_created"] == 11
    assert sorted(board_rows()[0]) == ["READY", "backlog"]


def test_replace_wipes_and_rebuilds():
    seed()
    c = make_client(1)
    c.post("/boards/1/srs/generate-board", json={})
    db = SessionLocal()
    db.add(BoardColumn(name="Custom", board_id=1)); db.commit()
    first_ids = {t.id for t in db.query(Task).all()}
    db.close()
    j = c.post("/boards/1/srs/generate-board", json={"mode": "replace"})
    assert j.status_code == 200
    cols, tasks, _ = board_rows()
    assert cols == STANDARD_COLUMNS and len(tasks) == 11          # Custom column is gone too
    db = SessionLocal()
    assert db.query(BoardColumn).count() == 5                     # no orphans
    db.close()


def test_replace_does_not_touch_other_boards():
    seed()
    db = SessionLocal()
    col = BoardColumn(name="Keep", board_id=2); db.add(col); db.flush()
    db.add(Task(title="Safe", description="", priority="low", column_id=col.id, created_by=1)); db.commit(); db.close()
    make_client(1).post("/boards/1/srs/generate-board", json={"mode": "replace"})
    assert [t.title for t in board_rows(2)[1]] == ["Safe"]


def test_include_nfr_false_via_api():
    seed()
    j = make_client(1).post("/boards/1/srs/generate-board", json={"include_nfr": False}).json()
    assert j["tasks_created"] == 8


def test_no_srs_is_404_and_other_boards_srs_is_404():
    seed(with_srs=False)
    c = make_client(1)
    assert c.post("/boards/1/srs/generate-board", json={}).status_code == 404
    seed2 = SessionLocal(); r = sample_requirements()
    save_srs(seed2, 2, DESC, [], r, []); sid = seed2.query(SRSDocument).first().id; seed2.close()
    assert c.post("/boards/1/srs/generate-board", json={"srs_id": sid}).status_code == 404   # belongs to board 2
    assert c.post("/boards/2/srs/generate-board", json={"srs_id": sid}).status_code == 200


def test_old_srs_version_can_be_chosen():
    seed()
    r = sample_requirements(); r.functional_requirements = r.functional_requirements[:5]
    r.use_cases = r.use_cases[:4]
    for u in r.use_cases:
        u.fr_ids = [x for x in u.fr_ids if x in {f.id for f in r.functional_requirements}]
    db = SessionLocal(); save_srs(db, 1, DESC, [], r, []); db.close()
    j = make_client(1).post("/boards/1/srs/generate-board", json={"srs_id": 1, "include_nfr": False}).json()
    assert j["version"] == 1 and j["tasks_created"] == 8


def test_damaged_srs_gives_422_not_500():
    seed()
    db = SessionLocal(); d = db.query(SRSDocument).first(); d.requirements = {"title": 5}; db.commit(); db.close()
    r = make_client(1).post("/boards/1/srs/generate-board", json={})
    assert r.status_code == 422 and "damaged" in r.json()["detail"]


def test_srs_without_requirements_gives_422():
    seed(req=req_with([], ucs=[]))
    r = make_client(1).post("/boards/1/srs/generate-board", json={"include_nfr": False})
    assert r.status_code == 422 and "no requirements" in r.json()["detail"]


def test_failure_rolls_back_everything(monkeypatch):
    seed()
    real = board_service.plan_board

    def bad(req, include_nfr=True):
        plan = real(req, include_nfr)
        plan.tasks[-1].column = "Nowhere"          # forces a failure after columns and tasks were added
        return plan
    monkeypatch.setattr(board_service, "plan_board", bad)
    r = make_client(1).post("/boards/1/srs/generate-board", json={})
    assert r.status_code == 500 and "Nothing was changed" in r.json()["detail"]
    db = SessionLocal()
    assert db.query(BoardColumn).count() == 0 and db.query(Task).count() == 0
    db.close()


def test_replace_failure_keeps_old_board(monkeypatch):
    seed()
    c = make_client(1)
    c.post("/boards/1/srs/generate-board", json={})
    real = board_service.plan_board

    def bad(req, include_nfr=True):
        plan = real(req, include_nfr); plan.tasks[-1].column = "Nowhere"; return plan
    monkeypatch.setattr(board_service, "plan_board", bad)
    assert c.post("/boards/1/srs/generate-board", json={"mode": "replace"}).status_code == 500
    cols, tasks, _ = board_rows()
    assert cols == STANDARD_COLUMNS and len(tasks) == 11          # old board survived


def test_other_user_gets_404():
    seed()
    c = make_client(1)
    c.post("/boards/1/srs/generate-board", json={})
    tid = board_rows()[1][0].id
    intruder = make_client(2)
    assert intruder.post("/boards/1/srs/generate-board", json={}).status_code == 404
    assert intruder.post("/boards/1/srs/generate-board", json={"mode": "replace"}).status_code == 404
    assert intruder.get(f"/boards/1/tasks/{tid}/trace").status_code == 404
    assert len(board_rows()[1]) == 11


def test_validation_of_mode():
    seed()
    assert make_client(1).post("/boards/1/srs/generate-board", json={"mode": "nuke"}).status_code == 422


# ------------------------------------------------------------------ trace
def _task(req_id):
    return next(t for t in board_rows()[1] if t.requirement_id == req_id)


def test_trace_for_functional_task():
    seed()
    c = make_client(1)
    c.post("/boards/1/srs/generate-board", json={})
    t = _task("FR-003")
    j = c.get(f"/boards/1/tasks/{t.id}/trace").json()
    assert j["linked"] and j["kind"] == "functional" and j["srs_version"] == 1 and j["srs_is_latest"]
    assert j["requirement"]["id"] == "FR-003" and j["requirement"]["acceptance_criteria"]
    assert [u["id"] for u in j["use_cases"]] == ["UC-002"] and j["use_cases"][0]["main_flow"]
    assert j["depends_on"] == [{"requirement_id": "FR-002", "title": "Search catalogue",
                                "task_id": _task("FR-002").id, "column": "Ready"}]
    assert [b["requirement_id"] for b in j["blocks"]] == ["FR-008"]


def test_trace_for_nfr_manual_and_missing():
    seed()
    c = make_client(1)
    c.post("/boards/1/srs/generate-board", json={})
    n = c.get(f"/boards/1/tasks/{_task('NFR-002').id}/trace").json()
    assert n["kind"] == "non-functional" and n["requirement"]["category"] == "security" and n["use_cases"] == []

    db = SessionLocal()
    col = db.query(BoardColumn).first()
    manual = Task(title="By hand", description="", priority="low", column_id=col.id, created_by=1)
    ghost = Task(title="Ghost", description="", priority="low", column_id=col.id, created_by=1, requirement_id="FR-099", srs_id=1)
    db.add_all([manual, ghost]); db.commit(); mid, gid = manual.id, ghost.id; db.close()
    m = c.get(f"/boards/1/tasks/{mid}/trace").json()
    assert m["linked"] is False and "by hand" in m["reason"]
    g = c.get(f"/boards/1/tasks/{gid}/trace").json()
    assert g["linked"] and g["kind"] == "missing" and "no longer in SRS" in g["note"]


def test_trace_tells_when_srs_moved_on_and_dependency_moved():
    seed()
    c = make_client(1)
    c.post("/boards/1/srs/generate-board", json={})
    r = sample_requirements(); r.title = "v2"
    db = SessionLocal(); save_srs(db, 1, DESC, [], r, []); db.close()
    j = c.get(f"/boards/1/tasks/{_task('FR-003').id}/trace").json()
    assert j["srs_version"] == 1 and j["srs_is_latest"] is False            # task came from v1, v2 exists
    # move FR-002 to another column; trace reports the live column
    db = SessionLocal()
    done = db.query(BoardColumn).filter(BoardColumn.name == "Done").first()
    db.query(Task).filter(Task.requirement_id == "FR-002").first().column_id = done.id
    db.commit(); db.close()
    j = c.get(f"/boards/1/tasks/{_task('FR-003').id}/trace").json()
    assert j["depends_on"][0]["column"] == "Done"


def test_trace_task_of_other_board_is_404():
    seed()
    c = make_client(1)
    c.post("/boards/1/srs/generate-board", json={})
    tid = board_rows()[1][0].id
    assert c.get(f"/boards/2/tasks/{tid}/trace").status_code == 404
    assert c.get("/boards/1/tasks/99999/trace").status_code == 404


# ------------------------------------------------------------------ migration
def test_migration_adds_columns_once_and_keeps_rows():
    old = create_engine("sqlite://")
    with old.begin() as conn:
        conn.execute(text("CREATE TABLE tasks (id INTEGER PRIMARY KEY, title VARCHAR, description VARCHAR, "
                          "priority VARCHAR, column_id INTEGER, created_by INTEGER)"))
        conn.execute(text("INSERT INTO tasks (id, title, priority) VALUES (1, 'old task', 'low')"))
    assert set(ensure_task_columns(old)) == set(TASK_COLUMNS)
    cols = {c["name"] for c in inspect(old).get_columns("tasks")}
    assert set(TASK_COLUMNS) <= cols
    with old.connect() as conn:
        row = conn.execute(text("SELECT title, requirement_id, depends_on FROM tasks")).one()
    assert row == ("old task", None, None)
    assert ensure_task_columns(old) == []                       # idempotent


def test_migration_noop_when_table_missing_or_complete():
    assert ensure_task_columns(create_engine("sqlite://")) == []
    assert ensure_task_columns(engine) == []                    # create_all already made every column


def test_old_rows_with_null_depends_on_still_trace():
    seed()
    db = SessionLocal()
    col = BoardColumn(name="Backlog", board_id=1); db.add(col); db.flush()
    t = Task(title="[FR-001] x", description="", priority="low", column_id=col.id, created_by=1,
             requirement_id="FR-001", depends_on=None, srs_id=None)
    db.add(t); db.commit(); tid = t.id; db.close()
    j = make_client(1).get(f"/boards/1/tasks/{tid}/trace").json()
    assert j["linked"] and j["depends_on"] == [] and j["srs_version"] == 1     # falls back to latest SRS


# ------------------------------------------------------------------ vector indexing (best effort)
class FakeStore:
    def __init__(self): self.inserted, self.deleted = [], []
    def insert_vector(self, embedding, point_id, payload): self.inserted.append((point_id, payload))
    def delete_vector(self, point_id): self.deleted.append(point_id)


def test_index_tasks_indexes_new_and_deletes_removed():
    seed()
    make_client(1).post("/boards/1/srs/generate-board", json={})
    ids = [t.id for t in board_rows()[1]]
    store = FakeStore()
    board_service.index_tasks(ids, [901, 902], embedder=lambda t: [0.0] * 384, store=store)
    assert sorted(p for p, _ in store.inserted) == sorted(ids) and store.deleted == [901, 902]
    payload = dict(store.inserted)[ids[0]]
    assert payload["type"] == "task" and payload["board_id"] == 1 and "[FR-" in payload["title"]


def test_index_failures_never_raise():
    seed()
    make_client(1).post("/boards/1/srs/generate-board", json={})
    ids = [t.id for t in board_rows()[1]]

    class Broken(FakeStore):
        def insert_vector(self, *a, **k): raise RuntimeError("qdrant down")
        def delete_vector(self, *a): raise RuntimeError("qdrant down")
    board_service.index_tasks(ids, [1], embedder=lambda t: [0.0], store=Broken())
    board_service.index_tasks(ids, [], embedder=lambda t: 1 / 0, store=FakeStore())
    board_service.index_tasks([], [])                            # nothing to do, imports nothing


def test_route_does_not_import_qdrant_at_import_time():
    import sys
    assert "app.rag.qdrant_service" not in sys.modules
