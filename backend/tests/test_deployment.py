"""Issue #7: Document tab (stack -> suggestions with pricing -> selection -> generated document)."""
import json

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.database import Base, SessionLocal, engine
from app.models.board import Board
from app.models.chat import Chat  # noqa: F401
from app.models.deployment import DeploymentDoc, DeploymentPlan  # noqa: F401
from app.models.otp import OTP  # noqa: F401
from app.models.rbac import BoardMember  # noqa: F401
from app.models.sdd import SDDDocument, SDDJob  # noqa: F401
from app.models.srs import CostEstimate, Diagram, DiagramJob, SRSDocument, SRSJob  # noqa: F401
from app.models.user import User
from app.routes import deployment as dep_routes
from app.routes.auth import get_current_user
from app.services import deployment_catalog as D

STACK = {"frontend": "react", "backend": "fastapi", "database": "postgresql", "scale": "small", "extras": ["cache", "monitoring"]}


# ---------------------------------------------------------------- pure
def test_catalog_is_valid_and_honest_about_pricing():
    cat = D.load_catalog()
    assert len(cat["services"]) >= 30 and cat["pricing_status"]["verified"] is False
    for s in cat["services"]:
        for scale in ("small", "medium", "large"):
            plan, usd = s["plans"][scale]
            assert isinstance(plan, str) and usd >= 0


def test_needed_layers_follow_the_stack():
    assert D.needed_categories(STACK) == ["frontend_hosting", "backend_hosting", "database_hosting", "cache", "monitoring"]
    none = {**STACK, "frontend": "none", "backend": "none", "database": "none", "extras": []}
    assert D.needed_categories(none) == []


def test_services_are_filtered_by_what_they_support():
    layers = {l["category"]: l for l in D.suggest(STACK)}
    db_ids = {o["service_id"] for o in layers["database_hosting"]["options"]}
    assert "neon" in db_ids and "mongodb_atlas" not in db_ids                  # PostgreSQL only
    mongo = {l["category"]: l for l in D.suggest({**STACK, "database": "mongodb"})}
    assert {o["service_id"] for o in mongo["database_hosting"]["options"]} == {"mongodb_atlas"}
    assert "vercel" not in {o["service_id"] for o in layers["backend_hosting"]["options"]}


def test_recommendation_and_pricing_scale_with_size():
    small = D.suggest(STACK)[1]["options"][0]
    large = D.suggest({**STACK, "scale": "large"})[1]["options"][0]
    assert small["recommended"] is True and large["monthly_usd"] > small["monthly_usd"]
    assert small["monthly_pkr"] == round(small["monthly_usd"] * D.load_catalog()["currency"]["usd_to_pkr"])
    assert small["verified"] is False and small["source"] and small["last_updated"]


def test_resolve_rejects_bad_choices():
    layers = D.suggest(STACK)
    ok = {l["category"]: l["options"][0]["service_id"] for l in layers}
    D.resolve_selection(STACK, ok)
    with pytest.raises(ValueError, match="Choose a service"):
        D.resolve_selection(STACK, {k: v for k, v in ok.items() if k != "cache"})
    with pytest.raises(ValueError, match="not part of your stack"):
        D.resolve_selection(STACK, {**ok, "blockchain": "alchemy"})
    with pytest.raises(ValueError, match="not available"):
        D.resolve_selection(STACK, {**ok, "database_hosting": "mongodb_atlas"})
    with pytest.raises(ValueError, match="not available"):
        D.resolve_selection(STACK, {**ok, "backend_hosting": "no_such_service"})


def test_document_is_deterministic_and_complete():
    layers = D.suggest(STACK)
    r = D.resolve_selection(STACK, {l["category"]: l["options"][0]["service_id"] for l in layers})
    t = D.totals(r)
    kw = dict(version=2, generated_on="2026-10-22", domain="lib.pk", environments=["production"], notes="Use region ap-south")
    a, b = D.render_document("Library", STACK, r, t, **kw), D.render_document("Library", STACK, r, t, **kw)
    assert a == b
    for h in ("# Deployment Document: Library", "## 2. Technology stack", "## 3. Selected services", "## 5. Configuration",
              "## 6. Deployment steps", "## 8. Cost summary", "## 9. Price sources", "Use region ap-south", "`DATABASE_URL`", "`VITE_API_URL`"):
        assert h in a, h
    assert "Pricing warning" in a and "lib.pk" in a


# ---------------------------------------------------------------- API
@pytest.fixture(autouse=True)
def fresh_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    db.add_all([User(id=1, name="A", email="a@a.com"), User(id=2, name="B", email="b@b.com"), User(id=3, name="C", email="c@c.com")])
    db.add_all([Board(id=1, name="Lib", description="x", owner_id=1), Board(id=2, name="Other", description="x", owner_id=2)])
    db.add(BoardMember(board_id=1, user_id=3, role="viewer"))
    db.commit(); db.close()
    yield


