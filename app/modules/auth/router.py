from fastapi import APIRouter, Request,Depends, status, HTTPException
from app.modules.auth.controller import authenticate_user, create_user
from app.modules.auth.schemas import authenticate_user_schema, create_user_schema
from app.modules.auth.model import userModel
from app.core.database import get_db

auth_router = APIRouter(prefix="/api/auth")

@auth_router.post("/login")
def auth_login(request: Request, user: authenticate_user_schema, db  = Depends(get_db)):
    find_user = db.query(userModel).filter(userModel.email == user.email).first()
    if not find_user:
        raise HTTPException( 
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            )
    token = authenticate_user(request, user, db)
    return {"access_token": token, "token_type": "bearer"}



@auth_router.post("/create")
def auth_signup(request: Request, user: create_user_schema, db = Depends(get_db)):
    new_user = db_user = db.query(userModel).filter(userModel.email == user.email).first()
    if new_user:
        raise HTTPException(status_code=400, detail="User already exists")
    return create_user(request, user, db)
