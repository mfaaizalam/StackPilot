"""Phase 5 tests: Pakistan cost estimation. Fake LLM + SQLite, no keys, no network."""
import copy
import json

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.database import Base, SessionLocal, engine
from app.core.llm_fake import sample_requirements
from app.models.board import Board
from app.models.chat import Chat  # noqa: F401
from app.models.column import BoardColumn
from app.models.otp import OTP  # noqa: F401
from app.models.srs import CostEstimate, Diagram, DiagramJob, SRSDocument, SRSJob  # noqa: F401
from app.models.task import Task
from app.models.user import User
from app.routes import cost as cost_routes
from app.routes.auth import get_current_user
from app.schemas.cost import CostExplanation, CostRequest
from app.schemas.srs import Requirements
from app.services import cost_calculator as C
from app.services import cost_service
from app.services.cost_rates import RATES_PATH, RatesError, load_rates, unverified_items, validate_rates
from app.services.srs_service import save_srs
from app.services.srs_validator import validate_requirements


@pytest.fixture(autouse=True)
def fresh_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture
def raw():
    with open(RATES_PATH, encoding="utf-8") as f:
        return json.load(f)


def make_client(user_id):
    app = FastAPI()
    app.include_router(cost_routes.router)
    app.dependency_overrides[get_current_user] = lambda: type("U", (), {"id": user_id})()
    return TestClient(app)


def seed(with_srs=True):
    db = SessionLocal()
    db.add_all([User(id=1, name="A", email="a@a.com"), User(id=2, name="B", email="b@b.com")])
    db.add_all([Board(id=1, name="Library", description="x", owner_id=1)])
    db.commit()
    if with_srs:
        r = sample_requirements()
        save_srs(db, 1, "desc", [], r, validate_requirements(r))
    db.close()


def est(inp=None, req=None, rates=None):
    return C.estimate(req or sample_requirements(), inp or CostRequest(), rates or load_rates())


# ------------------------------------------------------------------ rate table
def test_shipped_rate_table_is_valid_and_flagged_unverified():
    t = load_rates()
    assert abs(sum(r.allocation for r in t.roles.values()) - 1) < 1e-9
    assert len(unverified_items(t)) >= 10  # honest: nothing is claimed as verified yet
    assert all(r.last_updated and r.source for r in t.roles.values())


def test_rate_table_rejects_bad_allocations(raw):
    raw["roles"]["qa"]["allocation"] = 0.5
    with pytest.raises(RatesError):
        validate_rates(raw)


def test_rate_table_rejects_min_above_max(raw):
    raw["roles"]["qa"]["monthly_min"] = 999999
    with pytest.raises(RatesError):
        validate_rates(raw)


def test_rate_table_rejects_missing_scenario(raw):
    del raw["scenarios"]["likely"]
    with pytest.raises(RatesError):
        validate_rates(raw)


def test_rate_table_rejects_missing_source(raw):
    del raw["roles"]["qa"]["source"]
    with pytest.raises(RatesError):
        validate_rates(raw)


def test_missing_rate_file_is_a_clean_error(tmp_path):
    with pytest.raises(RatesError):
        load_rates(tmp_path / "nope.json")


# ------------------------------------------------------------------ determinism and rate sensitivity
def test_same_input_same_numbers():
    assert est() == est()


def test_changing_a_rate_changes_the_result(raw):
    base = est()["pert"]["total"]
    raw["roles"]["senior_dev"]["monthly_max"] *= 2
    raw["roles"]["senior_dev"]["monthly_min"] *= 2
    higher = est(rates=validate_rates(raw))["pert"]["total"]
    assert higher > base


def test_changing_tax_and_contingency_changes_result(raw):
    base = est()
    raw["tax"]["pct"] = 0.0
    no_tax = est(rates=validate_rates(raw))
    assert no_tax["pert"]["groups"].get("tax", 0) == 0
    assert no_tax["pert"]["total"] < base["pert"]["total"]
    raw["contingency"]["pct"] = 0.0
    assert est(rates=validate_rates(raw))["pert"]["groups"].get("contingency", 0) == 0


