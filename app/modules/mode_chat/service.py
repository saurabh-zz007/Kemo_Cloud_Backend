import json
import asyncio
import inspect
from typing import Dict, Any, AsyncGenerator
from openai import AsyncOpenAI
from app.core.config import settings
from .repository import ChatRepository
from app.modules.RAG.services import delete_memory_service, update_memory_services, add_memory_service, search_memory_service
from app.common.Tools.search_tool import WebSearchTool


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

        self.system_prompt = """
        You are KEMO, an AI desktop assistant system brain operating strictly as a Tier 3 Web and Memory Worker.
        You do NOT have permissions to execute physical OS tasks, open applications, or modify local environments. Your core responsibilities are to act as the primary research engine and to autonomously manage long-term user memory, either directly answering user queries or fulfilling directives passed down by upper-tier orchestrator AIs.

        Your decision engine must analyze the prompt and route your behavior into one of the following execution paths:

        Case 1: Web Research (Using web search, extraction, and crawling to ingest live data, read documentation, or verify facts).

        Case 2: Memory Management (Saving, recalling, updating, or deleting facts about the user, their projects, or preferences using the vector database).

        Case 3: General Intelligence (Conversational replies, writing code, or explaining concepts using your internal knowledge or provided context).

        Case 4: Hybrid (Combining multiple research or memory actions to build a complete answer).

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
        OUTPUT FORMAT (STRICT JSON)
        You MUST respond EXCLUSIVELY in valid JSON format. Do not include markdown code blocks (```json) around your response, no conversational filler outside the JSON, and no preambles.

        IF ACTIONS ARE NEEDED (Cases 1, 2, and 4):
        Return a JSON object containing a "tasks" array of the actions to execute, and a "message" explaining your intent.
        {
        "tasks": [
        {
        "action": "<action_name>",
        "arguments": {
        "<arg_key>": "<arg_value>"
        }
        }
        ],
        "message": ""
        }

        IF NO ACTIONS ARE NEEDED (Case 3):
        Return a JSON object containing only a "message" key.
        {
        "message": "<Your complete, detailed conversational or generated response.>"
        }

        =========================================
        EXAMPLES
        Example 1: Saving a new user preference.
        {"tasks": [{"action": "add_memory", "arguments": {"fact_data": ["User is building a FastAPI backend", "User prefers modular architecture"]}}], "message": "Saving your framework and architectural preferences to long-term memory."}

        Example 2: Searching memory for context before answering.
        {"tasks": [{"action": "search_memory", "arguments": {"query_text": "current desktop application tech stack"}}], "message": "I need to check my memory to recall what tech stack we are using for your desktop app."}

        Example 3: Answering a general question without tools.
        {"message": "Python FastAPI is an excellent choice for building asynchronous APIs due to its native support for async/await and automatic interactive documentation generation."}
        """
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
            

    async def generate_plan(self, user_id: str, user_prompt: str, repo: ChatRepository, mode_name: str = "mode_chat") -> AsyncGenerator[str, None]:
    
        session = await repo.get_or_create_active_session(user_id)
        history = await repo.get_recent_messages(session.id, limit=10) #type:ignore

        messages: list[dict[str, Any]] = [{"role": "system", "content": self.system_prompt}]

        #for msg in history:
        #    messages.append({"role": msg.role, "content": msg.content})
        
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
            },
            {
                "type": "function",
                "function": {
                    "name": "web_extract",
                    "description": "Extract clean, raw text content from a specific URL. Use this when you already have a link and need to read the full page.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "url": {
                                "type": "string",
                                "description": "The specific URL to extract content from."
                            },
                            "query": {
                                "type": "string",
                                "description": "Optional. A query to focus the extraction on specific information, returning relevant chunks instead of the full page."
                            },
                            "extract_depth": {
                                "type": "string",
                                "enum": ["basic", "advanced"],
                                "description": "Optional. 'basic' is faster, 'advanced' bypasses more complex site protections. Defaults to 'basic'."
                            },
                            "chunks": {
                                "type": "integer",
                                "description": "Optional. The maximum number of relevant snippets to return per source. Only used if 'query' is provided. Defaults to 3."
                            }
                        },
                        "required": ["url"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "web_crawl",
                    "description": "Crawl a website starting from a specific URL to discover and extract information across multiple pages.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "url": {
                                "type": "string",
                                "description": "The root URL to begin the crawl."
                            },
                            "instructions": {
                                "type": "string",
                                "description": "Optional. Natural language instructions to guide the crawler (e.g., 'Find all pricing pages'). Required if using chunks_per_source."
                            },
                            "chunks_per_source": {
                                "type": "integer",
                                "description": "Optional. Max snippets to extract per page. Requires 'instructions' to be set. Defaults to 3."
                            },
                            "max_depth": {
                                "type": "integer",
                                "description": "Optional. How many levels deep to click from the starting URL. Defaults to 1."
                            },
                            "max_breadth": {
                                "type": "integer",
                                "description": "Optional. Maximum links to follow per page level. Defaults to 10."
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Optional. The hard limit on total pages to crawl and process. Defaults to 1."
                            }
                        },
                        "required": ["url"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                "name": "add_memory",
                "description": "Save important new facts, user preferences, or project details to long-term memory. Use this when the user shares information that should be remembered for future conversations.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "fact_data": {
                            "type": "array",
                            "items": {
                            "type": "string"
                            },
                            "description": "A list of clean, standalone factual statements to save. E.g., ['User prefers C++ for backends.', 'User is building a desktop app.']"
                        }
                    },
                    "required": ["fact_data"]
                }
                }
            },
            {
                "type": "function",
                "function": {
                "name": "search_memory",
                "description": "Search long-term memory for past context, user preferences, or specific past conversations using semantic search.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query_text": {
                            "type": "string",
                            "description": "The search query to find relevant memories. E.g., 'What framework are we using?'"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "The maximum number of results to return. Allowed values: 1 to 20. If you do not pass this parameter, it will automatically default to 5.",
                            "minimum": 1,
                            "maximum": 20,
                            "default": 5
                        },
                        "score_threshold": {
                            "type": "number",
                            "description": "The minimum similarity score a memory must have to be included. Allowed values: 0.0 to 1.0. If you do not pass this parameter, it will automatically default to 0.5.",
                            "minimum": 0.0,
                            "maximum": 1.0,
                            "default": 0.5
                        }
                    },
                    "required": ["query_text"]
                }
                }
            },
            {
                "type": "function",
                "function": {
                "name": "update_memory",
                "description": "Update an existing memory with new information. Use this when the user changes their mind or a previously saved fact becomes outdated.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "point_id": {
                            "type": "string",
                            "description": "The exact UUID of the memory to update, retrieved from a previous search_memory call."
                        },
                        "update_fact_data": {
                            "type": "string",
                            "description": "The completely new fact text that will replace the old memory."
                        }
                    },
                    "required": ["point_id", "update_fact_data"]
                }
                }
            },
            {
                "type": "function",
                "function": {
                "name": "delete_memory",
                "description": "Permanently delete a memory that is incorrect, hallucinated, or no longer relevant.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "point_id": {
                            "type": "string",
                            "description": "The exact UUID of the memory to delete, retrieved from a previous search_memory call."
                        }
                    },
                    "required": ["point_id"]
                }
                }
            }
        ]

        full_text = ""
        max_tool_iterations = 8
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
                                user_id=user_id,
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


        except Exception as e:
            print(f"[DEEPSEEK ERROR] {e}")
            error_fallback = json.dumps({"message": "An error occurred while generating a plan.", "tasks": []})
            yield error_fallback