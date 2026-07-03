from pydantic import BaseModel
from datetime import datetime
class ChatRequest(BaseModel):
    message:str

class ChatResponse(BaseModel):
    role:str
    message:str
   

    class config:
        from_attributes:True
        