from typing import List, Optional
from pydantic import BaseModel, Field

# ============================================================================
# Planner Structured Output Schemas
# ============================================================================

class SubTask(BaseModel):
    task_id: int = Field(..., description="Unique incremental integer ID for the subtask")
    sub_query: str = Field(..., description="Targeted web search or deep research query for the worker")

class PlannerOutput(BaseModel):
    reasoning: Optional[str] = Field(
        default=None, 
        description="Reasoning breakdown of why these specific sub-queries were chosen"
    )
    tasks: List[SubTask] = Field(
        ..., 
        description="List of 2 to 5 distinct, high-impact sub-queries to gather comprehensive research"
    )


# ============================================================================
# HTTP API Request & Response DTOs
# ============================================================================

class ResearchRequest(BaseModel):
    query: str = Field(
        ..., 
        min_length=3,
        description="Complex topic or multi-faceted question requiring autonomous research",
        example="Analyze the latest advancements in solid-state batteries in 2026 and compare key commercial players."
    )
    user_id: Optional[str] = Field(
        default=None,
        description="Optional user ID. If not provided, the authenticated user or default test user is used."
    )

class WorkerFindingDTO(BaseModel):
    task_id: int = Field(..., description="Identifier of the executed subtask")
    sub_query: str = Field(..., description="Search sub-query that was researched")
    findings: str = Field(..., description="Raw research findings and summaries gathered by the worker")

class ResearchResponse(BaseModel):
    query: str = Field(..., description="The original research query")
    tasks: List[SubTask] = Field(..., description="List of sub-tasks produced by the planner")
    worker_results: List[WorkerFindingDTO] = Field(..., description="Aggregated results from all parallel workers")
    final_response: str = Field(..., description="Synthesized, well-cited markdown report")
