from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.task import TaskCreate
from app.schemas.task import TaskUpdate
from app.routes.auth import get_current_user
from app.models.task import Task
from app.models.user import User
from app.models.column import BoardColumn
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
    Column= (
        db.query(BoardColumn).filter(BoardColumn.id ==task.column_id ).first()
    )
    if not Column:
        raise HTTPException(
            status_code=404,
            detail="Board not found"
        )
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
    return new_task

# READ
@router.get("/")
def get_tasks(
    db:Session =Depends(get_db)
):
    return db.query(Task).all()


@router.get("/{task_id}")
def get_task(
    task_id: int,
    db: Session = Depends(get_db)
):
    task = (
        db.query(Task)
        .filter(Task.id == task_id)
        .first()
    )

    if not task:
        raise HTTPException(
            status_code=404,
            detail="Task not found"
        )

    return task

# Update 
@router.put("/{task_id}")
def update_task(
    task_id:int,
    task_data:TaskUpdate,
    db:Session=Depends(get_db)
):
    task = (
        db.query(Task)
        .filter(Task.id == task_id)
        .first()
    )
    if not task:
        raise HTTPException(
            status_code=404,
            detail="Task not found"
        )
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

    return task    

# Delete 
@router.delete("/{task_id}")
def delete_task(
    task_id:int,
      db: Session = Depends(get_db)
):
    task = (
        db.query(Task).filter(Task.id==task_id).first()
    )
    db.delete(task)
    db.commit()
    return {
        "message":"Task Deleted Successfully"
    }