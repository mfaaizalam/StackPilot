from sqlalchemy import Column, Integer, String, Boolean,ForeignKey
from app.core.database import Base
class Board(Base):
    __tablename__="boards"
    id = Column(Integer,primary_key=True,index=True)
    name = Column(String,nullable=False)
    description = Column(String)
    owner_id = Column (Integer,ForeignKey("users.id"))