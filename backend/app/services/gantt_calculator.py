"""Pure Gantt / finance maths for Issue #9. No database, no network, no clock:
everything takes plain objects (ORM rows or SimpleNamespace) and an explicit `today`,
so the same input always gives the same output (the PRD's determinism rule).

Finance vocabulary (one definition, used by the API, the UI and the tests):
  committed budget = base + approved + disbursed increments
  available funds  = base + disbursed increments  (cash actually received)
  forecast budget  = committed + planned increments
  cost variance    = actual - estimated           (positive = overrun)
"""
import math
from datetime import date, timedelta
from decimal import Decimal

D = Decimal
STATUSES = ("planned", "approved", "disbursed")
SCHEDULE_TOLERANCE = 15      # progress may trail elapsed time by this many points before we flag it
BURN_TOLERANCE = 25          # budget used may lead progress by this many points before we flag it
POINTS_PER_DAY = 2           # seeding assumption: 2 story points of work per calendar day
HOURS_PER_POINT = 6          # seeding fallback when no cost estimate exists
HOURS_PER_PERSON_MONTH = 160


def dec(v) -> Decimal:
    return D(str(v)) if v not in (None, "") else D(0)


def q2(v: Decimal) -> Decimal:
    return v.quantize(D("0.01"))


# ---------------------------------------------------------------- activities
def duration_days(start: date, end: date) -> int:
    return (end - start).days + 1


def elapsed_pct(start: date, end: date, today: date) -> int:
    if today < start:
        return 0
    if today >= end:
        return 100
    return round(100 * ((today - start).days + 1) / duration_days(start, end))


def activity_metrics(a, today: date) -> dict:
    est, act = dec(a.estimated_cost), dec(a.actual_cost)
    ph, ah = dec(a.planned_hours), dec(a.actual_hours)
    prog = int(a.progress_pct or 0)
    el = elapsed_pct(a.start_date, a.end_date, today)
    budget_used = float(act / est * 100) if est > 0 else None
    time_used = float(ah / ph * 100) if ph > 0 else None

    flags: list[str] = []
    if est > 0 and act > est:
        flags.append("cost_overrun")
    elif est == 0 and act > 0:
        flags.append("unbudgeted_cost")
    if ph > 0 and ah > ph:
        flags.append("time_overrun")
    if prog < 100 and prog < el - SCHEDULE_TOLERANCE:
        flags.append("behind_schedule")
    if prog < 100 and today > a.end_date:
        flags.append("overdue")
    if prog < 100 and budget_used is not None and budget_used > prog + BURN_TOLERANCE and "cost_overrun" not in flags:
        flags.append("burning_faster_than_progress")
    return {
        "duration_days": duration_days(a.start_date, a.end_date),
        "elapsed_pct": el,
        "cost_variance": act - est,
        "cost_variance_pct": round(float((act - est) / est * 100), 1) if est > 0 else None,
        "hours_variance": ah - ph,
        "budget_used_pct": None if budget_used is None else round(budget_used, 1),
        "time_used_pct": None if time_used is None else round(time_used, 1),
        "flags": flags,
    }


def schedule_conflicts(activities) -> dict[int, list[int]]:
    """activity id -> ids of dependencies that END on/after this activity STARTS."""
    by_id = {a.id: a for a in activities}
    out: dict[int, list[int]] = {}
    for a in activities:
        bad = [d for d in (a.depends_on or []) if d in by_id and by_id[d].end_date >= a.start_date]
        if bad:
            out[a.id] = bad
    return out


def project_summary(activities, today: date) -> dict:
    if not activities:
        return {"start_date": None, "end_date": None, "duration_days": 0, "progress_pct": 0,
                "elapsed_pct": 0, "planned_hours": D(0), "actual_hours": D(0), "activity_count": 0}
    start = min(a.start_date for a in activities)
    end = max(a.end_date for a in activities)
    weights = [duration_days(a.start_date, a.end_date) for a in activities]
    prog = sum(w * (a.progress_pct or 0) for w, a in zip(weights, activities)) / sum(weights)
    return {"start_date": start, "end_date": end, "duration_days": duration_days(start, end),
            "progress_pct": round(prog), "elapsed_pct": elapsed_pct(start, end, today),
            "planned_hours": sum((dec(a.planned_hours) for a in activities), D(0)),
            "actual_hours": sum((dec(a.actual_hours) for a in activities), D(0)),
            "activity_count": len(activities)}


# ---------------------------------------------------------------- dependencies
def validate_dependencies(graph: dict[int, list[int]]) -> None:
    """graph: activity id -> ids it depends on. Raises ValueError on a missing id,
    a self-dependency or a cycle."""
    for node, deps in graph.items():
        for d in deps:
            if d == node:
                raise ValueError("An activity cannot depend on itself.")
            if d not in graph:
                raise ValueError(f"Dependency {d} does not exist on this board.")
    state: dict[int, int] = {}          # 0/absent = new, 1 = visiting, 2 = done

    def visit(n: int):
        if state.get(n) == 2:
            return
        if state.get(n) == 1:
            raise ValueError("These dependencies form a loop (A needs B needs A).")
        state[n] = 1
        for d in graph[n]:
            visit(d)
        state[n] = 2

    for n in graph:
        visit(n)


