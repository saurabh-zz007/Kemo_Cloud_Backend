from fastapi import APIRouter, Request,Depends, status, HTTPException
from app.modules.auth.controller import authenticate_user, create_user
from app.modules.auth.schemas import authenticate_user_schema, create_user_schema
from app.modules.auth.model import userModel
from app.core.database import get_db
from sqlalchemy import select

auth_router = APIRouter(prefix="/api/auth")

@auth_router.post("/login")
async def auth_login(request: Request, user: authenticate_user_schema, db  = Depends(get_db)):
    user_req = select(userModel).where(userModel.email == user.email)
    find_user = await db.execute(user_req)
    final_user = find_user.scalars().first()
    if not final_user:
        raise HTTPException( 
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            )
    token = await authenticate_user(request, user, db)
    return {"access_token": token, "token_type": "bearer"}



@auth_router.post("/create")
async def auth_signup(request: Request, user: create_user_schema, db = Depends(get_db)):
    user_req = select(userModel).where(userModel.email == user.email)
    new_user = await db.execute(user_req)
    final_user = new_user.scalars().first()
    if final_user:
        raise HTTPException(status_code=400, detail="User already exists")
    return await create_user(request, user, db)
