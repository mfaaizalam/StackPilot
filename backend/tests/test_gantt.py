"""Issue #9 tests: Gantt, time allocation, cost and finance tracking.
Pure-function tests first, then API tests (SQLite, fake LLM, no network)."""
from datetime import date, timedelta
from decimal import Decimal
from types import SimpleNamespace as NS

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.database import Base, SessionLocal, engine
from app.models.board import Board
from app.models.chat import Chat  # noqa: F401
from app.models.column import BoardColumn
from app.models.gantt import Activity  # noqa: F401
from app.models.otp import OTP  # noqa: F401
from app.models.rbac import BoardMember  # noqa: F401
from app.models.sdd import SDDDocument, SDDJob  # noqa: F401
from app.models.srs import CostEstimate, Diagram, DiagramJob, SRSDocument, SRSJob  # noqa: F401
from app.models.task import Task
from app.models.user import User
from app.routes import gantt as gantt_routes
from app.routes.auth import get_current_user
from app.services import gantt_calculator as C

D = Decimal
TODAY = date(2026, 3, 11)


def act(id=1, s="2026-03-01", e="2026-03-20", est=1000, actual=0, ph=0, ah=0, prog=0, deps=None, phase="Build"):
    return NS(id=id, start_date=date.fromisoformat(s), end_date=date.fromisoformat(e), estimated_cost=est,
              actual_cost=actual, planned_hours=ph, actual_hours=ah, progress_pct=prog,
              depends_on=deps or [], phase=phase)


def inc(id, amount, d, status, phase=None, activity_id=None):
    return NS(id=id, amount=amount, effective_date=date.fromisoformat(d), status=status,
              phase=phase, activity_id=activity_id)


# ------------------------------------------------------------------ pure: activities
def test_duration_is_inclusive():
    assert C.duration_days(date(2026, 3, 1), date(2026, 3, 1)) == 1
    assert C.duration_days(date(2026, 3, 1), date(2026, 3, 10)) == 10


def test_elapsed_pct_bounds():
    assert C.elapsed_pct(date(2026, 3, 10), date(2026, 3, 20), date(2026, 3, 1)) == 0
    assert C.elapsed_pct(date(2026, 3, 10), date(2026, 3, 20), date(2026, 4, 1)) == 100


def test_cost_and_time_overrun_flags():
    m = C.activity_metrics(act(est=1000, actual=1200, ph=10, ah=12, prog=50), TODAY)
    assert "cost_overrun" in m["flags"] and "time_overrun" in m["flags"]
    assert m["cost_variance"] == D(200) and m["cost_variance_pct"] == 20.0 and m["hours_variance"] == D(2)


def test_zero_estimate_does_not_divide_by_zero():
    m = C.activity_metrics(act(est=0, actual=50), TODAY)
    assert m["cost_variance_pct"] is None and m["budget_used_pct"] is None
    assert "unbudgeted_cost" in m["flags"]


def test_behind_schedule_threshold():
    # 03-01..03-20 is 20 days; on 03-11 that is 50% elapsed
    assert "behind_schedule" not in C.activity_metrics(act(prog=40), TODAY)["flags"]   # within 15 points
    assert "behind_schedule" in C.activity_metrics(act(prog=30), TODAY)["flags"]
    assert "behind_schedule" not in C.activity_metrics(act(prog=100), TODAY)["flags"]


def test_overdue_and_burn_flags():
    assert "overdue" in C.activity_metrics(act(e="2026-03-05", prog=90), TODAY)["flags"]
    assert "burning_faster_than_progress" in C.activity_metrics(act(est=1000, actual=900, prog=20), TODAY)["flags"]


def test_dependency_conflict_detected():
    a, b = act(id=1, s="2026-03-01", e="2026-03-10"), act(id=2, s="2026-03-05", e="2026-03-12", deps=[1])
    assert C.schedule_conflicts([a, b]) == {2: [1]}
    b2 = act(id=2, s="2026-03-11", e="2026-03-12", deps=[1])
    assert C.schedule_conflicts([a, b2]) == {}


# ------------------------------------------------------------------ pure: dependencies
def test_cycle_missing_and_self_dependency_rejected():
    C.validate_dependencies({1: [], 2: [1], 3: [1, 2]})
    with pytest.raises(ValueError):
        C.validate_dependencies({1: [2], 2: [1]})
    with pytest.raises(ValueError):
        C.validate_dependencies({1: [9]})
    with pytest.raises(ValueError):
        C.validate_dependencies({1: [1]})


