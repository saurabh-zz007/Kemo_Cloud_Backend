import json
import re
import operator
from typing import TypedDict, Annotated, List, Dict, Any, Optional
from openai import AsyncOpenAI

from app.core.config import settings
from app.modules.mode_chat.service import DeepSeekService
from .data_transfer_object import SubTask, PlannerOutput
from .system_prompt import PLANNER_SYSTEM_PROMPT, SYNTHESIZER_SYSTEM_PROMPT

# ============================================================================
# State Definitions for LangGraph
# ============================================================================

class ResearchState(TypedDict):
    """
    Parent graph state for the Layer 2 multi-agent research pipeline.
    Accumulates worker results concurrently using operator.add.
    """
    original_query: str
    tasks: list[dict[str, Any]]
    worker_results: Annotated[list[dict[str, Any]], operator.add]
    final_response: Optional[str]
    user_id: Optional[str]

class WorkerState(TypedDict):
    """
    Sub-state received by each dynamic worker dispatched via the Send API.
    Contains just the task_id and sub_query.
    """
    task_id: int
    sub_query: str


# ============================================================================
# Clients & Services Initialization
# ============================================================================

# OpenRouter async client
openrouter_client = AsyncOpenAI(
    api_key=settings.OPENROUTER_API_KEY,
    base_url=settings.OPENROUTER_BASE_URL if settings.OPENROUTER_BASE_URL else "https://openrouter.ai/api/v1",
    default_headers={
        "HTTP-Referer": "https://kemo.ai",
        "X-Title": settings.PROJECT_NAME
    }
)

# Shared instance of the existing DeepSeek web-research worker from mode_chat
deepseek_service = DeepSeekService()

# Model configurations (with sensible fallbacks if empty in .env)
PLANNER_MODEL = settings.OPENROUTER_PLANNER_MODEL_NAME 
SYNTHESIZER_MODEL = settings.OPENROUTER_SYNTHESIZER_MODEL_NAME 


# ============================================================================
# LangGraph Node Functions
# ============================================================================

def _clean_json_string(raw_text: str) -> str:
    """Helper to extract JSON object from markdown fences or raw text."""
    text = raw_text.strip()
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if match:
        return match.group(1).strip()
    return text


async def planner_node(state: ResearchState) -> dict[str, Any]:
    """
    Planner Node: Evaluates the original query using a high-reasoning model on OpenRouter
    and breaks it down into a structured list of 2 to 4 targeted sub-queries.
    """
    query = state["original_query"]
    print(f"[Actuator Planner] Deconstructing query with model '{PLANNER_MODEL}': {query}")

    system_prompt = PLANNER_SYSTEM_PROMPT

    try:
        response = await openrouter_client.chat.completions.create(
            model=PLANNER_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Deconstruct this research query into subtasks:\n{query}"}
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
        )

        raw_content = response.choices[0].message.content or "{}"
        cleaned = _clean_json_string(raw_content)
        parsed = json.loads(cleaned)
        validated = PlannerOutput.model_validate(parsed)
        tasks = [task.model_dump() for task in validated.tasks]

        if not tasks:
            tasks = [{"task_id": 1, "sub_query": query}]

        print(f"[Actuator Planner] Produced {len(tasks)} subtasks:")
        for t in tasks:
            print(f"  - [#{t['task_id']}] {t['sub_query']}")

        return {"tasks": tasks}

    except Exception as e:
        print(f"[Actuator Planner Error] Error calling OpenRouter planner: {e}. Falling back to default plan.")
        fallback_tasks = [
            {"task_id": 1, "sub_query": f"{query} technical architecture and overview"},
            {"task_id": 2, "sub_query": f"{query} current state of the art benchmarks and applications"}
        ]
        return {"tasks": fallback_tasks}


async def worker_node(state: WorkerState) -> dict[str, Any]:
    """
    Worker Node: Executes an individual research subtask by reusing the existing
    DeepSeekService.handle_research_subtask from app.modules.mode_chat.service.
    """
    task_id = state["task_id"]
    sub_query = state["sub_query"]
    user_id = getattr(settings, "TEST_USER_ID", "default_actuator_user")

    print(f"[Actuator Worker #{task_id}] Executing research for: '{sub_query}'")

    try:
        # Reusing the existing web-research worker logic without rewriting it
        findings = await deepseek_service.handle_research_subtask(
            user_id=user_id,
            task_query=sub_query
        )
    except Exception as e:
        print(f"[Actuator Worker #{task_id} Error] Failed to execute subtask: {e}")
        findings = f"Research subtask encountered an error: {str(e)}"

    print(f"[Actuator Worker #{task_id}] Completed research ({len(findings)} characters).")

    # Accumulates into parent ResearchState via operator.add
    return {
        "worker_results": [{
            "task_id": task_id,
            "sub_query": sub_query,
            "findings": findings
        }]
    }


async def synthesizer_node(state: ResearchState) -> dict[str, Any]:
    """
    Synthesizer Node: Aggregates findings from all parallel workers and generates
    a final, well-cited, publication-grade markdown report using a high-context OpenRouter model.
    """
    original_query = state["original_query"]
    worker_results = state.get("worker_results", [])
    print(f"[Actuator Synthesizer] Synthesizing findings from {len(worker_results)} workers using '{SYNTHESIZER_MODEL}'...")

    findings_sections = []
    for item in worker_results:
        findings_sections.append(
            f"### Subtask #{item.get('task_id')}: {item.get('sub_query')}\n"
            f"**Findings:**\n{item.get('findings', 'No findings reported.')}\n"
        )
    combined_findings = "\n\n---\n\n".join(findings_sections)

    system_prompt = SYNTHESIZER_SYSTEM_PROMPT

    user_prompt = (
        f"# ORIGINAL QUERY:\n{original_query}\n\n"
        f"# AGGREGATED WORKER FINDINGS:\n{combined_findings}\n\n"
        f"# INSTRUCTION:\n"
        f"Synthesize the findings above into a comprehensive, well-structured, and well-cited markdown report."
    )

    try:
        response = await openrouter_client.chat.completions.create(
            model=SYNTHESIZER_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,
        )
        synthesis = response.choices[0].message.content or "No synthesis could be generated."
    except Exception as e:
        print(f"[Actuator Synthesizer Error] Failed during synthesis: {e}")
        synthesis = (
            f"# Research Summary\n\n"
            f"**Original Query:** {original_query}\n\n"
            f"Synthesizer encountered an error ({str(e)}). Below are the raw findings gathered:\n\n"
            f"{combined_findings}"
        )

    return {"final_response": synthesis}
