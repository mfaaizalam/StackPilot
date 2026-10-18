"""Pakistan cost estimation: PURE Python, no AI, no database (golden rules 1, 2 and 7).

    requirements JSON  ->  size (function points)  ->  COCOMO II effort + schedule
    ->  cost per role in PKR (rate table)  ->  optimistic / likely / pessimistic
    ->  PERT  (O + 4M + P) / 6  ->  sensitivity table  ->  optional ROI.

Same input + same rate table always gives the same numbers. Changing a rate changes the result.
"""
import math
import re
from typing import Any

from app.schemas.cost import CostRequest, RatesTable
from app.schemas.srs import Requirements
from app.services.cost_rates import SCENARIOS, unverified_items

# --- published COCOMO II.2000 constants -------------------------------------------------
COCOMO_A = 2.94
COCOMO_B = 0.91
COCOMO_C = 3.67
COCOMO_D = 0.28
# Nominal scale factors: PREC 3.72, FLEX 3.04, RESL 4.24, TEAM 3.29, PMAT 4.68
SCALE_FACTOR_SUM = 19.0
EM_CPLX = {"low": 0.87, "nominal": 1.00, "high": 1.17}
EM_RELY = {"low": 0.92, "nominal": 1.00, "high": 1.10}
EM_TEAM = {"low": 1.15, "nominal": 1.00, "high": 0.88}  # PCAP: more experienced team = less effort

# --- sensitivity settings (from the build plan) -----------------------------------------
SALARY_DELTA = 0.20
SCOPE_DELTA = 0.30

DISCLAIMER = ("These figures are planning estimates, not a quotation. They come from a size model "
              "(COCOMO II) and the salary and cost rates shown below, and real projects vary.")

_SYSTEM_ACTOR = re.compile(r"\b(system|api|service|gateway|external|scheduler|bot|server|payment|sms|email)\b", re.I)


# ------------------------------------------------------------------------------ size
def _fr_weight(criteria: int, words: int) -> tuple[str, int]:
    """IFPUG-style transaction weights (EI: 3 / 4 / 6)."""
    if criteria >= 5 or words > 40:
        return "complex", 6
    if criteria <= 2 and words <= 25:
        return "simple", 3
    return "average", 4


def _entity_weight(attrs: int) -> tuple[str, int]:
    """IFPUG internal logical file weights (7 / 10 / 15)."""
    if attrs <= 5:
        return "simple", 7
    if attrs <= 10:
        return "average", 10
    return "complex", 15


def size_from_requirements(req: Requirements) -> dict[str, Any]:
    fr_pts = 0
    fr_levels = {"simple": 0, "average": 0, "complex": 0}
    for fr in req.functional_requirements:
        lvl, w = _fr_weight(len(fr.acceptance_criteria), len(fr.statement.split()))
        fr_levels[lvl] += 1
        fr_pts += w
    ent_pts = sum(_entity_weight(len(e.attributes))[1] for e in req.entities)
    if_pts = 5 * len(req.external_interfaces)  # IFPUG external interface file, average weight
    return {
        "ufp": fr_pts + ent_pts + if_pts,
        "breakdown": {"functional_requirements": fr_pts, "data_entities": ent_pts, "external_interfaces": if_pts},
        "counts": {"functional_requirements": len(req.functional_requirements), "entities": len(req.entities),
                   "external_interfaces": len(req.external_interfaces), "use_cases": len(req.use_cases),
                   "actors": len(req.actors), "fr_complexity": fr_levels,
                   "priorities": {k: sum(1 for f in req.functional_requirements if f.priority == k)
                                  for k in ("must", "should", "could")}},
    }


def use_case_points(req: Requirements, rates: RatesTable) -> dict[str, Any]:
    """Karner's Use Case Points, used only as an independent cross-check of the COCOMO result.
    Technical and environment factors are taken as nominal (adjustment = 1.0)."""
    uaw = sum(1 if _SYSTEM_ACTOR.search(a.name) else 3 for a in req.actors)
    uucw = 0
    for uc in req.use_cases:
        n = len(uc.main_flow)
        uucw += 5 if n <= 3 else 10 if n <= 7 else 15
    ucp = uaw + uucw
    pm = ucp * rates.model.ucp_hours_per_point / rates.model.hours_per_person_month
    return {"ucp": ucp, "actor_weight": uaw, "use_case_weight": uucw, "person_months": round(pm, 2)}


