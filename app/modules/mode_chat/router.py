from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.responses import StreamingResponse

# Core dependencies (adjust imports based on your actual auth/db paths)
from app.core.database import get_db
from app.core.helper import get_user_id 

from .data_transfer_objects import ChatRequest, ChatResponse
from .controller import ChatController

mode_chat_router = APIRouter(prefix="/chat", tags=["Chat"])

@mode_chat_router.post(
    "",
    status_code=status.HTTP_200_OK,
    summary="Process user prompt with short-term memory awareness"
)
async def chat_endpoint(
    request: ChatRequest,
    user_id: str = Depends(get_user_id),
    db: AsyncSession = Depends(get_db)
):
    generator=ChatController.process_user_query(
        user_id=user_id,
        request=request,
        db=db
    )
    return StreamingResponse(generator, media_type="text/event-stream")