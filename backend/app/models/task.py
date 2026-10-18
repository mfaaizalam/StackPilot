from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.core.database import Base

class Task(Base):
    __tablename__ = "tasks"
    id = Column(Integer,primary_key=True,index=True)
    title = Column(String)
    description = Column(String)
    priority = Column(String)
    column_id = Column(
        Integer,
        ForeignKey("columns.id", ondelete="CASCADE")
    )

    created_by = Column(Integer, ForeignKey("users.id"))

    # --- Phase 4: traceability back to the SRS (all optional, NULL for hand-made tasks) ---
    # NOTE: existing databases get these columns from app/core/migrate.py at startup.
    requirement_id = Column(String(40), nullable=True)   # "FR-004" / "NFR-002"
    estimate_points = Column(Integer, nullable=True)     # relative story points
    depends_on = Column(JSON, nullable=True)             # ["FR-001", "FR-002"] (requirement IDs)
    srs_id = Column(Integer, nullable=True)              # srs_documents.id the task was generated from

    column = relationship(
        "BoardColumn",
        back_populates="tasks"
    )
