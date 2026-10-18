# app/main.py

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from app.core.database import Base, engine
from app.core.config import settings
# Import models so SQLAlchemy can detect them
from app.routes.auth import router as auth_router
from app.models.user import User
from app.models.otp import OTP
from app.models.srs import SRSDocument, SRSJob, Diagram, DiagramJob, CostEstimate
from app.routes.board import router as Board_router
from app.routes.column import router as Column_router
from app.routes.task import router as task_router
from app.routes.ai import router as ai_router
from app.routes.chat import router as ai_chat
from app.routes.srs import router as srs_router
from app.routes.diagrams import router as diagrams_router
from app.routes.srs_board import router as srs_board_router
from app.routes.cost import router as cost_router
from app.routes.demo import router as demo_router
from app.core.migrate import ensure_task_columns
import logging
app = FastAPI(
    title="AI Project Management API",
    version="1.0.0"
)
_origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
] + [o.strip().rstrip("/") for o in settings.FRONTEND_ORIGINS.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create tables in Neon PostgreSQL
Base.metadata.create_all(bind=engine)
# create_all never adds columns to existing tables: add the Phase 4 task columns if missing
try:
    ensure_task_columns(engine)
except Exception:  # never stop the API from starting; the error is logged
    logging.getLogger("stackpilot").exception("Task column migration failed")

# REGISTER ROUTES
app.include_router(auth_router)

# Board Routes
app.include_router(Board_router)
# Column Route
app.include_router(Column_router)
#Task Route
app.include_router(task_router)

#Generate AI project route
app.include_router(ai_router)
# Get AI assistance
app.include_router(ai_chat)



# SRS generation (questions -> requirements -> SRS document)
app.include_router(srs_router)

# UML diagrams generated from the SRS
app.include_router(diagrams_router)

# SRS -> Kanban board generation and per-task traceability
app.include_router(srs_board_router)

# Pakistan cost estimation (deterministic engine + optional AI explanation)
app.include_router(cost_router)
app.include_router(demo_router)



@app.exception_handler(Exception)
async def safe_unexpected_error(request: Request, exc: Exception):
    """Log diagnostic details server-side; never expose stack traces to visitors."""
    logging.getLogger("stackpilot").exception("Unhandled API error on %s", request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Something went wrong on our side. Please try again. If the problem continues, contact the presenter."})

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