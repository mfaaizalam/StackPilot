"""Cost estimation service: loads the SRS and rate table, runs the deterministic calculator,
stores the result, and (optionally) asks the AI to EXPLAIN it. The AI never produces numbers."""
import re
from datetime import datetime, timedelta
from typing import Any

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.llm import LLMError, llm_json
from app.models.column import BoardColumn
from app.models.srs import CostEstimate, SRSDocument
from app.models.task import Task
from app.prompts import cost_prompt as P
from app.schemas.cost import CostExplanation, CostRequest
from app.schemas.srs import Requirements
from app.services import cost_calculator as C
from app.services.cost_rates import RatesError, load_rates

MAX_ESTIMATES_PER_HOUR = 30
MAX_EXPLAINS_PER_HOUR = 10


# ------------------------------------------------------------------ formatting / figures
def pkr(n: float) -> str:
    return f"PKR {int(round(n)):,}"


def figures(result: dict[str, Any]) -> dict[str, str]:
    """Every number the explanation may quote, already formatted."""
    pert, eff, size = result["pert"], result["effort"], result["size"]
    total = pert["total"] or 1
    top = max(result["roles"], key=lambda r: r["cost"])
    sens = {s["label"]: s for s in result["sensitivity"]}
    f = {
        "expected_total_cost": pkr(pert["total"]),
        "optimistic_total_cost": pkr(pert["low"]),
        "pessimistic_total_cost": pkr(pert["high"]),
        "duration_months": f"{eff['duration_months']:g} months",
        "effort_person_months": f"{eff['person_months']:g} person-months",
        "average_team_size": f"{eff['team_size']} people",
        "monthly_burn": pkr(result["monthly_burn"]),
        "labour_cost": pkr(pert["groups"].get("labour", 0)),
        "non_labour_cost": pkr(pert["total"] - pert["groups"].get("labour", 0)),
        "labour_share": f"{round(pert['groups'].get('labour', 0) / total * 100)}%",
        "largest_role": f"{top['label']}: {pkr(top['cost'])}",
        "functional_requirements": str(size["counts"]["functional_requirements"]),
        "function_points": str(size["ufp"]),
        "scope_change_tested": f"{round(C.SCOPE_DELTA * 100)}%",
        "salary_change_tested": f"{round(C.SALARY_DELTA * 100)}%",
        "scope_plus_30_percent_cost": pkr(sens[next(k for k in sens if k.startswith("Scope +"))]["total"]),
        "salaries_plus_20_percent_cost": pkr(sens[next(k for k in sens if k.startswith("Salaries +"))]["total"]),
    }
    roi = result.get("roi")
    if roi and roi.get("payback_months") is not None:
        f["payback_months"] = f"{roi['payback_months']:g} months"
    return f


_NUM = re.compile(r"\d[\d,]*(?:\.\d+)?")


def _numbers(text: str) -> list[float]:
    out = []
    for m in _NUM.findall(text):
        try:
            out.append(round(float(m.replace(",", "")), 2))
        except ValueError:
            pass
    return out


def explanation_is_safe(exp: CostExplanation, figs: dict[str, str]) -> bool:
    """Code-side check (golden rule 2): the AI may only quote numbers that appear in `figures`.
    Whole numbers below 10 are allowed ("3 risks"); anything else must match a given figure."""
    allowed = {n for v in figs.values() for n in _numbers(v)}
    text = " ".join([exp.summary, *exp.key_drivers, *exp.risks, *exp.tips])
    for n in _numbers(text):
        if n < 10 and n == int(n):
            continue
        if n not in allowed:
            return False
    return bool(exp.summary.strip())


def template_explanation(result: dict[str, Any]) -> dict[str, Any]:
    """Deterministic explanation used by default and whenever the AI is down."""
    f, pert, size, eff = figures(result), result["pert"], result["size"], result["effort"]
    pr = size["counts"].get("priorities", {})
    drivers = [
        f"Labour is about {f['labour_share']} of the total ({f['labour_cost']}); the largest single role is {f['largest_role']}.",
        f"The project is sized at {f['function_points']} function points from {f['functional_requirements']} functional requirements, "
        f"which the model turns into {f['effort_person_months']} over {f['duration_months']}.",
        f"Overheads, hosting, tools, contingency and tax make up the rest ({f['non_labour_cost']}).",
    ]
    risks = [f"If the scope grows by 30%, the expected cost rises to {f['scope_plus_30_percent_cost']}.",
             f"If salaries are 20% higher than the table, the expected cost rises to {f['salaries_plus_20_percent_cost']}."]
    if result["rates_meta"]["unverified_items"]:
        risks.append("Some rates in the table are still unverified placeholders, so treat the figures as indicative.")
    tips = ["Build the must-have requirements first and release early.",
            "Confirm each salary and cost rate with current local quotes before relying on the total."]
    if pr.get("could"):
        tips.insert(1, f"Postpone the {pr['could']} optional ('could') requirement(s) to reduce scope.")
    summary = (f"The expected cost is {f['expected_total_cost']}, with a likely range from {f['optimistic_total_cost']} "
               f"to {f['pessimistic_total_cost']}. The work is estimated at {f['duration_months']} with an average team of "
               f"{f['average_team_size']}, a monthly spend of about {f['monthly_burn']}.")
    return {"summary": summary, "key_drivers": drivers, "risks": risks, "tips": tips}


