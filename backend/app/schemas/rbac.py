from datetime import datetime

from pydantic import BaseModel, EmailStr, field_validator


class InviteIn(BaseModel):
    email: EmailStr
    role: str

    @field_validator("email")
    @classmethod
    def _lower(cls, v):
        return v.lower().strip()


class RoleUpdate(BaseModel):
    role: str


class MemberOut(BaseModel):
    user_id: int
    name: str | None
    email: str
    role: str
    is_owner: bool = False


class InvitationOut(BaseModel):
    id: int
    board_id: int
    board_name: str | None = None
    email: str
    role: str
    status: str
    expires_at: datetime


class ActivityOut(BaseModel):
    id: int
    user_name: str | None
    action: str
    summary: str
    created_at: datetime