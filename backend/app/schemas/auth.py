from pydantic import BaseModel, EmailStr, Field
from typing import Optional         

class SendOTPRequest(BaseModel):
    email: EmailStr


class RegisterRequest(BaseModel):
    name: str
    email: EmailStr
    password: str = Field(max_length=72)
    otp: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str