import time
from dataclasses import dataclass, field

@dataclass
class ContextChunk:
    """
    Represents one piece of context stored in the agent's memory.
    A chunk can be a user question, assistant answer, or initial instruction.
    """
    id: str
    content: str
    role: str  # "user" or "assistant"

    # Time when the chunk was created
    timestamp: float = field(default_factory=time.time)

    # Higher relevance means this chunk is more important to keep
    relevance_score: float = 1.0

    # Tracks how often this chunk has been included in LLM calls
    access_count: int = 0

    # Rough estimate of token count for this chunk
    token_estimate: int = 0

    def __post_init__(self):
        # Estimate tokens using a simple word-based approximation
        # Not exact, but good enough for tracking context pressure
        self.token_estimate = len(self.content.split()) * 4 // 3


class ContextManager:
    """
    Manages the agent's context window.

    Responsibilities:
    - Store context chunks
    - Estimate token usage
    - Score chunks by importance
    - Evict low-value chunks when context gets too full
    - Return context in LLM message format
    """

    def __init__(self, max_tokens: int = 4000, compression_threshold: float = 0.8):
        self.max_tokens = max_tokens
        self.compression_threshold = compression_threshold

        # Active chunks currently kept in context
        self.chunks: list[ContextChunk] = []

        # Tracks chunks that were removed
        self.eviction_log: list[dict] = []

        # Total number of tokens removed over time
        self.total_tokens_evicted: int = 0

        # Used to generate unique chunk IDs
        self.chunk_counter: int = 0

    def add_chunk(self, content: str, role: str, relevance_score: float = 1.0):
        """
        Add a new chunk to context, then check whether eviction is needed.
        """
        chunk = ContextChunk(
            id=f"chunk_{self.chunk_counter}",
            content=content,
            role=role,
            relevance_score=relevance_score
        )

        self.chunk_counter += 1
        self.chunks.append(chunk)

        # Evict low-value chunks if context is too full
        self._maybe_evict()

        return chunk

    def _score_chunk(self, chunk: ContextChunk) -> float:
        """
        Calculate how valuable a chunk is.

        Higher score = more likely to stay.
        Lower score = more likely to be evicted.
        """
        age = time.time() - chunk.timestamp

        # Newer chunks get higher score; older chunks slowly decay
        recency_score = 1.0 / (1.0 + age / 60.0)

        # Frequently accessed chunks get higher score
        frequency_score = min(chunk.access_count / 5.0, 1.0)

        # Weighted importance score
        return (
            (0.5 * chunk.relevance_score)
            + (0.3 * recency_score)
            + (0.2 * frequency_score)
        )

    def _current_tokens(self) -> int:
        """
        Estimate total tokens currently stored in context.
        """
        return sum(chunk.token_estimate for chunk in self.chunks)

    def _maybe_evict(self):
        """
        Evict low-scoring chunks if context usage passes the threshold.
        """
        usage = self._current_tokens() / self.max_tokens

        # If context is still under the threshold, keep everything
        if usage < self.compression_threshold:
            return

        # Sort chunks from least important to most important
        scored = sorted(self.chunks, key=lambda chunk: self._score_chunk(chunk))

        # Evict until usage drops below 60%
        # Keep at least 2 chunks so context is not completely wiped out
        while self._current_tokens() / self.max_tokens > 0.6 and len(scored) > 2:
            to_evict = scored.pop(0)

            self.chunks.remove(to_evict)
            self.total_tokens_evicted += to_evict.token_estimate

            self.eviction_log.append({
                "id": to_evict.id,
                "role": to_evict.role,
                "preview": to_evict.content[:80] + "...",
                "score": round(self._score_chunk(to_evict), 3),
                "tokens": to_evict.token_estimate,
                "reason": "low relevance/recency/frequency score"
            })

    def get_messages(self) -> list[dict]:
        """
        Convert stored chunks into the message format expected by the LLM.
        """
        for chunk in self.chunks:
            chunk.access_count += 1

        return [
            {"role": chunk.role, "content": chunk.content}
            for chunk in self.chunks
        ]

    def get_stats(self) -> dict:
        """
        Return context health metrics for the frontend dashboard.
        """
        current = self._current_tokens()

        return {
            "current_tokens": current,
            "max_tokens": self.max_tokens,
            "usage_pct": round(current / self.max_tokens * 100, 1),
            "chunk_count": len(self.chunks),
            "total_evicted": self.total_tokens_evicted,
            "eviction_log": self.eviction_log[-10:],
            "chunks": [
                {
                    "id": chunk.id,
                    "role": chunk.role,
                    "preview": chunk.content[:60] + "...",
                    "tokens": chunk.token_estimate,
                    "score": round(self._score_chunk(chunk), 3),
                    "relevance": chunk.relevance_score
                }
                for chunk in self.chunks
            ]
        }