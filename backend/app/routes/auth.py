import random

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token
)

from app.models.user import User
from app.models.otp import OTP

from app.schemas.auth import (
    SendOTPRequest,
    RegisterRequest,
    LoginRequest
)

from app.services.email_service import send_email

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)


@router.post("/send-otp")
def send_otp(
    data: SendOTPRequest,
    db: Session = Depends(get_db)
):

    otp = str(random.randint(100000, 999999))

    otp_record = OTP(
        email=data.email,
        otp=otp
    )

    db.add(otp_record)
    db.commit()

    send_email(
        data.email,
        otp
    )

    return {
        "message": "OTP sent successfully"
    }


@router.post("/register")
def register(
    data: RegisterRequest,
    db: Session = Depends(get_db)
):

    if len(data.password) > 72:
        raise HTTPException(
            status_code=400,
            detail="Password too long. Max 72 characters allowed."
        )

    existing_user = db.query(User).filter(
        User.email == data.email
    ).first()

    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )

    otp_record = db.query(OTP).filter(
        OTP.email == data.email,
        OTP.otp == data.otp,
        OTP.is_used == False
    ).first()

    if not otp_record:
        raise HTTPException(
            status_code=400,
            detail="Invalid OTP"
        )

    user = User(
        name=data.name,
        email=data.email,
        password_hash=hash_password(
            data.password
        ),
        is_verified=True
    )

    db.add(user)

    otp_record.is_used = True

    db.commit()

    return {
        "message": "User registered successfully"
    }


@router.post("/login")
def login(
    data: LoginRequest,
    db: Session = Depends(get_db)
):

    user = db.query(User).filter(
        User.email == data.email
    ).first()

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials"
        )

    if not verify_password(
        data.password,
        user.password_hash
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials"
        )

    token = create_access_token(
        {
            "sub": str(user.id),
            "email": user.email
        }
    )

    return {
    "access_token": token,
    "token_type": "bearer",
    "user": {
        "id": user.id,
        "name": user.name,
        "email": user.email
    }
}