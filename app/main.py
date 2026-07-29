from fastapi import FastAPI, Depends, HTTPException
from app.modules.mode_chat.data_transfer_objects import UserRequest, TaskResponse
from app.modules.mode_chat.router import mode_chat_router
from app.modules.auth.router import auth_router

app = FastAPI(title="KEMO.ai")

app.include_router(auth_router)
app.include_router(mode_chat_router)