def test_hosting_rate_flows_into_result(raw):
    base = est()["pert"]["total"]
    raw["monthly_costs"][0]["pkr_per_month"] += 100000
    assert est(rates=validate_rates(raw))["pert"]["total"] > base


# ------------------------------------------------------------------ the maths
def test_total_equals_sum_of_lines_in_every_scenario():
    r = est()
    assert r["pert"]["total"] == sum(ln["amount"] for ln in r["pert"]["lines"])
    assert r["pert"]["total"] == sum(r["pert"]["groups"].values())
    for s in r["scenarios"].values():
        assert s["total"] == sum(s["groups"].values())


def test_scenarios_are_ordered_and_pert_is_between():
    r = est()
    o, m, p = (r["scenarios"][k]["total"] for k in ("optimistic", "likely", "pessimistic"))
    assert o < m < p
    assert o <= r["pert"]["total"] <= p
    # PERT within rounding of the formula applied to the three totals
    assert abs(r["pert"]["total"] - (o + 4 * m + p) / 6) <= len(r["pert"]["lines"])


def test_pert_effort_matches_formula():
    r = est()
    s = r["scenarios"]
    expect = (s["optimistic"]["person_months"] + 4 * s["likely"]["person_months"] + s["pessimistic"]["person_months"]) / 6
    assert abs(r["effort"]["person_months"] - expect) < 0.02


def test_cocomo_value_matches_hand_calculation():
    # sample requirements: 8 simple FRs (3 each) + 3 entities (7 each) + 1 interface (5) = 50 FP
    r = est()
    assert r["size"]["ufp"] == 50
    ksloc = 50 * 45 / 1000
    likely_pm = 2.94 * ksloc ** 1.10
    assert abs(r["scenarios"]["likely"]["person_months"] - likely_pm) < 0.01
    tdev = 3.67 * likely_pm ** (0.28 + 0.2 * (1.10 - 0.91))
    assert abs(r["scenarios"]["likely"]["duration_months"] - tdev) < 0.06


def test_role_costs_sum_to_labour_and_shares_sum_to_one():
    r = est()
    assert abs(sum(x["share"] for x in r["roles"]) - 1) < 1e-9
    assert sum(x["cost"] for x in r["roles"]) == r["pert"]["groups"]["labour"]


def test_more_requirements_means_more_cost():
    small = sample_requirements()
    big = sample_requirements()
    extra = copy.deepcopy(big.functional_requirements[0])
    extra.id, extra.title = "FR-009", "Extra"
    big.functional_requirements += [extra] * 6
    assert est(req=big)["pert"]["total"] > est(req=small)["pert"]["total"]


def test_effort_multipliers_move_cost_in_the_right_direction():
    base = est()["pert"]["total"]
    assert est(CostRequest(complexity="high"))["pert"]["total"] > base
    assert est(CostRequest(complexity="low"))["pert"]["total"] < base
    assert est(CostRequest(reliability="high"))["pert"]["total"] > base
    assert est(CostRequest(team_experience="high"))["pert"]["total"] < base
    assert est(CostRequest(team_experience="low"))["pert"]["total"] > base
    assert est(CostRequest(platform="web_mobile"))["pert"]["total"] > base


def test_empty_requirements_raise():
    r = sample_requirements()
    r.functional_requirements, r.entities, r.external_interfaces = [], [], []
    with pytest.raises(ValueError):
        est(req=r)


def test_fr_and_entity_weights():
    assert C._fr_weight(2, 10) == ("simple", 3)
    assert C._fr_weight(3, 10) == ("average", 4)
    assert C._fr_weight(5, 10) == ("complex", 6)
    assert C._fr_weight(1, 41) == ("complex", 6)
    assert C._entity_weight(5)[1] == 7 and C._entity_weight(8)[1] == 10 and C._entity_weight(11)[1] == 15


