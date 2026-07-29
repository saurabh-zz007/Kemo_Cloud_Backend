from fastapi import Request
from app.modules.auth.data_transfer_objects import authDTO

def login(request: Request, user: authDTO):
    return {"Email": user.email,
            "Password": user.password}

def signup(request: Request, user: authDTO):
    return {"Email": user.email,
            "Password": user.password}
