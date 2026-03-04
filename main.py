from fastapi import FastAPI, Depends, HTTPException
from schemas.kemo_schema import UserRequest, TaskResponse
from services.llm_service import DeepSeekService

app = FastAPI(title="KEMO Cloud Brain")

# Dependency Injection for the LLM Service
def get_llm_service():
    return DeepSeekService()

@app.post("/api/plan", response_model=TaskResponse)
async def plan_tasks(req: UserRequest, llm: DeepSeekService = Depends(get_llm_service)):
    """
    Receives voice text from the local Flutter app, 
    fetches the cached DeepSeek plan, and returns JSON.
    """
    try:
        tasks = llm.generate_plan(req.prompt)
        return TaskResponse(status="success", tasks=tasks)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal Server Error during task planning.")