"""KURE-v1 및 외부 모델이 필요 없는 smoke 임베딩 어댑터."""

from __future__ import annotations

import hashlib
import json
import math
from typing import Literal


SMOKE_SIGNATURE = "smoke-sha256-bigram-v1"
KURE_SIGNATURE_PREFIX = "sentence-transformers:"


class SmokeEmbedder:
    dimension = 384
    signature = SMOKE_SIGNATURE

    @staticmethod
    def _embed_one(text: str) -> list[float]:
        normalized = " ".join(text.lower().split())
        grams = [normalized[index:index + 2] for index in range(max(1, len(normalized) - 1))]
        vector = [0.0] * SmokeEmbedder.dimension
        for gram in grams or [normalized]:
            digest = hashlib.sha256(gram.encode("utf-8")).digest()
            position = int.from_bytes(digest[:4], "big") % SmokeEmbedder.dimension
            vector[position] += -1.0 if digest[4] & 1 else 1.0
        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [value / norm for value in vector]

    def embed(self, texts: list[str], *, kind: Literal["passage", "query"] = "passage") -> list[list[float]]:
        del kind
        return [self._embed_one(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed_one(text)


class HuggingFaceEmbedder:
    """무거운 모델을 생성 시점이 아니라 최초 호출 때 적재함."""

    def __init__(self, model_name: str, *, batch_size: int = 32, device: str = "cpu") -> None:
        self.model_name = model_name
        self.batch_size = batch_size
        self.device = device
        self.signature = f"{KURE_SIGNATURE_PREFIX}{model_name}:prompt-policy-v2"
        self._model = None
        self._dimension = 0

    def _load(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self.model_name, device=self.device)
            dimension_getter = getattr(
                self._model,
                "get_embedding_dimension",
                self._model.get_sentence_embedding_dimension,
            )
            self._dimension = int(dimension_getter())
        return self._model

    @property
    def dimension(self) -> int:
        if not self._dimension:
            self._load()
        return self._dimension

    def embed(self, texts: list[str], *, kind: Literal["passage", "query"] = "passage") -> list[list[float]]:
        del kind
        model = self._load()
        values = model.encode(texts, batch_size=self.batch_size, normalize_embeddings=True)
        return values.tolist() if hasattr(values, "tolist") else [list(row) for row in values]

    def embed_query(self, text: str) -> list[float]:
        return self.embed([text], kind="query")[0]


def create_embedder(backend: str, model_name: str, *, batch_size: int = 32):
    if backend == "smoke":
        return SmokeEmbedder()
    if backend == "sentence-transformers":
        return HuggingFaceEmbedder(model_name, batch_size=batch_size)
    raise ValueError(f"지원하지 않는 임베딩 backend: {backend}")


def chunk_hash(text: str, metadata: dict) -> tuple[str, str]:
    """증분 판정에 사용하는 본문·메타데이터 지문을 안정적으로 계산함."""

    text_digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    metadata_payload = json.dumps(metadata, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    metadata_digest = hashlib.sha256(metadata_payload.encode("utf-8")).hexdigest()
    return text_digest, metadata_digest


def plan_incremental(
    chunks: list,
    manifest: dict | None,
    *,
    embedding_signature: str,
    chunk_params: dict,
    full_reindex: bool = False,
) -> dict:
    """서명·청킹 파라미터 변경은 전량, 같은 두 해시는 건너뛰도록 판정함."""

    previous = manifest or {}
    promoted = (
        full_reindex
        or previous.get("embedding_signature") not in {None, embedding_signature}
        or (
            previous.get("chunk_params") is not None
            and previous.get("chunk_params") != chunk_params
        )
    )
    old_chunks = previous.get("chunks", {}) if not promoted else {}
    pending_ids, skipped_ids, hashes = [], [], {}
    for chunk in chunks:
        chunk_id = str(getattr(chunk, "id", None) or getattr(chunk, "chunk_id", ""))
        text = getattr(chunk, "page_content", None) or getattr(chunk, "text", "")
        metadata = dict(getattr(chunk, "metadata", {}))
        text_digest, metadata_digest = chunk_hash(text, metadata)
        hashes[chunk_id] = {"text_sha256": text_digest, "metadata_sha256": metadata_digest}
        prior = old_chunks.get(chunk_id, {})
        if prior.get("text_sha256") == text_digest and prior.get("metadata_sha256") == metadata_digest:
            skipped_ids.append(chunk_id)
        else:
            pending_ids.append(chunk_id)
    return {
        "pending_ids": pending_ids,
        "skipped_ids": skipped_ids,
        "hashes": hashes,
        "full_reindex": promoted,
    }
