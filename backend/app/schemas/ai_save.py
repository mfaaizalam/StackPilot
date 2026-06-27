from pydantic import BaseModel
from app.schemas.ai import GenerateTask
class SaveProjectRequest(BaseModel):
    board_name:str
    project_description:str
    columns:list[str]
    tasks:list[GenerateTask]