def client(uid=1):
    app = FastAPI()
    app.include_router(dep_routes.router)
    app.dependency_overrides[get_current_user] = lambda: type("U", (), {"id": uid})()
    return TestClient(app)


def pick(c, stack=STACK):
    layers = c.post("/boards/1/deployment/suggest", json=stack).json()["layers"]
    return {l["category"]: l["options"][0]["service_id"] for l in layers}


def test_options_and_suggest():
    c = client()
    o = c.get("/boards/1/deployment/options").json()
    assert {"frontend", "backend", "database", "scale"} <= set(o["stack"]) and o["pricing_status"]["verified"] is False
    assert o["can_edit"] is True and client(3).get("/boards/1/deployment/options").json()["can_edit"] is False
    s = c.post("/boards/1/deployment/suggest", json=STACK).json()
    assert [l["category"] for l in s["layers"]][:3] == ["frontend_hosting", "backend_hosting", "database_hosting"]
    assert all(l["options"][0]["recommended"] for l in s["layers"]) and s["currency"]["usd_to_pkr"] > 0


def test_generate_versions_and_history():
    c = client()
    body = {"stack": STACK, "selected": pick(c), "domain": "Lib.PK", "environments": ["production", "staging"], "notes": "Note A"}
    r = c.post("/boards/1/deployment/generate", json=body)
    assert r.status_code == 201
    j = r.json()
    assert j["version"] == 1 and "# Deployment Document: Lib" in j["document_md"] and j["options"]["domain"] == "lib.pk"
    assert c.post("/boards/1/deployment/generate", json={**body, "notes": "Note B"}).json()["version"] == 2
    plans = c.get("/boards/1/deployment/plans").json()
    assert [p["version"] for p in plans] == [2, 1] and "document_md" not in plans[0]
    assert "Note A" in c.get(f"/boards/1/deployment/plans/{plans[1]['id']}").json()["document_md"]


def test_generate_validation():
    c = client()
    sel = pick(c)
    bad = [{"stack": {**STACK, "frontend": "cobol"}, "selected": sel},
           {"stack": {**STACK, "extras": ["teleporter"]}, "selected": sel},
           {"stack": STACK, "selected": {k: v for k, v in sel.items() if k != "database_hosting"}},
           {"stack": STACK, "selected": {**sel, "database_hosting": "mongodb_atlas"}},
           {"stack": STACK, "selected": sel, "domain": "http://evil.com/x"},
           {"stack": STACK, "selected": sel, "environments": []},
           {"stack": STACK, "selected": sel, "notes": "x" * 4001}]
    for b in bad:
        assert c.post("/boards/1/deployment/generate", json=b).status_code == 422, b


def test_supporting_docs_crud_and_url_safety():
    c = client()
    d = c.post("/boards/1/deployment/docs", json={"title": "Server config", "category": "configuration", "content": "nginx.conf notes", "url": "https://x.com/a"}).json()
    assert c.patch(f"/boards/1/deployment/docs/{d['id']}", json={"content": "updated"}).json()["content"] == "updated"
    assert len(c.get("/boards/1/deployment/docs").json()) == 1
    assert c.post("/boards/1/deployment/docs", json={"title": "x", "url": "javascript:alert(1)"}).status_code == 422
    assert c.post("/boards/1/deployment/docs", json={"title": "x", "category": "weird"}).status_code == 422
    assert c.delete(f"/boards/1/deployment/docs/{d['id']}").status_code == 204
    assert c.get("/boards/1/deployment/docs").json() == []


def test_ownership_roles_and_401():
    mine = client(1)
    sel = pick(mine)
    plan = mine.post("/boards/1/deployment/generate", json={"stack": STACK, "selected": sel}).json()
    doc = mine.post("/boards/1/deployment/docs", json={"title": "t"}).json()
    other = client(2)
    calls = [("get", "/boards/1/deployment/options", None), ("post", "/boards/1/deployment/suggest", STACK),
             ("post", "/boards/1/deployment/generate", {"stack": STACK, "selected": sel}), ("get", "/boards/1/deployment/plans", None),
             ("get", f"/boards/1/deployment/plans/{plan['id']}", None), ("get", "/boards/1/deployment/docs", None),
             ("post", "/boards/1/deployment/docs", {"title": "t"}), ("patch", f"/boards/1/deployment/docs/{doc['id']}", {"title": "z"}),
             ("delete", f"/boards/1/deployment/docs/{doc['id']}", None)]
    for m, u, b in calls:
        assert getattr(other, m)(u, **({"json": b} if b else {})).status_code == 404, (m, u)
    # a plan/doc id from board 2 on board 1's path is a 404
    viewer = client(3)
    assert viewer.get("/boards/1/deployment/plans").status_code == 200
    assert viewer.post("/boards/1/deployment/generate", json={"stack": STACK, "selected": sel}).status_code == 403
    assert viewer.post("/boards/1/deployment/docs", json={"title": "t"}).status_code == 403
    app = FastAPI(); app.include_router(dep_routes.router)
    assert TestClient(app).get("/boards/1/deployment/plans").status_code == 401


