from app.rag.embedding_service import create_embedding
from app.rag.qdrant_service import qdrant


def retrieve_chat_memory(
    board_id: int,
    question: str
):
    embedding = create_embedding(question)

    results = qdrant.search_vectors(
        embedding=embedding,
        board_id=board_id,
        limit=5
    )

    memory = ""

    for result in results:

        payload = result.payload

        if payload["type"] != "chat":
            continue

        memory += f'{payload["role"]}: {payload["text"]}\n'

    return memory