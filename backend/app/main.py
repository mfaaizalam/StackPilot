# app/main.py

from fastapi import FastAPI

from app.core.database import Base, engine
# Import models so SQLAlchemy can detect them
from app.routes.auth import router as auth_router
from app.models.user import User
from app.models.otp import OTP
app = FastAPI(
    title="AI Project Management API",
    version="1.0.0"
)

# Create tables in Neon PostgreSQL
Base.metadata.create_all(bind=engine)

# REGISTER ROUTES
app.include_router(auth_router)
@app.get("/")
def root():
    return {
        "message": "AI Project Management Backend Running"
    }


@app.get("/health")
def health_check():
    return {
        "status": "success",
        "database": "connected"
    }



