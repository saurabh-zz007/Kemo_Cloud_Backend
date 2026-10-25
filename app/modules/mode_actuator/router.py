from fastapi import APIRouter, status, HTTPException
from app.core.config import settings
from .data_transfer_object import ResearchRequest, ResearchResponse
from .controller import ActuatorController

mode_actuator_router = APIRouter(prefix="/actuator", tags=["Actuator (Layer 2 Multi-Agent)"])

@mode_actuator_router.post(
    "/research",
    response_model=ResearchResponse,
    status_code=status.HTTP_200_OK,
    summary="Execute Layer 2 Multi-Agent Research Pipeline (Planner -> Dynamic Workers -> Synthesizer)"
)
async def run_research_endpoint(request: ResearchRequest) -> ResearchResponse:
    """
    Triggers the LangGraph orchestration loop:
    1. **Planner Node**: Breaks down the query into distinct subtasks using an OpenRouter reasoning model.
    2. **Dynamic Workers**: Concurrently fans-out via the LangGraph Send API, executing each subtask using the mode_chat web-research worker.
    3. **Synthesizer Node**: Fans-in and aggregates all worker findings into a publication-grade cited markdown report.
    """
    try:
        user_id = request.user_id or getattr(settings, "TEST_USER_ID", "default_actuator_user")
        response = await ActuatorController.execute_research_pipeline(
            query=request.query,
            user_id=str(user_id)
        )
        return response
    except Exception as e:
        print(f"[Actuator Router Error] Pipeline execution failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Research orchestration pipeline failed: {str(e)}"
        )


@mode_actuator_router.post(
    "",
    response_model=ResearchResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False
)
async def run_research_endpoint_alias(request: ResearchRequest) -> ResearchResponse:
    """Convenience alias for /actuator."""
    return await run_research_endpoint(request)
