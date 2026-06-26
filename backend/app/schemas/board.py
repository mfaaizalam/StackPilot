from pydantic import BaseModel

class BoardCreate(BaseModel):
    name:str
    description:str | None = None

class BoardResponse(BoardCreate):
    id: int 
    owner_id:int 
class Config:
    from_attributes = True