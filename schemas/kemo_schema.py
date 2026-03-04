from pydantic import BaseModel
from typing import List, Dict, Any

class UserRequest(BaseModel):
    prompt: str

class TaskResponse(BaseModel):
    status: str
    tasks: List[Dict[str, Any]]