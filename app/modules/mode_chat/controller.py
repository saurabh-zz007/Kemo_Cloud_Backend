from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any

from .repository import ChatRepository
from .service import DeepSeekService
from .data_transfer_objects import ChatRequest

# Instantiating the service at module level to reuse the client & system prompt cache
deepseek_service = DeepSeekService()

class ChatController:
    @staticmethod
    def process_user_query(
        user_id: str,
        request: ChatRequest,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        Coordinates repository and service execution for incoming user prompts.
        """
        if not request.prompt.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Prompt cannot be empty."
            )

        try:
            repo = ChatRepository(db)
            
            # Delegates memory fetching, LLM generation, and memory storage to service
            generator = deepseek_service.generate_plan(
                user_id=user_id,
                user_prompt=request.prompt,
                repo=repo
            )
            
            return generator

        except Exception as e:
            # Handle controller-level errors gracefully
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error processing chat request: {str(e)}"
            )