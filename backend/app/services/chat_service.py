from sqlalchemy.orm import Session
from app.models.chat import Chat
from app.models.board import Board
from app.rag.chat_memory import index_chat
def save_message(
        db:Session,
        board_id:int,
        user_id:int,
        role:str,
        message:str
):
    chat = Chat(
        board_id=board_id,
        user_id =user_id,
        role =role,
        message=message
    )
    db.add(chat)
    db.commit()
    db.refresh(chat)

    index_chat(chat)
    return chat


