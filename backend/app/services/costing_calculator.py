"""Pure maths for Issue #7 (expense categories and activity cost roll-up). No DB, no clock.

Rule that keeps the numbers honest: an activity's cost comes from its expense lines when it
has any; otherwise from the manual estimated/actual fields entered in Issue #9. Expenses with no
activity are project-level (hosting, tools...) and are added on top. So nothing is counted twice."""
from decimal import Decimal
from types import SimpleNamespace

from app.services.gantt_calculator import dec

D = Decimal
CATEGORIES = ("labour", "infrastructure", "tools", "licences", "travel", "training", "contingency", "other")
LABELS = {"labour": "Labour", "infrastructure": "Hosting and infrastructure", "tools": "Tools and software",
          "licences": "Licences", "travel": "Travel", "training": "Training", "contingency": "Contingency",
          "other": "Other", "unallocated": "Activity totals (no breakdown yet)"}


def split_expenses(activities, expenses):
    ids = {a.id for a in activities}
    by_act: dict[int, list] = {}
    project_level = []
    for e in expenses:
        if e.activity_id in ids:
            by_act.setdefault(e.activity_id, []).append(e)
        else:
            project_level.append(e)          # NULL or a deleted activity: counts for the whole project
    return by_act, project_level


def apply_expenses(activities, expenses):
    """-> (activities with effective costs, project-level estimated, project-level actual, project-level count)."""
    by_act, project_level = split_expenses(activities, expenses)
    out = []
    for a in activities:
        lines = by_act.get(a.id)
        est = sum((dec(x.estimated_amount) for x in lines), D(0)) if lines else dec(a.estimated_cost)
        act = sum((dec(x.actual_amount) for x in lines), D(0)) if lines else dec(a.actual_cost)
        out.append(SimpleNamespace(
            id=a.id, task_id=getattr(a, "task_id", None), name=a.name, phase=a.phase,
            start_date=a.start_date, end_date=a.end_date, planned_hours=a.planned_hours,
            actual_hours=a.actual_hours, progress_pct=a.progress_pct, depends_on=a.depends_on,
            position=getattr(a, "position", 0), estimated_cost=est, actual_cost=act,
            cost_source="expenses" if lines else "manual", expense_count=len(lines or [])))
    return (out, sum((dec(x.estimated_amount) for x in project_level), D(0)),
            sum((dec(x.actual_amount) for x in project_level), D(0)), len(project_level))


def category_breakdown(activities, expenses) -> list[dict]:
    """Estimated vs actual per category. Activities without expense lines appear as one
    'unallocated' row, so the rows always add up to the project total."""
    by_act, project_level = split_expenses(activities, expenses)
    rows: dict[str, dict] = {}

    def add(cat, est, act):
        r = rows.setdefault(cat, {"category": cat, "label": LABELS.get(cat, cat), "estimated": D(0), "actual": D(0)})
        r["estimated"] += est
        r["actual"] += act

    for lines in by_act.values():
        for x in lines:
            add(x.category, dec(x.estimated_amount), dec(x.actual_amount))
    for x in project_level:
        add(x.category, dec(x.estimated_amount), dec(x.actual_amount))
    for a in activities:
        if a.id not in by_act and (dec(a.estimated_cost) or dec(a.actual_cost)):
            add("unallocated", dec(a.estimated_cost), dec(a.actual_cost))

    total_act = sum((r["actual"] for r in rows.values()), D(0))
    total_est = sum((r["estimated"] for r in rows.values()), D(0))
    out = []
    for r in rows.values():
        base, tot = (r["actual"], total_act) if total_act > 0 else (r["estimated"], total_est)
        r["variance"] = r["actual"] - r["estimated"]
        r["variance_pct"] = round(float(r["variance"] / r["estimated"] * 100), 1) if r["estimated"] > 0 else None
        r["share_pct"] = round(float(base / tot * 100), 1) if tot > 0 else 0.0
        r["overrun"] = r["estimated"] > 0 and r["actual"] > r["estimated"]
        out.append(r)
    order = {c: i for i, c in enumerate(CATEGORIES)}
    return sorted(out, key=lambda r: order.get(r["category"], 99))
