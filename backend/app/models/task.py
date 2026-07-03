from sqlalchemy import Column, Integer, String, Boolean,ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base

class Task(Base):
    __tablename__ = "tasks"
    id = Column(Integer,primary_key=True,index=True)
    title = Column(String)
    description = Column(String)
    priority = Column(String)
    column_id =Column(Integer,ForeignKey("columns.id"))
    created_by =Column(Integer,ForeignKey("users.id"))
    column_id = Column(
        Integer,
        ForeignKey("columns.id", ondelete="CASCADE")
    )

    created_by = Column(Integer, ForeignKey("users.id"))

    column = relationship(
        "BoardColumn",
        back_populates="tasks"
    )