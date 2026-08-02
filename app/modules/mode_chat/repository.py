from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from app.modules.mode_chat.models import ChatSession, ChatMessage
import uuid
class ChatRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_or_create_active_session(self, user_id: str) -> ChatSession:
        # Grab the user's most recently updated session
        safe_user_id = str(user_id)  # Ensure user_id is a string
        stmt = select(ChatSession).where(ChatSession.user_id == safe_user_id).order_by(ChatSession.updated_at.desc()).limit(1)
        result = await self.session.execute(stmt)
        chat_session = result.scalar_one_or_none()

        # If no session exists, create one
        if not chat_session:
            chat_session = ChatSession(user_id=user_id)
            self.session.add(chat_session)
            await self.session.commit()
            await self.session.refresh(chat_session)

        return chat_session

    async def get_recent_messages(self, session_id: str, limit: int = 10) -> List[ChatMessage]:
        stmt = (
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())[::-1] # Reverse to chronological order

    async def save_message(self, session_id: str, role: str, content: str) -> ChatMessage:
        message = ChatMessage(session_id=session_id, role=role, content=content)
        self.session.add(message)
        
        # Touch the session's updated_at timestamp
        stmt = select(ChatSession).where(ChatSession.id == session_id)
        result = await self.session.execute(stmt)
        chat_session = result.scalar_one()

        await self.session.commit()
        return message