import json
import asyncio
import inspect
import copy
from typing import Dict, Any, AsyncGenerator
from openai import AsyncOpenAI

from app.core.config import settings
from app.core.config import settings
from .repository import ChatRepository
from app.common.RAG.services import delete_memory_service, update_memory_services, add_memory_service, search_memory_service
from app.common.Tools.search_tool import WebSearchTool
from app.modules.mode_chat.tool_definition import WEB_TOOLS, MEMORY_TOOLS
from app.modules.mode_chat.system_prompt import direct_system_prompt_reasoning, direct_system_prompt_synthesizer, worker_system_prompt_reasoning, worker_system_prompt_synthesis

class DeepSeekService:
    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=settings.OPENROUTER_API_KEY, 
            base_url=settings.OPENROUTER_BASE_URL,
            default_headers={
                "X-Title": settings.PROJECT_NAME, 
            }
        )
        self.mode_name = "mode_chat"
        self.search_tool = WebSearchTool()
        self.tool_registry = {
            "web_search": self.search_tool.search,
            "web_extract": self.search_tool.extract,
            "web_crawl": self.search_tool.crawl,
            "delete_memory": delete_memory_service,
            "update_memory": update_memory_services,
            "add_memory": add_memory_service,
            "search_memory": search_memory_service
        }

        
    async def _execute_tool(self, tool_name: str, arguments_str: str,user_id:str, user_prompt: str) -> str:
        print(f"Executing tool: {tool_name} with arguments: {arguments_str}")
        try:
            args = json.loads(arguments_str) if arguments_str else {}
        except Exception:
            args = {}

        tool_function = self.tool_registry.get(tool_name)

        if not tool_function:
            return f"Error: Tool '{tool_name}' is not registered."
            
        try:
            sig = inspect.signature(tool_function)
            params = sig.parameters
            context_pool = {
                "user_id": user_id,
                "user_prompt": user_prompt,
                "mode_name": getattr(self, "mode_name", "mode_chat"),  
            }
            for key, value in context_pool.items():
                if key in params and key not in args:
                    args[key] = value
                    
            return await tool_function(**args)
        
        except Exception as e:
            print(f"[TOOL EXECUTOR ERROR] Failed running {tool_name}: {e}")
            return f"Observation: The tool '{tool_name}' encountered an error: {str(e)}"
            

    async def generate_plan(
        self, 
        user_id: str, 
        messages: list[dict[str, Any]], 
        tools: list[dict[str, Any]],
        system_prompt_reasoning: str,
        system_prompt_synthesizer: str
    ) -> AsyncGenerator[str, None]:


        full_text = ""
        max_tool_iterations = 8
        iteration = 0

        try:
            while iteration < max_tool_iterations:
                iteration += 1
                print(f"[DEEPSEEK] Reasoning loop iteration {iteration}...")

                temp_message = copy.deepcopy(messages) #creating a deep copy
                budget_remaining = max_tool_iterations - iteration
                
                if budget_remaining == 0:
                    temp_message[0]["content"] += "\nWARNING: This is the final reasoning loop. You may execute one last batch of tool calls if absolutely necessary, but you will not be able to follow up on their results."
                else:
                    temp_message[0]["content"] += f"\n\nCRITICAL SYSTEM UPDATE: Reasoning loop iterations remaining: {budget_remaining}."

                response = await self.client.chat.completions.create(
                    model=settings.OPENROUTER_WORKER_MODEL_NAME,
                    messages=temp_message,  # type: ignore
                    tools=tools if tools else None,  # type: ignore
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
                                user_id=user_id,
                                tool_name=tool_call.function.name, #type: ignore
                                arguments_str=tool_call.function.arguments, #type: ignore
                                user_prompt=messages[-1]["content"]
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

            messages[0]["content"] = system_prompt_synthesizer
            stream_response = await self.client.chat.completions.create(
                model=settings.OPENROUTER_WORKER_MODEL_NAME,
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
                yield fallback_msg

        except Exception as e:
            print(f"[DEEPSEEK ERROR] {e}")
            error_fallback = json.dumps({"message": "An error occurred while generating a plan.", "tasks": []})
            yield error_fallback


    async def handle_direct_chat(self, user_id: str, user_prompt: str, repo: ChatRepository) -> AsyncGenerator[str, None]:
        """Layer 1 Wrapper: Orchestrates DB history and the core worker."""
        session = await repo.get_or_create_active_session(user_id)
        history = await repo.get_recent_messages(session.id, limit=10)
        
        messages = [{"role": "system", "content": direct_system_prompt_reasoning}]
        for msg in history:
            messages.append({"role": msg.role, "content": msg.content})
        messages.append({"role": "user", "content": user_prompt})
        
        available_tools = WEB_TOOLS + MEMORY_TOOLS
        
        full_response = ""
        async for chunk in self.generate_plan(user_id, messages, available_tools, direct_system_prompt_reasoning, direct_system_prompt_synthesizer):
            full_response += chunk
            yield chunk
            
        await repo.save_message(session.id, role="user", content=user_prompt, mode_name="mode_chat")
        await repo.save_message(session.id, role="assistant", content=full_response, mode_name="mode_chat")


    async def handle_research_subtask(self, user_id: str, task_query: str) -> str:
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": worker_system_prompt_reasoning},
            {"role": "user", "content": f"Research Task: {task_query}"}
        ]

        available_tools = WEB_TOOLS

        full_response = ""
        async for chunk in self.generate_plan(user_id, messages, available_tools, worker_system_prompt_reasoning, worker_system_prompt_synthesis):
            full_response += chunk

        return full_response
