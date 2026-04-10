import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import json
from agent import run_agent

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class ResearchRequest(BaseModel):
    topic: str

@app.post("/research/stream")
async def research_stream(req: ResearchRequest):
    """Stream agent steps as they complete."""
    def generate():
        def on_step(step):
            yield f"data: {json.dumps({'type': 'step', 'data': step})}\n\n"

        # Run agent synchronously, streaming each step
        steps = []
        result_container = {}

        def on_step_collect(step):
            steps.append(step)

        # We'll collect then stream
        pass

    async def event_stream():
        loop = asyncio.get_event_loop()
        queue = asyncio.Queue()

        def on_step(step):
            loop.call_soon_threadsafe(queue.put_nowait, {"type": "step", "data": step})

        async def run():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                result = await loop.run_in_executor(pool, lambda: run_agent(req.topic, on_step))
            queue.put_nowait({"type": "done", "data": result})

        asyncio.create_task(run())

        while True:
            item = await queue.get()
            yield f"data: {json.dumps(item)}\n\n"
            if item["type"] == "done":
                break

    return StreamingResponse(event_stream(), media_type="text/event-stream")

@app.post("/research")
async def research(req: ResearchRequest):
    """Non-streaming version."""
    import concurrent.futures
    loop = asyncio.get_event_loop()
    with concurrent.futures.ThreadPoolExecutor() as pool:
        result = await loop.run_in_executor(pool, lambda: run_agent(req.topic))
    return result

@app.get("/health")
async def health():
    return {"status": "ok"}