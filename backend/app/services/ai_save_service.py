from sqlalchemy.orm import Session

from app.models.board import Board
from app.models.column import BoardColumn
from app.models.task import Task
from app.schemas.ai_save import SaveProjectRequest
from fastapi import HTTPException
def save_project(
    db: Session,
    board_id: int,
    data: SaveProjectRequest,
    user_id: int,
):
    try:
        # found Board
        board = db.query(Board).filter(
            Board.id == board_id,
            Board.owner_id == user_id
        ).first()

        if not board:
            raise HTTPException(
                status_code=404,
                detail="Board not found."
            )
        existing_columns = db.query(BoardColumn).filter(
        BoardColumn.board_id == board.id
        ).first()

        if existing_columns:
            raise HTTPException(
            status_code=400,
            detail="This board already contains columns. AI generation is only available for empty boards."
            )
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

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
        status_code=500,
        detail=str(e)
    )