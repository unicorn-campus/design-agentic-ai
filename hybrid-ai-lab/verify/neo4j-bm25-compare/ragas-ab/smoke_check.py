"""바꿔 끼우기가 실제로 먹히는지 LLM 없이 확인하는 점검 스크립트임(외부 API 호출 0회).

확인하는 것
1. 사용 중 세대를 올린 뒤 `acquire`가 돌려주는 색인이 Neo4j 어댑터로 바뀌는지
2. 같은 질문에 기존 BM25와 A 방식의 상위 10이 얼마나 겹치는지(직전 시험 결과를 이 경로에서 다시 확인)
3. 열람 등급과 회원 필터가 A 방식에서도 걸리는지(상담 문항 1건으로 확인)

실행:
    retriever/vector-retriever/.venv/Scripts/python verify/neo4j-bm25-compare/ragas-ab/smoke_check.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LAB_ROOT = ROOT.parent.parent.parent
RETRIEVER_DIR = LAB_ROOT / "retriever" / "vector-retriever"
EVAL_SET = LAB_ROOT / "ragas" / "eval-set.json"
OUT = ROOT / "smoke_check.json"

sys.path.insert(0, str(RETRIEVER_DIR))
sys.path.insert(0, str(ROOT))

K = 10
ACCESS = ("public", "restricted")


def main() -> int:
    """점검을 실행하고 결과를 출력하고 저장함. 반환값은 종료 코드(정상 0)."""

    from neo4j_keyword_index import (
        BASELINE,
        Neo4jKeywordIndex,
        Neo4jQuerySession,
        read_connection,
        setup_index,
        teardown_index,
    )
    from app.domain.member import member_pseudonym
    from app.infrastructure.embedder import SentenceTransformerEmbedder
    from app.infrastructure.index_store import LocalIndexProvider
    from app.infrastructure.settings import load_settings

    fixture = json.loads(BASELINE.read_text(encoding="utf-8"))
    questions = json.loads(EVAL_SET.read_text(encoding="utf-8"))["questions"]

    settings = load_settings()
    embedder = SentenceTransformerEmbedder(
        settings.embed_model, revision=settings.embed_revision, device=settings.embed_device,
        max_seq_length=settings.embed_max_tokens, dimension=settings.embed_dimension,
        local_files_only=settings.hf_local_files_only,
    )
    provider = LocalIndexProvider(
        settings.data_root, embedder=embedder,
        expected_embedding_contract={"model": settings.embed_model, "revision": settings.embed_revision,
                                     "dimension": settings.embed_dimension, "normalize_embeddings": True},
    )
    provider.load_initial()
    base_index = provider.acquire().index
    if base_index.generation_id() != fixture["generation"]:
        raise SystemExit(f"세대가 다름: {base_index.generation_id()} != {fixture['generation']}")

    url, auth = read_connection()
    session = Neo4jQuerySession(url, auth)
    rows: list[dict] = []
    try:
        setup_index(session, fixture["chunks"])
        neo_index = Neo4jKeywordIndex(base_index, session)
        for question in questions:
            member_id = next((item["member_id"] for item in question.get("filters") or [] if "member_id" in item), None)
            member = member_pseudonym(member_id) if member_id else None
            base_hits = base_index.keyword_search(question["question"], access_levels=ACCESS, k=K,
                                                  member_pseudo_id=member)
            neo_hits = neo_index.keyword_search(question["question"], access_levels=ACCESS, k=K,
                                                member_pseudo_id=member)
            base_ids = [hit.chunk_id for hit in base_hits]
            neo_ids = [hit.chunk_id for hit in neo_hits]
            common = len(set(base_ids) & set(neo_ids)) / len(base_ids) if base_ids else 1.0
            rows.append({
                "id": question["id"],
                "member_filter": member is not None,
                "base_top": base_ids,
                "neo_top": neo_ids,
                "overlap10": round(common, 3),
                "top1_same": bool(base_ids[:1] == neo_ids[:1]),
            })
    finally:
        teardown_index(session)
        session.close()

    overlap = sum(row["overlap10"] for row in rows) / len(rows)
    top1 = sum(row["top1_same"] for row in rows)
    report = {
        "generation": fixture["generation"],
        "questions": len(rows),
        "mean_overlap10": round(overlap, 3),
        "top1_same": f"{top1}/{len(rows)}",
        "neo4j_calls": neo_index.neo4j_calls,
        "rows": rows,
    }
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({key: value for key, value in report.items() if key != "rows"}, ensure_ascii=False, indent=2))
    print(f"결과 저장: {OUT}")
    return 0


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    raise SystemExit(main())
