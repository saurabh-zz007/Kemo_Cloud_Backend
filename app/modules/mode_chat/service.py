import json
import asyncio
from typing import Dict, Any, AsyncGenerator
from openai import AsyncOpenAI
from app.core.config import settings
from .repository import ChatRepository
from app.modules.RAG.services import rag_pipeline_task
from app.modules.RAG.vector_search import VectorSearchService
from app.common.Tools.search_tool import SearchTool

vector_search_service = VectorSearchService()

class DeepSeekService:
    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=settings.DEEPSEEK_API_KEY, 
            base_url="https://api.deepseek.com"
        )
        self.search_tool = SearchTool()
        

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
    async def _execute_tool(self, tool_name: str, arguments_str: str, user_prompt: str) -> str:
        try:
            args = json.loads(arguments_str) if arguments_str else {}
        except Exception:
            args = {}

        match tool_name:
            case "web_search":
                query = args.get("query", user_prompt)
                return await self.search_tool.search(query=query)


            case _:
                return f"Error: Tool '{tool_name}' is not registered."
            

    async def generate_plan(self, user_id: str, user_prompt: str, repo: ChatRepository) -> AsyncGenerator[str, None]:
    
        session = await repo.get_or_create_active_session(user_id)
        history = await repo.get_recent_messages(session.id, limit=10) #type:ignore

        messages: list[dict[str, Any]] = [{"role": "system", "content": self.system_prompt}]

        for msg in history:
            messages.append({"role": msg.role, "content": msg.content})
        long_term_memory = await vector_search_service.search_similar_memories(
            user_id=user_id, 
            query=user_prompt,
            mode_name="mode_chat"
        )

        if long_term_memory:
            augmented_user_prompt = (
                f"<past_memories>\n{long_term_memory}\n</past_memories>\n\n"
                f"User Question: {user_prompt}"
            )
        else:
            augmented_user_prompt = user_prompt

        messages.append({"role": "user", "content": augmented_user_prompt})

        tools = [
            {
                "type": "function",
                "function": {
                    "name": "web_search",
                    "description": "Search the live web for real-time information, documentation, package names (winget), news, or accurate facts.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "The search query to look up on the web."
                            }
                        },
                        "required": ["query"]
                    }
                }
            }
        ]

        full_text = ""
        max_tool_iterations = 3
        iteration = 0

        try:
            while iteration < max_tool_iterations:
                iteration += 1
                print(f"[DEEPSEEK] Reasoning loop iteration {iteration}...")

                response = await self.client.chat.completions.create(
                    model="deepseek-chat",
                    messages=messages,  # type: ignore
                    tools=tools,  # type: ignore
                    tool_choice="auto",
                    temperature=0.0
                )

                response_message = response.choices[0].message

                if response_message.tool_calls:
                    print(f"[DEEPSEEK] Tool call requested: {len(response_message.tool_calls)} tool(s)")

                    formatted_tool_calls = []
                    for tc in response_message.tool_calls:
                        if hasattr(tc, "function") and tc.function: #type: ignore
                            formatted_tool_calls.append({
                                "id": tc.id,
                                "type": "function",
                                "function": {
                                    "name": tc.function.name, #type: ignore
                                    "arguments": tc.function.arguments #type: ignore
                                }
                            })

                    messages.append({
                        "role": "assistant",
                        "content": response_message.content or "",
                        "tool_calls": formatted_tool_calls
                    })

                    for tool_call in response_message.tool_calls:
                        if hasattr(tool_call, "function") and tool_call.function: #type: ignore
                            tool_result = await self._execute_tool(
                                tool_name=tool_call.function.name, #type: ignore
                                arguments_str=tool_call.function.arguments, #type: ignore
                                user_prompt=user_prompt
                            )

                            messages.append({
                                "role": "tool",
                                "tool_call_id": tool_call.id,
                                "content": tool_result or "No results found on the web."
                            })

                    continue

                else:
                    print("[DEEPSEEK] Final response ready. Yielding output...")
                    break

            print("[DEEPSEEK] Streaming final response...")
            stream_response = await self.client.chat.completions.create(
                model="deepseek-chat",
                messages=messages,  # type: ignore
                # Note: We do NOT pass tools here so it focuses entirely on text generation
                temperature=0.0,
                stream=True
            )

            async for chunk in stream_response:
                if chunk.choices and chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    full_text += content
                    yield content

            if not full_text.strip():
                fallback_msg = json.dumps({"message": "I searched the web but could not structure a response.", "tasks": []})
                full_text = fallback_msg
                yield fallback_msg

            await repo.save_message(session.id, role="user", content=user_prompt, mode_name="mode_chat") #type: ignore
            await repo.save_message(session.id, role="assistant", content=full_text, mode_name="mode_chat") #type: ignore

            asyncio.create_task(
                rag_pipeline_task(
                    mode_name="mode_chat",
                    user_prompt=user_prompt,
                    response=full_text,
                    user_id=user_id
                )
            )

        except Exception as e:
            print(f"[DEEPSEEK ERROR] {e}")
            error_fallback = json.dumps({"message": "An error occurred while generating a plan.", "tasks": []})
            yield error_fallback