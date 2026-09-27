"""슬라이드 8~9: 조별 실습 골격. TODO 1~3 완성 후 실행."""

from .helpers import embed_texts, get_collection, sanitize_metadata
from .models import Chunk


def embed_and_upsert(chunks: list[Chunk], batch_size: int = 32) -> dict:
    """배치로 임베딩·적재하고 {"ok": 성공 수, "failed": 실패 ID 목록} 반환."""
    if isinstance(batch_size, bool) or not isinstance(batch_size, int) or batch_size <= 0:
        raise ValueError("batch_size는 양의 정수여야 함")
    ids = [c.chunk_id for c in chunks]
    if len(ids) != len(set(ids)):
        raise ValueError("입력에 중복 chunk_id가 있음: S3.1 결과 확인 필요")
    col, ok, failed = get_collection("card_docs"), 0, []
    for start in range(0, len(chunks), batch_size):
        batch = chunks[start:start + batch_size]
        good = [c for c in batch if c.text.strip()]
        failed.extend(c.chunk_id for c in batch if not c.text.strip())
        if not good:
            continue
        try:
            # TODO 1: good의 text 목록을 만들고 embed_texts(..., kind="passage") 호출
            raise NotImplementedError("TODO 1: 묶음을 임베딩하세요")
            # TODO 2: col.upsert에 ids, documents, embeddings, metadatas 전달
            # metadatas의 각 값은 sanitize_metadata(c.metadata)로 정리
            raise NotImplementedError("TODO 2: 임베딩과 꼬리표를 적재하세요")
            ok += len(good)
        except NotImplementedError:
            # 골격 미완성을 데이터 실패로 삼키지 않음. 이 블록은 유지.
            raise
        except Exception:
            # TODO 3: 같은 good 묶음으로 임베딩·upsert 1회 재시도
            # 성공 시 ok += len(good), 재실패 시 failed에 good의 chunk_id 추가
            raise NotImplementedError("TODO 3: 재시도와 실패 ID 기록을 작성하세요")
    return {"ok": ok, "failed": failed}
