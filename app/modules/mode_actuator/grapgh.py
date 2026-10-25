from typing import List
from langgraph.graph import StateGraph, START, END
from langgraph.types import Send

from .services import (
    ResearchState,
    WorkerState,
    planner_node,
    worker_node,
    synthesizer_node
)

# ============================================================================
# Dynamic Fan-Out Edge using LangGraph Send API
# ============================================================================

def dispatch_workers(state: ResearchState) -> List[Send]:
    """
    Conditional edge function that reads the planner's output subtasks
    and dynamically dispatches multiple parallel worker nodes via the Send API.
    """
    tasks = state.get("tasks", [])
    if not tasks:
        # Fallback to dispatching a single worker with the original query if no tasks exist
        return [
            Send("research_worker", {
                "task_id": 1,
                "sub_query": state.get("original_query", "")
            })
        ]

    # Dispatch dynamic worker instances with their specific WorkerState
    return [
        Send("research_worker", {
            "task_id": task["task_id"],
            "sub_query": task["sub_query"]
        })
        for task in tasks
    ]


# ============================================================================
# LangGraph StateGraph Definition & Compilation
# ============================================================================

workflow = StateGraph(ResearchState)

# 1. Register Nodes
workflow.add_node("planner", planner_node)
workflow.add_node("research_worker", worker_node)
workflow.add_node("synthesizer", synthesizer_node)

# 2. Build Pipeline Flow
# START -> planner
workflow.add_edge(START, "planner")

# planner -> (Dynamic Fan-Out via Send API) -> research_worker
workflow.add_conditional_edges(
    "planner",
    dispatch_workers,
    ["research_worker"]
)

# research_worker -> synthesizer (LangGraph fans-in after all parallel workers complete)
workflow.add_edge("research_worker", "synthesizer")

# synthesizer -> END
workflow.add_edge("synthesizer", END)

# 3. Compile the Executable Graph
research_graph = workflow.compile()