# ------------------------------------------------------------------ sensitivity
def test_sensitivity_table_is_full_recomputation():
    r = est()
    rows = {s["label"]: s for s in r["sensitivity"]}
    assert rows["Base case"]["total"] == r["pert"]["total"] and rows["Base case"]["delta_pct"] == 0
    assert rows["Salaries -20%"]["total"] < r["pert"]["total"] < rows["Salaries +20%"]["total"]
    assert rows["Scope -30%"]["total"] < r["pert"]["total"] < rows["Scope +30%"]["total"]
    worst = next(v for k, v in rows.items() if k.startswith("Worst"))
    best = next(v for k, v in rows.items() if k.startswith("Best"))
    assert best["total"] < r["pert"]["total"] < worst["total"]
    # salary +20% moves labour exactly 20% (overhead is % of labour); total moves by less than 20%
    assert 0 < rows["Salaries +20%"]["delta_pct"] < 20
    # a scope change of +30% must cost at least ~ +25% (COCOMO exponent > 1)
    assert rows["Scope +30%"]["delta_pct"] > 25


# ------------------------------------------------------------------ ROI
def test_no_roi_without_revenue():
    assert est()["roi"] is None


def test_roi_with_revenue():
    r = est(CostRequest(expected_annual_revenue=20_000_000, horizon_years=3))
    roi = r["roi"]
    assert roi["annual_running_cost"] == int(round(r["pert"]["total"] * 0.18))
    assert roi["net_annual"] == 20_000_000 - roi["annual_running_cost"]
    assert roi["payback_months"] == round(r["pert"]["total"] / (roi["net_annual"] / 12), 1)
    assert roi["payback_months_best"] <= roi["payback_months"] <= roi["payback_months_worst"]
    assert roi["break_even_month_from_start"] > roi["payback_months"]
    assert len(roi["cumulative"]) == 3
    assert roi["cumulative"][0]["net_position"] == roi["net_annual"] - r["pert"]["total"]


def test_roi_when_running_cost_exceeds_revenue():
    r = est(CostRequest(expected_annual_revenue=1000, horizon_years=2))
    assert r["roi"]["payback_months"] is None and r["roi"]["break_even_month_from_start"] is None
    assert r["roi"]["roi_pct"] < 0 and "never pays back" in r["roi"]["note"]


# ------------------------------------------------------------------ cross-checks
def test_use_case_points_cross_check():
    r = est()
    u = r["cross_checks"]["use_case_points"]
    assert u["ucp"] == 34 and u["actor_weight"] == 9 and u["use_case_weight"] == 25
    assert u["agreement"] in ("close", "differs") and "board_points" not in r["cross_checks"]


def test_system_actor_counts_as_simple():
    req = sample_requirements()
    req.actors[0].name = "Payment Gateway"
    assert C.use_case_points(req, load_rates())["actor_weight"] == 1 + 3 + 3


# ------------------------------------------------------------------ explanation (AI only explains)
def test_template_explanation_uses_only_computed_numbers():
    r = est()
    exp = cost_service.template_explanation(r)
    figs = cost_service.figures(r)
    assert cost_service.explanation_is_safe(CostExplanation(**exp), figs)
    assert figs["expected_total_cost"] in exp["summary"]


def test_guard_rejects_invented_numbers():
    r = est()
    figs = cost_service.figures(r)
    ok = CostExplanation(summary=f"Total {figs['expected_total_cost']}.", key_drivers=["a"], risks=["b"], tips=["c"])
    assert cost_service.explanation_is_safe(ok, figs)
    bad = CostExplanation(summary="Total is PKR 1,234,567.", key_drivers=["a"], risks=["b"], tips=["c"])
    assert not cost_service.explanation_is_safe(bad, figs)
    bad2 = CostExplanation(summary="ok", key_drivers=["it takes 37 weeks"], risks=["b"], tips=["c"])
    assert not cost_service.explanation_is_safe(bad2, figs)
    small = CostExplanation(summary="ok", key_drivers=["Three risks, 2 tips"], risks=["b"], tips=["c"])
    assert cost_service.explanation_is_safe(small, figs)
    empty = CostExplanation(summary="  ", key_drivers=[], risks=[], tips=[])
    assert not cost_service.explanation_is_safe(empty, figs)


