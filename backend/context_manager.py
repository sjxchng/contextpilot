import time
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class ContextChunk:
    id: str
    content: str
    role: str  # "user" or "assistant"
    timestamp: float = field(default_factory=time.time)
    relevance_score: float = 1.0
    access_count: int = 0
    token_estimate: int = 0

    def __post_init__(self):
        self.token_estimate = len(self.content.split()) * 4 // 3

class ContextManager:
    def __init__(self, max_tokens: int = 4000, compression_threshold: float = 0.8):
        self.max_tokens = max_tokens
        self.compression_threshold = compression_threshold
        self.chunks: list[ContextChunk] = []
        self.eviction_log: list[dict] = []
        self.total_tokens_evicted: int = 0
        self.chunk_counter: int = 0

    def add_chunk(self, content: str, role: str, relevance_score: float = 1.0):
        chunk = ContextChunk(
            id=f"chunk_{self.chunk_counter}",
            content=content,
            role=role,
            relevance_score=relevance_score
        )
        self.chunk_counter += 1
        self.chunks.append(chunk)
        self._maybe_evict()
        return chunk

    def _score_chunk(self, chunk: ContextChunk) -> float:
        """
        Hybrid scoring: recency + relevance + access frequency.
        Inspired by database buffer pool management (LRU + cost model).
        Higher score = more important to keep.
        """
        age = time.time() - chunk.timestamp
        recency_score = 1.0 / (1.0 + age / 60.0)  # decays over minutes
        frequency_score = min(chunk.access_count / 5.0, 1.0)
        return (0.5 * chunk.relevance_score) + (0.3 * recency_score) + (0.2 * frequency_score)

    def _current_tokens(self) -> int:
        return sum(c.token_estimate for c in self.chunks)

    def _maybe_evict(self):
        usage = self._current_tokens() / self.max_tokens
        if usage < self.compression_threshold:
            return

        # Sort by score ascending — evict lowest scoring first (like LRU eviction)
        scored = sorted(self.chunks, key=lambda c: self._score_chunk(c))

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
                "reason": "LRU+relevance eviction"
            })

    def get_messages(self) -> list[dict]:
        for chunk in self.chunks:
            chunk.access_count += 1
        return [{"role": c.role, "content": c.content} for c in self.chunks]

    def get_stats(self) -> dict:
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
                    "id": c.id,
                    "role": c.role,
                    "preview": c.content[:60] + "...",
                    "tokens": c.token_estimate,
                    "score": round(self._score_chunk(c), 3),
                    "relevance": c.relevance_score
                }
                for c in self.chunks
            ]
        }