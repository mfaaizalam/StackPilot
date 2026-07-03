from sqlalchemy.orm import Session

from app.models.board import Board
from app.models.column import BoardColumn
from app.models.task import Task

from app.rag.embedding_service import create_embedding
from app.rag.qdrant_service import qdrant


def build_rag_context(
    db: Session,
    board_id: int,
    question: str,
):
    # -----------------------------
    # Get Board
    # -----------------------------
    board = (
        db.query(Board)
        .filter(Board.id == board_id)
        .first()
    )

    if not board:
        return "Board not found."

    # -----------------------------
    # Get Columns
    # -----------------------------
    columns = (
        db.query(BoardColumn)
        .filter(BoardColumn.board_id == board_id)
        .all()
    )

    # -----------------------------
    # Semantic Task Retrieval
    # -----------------------------
    embedding = create_embedding(question)

    results = qdrant.search_vectors(
        embedding=embedding,
        board_id=board_id,
        limit=5
    )

    relevant_task_ids = set()

    for result in results:
        payload = result.payload

        if payload.get("type") == "task":
            relevant_task_ids.add(payload.get("task_id"))

    # -----------------------------
    # Build Column -> Task Mapping
    # -----------------------------
    project_structure = ""

    for column in columns:

        project_structure += f"\n{column.name}\n"

        tasks = (
            db.query(Task)
            .filter(Task.column_id == column.id)
            .all()
        )

        if not tasks:
            project_structure += "  (No tasks)\n"
            continue

        for task in tasks:

            marker = ""

            if task.id in relevant_task_ids:
                marker = "⭐ "

            project_structure += (
                f"- {marker}{task.title} "
                f"(Priority: {task.priority})\n"
            )

    # -----------------------------
    # Final Context
    # -----------------------------
    context = f"""
Board Name:
{board.name}

Board Description:
{board.description}

Project Structure:
{project_structure}
"""

    return context.strip()