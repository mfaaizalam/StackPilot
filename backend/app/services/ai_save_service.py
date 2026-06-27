from sqlalchemy.orm import Session

from app.models.board import Board
from app.models.column import BoardColumn
from app.models.task import Task

from app.schemas.ai_save import SaveProjectRequest


def save_project(
    db: Session,
    data: SaveProjectRequest,
    user_id: int
):
    try:
        # Create Board
        board = Board(
            name=data.board_name,
            description=data.project_description,
            owner_id=user_id
        )

        db.add(board)
        db.flush()   # Generate board.id without committing

        # Store column name -> column id
        column_map = {}

        # Create Columns
        for column_name in data.columns:
            column = BoardColumn(
                name=column_name,
                board_id=board.id
            )

            db.add(column)
            db.flush()   # Generate column.id

            column_map[column_name] = column.id

        # Create Tasks
        for task in data.tasks:
            new_task = Task(
                title=task.title,
                description=task.description,
                priority=task.priority,
                column_id=column_map[task.column_name],
                created_by=user_id
            )

            db.add(new_task)

        # Save everything at once
        db.commit()

        return {
            "message": "Project saved successfully.",
            "board_id": board.id,
            "board_name": board.name
        }

    except Exception:
        db.rollback()
        raise