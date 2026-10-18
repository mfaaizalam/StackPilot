from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import relationship

from app.core.database import Base


class SRSDocument(Base):
    __tablename__ = "srs_documents"

    id = Column(Integer, primary_key=True, index=True)
    board_id = Column(Integer, ForeignKey("boards.id", ondelete="CASCADE"), nullable=False, index=True)
    version = Column(Integer, nullable=False, default=1)
    description = Column(Text, nullable=False)
    answers = Column(JSON, default=list)
    requirements = Column(JSON, nullable=False)
    issues = Column(JSON, default=list)
    markdown = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    board = relationship("Board", back_populates="srs_documents")
    diagrams = relationship("Diagram", back_populates="srs", cascade="all, delete-orphan")


class SRSJob(Base):
    __tablename__ = "srs_jobs"

    id = Column(String(36), primary_key=True)
    board_id = Column(Integer, ForeignKey("boards.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(String(20), nullable=False, default="queued")  # queued|running|done|failed
    stage = Column(String(40), default="queued")
    error = Column(Text)
    srs_id = Column(Integer)
    payload = Column(JSON)  # {"description":..., "answers":[...]}
    created_at = Column(DateTime, default=datetime.utcnow)


class Diagram(Base):
    """One row per diagram. model = {"spec":..., "warnings":[...], "source":"ai|fallback|rules", "actors":[...], "order":int}"""
    __tablename__ = "diagrams"

    id = Column(Integer, primary_key=True, index=True)
    srs_id = Column(Integer, ForeignKey("srs_documents.id", ondelete="CASCADE"), nullable=False, index=True)
    type = Column(String(30), nullable=False)
    title = Column(String(200))
    model = Column(JSON, nullable=False)
    stale = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    srs = relationship("SRSDocument", back_populates="diagrams")


class DiagramJob(Base):
    """Background job that generates the diagrams of one SRS version."""
    __tablename__ = "diagram_jobs"

    id = Column(String(36), primary_key=True)
    board_id = Column(Integer, ForeignKey("boards.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    srs_id = Column(Integer, nullable=False)
    status = Column(String(20), nullable=False, default="queued")  # queued|running|done|failed
    stage = Column(String(40), default="queued")                    # "3/9" progress
    error = Column(Text)
    payload = Column(JSON)  # {"types": [...]}
    created_at = Column(DateTime, default=datetime.utcnow)


class CostEstimate(Base):
    """One saved cost estimate. result = the full deterministic output of cost_calculator.estimate()."""
    __tablename__ = "cost_estimates"

    id = Column(Integer, primary_key=True, index=True)
    board_id = Column(Integer, ForeignKey("boards.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    srs_id = Column(Integer, nullable=False)
    srs_version = Column(Integer)
    inputs = Column(JSON, nullable=False)
    result = Column(JSON, nullable=False)
    explanation = Column(JSON)                                  # {summary, key_drivers, risks, tips}
    explanation_source = Column(String(20), default="template")  # template | ai
    explained_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)

    board = relationship("Board", back_populates="cost_estimates")