# ------------------------------------------------------------------------------ one scenario
def _salary(role, point: float, factor: float) -> float:
    return (role.monthly_min + (role.monthly_max - role.monthly_min) * point) * factor


def effort_multiplier(inp: CostRequest, rates: RatesTable) -> float:
    return EM_CPLX[inp.complexity] * EM_RELY[inp.reliability] * EM_TEAM[inp.team_experience] \
        * rates.model.platform_multiplier.get(inp.platform, 1.0)


def _exponent() -> float:
    return COCOMO_B + 0.01 * SCALE_FACTOR_SUM


def _scenario(ufp: float, inp: CostRequest, rates: RatesTable, name: str, salary_factor: float) -> dict[str, Any]:
    sc = rates.scenarios[name]
    ksloc = ufp * rates.model.loc_per_function_point / 1000.0
    e = _exponent()
    pm = COCOMO_A * (ksloc ** e) * effort_multiplier(inp, rates) * sc.effort_factor
    f = COCOMO_D + 0.2 * (e - COCOMO_B)
    months = COCOMO_C * (pm ** f)
    team = max(1, math.ceil(pm / months))

    lines: list[dict[str, Any]] = []
    labour = 0.0
    for rid, r in rates.roles.items():
        monthly = _salary(r, sc.salary_point, salary_factor)
        amount = pm * r.allocation * monthly
        labour += amount
        lines.append({"key": f"role:{rid}", "label": r.label, "group": "labour", "amount": amount})
    infra = 0.0
    for o in rates.overheads:
        a = labour * o.pct
        infra += a
        lines.append({"key": f"overhead:{o.id}", "label": o.label, "group": "overhead", "amount": a})
    for m in rates.monthly_costs:
        a = m.pkr_per_month * (team if m.per_head else 1) * months
        infra += a
        lines.append({"key": f"monthly:{m.id}", "label": m.label, "group": "infrastructure", "amount": a})
    for o in rates.one_time_costs:
        infra += o.pkr
        lines.append({"key": f"once:{o.id}", "label": o.label, "group": "infrastructure", "amount": o.pkr})
    subtotal = labour + infra
    cont = subtotal * rates.contingency.pct
    lines.append({"key": "contingency", "label": rates.contingency.label, "group": "contingency", "amount": cont})
    tax = (subtotal + cont) * rates.tax.pct
    lines.append({"key": "tax", "label": rates.tax.label, "group": "tax", "amount": tax})
    return {"pm": pm, "months": months, "team": team, "ksloc": ksloc, "lines": lines}


def _pert(o: float, m: float, p: float) -> float:
    return (o + 4 * m + p) / 6.0


def _combine(ufp: float, inp: CostRequest, rates: RatesTable, salary_factor: float = 1.0) -> dict[str, Any]:
    """Runs the three scenarios and the PERT blend (all unrounded)."""
    sc = {n: _scenario(ufp, inp, rates, n, salary_factor) for n in SCENARIOS}
    o, m, p = sc["optimistic"], sc["likely"], sc["pessimistic"]
    pert_lines = []
    for lo, lm, lp in zip(o["lines"], m["lines"], p["lines"]):
        pert_lines.append({**lm, "amount": _pert(lo["amount"], lm["amount"], lp["amount"])})
    return {
        "scenarios": sc,
        "pert": {"pm": _pert(o["pm"], m["pm"], p["pm"]), "months": _pert(o["months"], m["months"], p["months"]),
                 "team": max(1, math.ceil(_pert(o["team"], m["team"], p["team"]))), "lines": pert_lines},
    }


