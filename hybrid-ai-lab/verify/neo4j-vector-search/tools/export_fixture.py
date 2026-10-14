"""기존 검색기(retriever/vector-retriever)의 사용 중 세대를 읽기 전용으로 열어 Neo4j 검증용 자료를 JSON으로 뽑는 스크립트임.

왜 따로 뽑나: 검증용 가상환경에는 neo4j-graphrag만 두고, 무거운 torch·Chroma·Kiwi는 기존 검색기 가상환경을 그대로 쓰기 위함.
기존 코드는 import해서 읽기만 하며 색인 파일·설정을 고치지 않음.

실행(기존 검색기 가상환경):
    ../../retriever/vector-retriever/.venv/Scripts/python tools/export_fixture.py
출력: fixtures/retriever_fixture.json — 청크(본문·메타데이터·저장된 벡터), 평가 질문 벡터, 기존 검색기의 벡터·BM25 결과
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
RETRIEVER = ROOT.parent.parent / "retriever" / "vector-retriever"
QUESTIONS = ROOT.parent.parent / "indexer" / "vector-bm25" / "evaluation" / "group2_questions.json"
OUT = ROOT / "fixtures" / "retriever_fixture.json"
TOP_K = 10

# 기존 검색기의 역할 → 열람 등급 규칙과 같은 조합만 시험함(app/domain/access.py)
SCENARIOS = (
    ("agent", ("public",), None),
    ("auditor", ("public", "restricted"), None),
    ("auditor_member", ("public", "restricted"), "MEMBER"),  # MEMBER는 말뭉치에 있는 회원 가명 하나로 바꿈
)


def main() -> None:
    sys.path.insert(0, str(RETRIEVER))
    from app.infrastructure.embedder import SentenceTransformerEmbedder
    from app.infrastructure.index_store import LocalIndexProvider
    from app.infrastructure.settings import load_settings
    import chromadb

    settings = load_settings()
    embedder = SentenceTransformerEmbedder(
        settings.embed_model, revision=settings.embed_revision, device=settings.embed_device,
        max_seq_length=settings.embed_max_tokens, dimension=settings.embed_dimension,
        local_files_only=settings.hf_local_files_only,
    )
    provider = LocalIndexProvider(settings.data_root, embedder=embedder, expected_embedding_contract={
        "model": settings.embed_model, "revision": settings.embed_revision,
        "dimension": settings.embed_dimension, "normalize_embeddings": True,
    }, background_reload=False)
    if not provider.load_initial():
        raise SystemExit(f"사용 중 세대를 올리지 못함: {provider.status()['last_error']}")
    index = provider.acquire().index

    pointer = json.loads((settings.data_root / "active_generation.json").read_text(encoding="utf-8-sig"))
    collection = chromadb.PersistentClient(path=str(settings.data_root / pointer["chroma_path"])).get_collection(
        pointer["collection"])
    stored = collection.get(include=["embeddings", "metadatas", "documents"])
    vectors = {str(i): [float(x) for x in v] for i, v in zip(stored["ids"], stored["embeddings"])}

    chunks = []
    for chunk_id, chunk in sorted(index.get_chunks(vectors.keys()).items()):
        chunks.append({
            "chunk_id": chunk_id,
            "text": chunk.text,
            "access_level": chunk.access_level,
            "doc_type": chunk.source.doc_type,
            "source": chunk.source.source,
            "doc_key": chunk.source.doc_key,
            "card_name": chunk.source.card_name,
            "member_pseudo_id": chunk.member_pseudo_id,
            "embedding": vectors[chunk_id],
        })
    members = sorted({c["member_pseudo_id"] for c in chunks if c["member_pseudo_id"]})
    member = members[0] if members else None

    questions = json.loads(QUESTIONS.read_text(encoding="utf-8"))["questions"]
    rows = []
    for q in questions:
        text = str(q["question"])
        row = {"id": q["id"], "question": text, "vector": [float(x) for x in embedder.embed(text)], "results": {}}
        for name, levels, member_slot in SCENARIOS:
            pseudo = member if member_slot else None
            vec = index.vector_search(text, access_levels=levels, k=TOP_K, member_pseudo_id=pseudo)
            kw = index.keyword_search(text, access_levels=levels, k=TOP_K, member_pseudo_id=pseudo)
            row["results"][name] = {
                "access_levels": list(levels), "member_pseudo_id": pseudo,
                "vector": [[s.chunk_id, s.score] for s in vec],
                "keyword": [[s.chunk_id, s.score] for s in kw],
            }
        rows.append(row)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        "generation": pointer["generation"], "embedding_dimension": pointer["embedding_dimension"],
        "embedding_signature": pointer["embedding_signature"], "chunk_count": pointer["chunk_count"],
        "member_pseudo_id": member, "top_k": TOP_K, "chunks": chunks, "questions": rows,
    }, ensure_ascii=False), encoding="utf-8")
    print(f"저장: {OUT} — 청크 {len(chunks)}개, 질문 {len(rows)}개, 회원 가명 {member}")


if __name__ == "__main__":
    main()
