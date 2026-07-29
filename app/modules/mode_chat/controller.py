from fastapi import Depends, HTTPException
from app.modules.mode_chat.data_transfer_objects import UserRequest, TaskResponse
from app.modules.mode_chat.service import DeepSeekService

def mode_chat_controller(req: UserRequest, llm: DeepSeekService):
    try:
        tasks = llm.generate_plan(req.prompt)
        task_list = tasks.get("tasks", [])
        msg = tasks.get("message", "Task processed.")
        return TaskResponse(status="success", tasks=task_list,message= msg)
    except Exception as e:
        print(f"CRITICAL ERROR: {repr(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error during task planning.")