# ------------------------------------------------------------------ API
def test_api_estimate_and_latest():
    seed()
    c = make_client(1)
    assert c.get("/boards/1/srs/cost/").status_code == 404
    res = c.post("/boards/1/srs/cost/estimate", json={})
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["result"]["pert"]["total"] > 0 and body["explanation_source"] == "template"
    assert body["srs_outdated"] is False and body["srs_version"] == 1
    latest = c.get("/boards/1/srs/cost/").json()
    assert latest["id"] == body["id"] and latest["result"] == body["result"]


def test_api_same_request_same_numbers():
    seed()
    c = make_client(1)
    a = c.post("/boards/1/srs/cost/estimate", json={"platform": "mobile"}).json()["result"]
    b = c.post("/boards/1/srs/cost/estimate", json={"platform": "mobile"}).json()["result"]
    assert a == b


def test_api_validation_errors():
    seed()
    c = make_client(1)
    assert c.post("/boards/1/srs/cost/estimate", json={"platform": "toaster"}).status_code == 422
    assert c.post("/boards/1/srs/cost/estimate", json={"expected_annual_revenue": -5}).status_code == 422
    assert c.post("/boards/1/srs/cost/estimate", json={"horizon_years": 0}).status_code == 422


def test_api_no_srs_gives_404():
    seed(with_srs=False)
    assert make_client(1).post("/boards/1/srs/cost/estimate", json={}).status_code == 404


def test_api_damaged_srs_gives_422():
    seed()
    db = SessionLocal()
    d = db.query(SRSDocument).first()
    d.requirements = {"title": "broken"}
    db.commit()
    db.close()
    assert make_client(1).post("/boards/1/srs/cost/estimate", json={}).status_code == 422


def test_api_srs_outdated_flag():
    seed()
    c = make_client(1)
    c.post("/boards/1/srs/cost/estimate", json={})
    db = SessionLocal()
    r = sample_requirements()
    save_srs(db, 1, "desc", [], r, validate_requirements(r))
    db.close()
    assert c.get("/boards/1/srs/cost/").json()["srs_outdated"] is True


def test_api_explain_with_fake_ai():
    seed()
    c = make_client(1)
    eid = c.post("/boards/1/srs/cost/estimate", json={}).json()["id"]
    res = c.post(f"/boards/1/srs/cost/{eid}/explain")
    assert res.status_code == 200, res.text
    assert res.json()["explanation_source"] == "ai" and "notice" not in res.json()


def test_api_explain_falls_back_when_ai_invents_a_number(monkeypatch):
    seed()
    c = make_client(1)
    eid = c.post("/boards/1/srs/cost/estimate", json={}).json()["id"]
    monkeypatch.setattr(cost_service, "llm_json", lambda *a, **k: CostExplanation(
        summary="It will cost PKR 999,999,999.", key_drivers=["x"], risks=["y"], tips=["z"]))
    res = c.post(f"/boards/1/srs/cost/{eid}/explain").json()
    assert res["explanation_source"] == "template" and "notice" in res
    assert "999,999,999" not in json.dumps(res["explanation"])


def test_api_explain_when_ai_is_down(monkeypatch):
    seed()
    c = make_client(1)
    eid = c.post("/boards/1/srs/cost/estimate", json={}).json()["id"]
    from app.core.llm import LLMError

    def boom(*a, **k):
        raise LLMError("down")
    monkeypatch.setattr(cost_service, "llm_json", boom)
    assert c.post(f"/boards/1/srs/cost/{eid}/explain").status_code == 503
    assert c.get("/boards/1/srs/cost/").json()["explanation_source"] == "template"  # still usable


def test_api_explain_rate_limit():
    seed()
    c = make_client(1)
    eid = c.post("/boards/1/srs/cost/estimate", json={}).json()["id"]
    for _ in range(cost_service.MAX_EXPLAINS_PER_HOUR):
        assert c.post(f"/boards/1/srs/cost/{eid}/explain").status_code in (200,)
    # same row re-explained: still counts only one row, so use other rows to hit the limit
    db = SessionLocal()
    for _ in range(cost_service.MAX_EXPLAINS_PER_HOUR):
        row = db.query(CostEstimate).first()
        db.add(CostEstimate(board_id=1, user_id=1, srs_id=row.srs_id, inputs={}, result=row.result,
                            explained_at=row.explained_at))
    db.commit()
    db.close()
    assert c.post(f"/boards/1/srs/cost/{eid}/explain").status_code == 429


