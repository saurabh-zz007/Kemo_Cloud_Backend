import json
import asyncio
import inspect
import copy
from typing import Dict, Any, AsyncGenerator
from openai import AsyncOpenAI

from app.core.config import settings
from .repository import ChatRepository
from app.common.RAG.services import delete_memory_service, update_memory_services, add_memory_service, search_memory_service
from app.common.Tools.search_tool import WebSearchTool
from app.modules.mode_chat.tool_definition import WEB_TOOLS, MEMORY_TOOLS

class DeepSeekService:
    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=settings.DEEPSEEK_API_KEY, 
            base_url="https://api.deepseek.com"
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

        self.reasoning_prompt = """
        CRITICAL: You are an autonomous backend processor. NEVER narrate your plans. If you need data, output ONLY the tool call.

        Your decision engine must analyze the prompt and route your behavior into one of the following execution paths:

        Case 1: Web Research (Using web search, extraction, and crawling to ingest live data, read documentation, or verify facts).

        Case 2: Memory Management (Saving, recalling, updating, or deleting facts about the user, their projects, or preferences using the vector database).

        Case 3: Hybrid (Combining multiple research or memory actions to build a complete answer).

        =========================================
        AVAILABLE ACTIONS
        [Web Research Actions]

        "web_search" (requires: 'query')
        Use to find real-time information, news, or discover URLs you don't know yet.

        "web_extract" (requires: 'url')
        Use to read the full text from a specific, known URL.

        "web_crawl" (requires: 'url', optional: 'instructions')
        Use to deeply scan documentation or map an entire domain.

        [Memory Actions]

        "add_memory" (requires: 'fact_data' [array of strings])
        Use to save important new facts, user preferences, or project details to long-term memory.

        "search_memory" (requires: 'query_text')
        Use to search long-term memory for past context, user preferences, or past conversations via semantic search.

        "update_memory" (requires: 'point_id', 'update_fact_data')
        Use to update an existing memory when the user changes their mind or a previously saved fact becomes outdated. Requires a point_id from a previous search.

        "delete_memory" (requires: 'point_id')
        Use to permanently delete a memory that is incorrect or no longer relevant. Requires a point_id from a previous search.

        =========================================
        MEMORY PROTOCOL & CONFLICT RESOLUTION
        =========================================
        1. RECONCILIATION BEFORE WRITING:
        - Before adding a new fact, you MUST FIRST call `search_memory` to check if a prior version exists.
        - If an existing memory conflicts with or is superseded by the new information:
            - DO NOT call `add_memory`.
            - Take the `id` from the search result and call `update_memory(point_id, update_fact_data)` or `delete_memory(point_id)`.

        2. NEVER CREATE CONFLICTING DUPLICATES:
        - If a search reveals two contradictory facts (e.g., two different names), prompt the user or update the record to reflect the latest confirmed fact.
        
        =========================================
        CRITICAL EXECUTION RULE
        =========================================
        You must perform actions using ONLY the provided native function tools. Do not output raw JSON plans, tasks arrays, or manual function calls in your text response. If an action is required, trigger the tool directly through the API.
        NEVER narrate your plan or explain what you are going to do before calling a tool. If an action is required, trigger the tool immediately without conversational filler.
        """
        self.synthesis_prompt = """You are KEMO, an AI desktop assistant. Using the context and research provided in the conversation history, synthesize a clear, helpful, and highly conversational response to the user. Do not mention your internal tools, reasoning loops, or memory databases to the user."""
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
        tools: list[dict[str, Any]]
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
                    model="deepseek-chat",
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

            messages[0]["content"] = self.synthesis_prompt
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
                yield fallback_msg

        except Exception as e:
            print(f"[DEEPSEEK ERROR] {e}")
            error_fallback = json.dumps({"message": "An error occurred while generating a plan.", "tasks": []})
            yield error_fallback


    async def handle_direct_chat(self, user_id: str, user_prompt: str, repo: ChatRepository) -> AsyncGenerator[str, None]:
        """Layer 1 Wrapper: Orchestrates DB history and the core worker."""
        session = await repo.get_or_create_active_session(user_id)
        history = await repo.get_recent_messages(session.id, limit=10)
        
        messages = [{"role": "system", "content": self.reasoning_prompt}]
        for msg in history:
            messages.append({"role": msg.role, "content": msg.content})
        messages.append({"role": "user", "content": user_prompt})
        
        available_tools = WEB_TOOLS + MEMORY_TOOLS
        
        full_response = ""
        async for chunk in self.generate_plan(user_id, messages, available_tools):
            full_response += chunk
            yield chunk
            
        await repo.save_message(session.id, role="user", content=user_prompt, mode_name="mode_chat")
        await repo.save_message(session.id, role="assistant", content=full_response, mode_name="mode_chat")


    async def handle_research_subtask(self, user_id: str, task_query: str) -> str:
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": self.reasoning_prompt},
            {"role": "user", "content": f"Research Task: {task_query}"}
        ]

        available_tools = WEB_TOOLS

        full_response = ""
        async for chunk in self.generate_plan(user_id, messages, available_tools):
            full_response += chunk

        return full_response
