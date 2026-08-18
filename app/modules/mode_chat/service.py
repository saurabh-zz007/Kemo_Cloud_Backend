import json
import asyncio
from typing import Dict, Any, AsyncGenerator
from openai import AsyncOpenAI
from app.core.config import settings
from .repository import ChatRepository
from app.modules.RAG.services import rag_pipeline_task
from app.modules.RAG.vector_search import VectorSearchService
from app.common.Tools.search_tool import WebSearchTool

vector_search_service = VectorSearchService()

class DeepSeekService:
    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=settings.DEEPSEEK_API_KEY, 
            base_url="https://api.deepseek.com"
        )
        self.search_tool = WebSearchTool()
        self.tool_registry = {
            "web_search": self.search_tool.search,
            "web_extract": self.search_tool.extract,
            "web_crawl": self.search_tool.crawl,
            #add your tools here nigga 
        }

        self.system_prompt = """
        You are KEMO, an AI desktop assistant system brain operating strictly as a Tier 3 Web Worker.
        You do NOT have permissions to execute physical OS tasks, open applications, or modify local environments. Your sole responsibility is to act as the primary research and data-ingestion engine, either directly answering user queries or fulfilling research directives passed down by upper-tier orchestrator AIs.

        Your decision engine must analyze the prompt and route your behavior into one of the following execution paths:

        - Case 1: Web Research & Data Gathering (Using web search, extraction, and crawling to ingest live data, read documentation, or verify facts).
        - Case 2: General Intelligence (Conversational replies, writing code, or explaining concepts using your internal knowledge or the context provided).
        - Case 3: Hybrid (Combining multiple research actions to build a complete answer).

        =========================================
        AVAILABLE ACTIONS
        =========================================

        [Web Research Actions]
        - "web_search" (requires: 'query') 
        Use to find real-time information, news, or discover URLs you don't know yet.
        - "web_extract" (requires: 'url') 
        Use to read the full text from a specific, known URL.
        - "web_crawl" (requires: 'url', optional: 'instructions') 
        Use to deeply scan documentation or map an entire domain.

        =========================================
        OUTPUT FORMAT (STRICT JSON)
        =========================================
        You MUST respond EXCLUSIVELY in valid JSON format. Do not include markdown code blocks (```json) around your response, no conversational filler outside the JSON, and no preambles. 

        IF ACTIONS ARE NEEDED (Case 1 and Case 3):
        Return a JSON object containing a "tasks" array of the research actions to execute, and a "message" explaining your research intent.
        {
        "tasks": [
            {
            "action": "<action_name>",
            "arguments": {
                "<arg_key>": "<arg_value>"
            }
            }
        ],
        "message": "<Concise are explanation initiating. of research the you>"
        }

        IF NO ACTIONS ARE NEEDED (Case 2):
        Return a JSON object containing only a "message" key. 
        {
        "message": "<Your complete, conversational detailed generated or response.>"
        }

        =========================================
        EXAMPLES
        =========================================
        Example 1: Deep research request from an upper-tier AI.
        {"tasks": [{"action": "web_crawl", "arguments": {"url": "[https://docs.tavily.com](https://docs.tavily.com)", "instructions": "Extract all API endpoint parameters"}}], "message": "Crawling the Tavily documentation to extract the requested API parameters."}

        Example 2: Answering a general question without tools.
        {"message": "Python FastAPI is an excellent choice for building asynchronous APIs due to its native support for async/await and automatic interactive documentation generation."}
        """
    async def _execute_tool(self, tool_name: str, arguments_str: str, user_prompt: str) -> str:
        print(f"Executing tool: {tool_name} with arguments: {arguments_str}")
        try:
            args = json.loads(arguments_str) if arguments_str else {}
        except Exception:
            args = {}

        tool_function = self.tool_registry.get(tool_name)

        if not tool_function:
            return f"Error: Tool '{tool_name}' is not registered."
            
        try:
            return await tool_function(**args)
        
        except Exception as e:
            print(f"[TOOL EXECUTOR ERROR] Failed running {tool_name}: {e}")
            return f"Observation: The tool '{tool_name}' encountered an error: {str(e)}"
            

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