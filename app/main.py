from dotenv import load_dotenv
load_dotenv()

import json
import asyncio
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from openai import AsyncOpenAI
from app.config import OPENAI_API_KEY
from app.kb import SYSTEM_PROMPT

app = FastAPI()
client = AsyncOpenAI(api_key=OPENAI_API_KEY)

@app.get("/health")
async def health():
    return {"status": "ok"}

async def stream_response(messages: list):
    try:
        stream = await client.chat.completions.create(
            model="gpt-4o",
            max_tokens=80,
            stream=True,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                *messages
            ]
        )

        async for chunk in stream:
            try:
                delta = chunk.choices[0].delta
                if delta.content:
                    data = {
                        "id": "chatcmpl-123",
                        "object": "chat.completion.chunk",
                        "choices": [{
                            "index": 0,
                            "delta": {"content": delta.content},
                            "finish_reason": None
                        }]
                    }
                    yield f"data: {json.dumps(data)}\n\n"
            except Exception:
                break

        final = {
            "id": "chatcmpl-123",
            "object": "chat.completion.chunk",
            "choices": [{
                "index": 0,
                "delta": {},
                "finish_reason": "stop"
            }]
        }
        yield f"data: {json.dumps(final)}\n\n"
        yield "data: [DONE]\n\n"

    except Exception as e:
        print(f"Stream error: {e}")

@app.post("/v1/chat/completions")
@app.post("/chat/completions")
async def chat_completions(request: Request):
    body = await request.json()
    messages = body.get("messages", [])

    filtered = [
        {"role": m["role"], "content": m["content"]}
        for m in messages
        if m.get("role") in ["user", "assistant"]
        and m.get("content")
    ]

    print(f"Incoming messages: {len(filtered)} turns")
    if filtered:
        print(f"Last user message: {filtered[-1]['content']}")

    return StreamingResponse(
        stream_response(filtered),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)