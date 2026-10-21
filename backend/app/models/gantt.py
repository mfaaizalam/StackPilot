"""Issue #9: Gantt activities, finance increments and the project's starting budget.

These are all NEW tables, so `Base.metadata.create_all` in main.py creates them on the
live database without touching any existing table. Money is Numeric(14,2), never float.
"""
from sqlalchemy import (CheckConstraint, Column, Date, DateTime, ForeignKey, Integer, JSON,
                        Numeric, String)
from sqlalchemy.orm import backref, relationship
from sqlalchemy.sql import func

from app.core.database import Base


class BoardBudget(Base):
    """The starting budget of a board (one row per board). Kept out of `boards` on purpose."""
    __tablename__ = "board_budgets"

    id = Column(Integer, primary_key=True)
    board_id = Column(Integer, ForeignKey("boards.id", ondelete="CASCADE"), nullable=False, unique=True)
    base_budget = Column(Numeric(14, 2), nullable=False, default=0)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    board = relationship("Board", backref=backref("budget", uselist=False, cascade="all, delete-orphan"))


class Activity(Base):
    __tablename__ = "activities"
    __table_args__ = (
        CheckConstraint("end_date >= start_date", name="ck_activity_dates"),
        CheckConstraint("progress_pct BETWEEN 0 AND 100", name="ck_activity_progress"),
    )

    id = Column(Integer, primary_key=True, index=True)
    board_id = Column(Integer, ForeignKey("boards.id", ondelete="CASCADE"), nullable=False, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True)
    name = Column(String(200), nullable=False)
    phase = Column(String(100), nullable=True)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    planned_hours = Column(Numeric(8, 2), nullable=False, default=0)
    actual_hours = Column(Numeric(8, 2), nullable=False, default=0)
    progress_pct = Column(Integer, nullable=False, default=0)
    estimated_cost = Column(Numeric(14, 2), nullable=False, default=0)
    actual_cost = Column(Numeric(14, 2), nullable=False, default=0)
    depends_on = Column(JSON, nullable=False, default=list)   # [activity ids on the same board]
    position = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    board = relationship("Board", backref=backref("activities", cascade="all, delete-orphan"))


class FinanceIncrement(Base):
    __tablename__ = "finance_increments"

    id = Column(Integer, primary_key=True, index=True)
    board_id = Column(Integer, ForeignKey("boards.id", ondelete="CASCADE"), nullable=False, index=True)
    activity_id = Column(Integer, ForeignKey("activities.id", ondelete="SET NULL"), nullable=True)
    phase = Column(String(100), nullable=True)
    amount = Column(Numeric(14, 2), nullable=False)
    effective_date = Column(Date, nullable=False)
    status = Column(String(20), nullable=False, default="planned")   # planned | approved | disbursed
    note = Column(String(300), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    board = relationship("Board", backref=backref("finance_increments", cascade="all, delete-orphan"))