def _rounded(lines: list[dict]) -> tuple[list[dict], int]:
    out = [{**ln, "amount": int(round(ln["amount"]))} for ln in lines]
    return out, sum(ln["amount"] for ln in out)


def _group_totals(lines: list[dict]) -> dict[str, int]:
    t: dict[str, int] = {}
    for ln in lines:
        t[ln["group"]] = t.get(ln["group"], 0) + ln["amount"]
    return t


# ------------------------------------------------------------------------------ ROI
def roi(total_cost: int, cost_low: int, cost_high: int, build_months: float, revenue: float,
        horizon_years: int, rates: RatesTable) -> dict[str, Any]:
    running = total_cost * rates.maintenance.annual_pct_of_build
    net = revenue - running

    def payback(cost: float) -> float | None:
        return round(cost / (net / 12.0), 1) if net > 0 else None

    out: dict[str, Any] = {
        "expected_annual_revenue": int(round(revenue)),
        "annual_running_cost": int(round(running)),
        "net_annual": int(round(net)),
        "horizon_years": horizon_years,
        "payback_months": payback(total_cost),
        "payback_months_best": payback(cost_low),
        "payback_months_worst": payback(cost_high),
    }
    out["break_even_month_from_start"] = (round(build_months + out["payback_months"], 1)
                                          if out["payback_months"] is not None else None)
    out["roi_pct"] = round((net * horizon_years - total_cost) / total_cost * 100, 1) if total_cost > 0 else None
    out["cumulative"] = [{"year": y, "net_position": int(round(net * y - total_cost))} for y in range(1, horizon_years + 1)]
    out["note"] = ("Running cost exceeds revenue, so the project never pays back at this revenue."
                   if net <= 0 else "Revenue is the owner's own expectation, not a forecast made by StackPilot.")
    return out


