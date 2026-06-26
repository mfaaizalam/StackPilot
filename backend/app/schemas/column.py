from pydantic import BaseModel

class ColumnCreate(BaseModel):
    name: str
    board_id: int

class ColumnResponse(ColumnCreate):
    id: int

    class Config:
        from_attributes = True