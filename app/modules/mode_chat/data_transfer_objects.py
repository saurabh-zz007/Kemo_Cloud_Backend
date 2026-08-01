from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class UserRequest(BaseModel):
    prompt: str

class TaskResponse(BaseModel):
    status: str
    tasks: List[Dict[str, Any]]
    message: str

class ChatRequest(BaseModel):
    prompt: str = Field(..., description="The user's input prompt or command.")

class TaskItem(BaseModel):
    action: str
    arguments: Optional[Dict[str, Any]] = None

class ChatResponse(BaseModel):
    message: Optional[str] = None
    tasks: Optional[List[TaskItem]] = None