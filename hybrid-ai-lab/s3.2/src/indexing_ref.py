"""슬라이드 8~9: 임베딩·적재 완성본."""

import logging

from .helpers import embed_texts, get_collection, sanitize_metadata
from .models import Chunk


logger = logging.getLogger(__name__)

def embed_and_upsert(chunks: list[Chunk], batch_size: int = 32) -> dict:
    """배치 적재 후 성공 수와 실패 ID 반환. 같은 ID의 재적재는 덮어쓰기."""
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
        # 최초 시도와 재시도 1회. 성공한 묶음만 ok에 더함.
        for attempt in range(2):
            try:
                texts = [c.text for c in good]
                vecs = embed_texts(texts, kind="passage")
                col.upsert(
                    ids=[c.chunk_id for c in good],
                    documents=texts,
                    embeddings=vecs,
                    metadatas=[sanitize_metadata(c.metadata) for c in good],
                )
            except NotImplementedError:
                raise
            except Exception as exc:
                if attempt == 1:
                    failed.extend(c.chunk_id for c in good)
                    logger.warning("배치 재시도 실패 ids=%s reason=%s: %s",
                                   [c.chunk_id for c in good], type(exc).__name__, exc)
            else:
                ok += len(good)
                break
    return {"ok": ok, "failed": failed}