def test_plan_schedule_follows_dependencies():
    plan = C.plan_schedule([{"key": "b", "days": 2, "deps": ["a"]}, {"key": "a", "days": 3, "deps": []}], date(2026, 3, 1))
    assert plan["a"] == (date(2026, 3, 1), date(2026, 3, 3))
    assert plan["b"] == (date(2026, 3, 4), date(2026, 3, 5))


def test_plan_schedule_survives_a_loop_and_fixed_ends():
    plan = C.plan_schedule([{"key": "a", "days": 1, "deps": ["b"]}, {"key": "b", "days": 1, "deps": ["a"]}], date(2026, 3, 1))
    assert set(plan) == {"a", "b"}
    plan = C.plan_schedule([{"key": "n", "days": 1, "deps": ["old"]}], date(2026, 3, 1), {"old": date(2026, 3, 9)})
    assert plan["n"][0] == date(2026, 3, 10)


# ------------------------------------------------------------------ pure: finance
def test_base_only():
    s = C.finance_summary(1000, [], [act(est=400, actual=100)])
    assert s["committed_budget"] == s["available_funds"] == s["forecast_budget"] == D(1000)
    assert s["remaining_funds"] == D(900) and s["alerts"] == []


def test_statuses_split_correctly():
    incs = [inc(1, 100, "2026-01-01", "planned"), inc(2, 200, "2026-02-01", "approved"), inc(3, 400, "2026-03-01", "disbursed")]
    s = C.finance_summary(1000, incs, [])
    assert s["committed_budget"] == D(1600)       # base + approved + disbursed
    assert s["available_funds"] == D(1400)        # base + disbursed only
    assert s["forecast_budget"] == D(1700)        # + planned
    assert s["awaiting_disbursement"] == D(200)


def test_timeline_sorted_by_date_even_if_input_is_not():
    incs = [inc(2, 300, "2026-05-01", "approved"), inc(1, 100, "2026-02-01", "planned")]
    t = C.finance_summary(1000, incs, [])["timeline"]
    assert [x["id"] for x in t] == [1, 2]
    assert [x["cumulative_budget"] for x in t] == [D(1100), D(1400)]
    assert [x["cumulative_committed"] for x in t] == [D(1000), D(1300)]   # planned is not committed


def test_insufficient_funds_and_planned_does_not_help():
    acts = [act(est=500, actual=1200)]
    s = C.finance_summary(1000, [inc(1, 5000, "2026-03-01", "planned")], acts)
    codes = {a["code"] for a in s["alerts"]}
    assert {"insufficient_funds", "over_committed_budget"} <= codes
    assert next(a for a in s["alerts"] if a["code"] == "insufficient_funds")["amount"] == D(200)


def test_approved_but_not_disbursed_is_committed_not_available():
    s = C.finance_summary(1000, [inc(1, 500, "2026-03-01", "approved")], [act(est=500, actual=1200)])
    codes = {a["code"] for a in s["alerts"]}
    assert "insufficient_funds" in codes and "over_committed_budget" not in codes


def test_low_funds_warning_and_estimate_warning():
    s = C.finance_summary(1000, [], [act(est=400, actual=950)])
    assert "funds_running_low" in {a["code"] for a in s["alerts"]}
    s = C.finance_summary(1000, [], [act(est=2000, actual=0)])
    assert "estimate_exceeds_forecast" in {a["code"] for a in s["alerts"]}


def test_money_stays_decimal_exact():
    s = C.finance_summary("0.10", [inc(1, "0.20", "2026-01-01", "disbursed")], [])
    assert s["available_funds"] == D("0.30")


def test_phase_summary_flags_overspent_phase():
    acts = [act(id=1, phase="Design", est=100, actual=300), act(id=2, phase="Build", est=100, actual=50)]
    incs = [inc(1, 200, "2026-01-01", "approved", phase="Design"), inc(2, 50, "2026-01-02", "approved", activity_id=2)]
    rows = {r["phase"]: r for r in C.phase_summary(incs, acts)}
    assert "phase_overspent" in rows["Design"]["alerts"] and "cost_overrun" in rows["Design"]["alerts"]
    assert rows["Build"]["committed_funding"] == D(50) and rows["Build"]["alerts"] == []


# ------------------------------------------------------------------ API
@pytest.fixture(autouse=True)
def fresh_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


def make_client(user_id=1):
    app = FastAPI()
    app.include_router(gantt_routes.router)
    app.dependency_overrides[get_current_user] = lambda: type("U", (), {"id": user_id})()
    return TestClient(app)


