from pydantic import BaseModel

class authDTO(BaseModel):
    email: str
    password: str