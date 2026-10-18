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
    # Phase 4 (None for tasks that were not generated from an SRS)
    requirement_id: str | None = None
    estimate_points: int | None = None
    depends_on: list[str] | None = None
    srs_id: int | None = None

    class Config:
        from_attributes = True
