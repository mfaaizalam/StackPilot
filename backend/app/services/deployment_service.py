"""DB side of the Document tab. Pricing and rendering live in deployment_catalog.py."""
from datetime import date

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.board import Board
from app.models.expense import Expense
from app.models.deployment import DeploymentDoc, DeploymentPlan
from app.schemas.deployment import DocIn, DocUpdate, GenerateIn
from app.services.gantt_calculator import D as Dec, dec, q2
from app.services import deployment_catalog as D


def catalog_or_503():
    try:
        return D.load_catalog()
    except D.CatalogError as e:
        raise HTTPException(status_code=503, detail=str(e))


def options_payload() -> dict:
    cat = catalog_or_503()
    return {"stack": {k: [{"value": v, "label": l} for v, l in opts] for k, opts in D.STACK_OPTIONS.items()},
            "extras": [{"value": v, "label": l} for v, l in D.EXTRAS],
            "environments": list(D.ENVIRONMENTS),
            "scales": cat["scales"], "currency": cat["currency"], "pricing_status": cat["pricing_status"],
            "catalog_version": cat["version"]}


def suggestions(stack: dict) -> dict:
    cat = catalog_or_503()
    return {"stack": stack, "layers": D.suggest(stack, cat), "currency": cat["currency"], "pricing_status": cat["pricing_status"]}


def plan_out(p: DeploymentPlan, with_document: bool = True) -> dict:
    out = {"id": p.id, "version": p.version, "stack": p.stack, "selected": p.selected, "options": p.options,
           "totals": p.totals, "created_at": p.created_at.isoformat() if p.created_at else None}
    if with_document:
        out["document_md"] = p.document_md
    return out


def generate(db: Session, board: Board, user_id: int, body: GenerateIn, today: date | None = None) -> DeploymentPlan:
    cat = catalog_or_503()
    stack = body.stack.model_dump()
    try:
        resolved = D.resolve_selection(stack, body.selected, cat)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    tot = D.totals(resolved, cat)
    last = (db.query(DeploymentPlan.version).filter(DeploymentPlan.board_id == board.id)
            .order_by(DeploymentPlan.version.desc()).first())
    version = (last[0] if last else 0) + 1
    md = D.render_document(board.name, stack, resolved, tot, version=version,
                           generated_on=(today or date.today()).isoformat(), domain=body.domain,
                           environments=body.environments, notes=body.notes, cat=cat)
    plan = DeploymentPlan(board_id=board.id, version=version, stack=stack, selected=body.selected,
                          options={"domain": body.domain, "environments": body.environments, "notes": body.notes},
                          totals=tot, document_md=md, created_by=user_id)
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan


def list_plans(db: Session, board_id: int) -> list[DeploymentPlan]:
    return db.query(DeploymentPlan).filter(DeploymentPlan.board_id == board_id).order_by(DeploymentPlan.version.desc()).all()


def get_plan(db: Session, board_id: int, plan_id: int) -> DeploymentPlan:
    p = db.query(DeploymentPlan).filter(DeploymentPlan.id == plan_id, DeploymentPlan.board_id == board_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Deployment plan not found")
    return p


# ---- supporting documents
def doc_out(d: DeploymentDoc) -> dict:
    return {"id": d.id, "title": d.title, "category": d.category, "content": d.content, "url": d.url,
            "updated_at": d.updated_at.isoformat() if d.updated_at else None}


def list_docs(db: Session, board_id: int) -> list[DeploymentDoc]:
    return db.query(DeploymentDoc).filter(DeploymentDoc.board_id == board_id).order_by(DeploymentDoc.id.desc()).all()


def _doc(db: Session, board_id: int, doc_id: int) -> DeploymentDoc:
    d = db.query(DeploymentDoc).filter(DeploymentDoc.id == doc_id, DeploymentDoc.board_id == board_id).first()
    if not d:
        raise HTTPException(status_code=404, detail="Document not found")
    return d


def create_doc(db: Session, board_id: int, user_id: int, body: DocIn) -> DeploymentDoc:
    d = DeploymentDoc(board_id=board_id, created_by=user_id, **body.model_dump())
    db.add(d)
    db.commit()
    db.refresh(d)
    return d


def update_doc(db: Session, board_id: int, doc_id: int, body: DocUpdate) -> DeploymentDoc:
    d = _doc(db, board_id, doc_id)
    data = body.model_dump(exclude_unset=True)
    for k in ("title", "category", "content"):
        if k in data and data[k] is None:
            raise HTTPException(status_code=422, detail=f"{k} cannot be empty.")
    for k, v in data.items():
        setattr(d, k, v)
    db.commit()
    db.refresh(d)
    return d


def delete_doc(db: Session, board_id: int, doc_id: int) -> None:
    db.delete(_doc(db, board_id, doc_id))
    db.commit()


# ---- hand the hosting cost to the Costing tab
MARKER = "Deployment v"      # description prefix that identifies lines created from a deployment plan


def add_to_costing(db: Session, board_id: int, plan: DeploymentPlan, months: int) -> dict:
    """One project-level `infrastructure` expense per paid service: monthly PKR x months (estimate only).
    Earlier deployment lines are replaced so the cost is never counted twice, except lines where
    someone already recorded an actual amount: those are kept."""
    cat = catalog_or_503()
    try:
        resolved = D.resolve_selection(plan.stack, plan.selected, cat)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=f"This plan can no longer be priced: {e}")
    paid = [r for r in resolved if r["monthly_usd"] > 0]
    if not paid:
        raise HTTPException(status_code=422, detail="All selected services are free, so there is no hosting cost to add.")

    old = db.query(Expense).filter(Expense.board_id == board_id, Expense.category == "infrastructure",
                                   Expense.description.like(f"{MARKER}%")).all()
    removed = kept = 0
    for e in old:
        if dec(e.actual_amount) > 0:
            kept += 1
        else:
            db.delete(e)
            removed += 1
    total = Dec(0)
    for r in paid:
        amount = q2(Dec(r["monthly_pkr"]) * months)
        total += amount
        db.add(Expense(board_id=board_id, activity_id=None, category="infrastructure",
                       description=f"{MARKER}{plan.version}: {r['name']} ({r['plan']}), {months} months"[:300],
                       estimated_amount=amount, actual_amount=0))
    db.commit()
    return {"added": len(paid), "removed": removed, "kept": kept, "months": months,
            "estimated_total": str(q2(total)), "price_table_version": cat["version"]}