def test_api_estimate_rate_limit():
    seed()
    c = make_client(1)
    for _ in range(cost_service.MAX_ESTIMATES_PER_HOUR):
        assert c.post("/boards/1/srs/cost/estimate", json={}).status_code == 200
    assert c.post("/boards/1/srs/cost/estimate", json={}).status_code == 429


def test_api_rates_endpoint():
    seed()
    body = make_client(1).get("/boards/1/srs/cost/rates").json()
    assert body["meta"]["currency"] == "PKR" and len(body["unverified_items"]) >= 10
    assert "qa" in body["roles"]


def test_api_bad_rate_file_is_503(monkeypatch):
    seed()
    from app.services import cost_rates

    def bad(path=None):
        raise RatesError("boom")
    monkeypatch.setattr(cost_service, "load_rates", bad)
    assert make_client(1).post("/boards/1/srs/cost/estimate", json={}).status_code == 503


def test_api_board_points_cross_check():
    seed()
    db = SessionLocal()
    col = BoardColumn(name="Backlog", board_id=1)
    db.add(col)
    db.commit()
    srs_id = db.query(SRSDocument).first().id
    db.add_all([Task(title="t1", column_id=col.id, estimate_points=3, srs_id=srs_id, created_by=1),
                Task(title="t2", column_id=col.id, estimate_points=5, srs_id=srs_id, created_by=1),
                Task(title="hand-made", column_id=col.id, created_by=1)])
    db.commit()
    db.close()
    r = make_client(1).post("/boards/1/srs/cost/estimate", json={}).json()["result"]
    bp = r["cross_checks"]["board_points"]
    assert bp["total_points"] == 8 and bp["tasks"] == 2 and "not hours" in bp["note"]


# ------------------------------------------------------------------ ownership
def test_other_user_gets_404_everywhere():
    seed()
    mine = make_client(1)
    eid = mine.post("/boards/1/srs/cost/estimate", json={}).json()["id"]
    other = make_client(2)
    assert other.post("/boards/1/srs/cost/estimate", json={}).status_code == 404
    assert other.get("/boards/1/srs/cost/").status_code == 404
    assert other.get("/boards/1/srs/cost/rates").status_code == 404
    assert other.post(f"/boards/1/srs/cost/{eid}/explain").status_code == 404


def test_estimate_of_another_board_is_not_reachable():
    seed()
    db = SessionLocal()
    db.add(Board(id=2, name="Second", description="y", owner_id=1))
    db.commit()
    db.close()
    c = make_client(1)
    eid = c.post("/boards/1/srs/cost/estimate", json={}).json()["id"]
    assert c.post(f"/boards/2/srs/cost/{eid}/explain").status_code == 404


def test_unauthenticated_gets_401():
    seed()
    app = FastAPI()
    app.include_router(cost_routes.router)
    assert TestClient(app).post("/boards/1/srs/cost/estimate", json={}).status_code == 401


def test_estimates_deleted_with_board():
    seed()
    make_client(1).post("/boards/1/srs/cost/estimate", json={})
    db = SessionLocal()
    db.delete(db.query(Board).filter(Board.id == 1).first())
    db.commit()
    assert db.query(CostEstimate).count() == 0
    db.close()


def test_labour_matches_hand_calculation():
    t = load_rates()
    r = est()
    pm = r["scenarios"]["likely"]["person_months"]
    blended = sum(x.allocation * (x.monthly_min + x.monthly_max) / 2 for x in t.roles.values())
    assert abs(r["scenarios"]["likely"]["groups"]["labour"] - pm * blended) / (pm * blended) < 0.005


def test_overhead_is_percentage_of_labour():
    t = load_rates()
    r = est()
    g = r["scenarios"]["likely"]["groups"]
    pct = sum(o.pct for o in t.overheads)
    assert abs(g["overhead"] - g["labour"] * pct) <= len(t.overheads)