# ------------------------------------------------------------------ estimate
def _get_doc(db: Session, board_id: int, srs_id: int | None) -> SRSDocument:
    q = db.query(SRSDocument).filter(SRSDocument.board_id == board_id)
    doc = q.filter(SRSDocument.id == srs_id).first() if srs_id else q.order_by(SRSDocument.version.desc()).first()
    if not doc:
        raise HTTPException(status_code=404, detail="No SRS has been generated for this board yet.")
    return doc


def _board_points(db: Session, board_id: int, srs_id: int) -> dict[str, Any] | None:
    rows = (db.query(func.count(Task.id), func.coalesce(func.sum(Task.estimate_points), 0))
            .join(BoardColumn, BoardColumn.id == Task.column_id)
            .filter(BoardColumn.board_id == board_id, Task.srs_id == srs_id, Task.estimate_points.isnot(None))
            .first())
    if not rows or not rows[0]:
        return None
    return {"tasks": int(rows[0]), "total_points": int(rows[1])}


def create_estimate(db: Session, board_id: int, user_id: int, body: CostRequest) -> dict[str, Any]:
    recent = (db.query(CostEstimate).filter(CostEstimate.user_id == user_id,
                                            CostEstimate.created_at > datetime.utcnow() - timedelta(hours=1)).count())
    if recent >= MAX_ESTIMATES_PER_HOUR:
        raise HTTPException(status_code=429, detail="Estimate limit reached. Please try again later.")
    doc = _get_doc(db, board_id, body.srs_id)
    try:
        req = Requirements.model_validate(doc.requirements)
    except ValidationError:
        raise HTTPException(status_code=422, detail="The saved SRS is damaged. Regenerate it before estimating cost.")
    try:
        rates = load_rates()
    except RatesError as e:
        raise HTTPException(status_code=503, detail=str(e))
    try:
        result = C.estimate(req, body, rates, _board_points(db, board_id, doc.id))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    row = CostEstimate(board_id=board_id, user_id=user_id, srs_id=doc.id, srs_version=doc.version,
                       inputs=body.model_dump(), result=result, explanation=template_explanation(result),
                       explanation_source="template")
    db.add(row)
    db.commit()
    db.refresh(row)
    return row_out(db, row)


def latest_srs_id(db: Session, board_id: int) -> int | None:
    d = (db.query(SRSDocument).filter(SRSDocument.board_id == board_id)
         .order_by(SRSDocument.version.desc()).first())
    return d.id if d else None


def row_out(db: Session, row: CostEstimate) -> dict[str, Any]:
    return {"id": row.id, "board_id": row.board_id, "srs_id": row.srs_id, "srs_version": row.srs_version,
            "created_at": row.created_at, "result": row.result, "explanation": row.explanation,
            "explanation_source": row.explanation_source,
            "srs_outdated": latest_srs_id(db, row.board_id) != row.srs_id}


def explain(db: Session, row: CostEstimate, user_id: int) -> dict[str, Any]:
    """Replace the template explanation with an AI-written one (kept only if it passes the number check)."""
    recent = (db.query(CostEstimate).filter(CostEstimate.user_id == user_id,
                                            CostEstimate.explained_at > datetime.utcnow() - timedelta(hours=1)).count())
    if recent >= MAX_EXPLAINS_PER_HOUR:
        raise HTTPException(status_code=429, detail="Explanation limit reached. Please try again later.")
    doc = db.query(SRSDocument).filter(SRSDocument.id == row.srs_id).first()
    title, scope = (doc.requirements.get("title", ""), doc.requirements.get("scope", "")) if doc else ("", "")
    figs = figures(row.result)
    row.explained_at = datetime.utcnow()  # counts against the limit even if the AI fails
    try:
        exp = llm_json(P.explain_prompt(title, scope, figs), CostExplanation, system=P.SYSTEM, temperature=0.3)
    except LLMError as e:
        db.commit()
        raise HTTPException(status_code=503, detail=str(e))
    if not explanation_is_safe(exp, figs):
        row.explanation = template_explanation(row.result)
        row.explanation_source = "template"
        db.commit()
        out = row_out(db, row)
        out["notice"] = "The AI wrote a figure that was not in the calculation, so the standard explanation is shown."
        return out
    row.explanation = exp.model_dump()
    row.explanation_source = "ai"
    db.commit()
    return row_out(db, row)