def seed_board(with_tasks=False, with_estimate=False):
    db = SessionLocal()
    db.add_all([User(id=1, name="A", email="a@a.com"), User(id=2, name="B", email="b@b.com"),
                User(id=3, name="C", email="c@c.com")])
    db.add(Board(id=1, name="Lib", description="x", owner_id=1))
    db.add(Board(id=2, name="Other", description="x", owner_id=2))
    db.add(BoardMember(board_id=1, user_id=3, role="viewer"))
    db.commit()
    if with_tasks:
        col = BoardColumn(id=1, name="Backlog", board_id=1)
        done = BoardColumn(id=2, name="Done", board_id=1)
        db.add_all([col, done])
        db.commit()
        db.add_all([Task(id=1, title="FR-001 Login", column_id=1, requirement_id="FR-001", estimate_points=4, depends_on=[]),
                    Task(id=2, title="FR-002 Search", column_id=1, requirement_id="FR-002", estimate_points=2, depends_on=["FR-001"]),
                    Task(id=3, title="NFR-001 Speed", column_id=2, requirement_id="NFR-001", estimate_points=2, depends_on=[])])
        db.commit()
    if with_estimate:
        db.add(CostEstimate(board_id=1, user_id=1, srs_id=1, inputs={}, result={"pert": {"total": 800000, "pm": 5}}))
        db.commit()
    db.close()


ACT = {"name": "Build login", "phase": "Build", "start_date": "2026-03-01", "end_date": "2026-03-10",
       "planned_hours": "40", "estimated_cost": "10000"}


def test_empty_board_payload():
    seed_board()
    r = make_client().get("/boards/1/gantt")
    assert r.status_code == 200
    j = r.json()
    assert j["activities"] == [] and j["summary"]["available_funds"] == "0.00" and j["can_edit"] is True


def test_activity_crud_and_money_as_strings():
    seed_board()
    c = make_client()
    aid = c.post("/boards/1/activities", json=ACT).json()["id"]
    assert c.patch(f"/boards/1/activities/{aid}", json={"actual_cost": "12500.50", "progress_pct": 60}).status_code == 200
    a = c.get("/boards/1/gantt").json()["activities"][0]
    assert a["actual_cost"] == "12500.50" and a["cost_variance"] == "2500.50" and "cost_overrun" in a["flags"]
    assert a["duration_days"] == 10
    assert c.delete(f"/boards/1/activities/{aid}").status_code == 204
    assert c.get("/boards/1/gantt").json()["activities"] == []


def test_validation_rejects_bad_input():
    seed_board()
    c = make_client()
    assert c.post("/boards/1/activities", json={**ACT, "end_date": "2026-02-01"}).status_code == 422
    assert c.post("/boards/1/activities", json={**ACT, "estimated_cost": "-5"}).status_code == 422
    assert c.post("/boards/1/activities", json={**ACT, "progress_pct": 101}).status_code == 422
    aid = c.post("/boards/1/activities", json=ACT).json()["id"]
    assert c.patch(f"/boards/1/activities/{aid}", json={"end_date": "2026-02-01"}).status_code == 422
    assert c.post("/boards/1/finance-increments", json={"amount": "-1", "effective_date": "2026-03-01"}).status_code == 422
    assert c.post("/boards/1/finance-increments", json={"amount": "1", "effective_date": "2026-03-01", "status": "paid"}).status_code == 422


def test_dependency_cycle_and_foreign_ids_rejected():
    seed_board()
    c = make_client()
    a = c.post("/boards/1/activities", json=ACT).json()["id"]
    b = c.post("/boards/1/activities", json={**ACT, "depends_on": [a]}).json()["id"]
    r = c.patch(f"/boards/1/activities/{a}", json={"depends_on": [b]})
    assert r.status_code == 422 and "loop" in r.json()["detail"]
    assert c.patch(f"/boards/1/activities/{a}", json={"depends_on": [999]}).status_code == 422
    assert c.patch(f"/boards/1/activities/{a}", json={"depends_on": [a]}).status_code == 422


def test_finance_flow_and_status_transition():
    seed_board()
    c = make_client()
    assert c.put("/boards/1/budget", json={"base_budget": "100000"}).status_code == 200
    iid = c.post("/boards/1/finance-increments", json={"amount": "50000", "effective_date": "2026-04-01"}).json()["id"]
    s = c.get("/boards/1/gantt").json()["summary"]
    assert s["available_funds"] == "100000.00" and s["forecast_budget"] == "150000.00"
    assert c.patch(f"/boards/1/finance-increments/{iid}", json={"status": "disbursed"}).json()["status"] == "disbursed"
    s = c.get("/boards/1/gantt").json()["summary"]
    assert s["available_funds"] == "150000.00" and s["timeline"][0]["cumulative_budget"] == "150000.00"


