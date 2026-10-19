"""기존 검색기의 사용 중 세대를 읽기 전용으로 열어 BM25 비교용 기준 자료를 JSON으로 뽑는 스크립트임.

왜 따로 뽑나: Kiwi·bm25s·torch는 기존 검색기 가상환경에만 있고, Neo4j 비교 스크립트는 neo4j 가상환경에서 돌기 때문임.
기존 코드는 import해서 읽기만 하며 색인 파일·설정을 고치지 않음.

실행(기존 검색기 가상환경):
    retriever/vector-retriever/.venv/Scripts/python verify/neo4j-bm25-compare/tools/export_baseline.py
출력: fixtures/baseline.json — 청크 218건(본문·색인용 본문·Kiwi 토큰), 질문 42건(토큰·기준 BM25·벡터 점수)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
LAB = ROOT.parent.parent
RETRIEVER = LAB / "retriever" / "vector-retriever"
E_QUESTIONS = LAB / "indexer" / "vector-bm25" / "evaluation" / "group2_questions.json"
Q_QUESTIONS = LAB / "ragas" / "eval-set.json"
OUT = ROOT / "fixtures" / "baseline.json"

TOP_K = 10
K_CANDIDATES = 40  # 기존 검색기 하이브리드 후보 수(top_k 5 × 2 × 4, steps.py:549)
# 비교는 어휘 검색 자체를 보는 것이라 가장 넓은 열람 등급에 회원 필터 없음 — 218건 전부가 후보임.
ACCESS_LEVELS = ("public", "restricted")


def raw_bm25_scores(index, query: str) -> dict[str, float]:
    """기존 색인에서 질문의 BM25 원점수를 걸러내기 없이 조각ID별로 얻음.

    왜 keyword_search를 안 쓰나: 그 함수는 열람 등급·회원 필터와 상위 k 자르기를 함께 하는데,
    여기서는 Neo4j 전문 검색과 같은 조건(218건 전부, 자르기 전)으로 점수를 맞대 보아야 함.
    반환값: 점수가 0보다 큰 조각만 담은 조각ID → BM25 원점수.
    부수효과: 없음(읽기 전용).
    """

    bm25 = index._bm25  # noqa: SLF001 - 검증 전용. 기존 코드를 고치지 않고 같은 색인을 그대로 씀
    tokens = index.tokens(query)
    vocabulary = dict(getattr(bm25, "vocab_dict", {}) or {})
    column_limit = len(bm25.scores["indptr"]) - 1
    token_ids = [
        vocabulary[token]
        for token in tokens
        if token in vocabulary and int(vocabulary[token]) < column_limit
    ]
    if not token_ids:
        return {}
    scores = bm25.get_scores_from_ids(token_ids)
    return {
        chunk_id: float(scores[row])
        for row, chunk_id in enumerate(index._order)  # noqa: SLF001
        if float(scores[row]) > 0.0
    }


def load_questions() -> list[dict]:
    """평가 질문 2벌(E01 ~ E20, Q01 ~ Q22)을 한 목록으로 합침. 기대 출처 문서도 함께 담음."""

    rows: list[dict] = []
    for path, group in ((E_QUESTIONS, "E"), (Q_QUESTIONS, "Q")):
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
        for item in payload["questions"]:
            sources = sorted({
                str(ref.get("source", "")).strip()
                for ref in (item.get("relevance") or [])
                if str(ref.get("source", "")).strip()
            })
            rows.append({
                "id": str(item["id"]),
                "group": group,
                "question": str(item["question"]),
                "answerable": bool(item.get("answerable", True)),
                "expected_sources": sources,
            })
    return rows


def main() -> None:
    sys.path.insert(0, str(RETRIEVER))
    from app.infrastructure.embedder import SentenceTransformerEmbedder
    from app.infrastructure.index_store import LocalIndexProvider
    from app.infrastructure.settings import load_settings

    settings = load_settings()
    embedder = SentenceTransformerEmbedder(
        settings.embed_model, revision=settings.embed_revision, device=settings.embed_device,
        max_seq_length=settings.embed_max_tokens, dimension=settings.embed_dimension,
        local_files_only=settings.hf_local_files_only,
    )
    provider = LocalIndexProvider(
        settings.data_root, embedder=embedder,
        expected_embedding_contract={
            "model": settings.embed_model, "revision": settings.embed_revision,
            "dimension": settings.embed_dimension, "normalize_embeddings": True,
        },
        background_reload=False,
    )
    if not provider.load_initial():
        raise SystemExit(f"사용 중 세대를 올리지 못함: {provider.status()['last_error']}")
    index = provider.acquire().index

    pointer = json.loads((settings.data_root / "active_generation.json").read_text(encoding="utf-8-sig"))
    manifest_path = settings.data_root / pointer["search_index_root"] / "generations" / pointer["generation"] / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))

    order = list(index._order)  # noqa: SLF001 - BM25 행 번호 순서(조각ID 오름차순)
    store = index.get_chunks(order)
    chunks = []
    for chunk_id in order:
        chunk = store[chunk_id]
        index_text = chunk.index_text or chunk.text
        chunks.append({
            "chunk_id": chunk_id,
            "text": chunk.text,
            "index_text": index_text,
            "tokens": index.tokens(index_text),
            "access_level": chunk.access_level,
            "doc_type": chunk.source.doc_type,
            "source": chunk.source.source,
            "member_pseudo_id": chunk.member_pseudo_id,
        })

    # 자체 점검: 뽑아낸 토큰으로 BM25를 다시 만들어 기존 색인 점수와 같은지 확인함.
    # 여기서 어긋나면 토큰 추출이 색인과 다르다는 뜻이라 뒤의 비교가 전부 무의미해짐.
    import bm25s

    rebuilt = bm25s.BM25(k1=manifest["bm25"]["k1"], b=manifest["bm25"]["b"], method=manifest["bm25"]["method"])
    rebuilt.index([row["tokens"] for row in chunks], show_progress=False)

    rows = []
    max_token_gap = 0.0
    for item in load_questions():
        text = item["question"]
        keyword = raw_bm25_scores(index, text)
        vector_hits = index.vector_search(text, access_levels=ACCESS_LEVELS, k=K_CANDIDATES, member_pseudo_id=None)
        vocabulary = dict(getattr(rebuilt, "vocab_dict", {}) or {})
        limit = len(rebuilt.scores["indptr"]) - 1
        ids = [vocabulary[t] for t in index.tokens(text) if t in vocabulary and int(vocabulary[t]) < limit]
        if ids:
            check = rebuilt.get_scores_from_ids(ids)
            for row, chunk_id in enumerate(order):
                max_token_gap = max(max_token_gap, abs(float(check[row]) - keyword.get(chunk_id, 0.0)))
        rows.append({
            **item,
            "tokens": index.tokens(text),
            "keyword_scores": keyword,
            "vector_scores": {hit.chunk_id: float(hit.score) for hit in vector_hits},
        })

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        "generation": pointer["generation"],
        "chunk_count": pointer["chunk_count"],
        "bm25": manifest["bm25"],
        "tokenizer_signature": manifest["tokenizer_signature"],
        "card_alias_count": manifest["card_aliases"]["count"],
        "card_dictionary_count": manifest["card_dictionary"]["count"],
        "top_k": TOP_K,
        "k_candidates": K_CANDIDATES,
        "access_levels": list(ACCESS_LEVELS),
        "token_rebuild_max_gap": max_token_gap,
        "chunks": chunks,
        "questions": rows,
    }, ensure_ascii=False), encoding="utf-8")
    print(f"저장: {OUT} — 청크 {len(chunks)}개, 질문 {len(rows)}개")
    print(f"토큰 재구성 점수 최대 차이: {max_token_gap:.3e} (0에 가까워야 토큰 추출이 색인과 같음)")


if __name__ == "__main__":
    main()
