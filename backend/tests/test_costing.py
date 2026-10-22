"""Issue #7: Costing tab (expense categories, activity roll-up, finance integration)."""
from decimal import Decimal
from types import SimpleNamespace as NS
from datetime import date

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.database import Base, SessionLocal, engine
from app.models.board import Board
from app.models.chat import Chat  # noqa: F401
from app.models.expense import Expense  # noqa: F401
from app.models.gantt import Activity  # noqa: F401
from app.models.otp import OTP  # noqa: F401
from app.models.rbac import BoardMember  # noqa: F401
from app.models.sdd import SDDDocument, SDDJob  # noqa: F401
from app.models.srs import CostEstimate, Diagram, DiagramJob, SRSDocument, SRSJob  # noqa: F401
from app.models.user import User
from app.routes import costing as costing_routes
from app.routes import gantt as gantt_routes
from app.routes.auth import get_current_user
from app.services import costing_calculator as K
from app.services import gantt_calculator as C

D = Decimal


def act(id, est=0, actual=0, phase="Build"):
    return NS(id=id, name=f"A{id}", phase=phase, start_date=date(2026, 3, 1), end_date=date(2026, 3, 10),
              planned_hours=0, actual_hours=0, progress_pct=0, depends_on=[], estimated_cost=est, actual_cost=actual)


def exp(id, cat, est, actual, activity_id=None):
    return NS(id=id, category=cat, estimated_amount=est, actual_amount=actual, activity_id=activity_id)


# ---------------------------------------------------------------- pure
def test_lines_override_manual_cost_and_project_level_is_added():
    acts = [act(1, est=1000, actual=900), act(2, est=500, actual=0)]
    exps = [exp(1, "labour", 300, 350, 1), exp(2, "tools", 100, 80, 1), exp(3, "infrastructure", 200, 220, None)]
    eff, x_est, x_act, x_count = K.apply_expenses(acts, exps)
    assert (eff[0].estimated_cost, eff[0].actual_cost, eff[0].cost_source, eff[0].expense_count) == (D(400), D(430), "expenses", 2)
    assert (eff[1].estimated_cost, eff[1].cost_source) == (D(500), "manual")      # no lines: manual value kept
    assert (x_est, x_act, x_count) == (D(200), D(220), 1)
    s = C.finance_summary(10_000, [], eff, x_est, x_act)
    assert s["estimated_total"] == D(1100) and s["actual_total"] == D(650)       # nothing counted twice


def test_deleted_activity_expense_counts_as_project_level():
    eff, x_est, _, n = K.apply_expenses([act(1)], [exp(1, "other", 50, 0, activity_id=99)])
    assert x_est == D(50) and n == 1


def test_category_breakdown_adds_up_to_total_and_flags_overrun():
    acts = [act(1, est=1000, actual=1200), act(2, est=500, actual=100)]
    exps = [exp(1, "labour", 300, 400, 2), exp(2, "infrastructure", 100, 50, None)]
    rows = {r["category"]: r for r in K.category_breakdown(acts, exps)}
    assert set(rows) == {"labour", "infrastructure", "unallocated"}            # act 1 has no lines
    assert rows["unallocated"]["estimated"] == D(1000) and rows["unallocated"]["overrun"] is True
    assert rows["labour"]["overrun"] is True and rows["infrastructure"]["overrun"] is False
    assert sum(r["actual"] for r in rows.values()) == D(1650)
    assert round(sum(r["share_pct"] for r in rows.values())) == 100


def test_breakdown_empty_and_zero_estimate_safe():
    assert K.category_breakdown([], []) == []
    r = K.category_breakdown([], [exp(1, "travel", 0, 40)])[0]
    assert r["variance_pct"] is None and r["variance"] == D(40)


# ---------------------------------------------------------------- API
@pytest.fixture(autouse=True)
def fresh_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    db.add_all([User(id=1, name="A", email="a@a.com"), User(id=2, name="B", email="b@b.com"), User(id=3, name="C", email="c@c.com")])
    db.add_all([Board(id=1, name="Lib", description="x", owner_id=1), Board(id=2, name="Other", description="x", owner_id=2)])
    db.add(BoardMember(board_id=1, user_id=3, role="editor"))
    db.commit(); db.close()
    yield


def client(uid=1):
    app = FastAPI()
    app.include_router(gantt_routes.router)
    app.include_router(costing_routes.router)
    app.dependency_overrides[get_current_user] = lambda: type("U", (), {"id": uid})()
    return TestClient(app)


