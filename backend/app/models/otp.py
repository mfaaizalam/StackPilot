from sqlalchemy import Column, Integer, String, Boolean, DateTime
from datetime import datetime

from app.core.database import Base


class OTP(Base):
    __tablename__ = "otp_codes"

    id = Column(Integer, primary_key=True, index=True)

    email = Column(String(255))

    otp = Column(String(6))

    is_used = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.utcnow)