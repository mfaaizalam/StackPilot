from app.rag.embedding_service import create_embedding
from app.rag.qdrant_service import qdrant

def index_chat(chat):
    text = chat.message

    embedding = create_embedding(text)

    payload = {
        "type": "chat",
        "board_id": chat.board_id,
        "chat_id": chat.id,
        "role": chat.role,
        "text": text
    }

    qdrant.insert_vector(
        point_id=1000000 + chat.id,
        embedding=embedding,
        payload=payload
    )