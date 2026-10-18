"""Project settings: members, invitations (by email) and the activity log."""
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import ASSIGNABLE_ROLES, get_board_and_role, get_owned_board
from app.models.rbac import BoardActivity, BoardInvitation, BoardMember
from app.models.user import User
from app.routes.auth import get_current_user
from app.schemas.rbac import ActivityOut, InvitationOut, InviteIn, MemberOut, RoleUpdate
from app.services.activity_service import log_activity
from app.services.email_service import send_invite_email

router = APIRouter(tags=["Members & roles"])


def _now():
    return datetime.now(timezone.utc)


def _aware(dt):
    """SQLite returns naive datetimes; PostgreSQL returns aware ones."""
    return dt if dt is None or dt.tzinfo else dt.replace(tzinfo=timezone.utc)


# ------------------------------------------------------------------ my role
@router.get("/boards/{board_id}/me")
def my_role(board_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    _, role = get_board_and_role(db, board_id, current_user, "viewer")
    return {"role": role}


# ------------------------------------------------------------------ members
@router.get("/boards/{board_id}/members", response_model=list[MemberOut])
def list_members(board_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    board = get_owned_board(db, board_id, current_user, "viewer")
    rows = db.query(BoardMember).filter(BoardMember.board_id == board_id).order_by(BoardMember.id).all()
    return [MemberOut(user_id=m.user_id, name=m.user.name, email=m.user.email,
                      role="admin" if m.user_id == board.owner_id else m.role,
                      is_owner=m.user_id == board.owner_id) for m in rows]


@router.patch("/boards/{board_id}/members/{user_id}")
def change_role(board_id: int, user_id: int, body: RoleUpdate, db: Session = Depends(get_db),
                current_user=Depends(get_current_user)):
    board = get_owned_board(db, board_id, current_user, "admin")
    if body.role not in ASSIGNABLE_ROLES:
        raise HTTPException(status_code=422, detail="Role must be project_manager, editor or viewer")
    if user_id == board.owner_id:
        raise HTTPException(status_code=400, detail="The project owner's role cannot be changed")
    m = db.query(BoardMember).filter_by(board_id=board_id, user_id=user_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="Member not found")
    old, m.role = m.role, body.role
    email = m.user.email
    db.commit()
    log_activity(db, board_id, current_user.id, "member.role_changed",
                 f"changed {email} from {old} to {body.role}", "member", user_id)
    return {"ok": True}


@router.delete("/boards/{board_id}/members/{user_id}")
def remove_member(board_id: int, user_id: int, db: Session = Depends(get_db),
                  current_user=Depends(get_current_user)):
    board, role = get_board_and_role(db, board_id, current_user, "viewer")
    is_self = user_id == current_user.id
    if not is_self and role != "admin":
        raise HTTPException(status_code=403, detail="Only an admin can remove members")
    if user_id == board.owner_id:
        raise HTTPException(status_code=400, detail="The project owner cannot be removed")
    m = db.query(BoardMember).filter_by(board_id=board_id, user_id=user_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="Member not found")
    email = m.user.email
    db.delete(m)
    db.commit()
    log_activity(db, board_id, current_user.id, "member.left" if is_self else "member.removed",
                 f"{email} left the project" if is_self else f"removed {email} from the project",
                 "member", user_id)
    return {"ok": True}


# ------------------------------------------------------------------ invitations (admin side)
@router.get("/boards/{board_id}/members/lookup")
def lookup_email(board_id: int, email: str, db: Session = Depends(get_db),
                 current_user=Depends(get_current_user)):
    """The admin types an email; show the registered name if that person has an account."""
    get_owned_board(db, board_id, current_user, "admin")
    u = db.query(User).filter(func.lower(User.email) == email.lower().strip()).first()
    return {"registered": bool(u), "name": u.name if u else None}


@router.get("/boards/{board_id}/invitations", response_model=list[InvitationOut])
def list_invitations(board_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    board = get_owned_board(db, board_id, current_user, "admin")
    rows = (db.query(BoardInvitation)
              .filter(BoardInvitation.board_id == board_id, BoardInvitation.status == "pending").all())
    return [InvitationOut(id=i.id, board_id=i.board_id, board_name=board.name, email=i.email,
                          role=i.role, status=i.status, expires_at=i.expires_at) for i in rows]


@router.post("/boards/{board_id}/invitations", response_model=InvitationOut)
def invite(board_id: int, body: InviteIn, background: BackgroundTasks, db: Session = Depends(get_db),
           current_user=Depends(get_current_user)):
    board = get_owned_board(db, board_id, current_user, "admin")
    if body.role not in ASSIGNABLE_ROLES:
        raise HTTPException(status_code=422, detail="Role must be project_manager, editor or viewer")

    user = db.query(User).filter(func.lower(User.email) == body.email).first()
    if user and db.query(BoardMember.id).filter_by(board_id=board_id, user_id=user.id).first():
        raise HTTPException(status_code=409, detail="This person is already a member")

    inv = (db.query(BoardInvitation)
             .filter_by(board_id=board_id, email=body.email, status="pending").first())
    if inv:  # inviting again = change the role and extend the deadline
        inv.role = body.role
    else:
        inv = BoardInvitation(board_id=board_id, email=body.email, role=body.role,
                              token=secrets.token_urlsafe(32), invited_by=current_user.id)
    inv.expires_at = _now() + timedelta(days=7)
    db.add(inv)
    db.commit()
    db.refresh(inv)

    log_activity(db, board_id, current_user.id, "member.invited",
                 f"invited {body.email} as {body.role}", "invitation", inv.id)
    background.add_task(send_invite_email, inv.email, board.name, inv.role, current_user.name, inv.token)
    return InvitationOut(id=inv.id, board_id=board_id, board_name=board.name, email=inv.email,
                         role=inv.role, status=inv.status, expires_at=inv.expires_at)


@router.delete("/boards/{board_id}/invitations/{inv_id}")
def revoke_invitation(board_id: int, inv_id: int, db: Session = Depends(get_db),
                      current_user=Depends(get_current_user)):
    get_owned_board(db, board_id, current_user, "admin")
    inv = db.query(BoardInvitation).filter_by(id=inv_id, board_id=board_id).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Invitation not found")
    inv.status = "revoked"
    db.commit()
    return {"ok": True}


# ------------------------------------------------------------------ invitations (invitee side)
def _my_pending(db: Session, user) -> list[BoardInvitation]:
    rows = (db.query(BoardInvitation)
              .filter(BoardInvitation.email == (user.email or "").lower().strip(),
                      BoardInvitation.status == "pending").all())
    return [i for i in rows if _aware(i.expires_at) > _now()]


def _my_invitation(db: Session, user, inv_id: int) -> BoardInvitation:
    inv = next((i for i in _my_pending(db, user) if i.id == inv_id), None)
    if not inv:
        raise HTTPException(status_code=404, detail="Invitation not found or expired")
    return inv


@router.get("/invitations/mine", response_model=list[InvitationOut])
def my_invitations(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    return [InvitationOut(id=i.id, board_id=i.board_id, board_name=i.board.name if i.board else None,
                          email=i.email, role=i.role, status=i.status, expires_at=i.expires_at)
            for i in _my_pending(db, current_user)]


def _join(db: Session, inv: BoardInvitation, user) -> dict:
    """Turn a valid invitation into a membership (idempotent)."""
    if not db.query(BoardMember.id).filter_by(board_id=inv.board_id, user_id=user.id).first():
        db.add(BoardMember(board_id=inv.board_id, user_id=user.id, role=inv.role,
                           invited_by=inv.invited_by))
    inv.status = "accepted"
    board_id, role = inv.board_id, inv.role
    db.commit()
    log_activity(db, board_id, user.id, "member.joined",
                 f"joined the project as {role.replace('_', ' ')}", "member", user.id)
    return {"ok": True, "board_id": board_id}


@router.post("/invitations/{inv_id}/accept")
def accept_invitation(inv_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    return _join(db, _my_invitation(db, current_user, inv_id), current_user)


@router.post("/invitations/{inv_id}/decline")
def decline_invitation(inv_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    inv = _my_invitation(db, current_user, inv_id)
    inv.status = "declined"
    db.commit()
    return {"ok": True}


# ------------------------------------------------------------------ invitations (email link)
def _by_token(db: Session, token: str) -> BoardInvitation:
    inv = db.query(BoardInvitation).filter(BoardInvitation.token == token).first()
    if not inv:
        raise HTTPException(status_code=404, detail="This invitation link is not valid")
    return inv


def _usable(inv: BoardInvitation) -> BoardInvitation:
    if inv.status != "pending":
        raise HTTPException(status_code=410, detail=f"This invitation was already {inv.status}")
    if _aware(inv.expires_at) <= _now():
        raise HTTPException(status_code=410, detail="This invitation has expired. Ask the admin to send a new one")
    return inv


def _for_this_user(inv: BoardInvitation, user) -> BoardInvitation:
    if (user.email or "").lower().strip() != inv.email:
        raise HTTPException(
            status_code=403,
            detail=f"This invitation was sent to {inv.email}, but you are signed in as {user.email}. "
                   f"Sign in with the invited email address.")
    return inv


@router.get("/invitations/token/{token}")
def invitation_preview(token: str, db: Session = Depends(get_db)):
    """Public (no login): lets the email link show what the invitation is for. The token is the secret."""
    inv = _by_token(db, token)
    inviter = db.get(User, inv.invited_by) if inv.invited_by else None
    registered = bool(db.query(User.id).filter(func.lower(User.email) == inv.email).first())
    expired = _aware(inv.expires_at) <= _now()
    return {"board_name": inv.board.name if inv.board else None, "role": inv.role, "email": inv.email,
            "invited_by": (inviter.name or inviter.email) if inviter else None,
            "status": "expired" if inv.status == "pending" and expired else inv.status,
            "registered": registered}


@router.post("/invitations/token/{token}/accept")
def accept_by_token(token: str, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    inv = _for_this_user(_usable(_by_token(db, token)), current_user)
    return _join(db, inv, current_user)


@router.post("/invitations/token/{token}/decline")
def decline_by_token(token: str, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    inv = _for_this_user(_usable(_by_token(db, token)), current_user)
    inv.status = "declined"
    db.commit()
    return {"ok": True}


# ------------------------------------------------------------------ activity
@router.get("/boards/{board_id}/activity", response_model=list[ActivityOut])
def activity(board_id: int, limit: int = 50, db: Session = Depends(get_db),
             current_user=Depends(get_current_user)):
    get_owned_board(db, board_id, current_user, "viewer")
    rows = (db.query(BoardActivity).filter(BoardActivity.board_id == board_id)
              .order_by(BoardActivity.id.desc()).limit(max(1, min(limit, 200))).all())
    return [ActivityOut(id=a.id, user_name=(a.user.name or a.user.email) if a.user else "Someone",
                        action=a.action, summary=a.summary, created_at=a.created_at) for a in rows]