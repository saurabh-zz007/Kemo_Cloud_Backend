from typing import Optional, Dict, Any
from app.core.config import settings
from .grapgh import research_graph
from .services import ResearchState
from .data_transfer_object import ResearchResponse, SubTask, WorkerFindingDTO

class ActuatorController:
    """
    Controller responsible for initializing the LangGraph research state
    and orchestrating pipeline execution.
    """

    @staticmethod
    async def execute_research_pipeline(query: str, user_id: Optional[str] = None) -> ResearchResponse:
        """
        Invokes the compiled Layer 2 LangGraph workflow with the given query.
        Returns the structured ResearchResponse including tasks, worker findings, and final synthesis.
        """
        effective_user_id = user_id or getattr(settings, "TEST_USER_ID", "default_actuator_user")

        initial_state: ResearchState = {
            "original_query": query,
            "tasks": [],
            "worker_results": [],
            "final_response": None,
            "user_id": str(effective_user_id)
        }

        print(f"[Actuator Controller] Initiating research orchestration for query: '{query}'")

        # Asynchronously execute the compiled LangGraph pipeline
        result_state: Dict[str, Any] = await research_graph.ainvoke(initial_state)

        # Convert raw tasks and worker results into strongly-typed DTOs
        subtasks = [
            SubTask(
                task_id=task.get("task_id", idx + 1),
                sub_query=task.get("sub_query", "")
            )
            for idx, task in enumerate(result_state.get("tasks", []))
        ]

        worker_findings = [
            WorkerFindingDTO(
                task_id=w.get("task_id", idx + 1),
                sub_query=w.get("sub_query", ""),
                findings=w.get("findings", "")
            )
            for idx, w in enumerate(result_state.get("worker_results", []))
        ]

        return ResearchResponse(
            query=result_state.get("original_query", query),
            tasks=subtasks,
            worker_results=worker_findings,
            final_response=result_state.get("final_response") or "No final response was produced."
        )
