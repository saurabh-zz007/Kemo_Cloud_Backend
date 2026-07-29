from fastapi import APIRouter, Depends, Request
from app.modules.mode_chat.data_transfer_objects import UserRequest, TaskResponse
from app.modules.mode_chat.service import DeepSeekService
from app.modules.mode_chat.controller import mode_chat_controller
mode_chat_router = APIRouter(prefix="/mode")

@mode_chat_router.post("/chat", response_model=TaskResponse)
def mode_chat(request: Request, user: UserRequest):
    return mode_chat_controller(user, llm=DeepSeekService())