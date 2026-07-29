from fastapi import APIRouter, Request,Depends, status
from app.modules.auth.controller import login, signup
from app.modules.auth.data_transfer_objects import authDTO

auth_router = APIRouter(prefix="/auth")

@auth_router.post("/login")
def auth_login(request: Request, user: authDTO):
    return login(request, user)



@auth_router.post("/signup")
def auth_signup(request: Request, user: authDTO):
    return signup(request, user)
