"""Issue #7, Document tab. Viewers read; editors generate and change documents."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_board_and_role, get_owned_board
from app.routes.auth import get_current_user
from app.schemas.deployment import AddToCostingIn, DocIn, DocUpdate, GenerateIn, StackIn
from app.services import deployment_service as S
from app.services.activity_service import log_activity

router = APIRouter(prefix="/boards/{board_id}/deployment", tags=["Deployment document"])


@router.get("/options")
def options(board_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    _, role = get_board_and_role(db, board_id, current_user, "viewer")
    return {**S.options_payload(), "role": role, "can_edit": role in ("editor", "project_manager", "admin"),
            "can_manage_finance": role in ("project_manager", "admin")}


@router.post("/suggest")
def suggest(board_id: int, body: StackIn, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    get_board_and_role(db, board_id, current_user, "viewer")
    return S.suggestions(body.model_dump())


@router.post("/generate", status_code=201)
def generate(board_id: int, body: GenerateIn, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    board = get_owned_board(db, board_id, current_user, "editor")
    p = S.generate(db, board, current_user.id, body)
    log_activity(db, board_id, current_user.id, "deployment.generated", f"generated deployment document v{p.version}", "deployment", p.id)
    return S.plan_out(p)


@router.get("/plans")
def plans(board_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    get_board_and_role(db, board_id, current_user, "viewer")
    return [S.plan_out(p, with_document=False) for p in S.list_plans(db, board_id)]


@router.get("/plans/{plan_id}")
def plan(board_id: int, plan_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    get_board_and_role(db, board_id, current_user, "viewer")
    return S.plan_out(S.get_plan(db, board_id, plan_id))


@router.post("/plans/{plan_id}/add-to-costing")
def add_to_costing(board_id: int, plan_id: int, body: AddToCostingIn, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    get_owned_board(db, board_id, current_user, "project_manager")      # it creates expenses, so money rules apply
    result = S.add_to_costing(db, board_id, S.get_plan(db, board_id, plan_id), body.months)
    log_activity(db, board_id, current_user.id, "deployment.added_to_costing",
                 f"added hosting costs from deployment document to Costing ({body.months} months)", "deployment", plan_id)
    return result


@router.get("/docs")
def docs(board_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    get_board_and_role(db, board_id, current_user, "viewer")
    return [S.doc_out(d) for d in S.list_docs(db, board_id)]


@router.post("/docs", status_code=201)
def add_doc(board_id: int, body: DocIn, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    get_owned_board(db, board_id, current_user, "editor")
    d = S.create_doc(db, board_id, current_user.id, body)
    log_activity(db, board_id, current_user.id, "deployment.doc_created", f"added the document “{d.title[:60]}”", "deployment_doc", d.id)
    return S.doc_out(d)


@router.patch("/docs/{doc_id}")
def edit_doc(board_id: int, doc_id: int, body: DocUpdate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    get_owned_board(db, board_id, current_user, "editor")
    d = S.update_doc(db, board_id, doc_id, body)
    log_activity(db, board_id, current_user.id, "deployment.doc_updated", f"updated the document “{d.title[:60]}”", "deployment_doc", d.id)
    return S.doc_out(d)


@router.delete("/docs/{doc_id}", status_code=204)
def remove_doc(board_id: int, doc_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    get_owned_board(db, board_id, current_user, "editor")
    S.delete_doc(db, board_id, doc_id)
    log_activity(db, board_id, current_user.id, "deployment.doc_deleted", "deleted a document", "deployment_doc", doc_id)
