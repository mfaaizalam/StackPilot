from sqlalchemy import Column,Text, Integer, String,DateTime, Boolean,ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base
from datetime import datetime
class Chat(Base):
    __tablename__ = "chat_messages"
    id = Column(Integer,primary_key=True,index=True)
    board_id=Column(Integer,ForeignKey("boards.id",ondelete="CASCADE"),  nullable=False)
    user_id = Column(Integer,ForeignKey("users.id"),  nullable=False)
    role = Column(String,nullable=False)       # user / assistant
    message = Column(Text,nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    board = relationship(
        "Board",
        back_populates="chats"
    )