# ---------------------------------------------------------------- add hosting cost to Costing
from app.routes import gantt as gantt_routes  # noqa: E402
from app.routes import costing as costing_routes  # noqa: E402


def full_client(uid=1):
    app = FastAPI()
    for r in (dep_routes.router, gantt_routes.router, costing_routes.router):
        app.include_router(r)
    app.dependency_overrides[get_current_user] = lambda: type("U", (), {"id": uid})()
    return TestClient(app)


PAID = {"frontend": "react", "backend": "fastapi", "database": "postgresql", "scale": "medium", "extras": []}


def make_plan(c, stack=PAID, notes=None):
    layers = c.post("/boards/1/deployment/suggest", json=stack).json()["layers"]
    sel = {l["category"]: l["options"][0]["service_id"] for l in layers}
    return c.post("/boards/1/deployment/generate", json={"stack": stack, "selected": sel, "notes": notes}).json()


def test_add_to_costing_creates_infrastructure_lines():
    c = full_client()
    plan = make_plan(c)
    r = c.post(f"/boards/1/deployment/plans/{plan['id']}/add-to-costing", json={"months": 12})
    assert r.status_code == 200
    j = r.json()
    assert j["added"] == 3 and j["months"] == 12 and j["removed"] == 0
    g = c.get("/boards/1/gantt").json()
    lines = g["expenses"]
    assert len(lines) == 3 and all(l["category"] == "infrastructure" and l["activity_id"] is None for l in lines)
    assert all(l["description"].startswith("Deployment v1:") and l["actual_amount"] == "0.00" for l in lines)
    assert g["summary"]["estimated_total"] == j["estimated_total"]
    assert float(j["estimated_total"]) == plan["totals"]["monthly_pkr"] * 12


def test_add_to_costing_twice_never_double_counts_and_keeps_actuals():
    c = full_client()
    p1 = make_plan(c)
    c.post(f"/boards/1/deployment/plans/{p1['id']}/add-to-costing", json={"months": 6})
    first = c.get("/boards/1/gantt").json()["expenses"]
    c.patch(f"/boards/1/expenses/{first[0]['id']}", json={"actual_amount": "500"})   # someone recorded real spending
    p2 = make_plan(c, notes="v2")
    r = c.post(f"/boards/1/deployment/plans/{p2['id']}/add-to-costing", json={"months": 12}).json()
    assert r["removed"] == 2 and r["kept"] == 1 and r["added"] == 3
    lines = c.get("/boards/1/gantt").json()["expenses"]
    assert len(lines) == 4
    assert sum(1 for l in lines if l["description"].startswith("Deployment v2:")) == 3
    assert any(l["actual_amount"] == "500.00" and l["description"].startswith("Deployment v1:") for l in lines)


def test_add_to_costing_free_stack_and_bad_months():
    c = full_client()
    free = {**PAID, "scale": "small", "frontend": "static", "backend": "none", "database": "none"}
    layers = c.post("/boards/1/deployment/suggest", json=free).json()["layers"]
    cf = next(o for o in layers[0]["options"] if o["monthly_usd"] == 0)
    plan = c.post("/boards/1/deployment/generate", json={"stack": free, "selected": {"frontend_hosting": cf["service_id"]}}).json()
    r = c.post(f"/boards/1/deployment/plans/{plan['id']}/add-to-costing", json={"months": 12})
    assert r.status_code == 422 and "free" in r.json()["detail"]
    paid = make_plan(c)
    for m in (0, 61, "x"):
        assert c.post(f"/boards/1/deployment/plans/{paid['id']}/add-to-costing", json={"months": m}).status_code == 422


def test_add_to_costing_permissions_and_ownership():
    c = full_client()
    plan = make_plan(c)
    url = f"/boards/1/deployment/plans/{plan['id']}/add-to-costing"
    assert full_client(2).post(url, json={"months": 12}).status_code == 404       # not a member
    assert full_client(3).post(url, json={"months": 12}).status_code == 403       # viewer
    assert c.post("/boards/1/deployment/plans/9999/add-to-costing", json={"months": 12}).status_code == 404
    assert c.get("/boards/1/deployment/options").json()["can_manage_finance"] is True
    assert full_client(3).get("/boards/1/deployment/options").json()["can_manage_finance"] is False
