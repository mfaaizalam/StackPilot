from pydantic import BaseModel
from app.schemas.ai import GenerateTask
class SaveProjectRequest(BaseModel):
    columns:list[str]
    tasks:list[GenerateTask]