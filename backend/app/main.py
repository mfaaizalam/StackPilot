# app/main.py

from fastapi import FastAPI

from app.core.database import Base, engine

# Import models so SQLAlchemy can detect them
from app.models.user import User

app = FastAPI(
    title="AI Project Management API",
    version="1.0.0"
)

# Create tables in Neon PostgreSQL
Base.metadata.create_all(bind=engine)


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