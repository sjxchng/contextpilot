# ContextPilot

An agentic research assistant with a live context management system. Demonstrates how long-horizon AI agents can dynamically manage their context window — compressing, scoring, and evicting chunks to stay within token limits without losing critical information.

Built as a proof-of-concept for the kind of infrastructure Pacific is building at enterprise scale.

---

## What It Does

ContextPilot runs a multi-step research agent on any topic. At each step, a context manager:

- **Scores** every chunk in the context window using a hybrid model: relevance × recency × access frequency
- **Evicts** the lowest-scoring chunks when usage exceeds 75% of the token budget
- **Tracks** TTFT (time to first token), token savings, and eviction history in real time

The eviction policy is inspired by **database buffer pool management** (LRU + cost model from CS 186), extended with semantic relevance scoring. Higher context pressure = more aggressive eviction, keeping the agent sharp without hitting token limits.

---

## Architecture

```
contextpilot/
  backend/
    main.py              # FastAPI server
    agent.py             # Multi-step research agent
    context_manager.py   # Scoring, compression, eviction engine
  frontend/
    src/
      App.jsx            # React dashboard
  README.md
```

**Backend:** FastAPI + Python, calling Groq (Llama 3.3 70B) for fast inference  
**Frontend:** React + Vite, polling the backend for live step updates  
**Context Manager:** Pure Python, no external dependencies

---

## How to Run

### Prerequisites
- Python 3.10+
- Node.js 18+
- A free Groq API key from [console.groq.com](https://console.groq.com)

### 1. Backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install fastapi uvicorn groq python-dotenv
```

Create a `.env` file in the `backend` folder:

```
GROQ_API_KEY=your_key_here
```

Start the server:

```bash
uvicorn main:app --reload
```

Backend runs at `http://localhost:8000`

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at `http://localhost:5173`

### 3. Use It

Open `http://localhost:5173`, type any research topic, and hit **Research**. Watch the agent work through sub-questions step by step, with live context health metrics updating as it goes.

---

## Key Metrics Shown

| Metric | What it means |
|---|---|
| Context Usage % | How full the token budget is |
| Tokens Evicted | Tokens saved by the eviction policy |
| Chunks in Context | Number of active memory chunks |
| TTFT (ms) | Time to first token per step — correlates with context size |
| Chunk Score | Relevance × recency × frequency — determines eviction order |

---

## Context Scoring Model

Each chunk is scored as:

```
score = 0.5 × relevance + 0.3 × recency + 0.2 × access_frequency
```

- **Relevance**: Set at insertion time based on chunk type and position
- **Recency**: Decays over time (half-life ~1 minute)
- **Access frequency**: Rewards chunks that get referenced often

When context exceeds 75% capacity, chunks are sorted by score ascending and evicted until usage drops below 60% — analogous to a database buffer pool flushing dirty pages under memory pressure.

---

## Relation to Pacific's Mission

Pacific is building an Enterprise Context Management System so AI agents can reliably operate on company-specific data. ContextPilot demonstrates one layer of that stack: the in-agent context buffer that decides what information an agent keeps, compresses, or discards during a long-horizon task.

Just as OS and database buffer management made personal computing reliable and efficient, intelligent context management makes personal AI reliable and efficient.

---

## Author

Siwoo Chung  
[github.com/sjxchng](https://github.com/sjxchng)
