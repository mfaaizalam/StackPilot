from fastapi import APIRouter
from app.services.ai import get_ai_response

router = APIRouter()

@router.post("/chat")
def chat(message:str):
    reply = get_ai_response(message)
    return {"response":reply}