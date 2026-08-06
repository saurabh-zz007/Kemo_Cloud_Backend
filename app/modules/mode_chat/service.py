import json
import asyncio
from typing import Dict, Any, AsyncGenerator
from openai import AsyncOpenAI
from app.core.config import settings
from .repository import ChatRepository
from app.modules.RAG.services import rag_pipeline_task
from app.modules.RAG.vector_search import VectorSearchService

vector_search_service = VectorSearchService()

class DeepSeekService:
    def __init__(self):
        # Using AsyncOpenAI so FastAPI can handle requests concurrently
        self.client = AsyncOpenAI(
            api_key=settings.DEEPSEEK_API_KEY, 
            base_url="https://api.deepseek.com"
        )
        
        # 🚨 THE PREFIX CACHE: This string must NEVER dynamically change. 
        # DeepSeek caches this exact block to save you 90% on tokens.
        self.system_prompt = """
        You are KEMO, an AI desktop assistant system brain.
        You have to decide weather the user needs to :
        Case-1. Do some physical tasks or actions with pc.
        Case-2. If wants to talk or get some general information on coding, system or anything.
        Case-3. If the user needs mix of both things.
        According to the user prompt.

        Available actions:
        - "openApp" (requires 'app_name')
        - "closeApp" (requires 'app_name')
        - "getSystemStatus" (no arguments)
        - "optimizeSystem" (no arguments)
        - "setupEnvironment" (requires 'package_id')
        - "removeEnvironment" (requires 'package_id')
        Critical: For setupEnvironment and removeEnvironment, the package id should be from windows winget list. Check the latest data of official winget before returning the package names.

        For Case-1 and Case-3.
        You MUST respond in strict JSON format containing a "tasks" array.
        Example: {"tasks": [{"action": "setupEnvironment", "arguments": {"package_id": "OpenJS.NodeJS"}}], "message": "Trying to setup OpenJS.NodeJS environment"}

        For Case-2.
        If no actions are needed, return: {"message": "Your response to the user according to the prompt"}
        """

    # Note the return type changed to AsyncGenerator to support streaming
    async def generate_plan(self, user_id: str, user_prompt: str, repo: ChatRepository) -> AsyncGenerator[str, None]:
        # 1. Fetch active session and short-term history from PostgreSQL
        session = await repo.get_or_create_active_session(user_id)
        history = await repo.get_recent_messages(session.id, limit=10) #type:ignore

        # 2. Build the messages array starting with the CACHED system prompt
        messages: list[dict[str, Any]] = [{"role": "system", "content": self.system_prompt}]

        # 3. Inject short-term memory chronologically
        #for msg in history:
        #    messages.append({"role": msg.role, "content": msg.content})
        # Fetch long-term memories from Qdrant filtered by user_id AND mode_chat
        # 1. Fetch long-term memories
        long_term_memory = await vector_search_service.search_similar_memories(
            user_id=user_id, 
            query=user_prompt,
            mode_name="mode_chat"
        )

        # 2. Format the user prompt with strict XML boundaries
        if long_term_memory:
            augmented_user_prompt = (
                f"<past_memories>\n{long_term_memory}\n</past_memories>\n\n"
                f"User Question: {user_prompt}"
            )
        else:
            augmented_user_prompt = user_prompt

        # 3. Append to messages
        messages.append({"role": "user", "content": augmented_user_prompt})
        # 4. Append current user query at the end
        messages.append({"role": "user", "content": user_prompt})

        # We will build the full string here as it streams
        full_text = ""

        try:
            # 5. Call DeepSeek asynchronously with stream=True
            response = await self.client.chat.completions.create(
                model="deepseek-chat",
                messages=messages, # type: ignore
                temperature=0.0, # Strict logic execution
                response_format={"type": "json_object"}, # Guarantees valid JSON output
                stream=True,
            )
            
            # 6. Stream the chunks as they arrive
            async for chunk in response:
                if chunk.choices and chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    full_text += content  # Accumulate the text for the database
                    yield content         # Yield chunk immediately to the frontend

            # --- THE STREAM IS NOW FINISHED ---

            # 7. Save user query and full AI response back to PostgreSQL
            await repo.save_message(session.id, role="user", content=user_prompt, mode_name="mode_chat")
            await repo.save_message(session.id, role="assistant", content=full_text, mode_name="mode_chat")

            # 8. Generate embedding asynchronously without blocking the main flow
            asyncio.create_task(
                rag_pipeline_task(
                    mode_name="mode_chat",
                    user_prompt=user_prompt,
                    response=full_text,
                    user_id=user_id
                )
            )
            
        except Exception as e:
            print(f"DeepSeek Service Error: {e}")
            # If an error happens, yield a valid fallback JSON string
            yield '{"message": "An error occurred while generating a plan.", "tasks": []}'