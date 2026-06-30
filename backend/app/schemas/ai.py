from pydantic import BaseModel


class ProjectGenerateRequest(BaseModel):
    project_name: str
    project_type: str = "fullstack"
    requirements: str


class GenerateTask(BaseModel):
    title: str
    description: str
    priority: str
    column_name: str


class ProjectGenerateResponse(BaseModel):
    columns: list[str]
    tasks: list[GenerateTask]