def plan_schedule(items: list[dict], start: date, fixed_ends: dict | None = None) -> dict:
    """Place seeded activities in dependency order.
    items: [{"key", "days", "deps": [keys]}]; fixed_ends: key -> end date of work that already exists.
    Returns key -> (start, end). Anything in a loop just starts at `start` (never raises)."""
    fixed_ends = fixed_ends or {}
    todo = {i["key"]: i for i in items}
    placed: dict = {}
    progress = True
    while todo and progress:
        progress = False
        for key in list(todo):
            it = todo[key]
            deps = [d for d in it["deps"] if d in todo or d in placed or d in fixed_ends]
            if any(d in todo for d in deps):
                continue                       # a dependency is still waiting to be placed
            ends = [placed[d][1] if d in placed else fixed_ends[d] for d in deps]
            s = (max(ends) + timedelta(days=1)) if ends else start
            placed[key] = (s, s + timedelta(days=max(1, it["days"]) - 1))
            del todo[key]
            progress = True
    for key, it in todo.items():               # loop leftovers
        placed[key] = (start, start + timedelta(days=max(1, it["days"]) - 1))
    return placed


def days_for_points(points: int | None) -> int:
    return max(1, math.ceil((points or 1) / POINTS_PER_DAY))


# ---------------------------------------------------------------- finance
def finance_summary(base_budget, increments, activities, extra_estimated=0, extra_actual=0) -> dict:
    inc = sorted(increments, key=lambda i: (i.effective_date, i.id))
    total = lambda s: sum((dec(i.amount) for i in inc if i.status == s), D(0))
    base = dec(base_budget)
    planned, approved, disbursed = total("planned"), total("approved"), total("disbursed")
    committed, available, forecast = base + approved + disbursed, base + disbursed, base + approved + disbursed + planned
    est_total = sum((dec(a.estimated_cost) for a in activities), D(0)) + dec(extra_estimated)
    act_total = sum((dec(a.actual_cost) for a in activities), D(0)) + dec(extra_actual)

    timeline, run_all, run_committed = [], base, base
    for i in inc:
        amt = dec(i.amount)
        run_all += amt
        if i.status != "planned":
            run_committed += amt
        timeline.append({"id": i.id, "date": i.effective_date, "status": i.status, "amount": amt,
                         "cumulative_budget": run_all, "cumulative_committed": run_committed})

    alerts = []
    if act_total > available:
        alerts.append({"level": "critical", "code": "insufficient_funds", "amount": act_total - available})
    if act_total > committed:
        alerts.append({"level": "critical", "code": "over_committed_budget", "amount": act_total - committed})
    if est_total > forecast:
        alerts.append({"level": "warning", "code": "estimate_exceeds_forecast", "amount": est_total - forecast})
    elif est_total > committed:
        alerts.append({"level": "warning", "code": "estimate_exceeds_committed", "amount": est_total - committed})
    if available > 0 and not any(a["code"] == "insufficient_funds" for a in alerts) \
            and available - act_total < available * D("0.1"):
        alerts.append({"level": "warning", "code": "funds_running_low", "amount": available - act_total})

    return {"base_budget": base, "planned_increments": planned, "approved_increments": approved,
            "disbursed_increments": disbursed, "committed_budget": committed,
            "available_funds": available, "forecast_budget": forecast,
            "awaiting_disbursement": committed - available,
            "estimated_total": est_total, "actual_total": act_total,
            "cost_variance": act_total - est_total, "remaining_funds": available - act_total,
            "remaining_committed": committed - act_total, "timeline": timeline, "alerts": alerts}


def phase_summary(increments, activities) -> list[dict]:
    """Per phase: funded by increments tagged with the phase (or with an activity in it)."""
    by_id = {a.id: a for a in activities}
    rows: dict[str, dict] = {}

    def row(name):
        return rows.setdefault(name, {"phase": name, "estimated_cost": D(0), "actual_cost": D(0),
                                      "planned_funding": D(0), "committed_funding": D(0),
                                      "activity_count": 0, "alerts": []})

    for a in activities:
        r = row(a.phase or "Unassigned")
        r["estimated_cost"] += dec(a.estimated_cost)
        r["actual_cost"] += dec(a.actual_cost)
        r["activity_count"] += 1
    for i in increments:
        name = i.phase or (by_id[i.activity_id].phase if i.activity_id in by_id else None)
        if not name:
            continue                              # project-wide increment: not tied to one phase
        r = row(name)
        if i.status == "planned":
            r["planned_funding"] += dec(i.amount)
        else:
            r["committed_funding"] += dec(i.amount)
    for r in rows.values():
        funded = r["committed_funding"] > 0 or r["planned_funding"] > 0
        if funded and r["actual_cost"] > r["committed_funding"]:
            r["alerts"].append("phase_overspent")
        if r["actual_cost"] > r["estimated_cost"] > 0:
            r["alerts"].append("cost_overrun")
        r["cost_variance"] = r["actual_cost"] - r["estimated_cost"]
    return sorted(rows.values(), key=lambda r: r["phase"])
