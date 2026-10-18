from sqlalchemy import (Column, Integer, String, ForeignKey, DateTime,
                        UniqueConstraint, Text)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base          # ASSUMPTION

class BoardMember(Base):
    __tablename__ = "board_members"
    __table_args__ = (UniqueConstraint("board_id", "user_id", name="uq_board_user"),)

    id = Column(Integer, primary_key=True)
    board_id = Column(Integer, ForeignKey("boards.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(20), nullable=False)       # admin | project_manager | editor | viewer
    invited_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", foreign_keys=[user_id], lazy="joined")


class BoardInvitation(Base):
    __tablename__ = "board_invitations"

    id = Column(Integer, primary_key=True)
    board_id = Column(Integer, ForeignKey("boards.id", ondelete="CASCADE"), nullable=False, index=True)
    email = Column(String(255), nullable=False, index=True)    # stored lowercase
    role = Column(String(20), nullable=False)
    token = Column(String(64), nullable=False, unique=True)
    status = Column(String(20), nullable=False, default="pending")  # pending|accepted|declined|revoked
    invited_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False)

    board = relationship("Board", lazy="joined")


class BoardActivity(Base):
    __tablename__ = "board_activity"

    id = Column(Integer, primary_key=True)
    board_id = Column(Integer, ForeignKey("boards.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    action = Column(String(50), nullable=False)        # e.g. task.created, srs.generated
    entity_type = Column(String(30), nullable=True)
    entity_id = Column(Integer, nullable=True)
    summary = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    user = relationship("User", foreign_keys=[user_id], lazy="joined")