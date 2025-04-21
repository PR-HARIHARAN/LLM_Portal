from my_agent.DatabaseManager import DatabaseManager
from my_agent.LLMHandler import LLMHandler
from my_agent.VisualizationHandler import VisualizationHandler
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from fastapi.responses import JSONResponse, StreamingResponse
from typing import List
import uuid
import time
import json
import asyncio
import os


app = FastAPI()

# Allow CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

db_manager = DatabaseManager()
db = db_manager.connect_database()
llm_handler = LLMHandler()
visualization_handler = VisualizationHandler()


# Pydantic schemas
class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    model: str
    messages: List[Message]
    stream: bool = False


"""
Function to be used to call llm and get the response and visualization
 """


# model str structure to openweb-ui

    output_str= f"""**Generated SQL Query:**
```sql
{sql}
```

<details>
<summary>📊 Click to view data</summary>

{table}
</details>

**Result:**
{summary}
"""
    return output_str



@app.get("/v1/models")
async def list_models():
    return {
        "object": "list",
        "data": [
            {
                "id": "LMS-MODEL",
                "object": "model",
                "created": int(time.time()),
                "owned_by": "local-user"
            }
        ]
    }



@app.post("/v1/chat/completions")
async def chat_with_agent(request: ChatRequest):
    try:
        # Get latest user message
        user_message = next((m.content for m in reversed(request.messages) if m.role == "user"), "")
        
        # Classify task
        task_type = await classify_task(user_message)
        
        # Route to appropriate handler
        if task_type == "SQL":
           """LOGIC FOR SQL QUERY GENERATION"""
            
        else: #chat
            """LOGIC FOR CHAT RESPONSE"""
           

        # Metadata
        completion_id = f"chatcmpl-{uuid.uuid4()}"
        created = int(time.time())

        # If streaming is enabled, stream chunked responses
        if request.stream:
            async def stream():
                # Start message
                yield f"data: {json.dumps({'id': completion_id, 'object': 'chat.completion.chunk', 'created': created, 'model': request.model, 'choices': [{'delta': {'role': 'assistant'}, 'index': 0}]})}\n\n"

                # Content
                yield f"data: {json.dumps({'id': completion_id, 'object': 'chat.completion.chunk', 'created': created, 'model': request.model, 'choices': [{'delta': {'content': output_str}, 'index': 0}]})}\n\n"

                # End
                yield f"data: {json.dumps({'id': completion_id, 'object': 'chat.completion.chunk', 'created': created, 'model': request.model, 'choices': [{'delta': {}, 'finish_reason': 'stop', 'index': 0}]})}\n\n"
                yield "data: [DONE]\n\n"

            return StreamingResponse(stream(), media_type="text/event-stream")

        
        # Non-streaming response
        return {
            "id": completion_id,
            "object": "chat.completion",
            "created": created,
            "model": request.model,
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": response_text
                },
                "finish_reason": "stop"
            }],
            "usage": {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0
            }
        }

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
