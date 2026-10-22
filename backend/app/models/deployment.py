"""Issue #7, Document tab: saved deployment plans (versioned) and supporting documents. New tables only."""
from sqlalchemy import Column, DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import backref, relationship
from sqlalchemy.sql import func

from app.core.database import Base


class DeploymentPlan(Base):
    __tablename__ = "deployment_plans"

    id = Column(Integer, primary_key=True, index=True)
    board_id = Column(Integer, ForeignKey("boards.id", ondelete="CASCADE"), nullable=False, index=True)
    version = Column(Integer, nullable=False)
    stack = Column(JSON, nullable=False)          # what the user said they use
    selected = Column(JSON, nullable=False)       # category -> service id
    options = Column(JSON, nullable=False)        # domain, environments, notes
    totals = Column(JSON, nullable=False)         # priced totals at generation time
    document_md = Column(Text, nullable=False)
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    board = relationship("Board", backref=backref("deployment_plans", cascade="all, delete-orphan"))


class DeploymentDoc(Base):
    __tablename__ = "deployment_docs"

    id = Column(Integer, primary_key=True, index=True)
    board_id = Column(Integer, ForeignKey("boards.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    category = Column(String(20), nullable=False, default="supporting")   # plan | configuration | supporting
    content = Column(Text, nullable=False, default="")
    url = Column(String(500), nullable=True)
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    board = relationship("Board", backref=backref("deployment_docs", cascade="all, delete-orphan"))
