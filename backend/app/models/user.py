# app/models/user.py

from sqlalchemy import Column, Integer, String, Boolean
from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String(100))
    email = Column(String(255), unique=True)

    password_hash = Column(String(255))

    is_verified = Column(Boolean, default=False)