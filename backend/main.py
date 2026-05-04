import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import json
from agent import run_agent

# Create FastAPI app instance
app = FastAPI()

# Enable CORS (Cross-Origin Resource Sharing)
# This allows your frontend (localhost:5173) to talk to your backend (localhost:8000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # allow all origins (good for dev, restrict in prod)
    allow_methods=["*"],   # allow all HTTP methods (GET, POST, etc.)
    allow_headers=["*"],   # allow all headers
)

# Defines the expected request body format
# When frontend sends { "topic": "AI" }, FastAPI validates it using this
class ResearchRequest(BaseModel):
    topic: str

@app.post("/research/stream")
async def research_stream(req: ResearchRequest):
    """
    Streaming version of the research endpoint.
    
    Instead of waiting for the entire result, this sends each step
    to the frontend as soon as it's ready (real-time updates).
    """

    async def event_stream():
        # Get current event loop (used for async coordination)
        loop = asyncio.get_event_loop()

        # Async queue to pass data between threads safely
        queue = asyncio.Queue()

        # This function is called every time the agent completes a step
        # It pushes the step into the queue so we can stream it
        def on_step(step):
            loop.call_soon_threadsafe(
                queue.put_nowait,
                {"type": "step", "data": step}
            )

        # This runs the agent in a separate thread (important!)
        # because run_agent is blocking (not async)
        async def run():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                # Run the agent in a background thread
                result = await loop.run_in_executor(
                    pool,
                    lambda: run_agent(req.topic, on_step)
                )

            # When done, send final result to queue
            queue.put_nowait({"type": "done", "data": result})

        # Start the background task
        asyncio.create_task(run())

        # Continuously listen for new items in queue
        while True:
            item = await queue.get()

            # Send data in Server-Sent Events (SSE) format
            # "data: ..." is required for SSE protocol
            yield f"data: {json.dumps(item)}\n\n"

            # Stop streaming once agent finishes
            if item["type"] == "done":
                break

    # Return streaming response with correct content type
    return StreamingResponse(event_stream(), media_type="text/event-stream")

@app.post("/research")
async def research(req: ResearchRequest):
    """
    Non-streaming version.
    
    Waits for the entire agent to finish before returning anything.
    Simpler, but no real-time updates.
    """
    import concurrent.futures
    loop = asyncio.get_event_loop()

    # Run blocking agent in a separate thread to avoid freezing FastAPI
    with concurrent.futures.ThreadPoolExecutor() as pool:
        result = await loop.run_in_executor(
            pool,
            lambda: run_agent(req.topic)
        )

    return result

@app.get("/health")
async def health():
    """
    Simple health check endpoint.
    
    Useful for:
    - testing if backend is running
    - deployment monitoring
    """
    return {"status": "ok"}