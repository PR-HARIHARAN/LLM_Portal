
from my_agent.DatabaseManager import DatabaseManager ,format_result_as_table
from my_agent.LLMHandler import LLMHandler
from my_agent.VisualizationHandler import VisualizationHandler
from fastapi import FastAPI
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Tuple, Optional
import pandas as pd
import base64
import time
import uuid
import json
import asyncio

app = FastAPI()

# Allow CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize components
db_manager = DatabaseManager()
llm_handler = LLMHandler()
visualization_handler = VisualizationHandler()

# Request/response schemas
class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    model: str
    messages: List[Message]
    stream: bool = False

# Task classifier
async def classify_task(user_message: str) -> str:
    intent = llm_handler.analyze_intent(user_message)
    print(intent)
    return intent

# Format final output
def format_output(sql: str, table_html: str, summary: str) -> str:
    return f"""**Generated SQL Query:**
```sql
{sql}
```

<details>
<summary>📊 Click to view data</summary>

{table_html}
</details>

**Result:**
{summary}
"""

# Route models
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
        user_message = next((m.content for m in reversed(request.messages) if m.role == "user"), "")
        task_type = await classify_task(user_message)
        print(f"User message: {user_message}")
        print(f"Classified as: {task_type}")

        if task_type == "SQL":
            schema = db_manager.get_database_schema()
            sql_query = llm_handler.get_query_from_llm(schema, user_message)
            
            try:
                columns, data = db_manager.execute_read_query(sql_query)
                result = [dict(zip(columns, row)) for row in data]
            except Exception as exec_error:
                corrected_query = llm_handler.correct_query(schema, user_message, sql_query, str(exec_error))
                if corrected_query:
                    try:
                        columns, data = db_manager.execute_read_query(corrected_query)
                        
                        sql_query = corrected_query
                    except Exception as corr_error:
                        issues = llm_handler.validate_generated_sql(corrected_query)
                        raise Exception(f"Validation failed: {', '.join(issues['issues'])}")
                else:
                    raise Exception(f"Execution failed: {exec_error}")
            
            # Generate visualization
            #df = pd.DataFrame(data, columns=columns)
            table_html = format_result_as_table(result)

            summary = llm_handler.generate_summary(
                user_message,
                [dict(zip(columns, row)) for row in data]
            )

            output_str = format_output(sql_query, table_html, summary)

        elif task_type == "CHAT":
            # Chat fallback
            output_str = llm_handler.generate_chat_response(user_message)

        # Build OpenAI-compatible response
        completion_id = f"chatcmpl-{uuid.uuid4()}"
        created = int(time.time())

        if request.stream:
            async def stream():
                yield f"data: {json.dumps({'id': completion_id, 'object': 'chat.completion.chunk', 'created': created, 'model': request.model, 'choices': [{'delta': {'role': 'assistant'}, 'index': 0}]})}\n\n"
                yield f"data: {json.dumps({'id': completion_id, 'object': 'chat.completion.chunk', 'created': created, 'model': request.model, 'choices': [{'delta': {'content': output_str}, 'index': 0}]})}\n\n"
                yield f"data: {json.dumps({'id': completion_id, 'object': 'chat.completion.chunk', 'created': created, 'model': request.model, 'choices': [{'delta': {}, 'finish_reason': 'stop', 'index': 0}]})}\n\n"
                yield "data: [DONE]\n\n"
            return StreamingResponse(stream(), media_type="text/event-stream")

        return {
            "id": completion_id,
            "object": "chat.completion",
            "created": created,
            "model": request.model,
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": output_str
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

