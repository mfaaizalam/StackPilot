from sqlalchemy import Column, Integer, String, Boolean,ForeignKey
from app.core.database import Base

class BoardColumn(Base):
    __tablename__ = "columns"
    id = Column(Integer,primary_key=True,index=True)
    name = Column(String,nullable=False)
    board_id =Column(Integer,ForeignKey("boards.id"))
    