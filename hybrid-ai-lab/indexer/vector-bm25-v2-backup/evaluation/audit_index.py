"""게시된 실측 인덱스의 건수·토큰·벡터·개인정보 형식을 확인함."""

from __future__ import annotations

from collections import Counter
import importlib.metadata
import json
import math
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from app.domain.text_rules import assert_no_residual_private
from app.infrastructure.index_repository import GenerationIndexRepository
from app.infrastructure.settings import load_settings
from app.infrastructure.token_counter import ModelTokenCounter


def main() -> None:
    """활성 인덱스의 청크·벡터·개인정보 조건을 검사하고 감사 결과를 저장함.

    반환값: 없음.
    예외: 활성 인덱스가 없거나 토큰·차원·정규화·개인정보 조건이 어긋나면 예외가 발생함.
    부수효과: 모델 토크나이저를 읽고 results 아래 감사·실행 결과 JSON을 기록하며 결과를 표준 출력함.
    """
    settings = load_settings()
    repository = GenerationIndexRepository(settings.output_path)
    snapshot = repository.load_active()
    assert snapshot is not None
    counter = ModelTokenCounter(settings.model_name, settings.model_revision, settings.max_tokens)
    vectors = repository.get_vectors([chunk.chunk_id for chunk in snapshot.chunks])
    token_counts = []
    norms = []
    for chunk in snapshot.chunks:
        assert_no_residual_private(chunk.text)
        assert_no_residual_private(json.dumps(chunk.metadata, ensure_ascii=False))
        count = counter.count(chunk.text)
        assert count == chunk.token_count and count <= settings.max_tokens
        vector = vectors[chunk.chunk_id]
        assert len(vector) == settings.embedding_dimension
        norm = math.sqrt(sum(value * value for value in vector))
        assert math.isclose(norm, 1, abs_tol=1e-5)
        token_counts.append(count)
        norms.append(norm)
    result = {
        "generation": snapshot.manifest["generation"],
        "chunk_count": len(snapshot.chunks), "vector_count": len(vectors),
        "chunks_by_document_type": dict(Counter(chunk.metadata["doc_key"] for chunk in snapshot.chunks)),
        "actual_token_min": min(token_counts), "actual_token_max": max(token_counts),
        "actual_vector_norm_min": min(norms), "actual_vector_norm_max": max(norms),
        "dimension": settings.embedding_dimension, "residual_pii_format_matches": 0,
        "embedding_contract": snapshot.manifest["embedding_contract"],
        "package_versions": {name: importlib.metadata.version(name) for name in (
            "langgraph", "langgraph-checkpoint-sqlite", "langchain-text-splitters", "sentence-transformers",
            "transformers", "torch", "chromadb", "bm25s", "kiwipiepy")},
    }
    output = HERE / "results"
    output.mkdir(exist_ok=True)
    (output / "index-audit.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    for name in ("build-result", "final-build-result", "noop-result"):
        source = settings.output_path / f"{name}.json"
        if source.exists():
            value = json.loads(source.read_text(encoding="utf-8-sig"))
            (output / f"{name}.json").write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
