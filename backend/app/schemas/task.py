from pydantic import BaseModel

class TaskCreate(BaseModel):
    title: str
    description: str | None = None
    priority: str
    column_id: int

class TaskUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    priority: str | None = None
    column_id: int | None = None

class TaskResponse(TaskCreate):
    id: int
    created_by: int

    class Config:
        from_attributes = True