def test_insufficient_funds_via_api():
    seed_board()
    c = make_client()
    c.put("/boards/1/budget", json={"base_budget": "1000"})
    c.post("/boards/1/activities", json={**ACT, "estimated_cost": "500", "actual_cost": "1500"})
    codes = [a["code"] for a in c.get("/boards/1/gantt").json()["summary"]["alerts"]]
    assert "insufficient_funds" in codes


def test_increment_must_target_an_activity_on_this_board():
    seed_board()
    c = make_client(2)
    other = c.post("/boards/2/activities", json=ACT).json()["id"]
    r = make_client(1).post("/boards/1/finance-increments", json={"amount": "5", "effective_date": "2026-03-01", "activity_id": other})
    assert r.status_code == 404


def test_other_user_gets_404_everywhere_and_no_token_401():
    seed_board()
    mine = make_client(1)
    aid = mine.post("/boards/1/activities", json=ACT).json()["id"]
    iid = mine.post("/boards/1/finance-increments", json={"amount": "5", "effective_date": "2026-03-01"}).json()["id"]
    c = make_client(2)
    calls = [("get", "/boards/1/gantt", None), ("post", "/boards/1/activities", ACT),
             ("patch", f"/boards/1/activities/{aid}", {"progress_pct": 5}), ("delete", f"/boards/1/activities/{aid}", None),
             ("post", "/boards/1/activities/seed", {"mode": "create"}), ("put", "/boards/1/budget", {"base_budget": "1"}),
             ("post", "/boards/1/finance-increments", {"amount": "5", "effective_date": "2026-03-01"}),
             ("patch", f"/boards/1/finance-increments/{iid}", {"status": "approved"}), ("delete", f"/boards/1/finance-increments/{iid}", None)]
    for method, url, body in calls:
        r = getattr(c, method)(url, **({"json": body} if body is not None else {}))
        assert r.status_code == 404, (method, url, r.status_code)
    # an id from board 2 used on board 1's path is also a 404
    other = make_client(2).post("/boards/2/activities", json=ACT).json()["id"]
    assert mine.patch(f"/boards/1/activities/{other}", json={"progress_pct": 5}).status_code == 404
    # no token at all
    app = FastAPI()
    app.include_router(gantt_routes.router)
    assert TestClient(app).get("/boards/1/gantt").status_code == 401


def test_viewer_can_read_but_not_write():
    seed_board()
    c = make_client(3)
    j = c.get("/boards/1/gantt").json()
    assert j["role"] == "viewer" and j["can_edit"] is False and j["can_manage_finance"] is False
    assert c.post("/boards/1/activities", json=ACT).status_code == 403
    assert c.put("/boards/1/budget", json={"base_budget": "1"}).status_code == 403


def test_seed_create_sync_and_idempotence():
    seed_board(with_tasks=True, with_estimate=True)
    c = make_client()
    r = c.post("/boards/1/activities/seed", json={"mode": "create"})
    assert r.status_code == 200 and r.json()["added"] == 3 and r.json()["used_cost_estimate"] is True
    assert c.post("/boards/1/activities/seed", json={"mode": "create"}).status_code == 409
    j = c.get("/boards/1/gantt").json()
    by = {a["name"][:6]: a for a in j["activities"]}
    assert by["FR-002"]["depends_on"] == [by["FR-001"]["id"]]
    assert by["FR-002"]["start_date"] > by["FR-001"]["end_date"]          # follows its dependency
    assert by["NFR-00"]["progress_pct"] == 100 and by["NFR-00"]["phase"] == "Non-functional"
    assert sum(float(a["estimated_cost"]) for a in j["activities"]) == pytest.approx(800000, abs=0.05)
    # sync adds nothing new...
    assert c.post("/boards/1/activities/seed", json={"mode": "sync"}).json()["added"] == 0
    # ...until a task without an activity appears
    db = SessionLocal()
    db.add(Task(id=9, title="FR-009 Reports", column_id=1, requirement_id="FR-009", estimate_points=3, depends_on=["FR-002"]))
    db.commit(); db.close()
    assert c.post("/boards/1/activities/seed", json={"mode": "sync"}).json()["added"] == 1
    assert len(c.get("/boards/1/gantt").json()["activities"]) == 4


def test_seed_without_tasks_is_422():
    seed_board()
    assert make_client().post("/boards/1/activities/seed", json={"mode": "create"}).status_code == 422
