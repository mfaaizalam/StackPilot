from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import relationship

from app.core.database import Base


class SDDDocument(Base):
    """One saved Software Design Description, versioned per board.

    design   = the validated DesignModel as JSON (source of truth, rendering is deterministic)
    diagrams = snapshot of the diagram titles/types the SDD embedded (for the audit trail)
    """
    __tablename__ = "sdd_documents"

    id = Column(Integer, primary_key=True, index=True)
    board_id = Column(Integer, ForeignKey("boards.id", ondelete="CASCADE"), nullable=False, index=True)
    srs_id = Column(Integer, nullable=False, index=True)
    srs_version = Column(Integer)
    version = Column(Integer, nullable=False, default=1)
    source = Column(String(20), default="ai")          # ai | fallback
    design = Column(JSON, nullable=False)
    issues = Column(JSON, default=list)
    diagrams = Column(JSON, default=list)               # [{"id":..,"type":..,"title":..,"stale":..}]
    markdown = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    board = relationship("Board", back_populates="sdd_documents")


class SDDJob(Base):
    """Background job that generates one SDD."""
    __tablename__ = "sdd_jobs"

    id = Column(String(36), primary_key=True)
    board_id = Column(Integer, ForeignKey("boards.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    srs_id = Column(Integer, nullable=False)
    status = Column(String(20), nullable=False, default="queued")  # queued|running|done|failed
    stage = Column(String(40), default="queued")                    # collecting|designing|validating|repairing|rendering|saving
    error = Column(Text)
    sdd_id = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)