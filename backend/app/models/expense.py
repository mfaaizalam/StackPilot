"""Issue #7: expense lines (category + description + estimated/actual amount).

An expense may belong to one activity or to the whole project (activity_id NULL, e.g. hosting).
New table only, so create_all builds it without touching existing tables."""
from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import backref, relationship
from sqlalchemy.sql import func

from app.core.database import Base


class Expense(Base):
    __tablename__ = "expenses"

    id = Column(Integer, primary_key=True, index=True)
    board_id = Column(Integer, ForeignKey("boards.id", ondelete="CASCADE"), nullable=False, index=True)
    activity_id = Column(Integer, ForeignKey("activities.id", ondelete="SET NULL"), nullable=True)
    category = Column(String(30), nullable=False)
    description = Column(String(300), nullable=False)
    estimated_amount = Column(Numeric(14, 2), nullable=False, default=0)
    actual_amount = Column(Numeric(14, 2), nullable=False, default=0)
    incurred_on = Column(Date, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    board = relationship("Board", backref=backref("expenses", cascade="all, delete-orphan"))
