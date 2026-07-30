from pydantic import BaseModel, EmailStr
from datetime import datetime
import uuid

class create_user_schema(BaseModel):
    email: EmailStr
    password: str
    full_name: str

class UserResponse(BaseModel):
    id: uuid.UUID
    email: EmailStr
    full_name: str
    created_at: datetime

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class authenticate_user_schema(BaseModel):
    email: str
    password: str