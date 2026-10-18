from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.task import TaskCreate
from app.schemas.task import TaskUpdate
from app.routes.auth import get_current_user
from app.models.task import Task
from app.models.user import User
from app.rag.embedding_service import create_embedding
from app.rag.qdrant_service import qdrant
from app.models.board import Board
from app.models.column import BoardColumn
from app.core.deps import accessible_board_ids, get_owned_column, get_owned_task
from app.services.activity_service import log_activity
router = APIRouter(
    prefix="/tasks",
    tags =["Task"]
)

# Create 
@router.post("/")
def create_column(
    task:TaskCreate,
    db:Session =Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    column = get_owned_column(db, task.column_id, current_user, "editor")
    new_task = Task(
        title = task.title,
        description =task.description,
        priority =task.priority,
        column_id =task.column_id,
        created_by=current_user.id
    )
    db.add(new_task)
    db.commit()
    db.refresh(new_task)
    log_activity(db, column.board_id, current_user.id, "task.created",
                 f"created the task “{new_task.title}” in {column.name}", "task", new_task.id)

    # Adding vector db
    text =f"""
        Title:{new_task.title}
        Description:{new_task.description}
        Priority: {task.priority}
    """
    embedding = create_embedding(text)

    payload = {
        "type":"task",
        "board_id":column.board_id,
        "task_id":new_task.id,
        "column_id":new_task.column_id,
        "priority":new_task.priority,
        "title":new_task.title,
        "text":text
    }
    qdrant.insert_vector(
        embedding=embedding,
        point_id=new_task.id,
        payload=payload
    )
    return new_task

# READ
@router.get("/")
def get_tasks(
    db:Session =Depends(get_db),
    current_user =Depends(get_current_user)
):
    ids = accessible_board_ids(db, current_user)
    if not ids:
        return []
    return db.query(Task).filter(Task.column.has(BoardColumn.board_id.in_(ids))).all()


@router.get("/{task_id}")
def get_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    return get_owned_task(db, task_id, current_user, "viewer")

# Update 
@router.put("/{task_id}")
def update_task(
    task_id:int,
    task_data:TaskUpdate,
    db:Session=Depends(get_db),
    current_user = Depends(get_current_user)
):
    task = get_owned_task(db, task_id, current_user, "editor")
    old_column = task.column
    old_title = task.title
    new_column = None
    if task_data.column_id is not None:
        new_column = get_owned_column(db, task_data.column_id, current_user, "editor")
    if task_data.title is not  None:
        task.title = task_data.title
    if task_data.description is not None:
        task.description = task_data.description
    if task_data.priority is not None:
        task.priority = task_data.priority

    if task_data.column_id is not None:
        task.column_id = task_data.column_id

    db.commit()
    db.refresh(task)
    if new_column is not None and new_column.id != old_column.id:
        log_activity(db, new_column.board_id, current_user.id, "task.moved",
                     f"moved “{task.title}” from {old_column.name} to {new_column.name}", "task", task.id)
    else:
        log_activity(db, old_column.board_id, current_user.id, "task.updated",
                     f"updated the task “{old_title}”", "task", task.id)

    #Update Vector Db
    column =(
        db.query(BoardColumn).filter(BoardColumn.id==task.column_id).first()
    )
    text =f"""
        Title:{task.title}
        Description:{task.description}
        Priority: {task.priority}
    """
    embedding = create_embedding(text)

    payload = {
        "type":"task",
        "board_id":column.board_id,
        "task_id":task.id,
        "column_id":task.column_id,
        "priority":task.priority,
        "title":task.title,
        "text":text
    }
    qdrant.insert_vector(
        embedding=embedding,
        point_id=task.id,
        payload=payload
    )

    return task    

# Delete 
@router.delete("/{task_id}")
def delete_task(
    task_id:int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    task = get_owned_task(db, task_id, current_user, "editor")
    board_id, title = task.column.board_id, task.title
    db.delete(task)
    db.commit()
    log_activity(db, board_id, current_user.id, "task.deleted", f"deleted the task “{title}”", "task", task_id)
    qdrant.delete_vector(task_id)
    return {
        "message":"Task Deleted Successfully"
    }