"""S3.1 JSONL과 다음 차시가 공유하는 데이터 모양."""
from dataclasses import dataclass


@dataclass
class Chunk:
    text: str
    chunk_id: str
    metadata: dict


@dataclass
class Hit:
    text: str
    score: float
    metadata: dict
    rerank_score: float | None = None
