from sqlalchemy import Column, Integer, String, Boolean,ForeignKey
from app.core.database import Base
from sqlalchemy.orm import relationship
class Board(Base):
    __tablename__="boards"
    id = Column(Integer,primary_key=True,index=True)
    name = Column(String,nullable=False)
    description = Column(String)
    owner_id = Column (Integer,ForeignKey("users.id"))
    # Delete all columns automatically when this board is deleted
    columns = relationship(
        "BoardColumn",
        back_populates="board",
        cascade="all, delete-orphan"
    )
    # Delete all chats automatically when board is deleted
    chats = relationship(
        "Chat",
        back_populates="board",
        cascade="all, delete-orphan"
    )