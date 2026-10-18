"""Invitation links: preview (public), accept/decline by token, wrong-account and expiry handling."""
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.database import Base, SessionLocal, engine
from app.models.board import Board
from app.models.chat import Chat  # noqa: F401
from app.models.otp import OTP  # noqa: F401
from app.models.rbac import BoardInvitation, BoardMember
from app.models.user import User
from app.routes import members as members_routes
from app.routes.auth import get_current_user


@pytest.fixture(autouse=True)
def fresh_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    db.add_all([User(id=1, name="Owner", email="owner@x.com"),
                User(id=2, name="Invitee", email="invitee@x.com"),
                User(id=3, name="Other", email="other@x.com")])
    db.add(Board(id=1, name="Library", description="x", owner_id=1))
    db.add(BoardMember(board_id=1, user_id=1, role="admin"))
    db.add(BoardInvitation(board_id=1, email="invitee@x.com", role="editor", token="tok123",
                           invited_by=1, expires_at=datetime.now(timezone.utc) + timedelta(days=7)))
    db.commit()
    db.close()
    yield


def client_for(user_id=None):
    app = FastAPI()
    app.include_router(members_routes.router)
    if user_id:
        db = SessionLocal()
        u = db.get(User, user_id)
        fake = type("U", (), {"id": u.id, "name": u.name, "email": u.email})()
        db.close()
        app.dependency_overrides[get_current_user] = lambda: fake
    return TestClient(app)


def test_preview_is_public_and_unknown_token_404():
    c = client_for()
    r = c.get("/invitations/token/tok123")
    assert r.status_code == 200
    body = r.json()
    assert body["board_name"] == "Library" and body["role"] == "editor"
    assert body["email"] == "invitee@x.com" and body["status"] == "pending" and body["registered"] is True
    assert c.get("/invitations/token/nope").status_code == 404


def test_accept_by_token_adds_member_with_role():
    r = client_for(2).post("/invitations/token/tok123/accept")
    assert r.status_code == 200 and r.json()["board_id"] == 1
    db = SessionLocal()
    m = db.query(BoardMember).filter_by(board_id=1, user_id=2).first()
    assert m is not None and m.role == "editor"
    assert db.query(BoardInvitation).first().status == "accepted"
    db.close()
    # the new member can now see the board's members
    assert client_for(2).get("/boards/1/members").status_code == 200


def test_wrong_account_cannot_accept():
    r = client_for(3).post("/invitations/token/tok123/accept")
    assert r.status_code == 403 and "invitee@x.com" in r.json()["detail"]
    db = SessionLocal()
    assert db.query(BoardMember).filter_by(board_id=1, user_id=3).first() is None
    assert db.query(BoardInvitation).first().status == "pending"
    db.close()


def test_accept_requires_login():
    assert client_for().post("/invitations/token/tok123/accept").status_code in (401, 403)


def test_used_invitation_cannot_be_reused():
    client_for(2).post("/invitations/token/tok123/accept")
    assert client_for(2).post("/invitations/token/tok123/accept").status_code == 410


def test_expired_invitation_is_rejected():
    db = SessionLocal()
    inv = db.query(BoardInvitation).first()
    inv.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
    db.commit()
    db.close()
    assert client_for().get("/invitations/token/tok123").json()["status"] == "expired"
    assert client_for(2).post("/invitations/token/tok123/accept").status_code == 410


def test_decline_by_token():
    assert client_for(2).post("/invitations/token/tok123/decline").status_code == 200
    db = SessionLocal()
    assert db.query(BoardInvitation).first().status == "declined"
    assert db.query(BoardMember).filter_by(board_id=1, user_id=2).first() is None
    db.close()


def test_id_based_accept_still_works():
    inv_id = client_for(2).get("/invitations/mine").json()[0]["id"]
    assert client_for(2).post(f"/invitations/{inv_id}/accept").status_code == 200
