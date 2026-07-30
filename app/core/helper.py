from jose import jwt, JWTError
import uuid
from fastapi import Request, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.config import settings

security = HTTPBearer()
def get_user_id(credentials:HTTPAuthorizationCredentials = Depends(security)):
    print("Extracting user ID from token")
    try:
        token = credentials.credentials
        print(token)
        if not token:
            raise HTTPException(status_code=401, detail="Invalid token format")
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]) 
        print(payload)
        user_id = uuid.UUID(payload.get("sub"))
        return user_id
    except (JWTError, ValueError): # type: ignore
        raise HTTPException(status_code=401, detail="Invalid token or expired token")