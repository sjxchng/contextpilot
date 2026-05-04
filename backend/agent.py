import os
import time
from groq import Groq
from context_manager import ContextManager
from dotenv import load_dotenv

# Load environment variables from .env file (e.g., API keys)
load_dotenv()

# Initialize Groq client using API key from environment
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

def run_agent(topic: str, on_step=None) -> dict:
    """
    Runs a multi-step research agent.

    Flow:
    1. Generate sub-questions
    2. Iteratively answer each question using LLM
    3. Dynamically manage context (eviction + scoring)
    4. Optionally stream intermediate steps via callback
    5. Return final results + summary
    """
    # Context manager controls token budget and eviction
    cm = ContextManager(max_tokens=3000, compression_threshold=0.75)

    # Stores all steps for final output
    steps = []

    # Add initial system instruction into context
    # High relevance ensures it stays in memory longer
    cm.add_chunk(
        f"You are a research assistant. Investigate the topic thoroughly and concisely: '{topic}'. "
        f"Answer each sub-question in 2-3 sentences max.",
        role="user",
        relevance_score=1.0
    )

    # Generate 5 sub-questions to guide the research process
    sub_questions = generate_sub_questions(topic)

    # Iterate through each sub-question
    for i, question in enumerate(sub_questions):
        step_start = time.time()  # (optional) measure total step time

        # Add the current question to context
        # Relevance decays slightly over time (later questions less important)
        cm.add_chunk(question, role="user", relevance_score=0.9 - (i * 0.05))

        # Convert internal context chunks into LLM message format
        messages = cm.get_messages()

        # Measure TTFT (time to first token / response latency)
        ttft_start = time.time()

        # Call Groq LLM with current context
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            max_tokens=200,
            stream=False  # full response (not token streaming)
        )

        # Convert latency to milliseconds
        ttft = round((time.time() - ttft_start) * 1000)

        # Extract generated answer and token usage
        answer = response.choices[0].message.content
        tokens_used = response.usage.total_tokens

        # Add answer back into context
        # Slightly lower relevance than question
        cm.add_chunk(answer, role="assistant", relevance_score=0.85 - (i * 0.05))

        # Get current context stats (usage %, chunk count, etc.)
        stats = cm.get_stats()

        # Store step result (used by frontend + final output)
        step = {
            "step": i + 1,
            "question": question,
            "answer": answer,
            "ttft_ms": ttft,
            "tokens_used": tokens_used,
            "context_usage_pct": stats["usage_pct"],
            "chunks_in_context": stats["chunk_count"],
            "evictions_so_far": len(cm.eviction_log)
        }

        steps.append(step)

        # If streaming is enabled, send step immediately
        if on_step:
            on_step(step)

    # Final context stats after all steps
    final_stats = cm.get_stats()

    return {
        "topic": topic,
        "steps": steps,
        "final_stats": final_stats,
        "summary": synthesize(steps, topic)  # final synthesized answer
    }

def generate_sub_questions(topic: str) -> list[str]:
    """
    Uses LLM to break a topic into 5 focused research questions.
    This helps guide the multi-step reasoning process.
    """
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{
            "role": "user",
            "content": f"Generate exactly 5 research sub-questions to thoroughly investigate: '{topic}'. "
                       f"Return only the questions, one per line, no numbering or bullets."
        }],
        max_tokens=200
    )

    # Split output into lines and clean formatting
    lines = response.choices[0].message.content.strip().split("\n")

    # Return exactly 5 cleaned questions
    cleaned = []
    for line in lines:
        line = line.strip()
        if line:
            cleaned.append(line)
    return cleaned[:5]

def synthesize(steps: list[dict], topic: str) -> str:
    """
    Combines all step-level answers into a final concise summary.
    """
    # Format all Q/A pairs into a single prompt
    findings = "\n".join([f"Q: {s['question']}\nA: {s['answer']}" for s in steps])

    # Ask LLM to summarize the full set of findings
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{
            "role": "user",
            "content": f"Synthesize these research findings on '{topic}' into a 3-4 sentence summary:\n\n{findings}"
        }],
        max_tokens=200
    )

    return response.choices[0].message.content