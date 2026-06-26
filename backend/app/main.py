# app/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.database import Base, engine
# Import models so SQLAlchemy can detect them
from app.routes.auth import router as auth_router
from app.models.user import User
from app.models.otp import OTP
from app.routes.board import router as Board_router
from app.routes.column import router as Column_router
from app.routes.task import router as task_router
app = FastAPI(
    title="AI Project Management API",
    version="1.0.0"
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create tables in Neon PostgreSQL
Base.metadata.create_all(bind=engine)

# REGISTER ROUTES
app.include_router(auth_router)

# Board Routes
app.include_router(Board_router)
# Column Route
app.include_router(Column_router)
#Task Route
app.include_router(task_router)
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