ACT = {"name": "Build", "phase": "Build", "start_date": "2026-03-01", "end_date": "2026-03-10", "estimated_cost": "1000", "actual_cost": "900"}
EXP = {"category": "labour", "description": "Developer time", "estimated_amount": "300", "actual_amount": "350"}


def test_expense_flow_and_payload_integration():
    c = client()
    aid = c.post("/boards/1/activities", json=ACT).json()["id"]
    c.put("/boards/1/budget", json={"base_budget": "5000"})
    j = c.get("/boards/1/gantt").json()
    assert j["activities"][0]["cost_source"] == "manual" and j["summary"]["estimated_total"] == "1000.00"

    c.post("/boards/1/expenses", json={**EXP, "activity_id": aid})
    c.post("/boards/1/expenses", json={"category": "infrastructure", "description": "Hosting", "estimated_amount": "200", "actual_amount": "260"})
    j = c.get("/boards/1/gantt").json()
    a = j["activities"][0]
    assert a["cost_source"] == "expenses" and a["expense_count"] == 1 and a["estimated_cost"] == "300.00"
    assert j["project_level"] == {"estimated": "200.00", "actual": "260.00", "count": 1}
    assert j["summary"]["estimated_total"] == "500.00" and j["summary"]["actual_total"] == "610.00"
    assert j["summary"]["remaining_funds"] == "4390.00"
    cats = {r["category"]: r for r in j["categories"]}
    assert cats["labour"]["actual"] == "350.00" and cats["infrastructure"]["overrun"] is True
    assert len(j["expenses"]) == 2 and j["expenses"][0]["variance"] == "50.00"


def test_expenses_trigger_insufficient_funds():
    c = client()
    c.put("/boards/1/budget", json={"base_budget": "100"})
    c.post("/boards/1/expenses", json={**EXP, "actual_amount": "500"})
    codes = [a["code"] for a in c.get("/boards/1/gantt").json()["summary"]["alerts"]]
    assert "insufficient_funds" in codes


def test_update_delete_and_clear_activity():
    c = client()
    aid = c.post("/boards/1/activities", json=ACT).json()["id"]
    eid = c.post("/boards/1/expenses", json={**EXP, "activity_id": aid}).json()["id"]
    r = c.patch(f"/boards/1/expenses/{eid}", json={"actual_amount": "400", "clear_activity": True})
    assert r.json()["activity_id"] is None and r.json()["actual_amount"] == "400.00"
    assert c.get("/boards/1/gantt").json()["activities"][0]["cost_source"] == "manual"
    assert c.delete(f"/boards/1/expenses/{eid}").status_code == 204
    assert c.get("/boards/1/gantt").json()["expenses"] == []


def test_deleting_an_activity_keeps_its_expenses_as_project_level():
    c = client()
    aid = c.post("/boards/1/activities", json=ACT).json()["id"]
    c.post("/boards/1/expenses", json={**EXP, "activity_id": aid})
    c.delete(f"/boards/1/activities/{aid}")
    j = c.get("/boards/1/gantt").json()
    assert j["expenses"][0]["activity_id"] is None and j["project_level"]["count"] == 1


def test_validation():
    c = client()
    assert c.post("/boards/1/expenses", json={**EXP, "category": "snacks"}).status_code == 422
    assert c.post("/boards/1/expenses", json={**EXP, "estimated_amount": "-1"}).status_code == 422
    assert c.post("/boards/1/expenses", json={**EXP, "description": ""}).status_code == 422
    assert c.post("/boards/1/expenses", json={**EXP, "activity_id": 999}).status_code == 404


def test_ownership_roles_and_foreign_ids():
    mine = client(1)
    eid = mine.post("/boards/1/expenses", json=EXP).json()["id"]
    other = client(2)
    for method, url, body in [("post", "/boards/1/expenses", EXP), ("patch", f"/boards/1/expenses/{eid}", {"actual_amount": "1"}),
                              ("delete", f"/boards/1/expenses/{eid}", None)]:
        r = getattr(other, method)(url, **({"json": body} if body else {}))
        assert r.status_code == 404, (method, r.status_code)
    foreign = other.post("/boards/2/expenses", json=EXP).json()["id"]
    assert mine.patch(f"/boards/1/expenses/{foreign}", json={"actual_amount": "1"}).status_code == 404
    # an editor may change activities but not money
    assert client(3).post("/boards/1/expenses", json=EXP).status_code == 403
    assert client(3).post("/boards/1/activities", json=ACT).status_code == 201
