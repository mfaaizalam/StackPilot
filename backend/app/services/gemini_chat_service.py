from google import genai

from app.core.config import settings
from app.prompts.chat_prompt import SYSTEM_PROMPT 
# from app.services.context_builder import build_context
from app.rag.retrieval_service import build_rag_context 
from app.services.chat_service import (
    save_message
)
from app.rag.chat_retrieval import retrieve_chat_memory
client = genai.Client(
    api_key=settings.GEMINI_API_KEY
)

def ask_ai(
        db,
        board_id:int,
        user_id:int,
        user_message:str,
):
    
      # Save user's message
    save_message(
        db=db,
        board_id=board_id,
        user_id=user_id,
        role="user",
        message=user_message
    )
    chat_memory = retrieve_chat_memory(
    board_id=board_id,
    question=user_message
    )
    
    rag_context = build_rag_context(
        db=db,
        board_id=board_id,
        question=user_message
        )
    
    prompt = f"""
    Current Project Context:
    {rag_context}
    Relevant Previous Conversation:
    {chat_memory}
    Current user Question:
    {user_message}
    """
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[
            SYSTEM_PROMPT,
            prompt
        ]
    )
    answer = response.text.strip()
     # Save AI's reply
    save_message(
        db=db,
        board_id=board_id,
        user_id=user_id,
        role="assistant",
        message=answer
    )

    return answer   


# 3 we replace  context_builder in service folder with  build_rag_context in rag folder to implement rag