# ------------------------------------------------------------------------------ main entry
def estimate(req: Requirements, inp: CostRequest, rates: RatesTable,
             board_points: dict[str, Any] | None = None) -> dict[str, Any]:
    size = size_from_requirements(req)
    if size["ufp"] <= 0:
        raise ValueError("The SRS has no functional requirements to size.")
    ufp = size["ufp"]
    base = _combine(ufp, inp, rates)

    scenarios_out: dict[str, Any] = {}
    for n in SCENARIOS:
        s = base["scenarios"][n]
        lines, total = _rounded(s["lines"])
        scenarios_out[n] = {"label": rates.scenarios[n].label, "person_months": round(s["pm"], 2),
                            "duration_months": round(s["months"], 1), "team_size": s["team"],
                            "total": total, "groups": _group_totals(lines)}
    pert_lines, pert_total = _rounded(base["pert"]["lines"])
    pert = base["pert"]
    groups = _group_totals(pert_lines)

    roles = []
    for rid, r in rates.roles.items():
        cost = next(ln["amount"] for ln in pert_lines if ln["key"] == f"role:{rid}")
        roles.append({"id": rid, "label": r.label, "share": r.allocation,
                      "person_months": round(pert["pm"] * r.allocation, 2),
                      "monthly_salary_min": int(r.monthly_min), "monthly_salary_max": int(r.monthly_max),
                      "cost": cost})

    # sensitivity: every row is a full recomputation
    def total_for(scope: float, sal: float) -> int:
        c = _combine(ufp * scope, inp, rates, sal)
        return _rounded(c["pert"]["lines"])[1]

    rows = [("Base case", 1.0, 1.0)]
    rows += [(f"Salaries -{int(SALARY_DELTA * 100)}%", 1.0, 1 - SALARY_DELTA),
             (f"Salaries +{int(SALARY_DELTA * 100)}%", 1.0, 1 + SALARY_DELTA),
             (f"Scope -{int(SCOPE_DELTA * 100)}%", 1 - SCOPE_DELTA, 1.0),
             (f"Scope +{int(SCOPE_DELTA * 100)}%", 1 + SCOPE_DELTA, 1.0),
             ("Best case (scope -30%, salaries -20%)", 1 - SCOPE_DELTA, 1 - SALARY_DELTA),
             ("Worst case (scope +30%, salaries +20%)", 1 + SCOPE_DELTA, 1 + SALARY_DELTA)]
    sensitivity = []
    for label, scope, sal in rows:
        t = pert_total if (scope, sal) == (1.0, 1.0) else total_for(scope, sal)
        sensitivity.append({"label": label, "scope_factor": scope, "salary_factor": sal, "total": t,
                            "delta_pct": round((t - pert_total) / pert_total * 100, 1) if pert_total else 0.0})

    ucp = use_case_points(req, rates)
    ratio = round(ucp["person_months"] / pert["pm"], 2) if pert["pm"] else None
    cross = {"use_case_points": {**ucp, "ratio_to_cocomo": ratio,
                                 "agreement": "close" if ratio and 0.5 <= ratio <= 2.0 else "differs"}}
    if board_points:
        cross["board_points"] = {**board_points,
                                 "points_per_person_month": round(board_points["total_points"] / pert["pm"], 1)
                                 if pert["pm"] else None,
                                 "note": "Story points are relative sizes, not hours. Shown only as a cross-check."}

    monthly_burn = int(round(pert_total / pert["months"])) if pert["months"] else 0
    e = _exponent()
    result = {
        "inputs": inp.model_dump(),
        "currency": rates.meta.currency,
        "rates_meta": {"version": rates.meta.version, "last_updated": rates.meta.last_updated,
                       "unverified_items": unverified_items(rates), "notes": rates.meta.notes},
        "size": {**size, "ksloc": round(ufp * rates.model.loc_per_function_point / 1000.0, 2),
                 "loc_per_function_point": rates.model.loc_per_function_point},
        "effort": {"exponent": round(e, 3), "scale_factor_sum": SCALE_FACTOR_SUM,
                   "effort_multiplier": round(effort_multiplier(inp, rates), 3),
                   "person_months": round(pert["pm"], 2), "duration_months": round(pert["months"], 1),
                   "team_size": pert["team"]},
        "scenarios": scenarios_out,
        "pert": {"total": pert_total, "low": scenarios_out["optimistic"]["total"],
                 "high": scenarios_out["pessimistic"]["total"], "groups": groups, "lines": pert_lines},
        "roles": roles,
        "monthly_burn": monthly_burn,
        "sensitivity": sensitivity,
        "roi": (roi(pert_total, scenarios_out["optimistic"]["total"], scenarios_out["pessimistic"]["total"],
                    pert["months"], inp.expected_annual_revenue, inp.horizon_years, rates)
                if inp.expected_annual_revenue else None),
        "cross_checks": cross,
        "assumptions": _assumptions(inp, rates),
        "disclaimer": DISCLAIMER,
    }
    return result


def _assumptions(inp: CostRequest, rates: RatesTable) -> list[str]:
    m = rates.model
    out = [
        f"Size is counted from the SRS as function points (functional requirements, data entities, external interfaces) "
        f"and converted at {m.loc_per_function_point:g} lines of code per function point.",
        f"Effort uses COCOMO II (exponent {_exponent():.2f}, nominal scale factors). Complexity: {inp.complexity}, "
        f"reliability: {inp.reliability}, team experience: {inp.team_experience}, platform: {inp.platform.replace('_', ' + ')}.",
        "Scenarios: optimistic = 80% of the effort at the lowest salaries, likely = estimated effort at mid salaries, "
        "pessimistic = 150% of the effort at the highest salaries (all editable in the rate table).",
        "The headline figure is the PERT expected value (optimistic + 4 x likely + pessimistic) / 6.",
        f"Effort is shared between roles using fixed allocations. Overheads are a percentage of labour; "
        f"contingency is {rates.contingency.pct * 100:g}% and tax is {rates.tax.pct * 100:g}%.",
        "Hosting and tool costs run for the whole project duration; tools are charged per team member.",
        f"Rates were last updated on {rates.meta.last_updated} (table version {rates.meta.version}).",
    ]
    if unverified_items(rates):
        out.append("Some rates in the table are still unverified placeholders (listed in the warning above).")
    return out
