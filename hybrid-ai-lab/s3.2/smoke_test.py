"""모델 다운로드 없이 실제 Chroma 적재·권한·검색 연결만 확인하는 기본 검사.

표현 변형 비교(슬라이드 15~16)와 실제 모델의 뜻 검색 품질 평가는 수행하지 않음.
실행할 때마다 별도 DB 디렉터리를 만들며 기존 실습 데이터는 수정하지 않음.
"""
from pathlib import Path
import sys
from unittest.mock import patch
from uuid import uuid4

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE))

from src import helpers, indexing_ref
from src.models import Chunk
from src.retrieval_ref import search


def main() -> int:
    db_path = BASE / "data" / "smoke" / uuid4().hex
    helpers.configure(backend="smoke", db_path=db_path, collection="card_docs")
    chunks = [
        Chunk("연회비 청구 기준 안내", "D1_smoke_0000", {
            "access_level": "public", "doc_type": "regulation",
            "source": "합성약관.md", "clause_no": "제1조", "optional": None,
        }),
        Chunk("상담사 내부 연회비 처리 안내", "D2_smoke_0000", {
            "access_level": "internal", "doc_type": "benefit_guide",
            "source": "합성혜택.md", "clause_no": "상담 처리",
        }),
        Chunk("연회비 상담 기록 고객 문의", "D3_smoke_0000", {
            "access_level": "restricted", "doc_type": "consult_log",
            "source": "합성상담.md", "record_id": "SMOKE-001",
            "consult_date": "2026-09-10",
        }),
        Chunk("   ", "D3_smoke_empty", {
            "access_level": "restricted", "doc_type": "consult_log",
        }),
    ]
    result = indexing_ref.embed_and_upsert(chunks, batch_size=2)
    col = helpers.get_collection()
    assert result == {"ok": 3, "failed": ["D3_smoke_empty"]}, result
    assert col.count() == 3
    assert indexing_ref.embed_and_upsert(chunks[:3]) == {"ok": 3, "failed": []}
    assert col.count() == 3, "동일 ID 재적재로 건수가 늘어나면 안 됨"
    metadata = col.get(ids=["D1_smoke_0000"])["metadatas"][0]
    assert "optional" not in metadata
    query = "연회비"
    agent_hits = search(query, top_k=5, user_role="agent")
    audit_hits = search(query, top_k=5, user_role="auditor")
    assert len(agent_hits) == 2
    assert len(audit_hits) == 3
    assert all(h.metadata["access_level"] != "restricted" for h in agent_hits)
    assert all("chunk_id" in h.metadata for h in audit_hits)
    assert [h.score for h in audit_hits] == sorted((h.score for h in audit_hits), reverse=True)
    assert all(-1.001 <= h.score <= 1.001 for h in audit_hits)
    assert search(query, filters={"doc_type": "consult_log"}, user_role="agent") == []
    assert len(search(query, filters={"doc_type": "consult_log"}, user_role="auditor")) == 1
    assert search(query, filters={"access_level": "restricted"}, user_role="agent") == []
    assert search(query, filters={"doc_type": "does_not_exist"}) == []
    try:
        search(query, user_role="unknown")
    except KeyError:
        pass
    else:
        raise AssertionError("모르는 역할은 KeyError로 멈춰야 함")
    # 임베딩 일시 실패 1회 뒤 실제 테스트 벡터로 재시도 성공 확인.
    real_embed = helpers.embed_texts
    calls = 0
    def fail_once(texts, kind="passage"):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError("smoke에서 만든 일시 오류")
        return real_embed(texts, kind=kind)
    with patch.object(indexing_ref, "embed_texts", side_effect=fail_once):
        assert indexing_ref.embed_and_upsert(chunks[:1]) == {"ok": 1, "failed": []}
    assert calls == 2
    assert col.count() == 3
    helpers.configure(collection="empty_smoke")
    assert search(query) == []
    helpers.configure(collection="card_docs")
    print("PASS: 적재 3건, 빈 본문 1건 기록, 재적재, 권한·조건, 점수순, 빈 결과, 재시도")
    print(f"DB: {db_path}")
    print("범위: 테스트 벡터와 실제 Chroma 연결 검증. 실제 모델·표현 변형 비교는 미실행.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
