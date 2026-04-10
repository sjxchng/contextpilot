import os
import time
from groq import Groq
from context_manager import ContextManager
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

def run_agent(topic: str, on_step=None) -> dict:
    """
    Multi-step research agent that investigates a topic through sub-questions.
    Context is managed dynamically — eviction policy inspired by DB buffer management.
    """
    cm = ContextManager(max_tokens=3000, compression_threshold=0.75)
    steps = []

    # System prompt counts toward context
    cm.add_chunk(
        f"You are a research assistant. Investigate the topic thoroughly and concisely: '{topic}'. "
        f"Answer each sub-question in 2-3 sentences max.",
        role="user",
        relevance_score=1.0
    )

    sub_questions = generate_sub_questions(topic)

    for i, question in enumerate(sub_questions):
        step_start = time.time()

        # Add question to context
        cm.add_chunk(question, role="user", relevance_score=0.9 - (i * 0.05))

        messages = cm.get_messages()

        # Call Groq
        ttft_start = time.time()
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            max_tokens=200,
            stream=False
        )
        ttft = round((time.time() - ttft_start) * 1000)  # ms

        answer = response.choices[0].message.content
        tokens_used = response.usage.total_tokens

        # Add answer to context with decaying relevance
        cm.add_chunk(answer, role="assistant", relevance_score=0.85 - (i * 0.05))

        stats = cm.get_stats()
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

        if on_step:
            on_step(step)

    final_stats = cm.get_stats()
    return {
        "topic": topic,
        "steps": steps,
        "final_stats": final_stats,
        "summary": synthesize(steps, topic)
    }

def generate_sub_questions(topic: str) -> list[str]:
    """Generate research sub-questions for a topic."""
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{
            "role": "user",
            "content": f"Generate exactly 5 research sub-questions to thoroughly investigate: '{topic}'. "
                       f"Return only the questions, one per line, no numbering or bullets."
        }],
        max_tokens=200
    )
    lines = response.choices[0].message.content.strip().split("\n")
    return [l.strip() for l in lines if l.strip()][:5]

def synthesize(steps: list[dict], topic: str) -> str:
    """Synthesize all findings into a final summary."""
    findings = "\n".join([f"Q: {s['question']}\nA: {s['answer']}" for s in steps])
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{
            "role": "user",
            "content": f"Synthesize these research findings on '{topic}' into a 3-4 sentence summary:\n\n{findings}"
        }],
        max_tokens=200
    )
    return response.choices[0].message.content