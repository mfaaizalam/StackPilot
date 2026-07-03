from sqlalchemy import Column, Integer, String, Boolean,ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base

class BoardColumn(Base):
    __tablename__ = "columns"
    id = Column(Integer,primary_key=True,index=True)
    name = Column(String,nullable=False)
    board_id = Column(
        Integer,
        ForeignKey("boards.id", ondelete="CASCADE")
    )

    # Parent board
    board = relationship(
        "Board",
        back_populates="columns"
    )

    # Delete all tasks automatically
    tasks = relationship(
        "Task",
        back_populates="column",
        cascade="all, delete-orphan"
    )