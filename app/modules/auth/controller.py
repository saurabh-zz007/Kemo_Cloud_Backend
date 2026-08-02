from fastapi import Request
from app.modules.auth.schemas import authenticate_user_schema, create_user_schema
from app.core.config import settings
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.auth.model import userModel
import bcrypt
from jose import jwt
from datetime import datetime, timedelta
from sqlalchemy import select

async def verify_password(plain_password, hashed_password) -> bool:
    try:
        # Convert strings to utf-8 bytes required by bcrypt
        plain_bytes = plain_password.encode('utf-8')
        # Truncate to 72 bytes to respect bcrypt's hard cap
        plain_bytes = plain_bytes[:72]
        
        hashed_bytes = hashed_password.encode('utf-8')
        
        # Direct bcrypt verification
        return bcrypt.checkpw(plain_bytes, hashed_bytes)
    except Exception as err:
        print(f"Password verification error: {err}")
        return False
    
async def create_access_token(data: dict) -> str:
    """Generates a JWT token embedding the user data."""
    to_encode = data.copy()
    expire = datetime.now() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

async def authenticate_user(request: Request, user: authenticate_user_schema, db: AsyncSession):
    try:
        find_user = select(userModel).where(userModel.email == user.email)
        user_result = await db.execute(find_user)
        db_user = user_result.scalars().first()
        if db_user:
            print(f"user: {user.password}")
            print(f"db_user: {db_user.hashed_password}")
        if not db_user:
            return {"error": "User not found"}
        if not await verify_password(user.password, db_user.hashed_password):
            return {"error": "Invalid password"}
        return await create_access_token({"sub": str(db_user.id)})
    except Exception as e:
        return {"error": str(e)}

async def create_user(request: Request, user: create_user_schema, db: AsyncSession):
    try:
        raw_hash = bcrypt.hashpw(user.password.encode('utf-8'), bcrypt.gensalt())
        hashed_password_str = raw_hash.decode('utf-8')
        print(f"Creating user with email: {user.email}, hashed_password: {hashed_password_str}, full_name: {user.full_name}")
        new_user = userModel(email=user.email, hashed_password=hashed_password_str, full_name=user.full_name)
        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)
        return new_user
    except Exception as e:
        return {"error": str(e)}
