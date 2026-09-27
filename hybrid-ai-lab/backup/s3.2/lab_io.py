"""S3.1에서 승인한 chunks.jsonl 읽기 및 기본 품질 수치."""
from collections import Counter
from pathlib import Path
import json

from src.models import Chunk

REQUIRED = ('doc_type', 'created_at', 'version', 'owner_dept', 'access_level',
            'chunk_index', 'char_len', 'source')


def load_chunks(path: Path) -> list[Chunk]:
    if path.name in ('review.jsonl', 'exceptions.jsonl'):
        raise ValueError('검토·보류 파일은 적재 불가. 승인된 chunks.jsonl 사용 필요')
    chunks = []
    seen = set()
    with path.open(encoding='utf-8-sig') as stream:
        for line_no, line in enumerate(stream, 1):
            if not line.strip():
                continue
            row = json.loads(line)
            if not isinstance(row, dict):
                raise ValueError(f'{line_no}행: JSON 객체 필요')
            text, chunk_id, metadata = row.get('text'), row.get('chunk_id'), row.get('metadata')
            if not isinstance(text, str) or not isinstance(chunk_id, str) or not chunk_id.strip():
                raise ValueError(f'{line_no}행: text·chunk_id 형식 오류')
            if not isinstance(metadata, dict) or any(metadata.get(k) is None for k in REQUIRED):
                raise ValueError(f'{line_no}행: 필수 메타데이터 누락')
            if chunk_id in seen:
                raise ValueError(f'{line_no}행: 중복 chunk_id {chunk_id}')
            if metadata['char_len'] != len(text):
                raise ValueError(f'{line_no}행: char_len과 본문 길이 불일치')
            if metadata['doc_type'] == 'consult_log' and any(
                not metadata.get(k) for k in ('record_id', 'member_pseudo_id', 'consult_date', 'turn_range')
            ):
                raise ValueError(f'{line_no}행: 상담 출처·가명 ID·턴 범위 누락')
            if metadata.get('size_exception') and metadata.get('token_check') != 'passed':
                raise ValueError(f'{line_no}행: 토큰 미확인 크기 예외는 적재 불가')
            seen.add(chunk_id)
            chunks.append(Chunk(text, chunk_id, metadata))
    if not chunks:
        raise ValueError('적재할 청크가 없음')
    return chunks


def summarize(chunks: list[Chunk]) -> dict:
    result = {}
    for doc_type in sorted({c.metadata['doc_type'] for c in chunks}):
        selected = [c for c in chunks if c.metadata['doc_type'] == doc_type]
        lengths = [len(c.text) for c in selected]
        result[doc_type] = {'count': len(selected), 'mean_chars': round(sum(lengths) / len(lengths), 2),
                            'max_chars': max(lengths)}
    return {'total': len(chunks), 'documents': result,
            'access_levels': dict(Counter(c.metadata['access_level'] for c in chunks)),
            'versions': sorted({str(c.metadata['version']) for c in chunks}),
            'empty_text_ids': [c.chunk_id for c in chunks if not c.text.strip()],
            'note': '경계 표본·개인정보의 사람 검토는 별도 수행 필요'}
