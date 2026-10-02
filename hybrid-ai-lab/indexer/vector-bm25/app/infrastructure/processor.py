"""정제를 마친 청크를 검증하고 검색 메타데이터를 붙여 저장 가능한 청크를 만드는 어댑터임."""

from __future__ import annotations

import json
from pathlib import Path
import re
from typing import Any

from app.application.ports import ChunkProcessorPort, TokenCounterPort
from app.domain.models import PreparedChunk, RawChunk
from app.domain.text_rules import (
    assert_no_residual_private,
    chunk_metadata,
    normalize_whitespace,
    sha256_text,
    stable_json_hash,
)


class ValidatingChunkProcessor(ChunkProcessorPort):
    """청크의 개인정보 잔존·토큰·메타데이터 계약을 검증함.

    토큰 계산기와 메타데이터 스키마를 주입받으며, 임베딩이나 색인 저장은 수행하지 않음.
    """

    def __init__(
        self,
        token_counter: TokenCounterPort,
        metadata_schema: str | Path | dict[str, Any] | None = None,
    ) -> None:
        """정제 후 검증에 사용할 토큰 계산기와 메타데이터 스키마를 설정함.

        인자: metadata_schema가 없으면 프로젝트 기본 스키마를 사용함.
        부수효과: 파일 경로를 받으면 생성 시점에 JSON 스키마를 읽음.
        """

        self._counter = token_counter
        if metadata_schema is None:
            metadata_schema = Path(__file__).resolve().parents[2] / "config" / "metadata_schema.json"
        if isinstance(metadata_schema, dict):
            self._schema = metadata_schema
        else:
            self._schema = json.loads(Path(metadata_schema).read_text(encoding="utf-8"))

    def process(self, chunk: RawChunk) -> PreparedChunk | None:
        """정제를 마친 청크를 검증하고 쪽·조항 메타데이터를 붙여 저장 가능한 청크를 만듦.

        목적: 로더의 문서 단위 정제를 빠져나간 개인정보가 벡터DB나 BM25 corpus에 기록되는 것을 막음.
        방법: 공백 정리 뒤 잔존 개인정보 검사, 토큰 상한, 메타데이터 스키마를 차례로 검증함.
          청크 위치는 쪽·조항 계산에만 쓰고 메타데이터에는 남기지 않음. 검색 이후 쓰는 곳이 없기 때문임.
        반환값: 공백 정리 결과가 비면 None, 저장 가능하면 해시와 안정 ID를 포함한 청크임.
        예외: 개인정보가 남거나 토큰 상한·메타데이터 계약을 위반하면 ValueError를 발생시킴.
        부수효과: 없음.
        """

        text = normalize_whitespace(chunk.text)
        if not text:
            return None
        assert_no_residual_private(text)
        # 머리말은 본문을 정리한 뒤에 만들어야 "본문에 이미 있으면 생략" 판정이 저장될 본문과 같은 기준이 됨.
        header = chunk.binding.index_header(text) if chunk.binding is not None else ""
        index_text = f"{header}{chunk.binding.header.separator}{text}" if header else text
        token_count = self._counter.count(index_text)
        if token_count > self._counter.max_tokens:
            raise ValueError("정제된 청크가 임베딩 모델 입력 상한을 초과했습니다.")

        metadata = chunk_metadata(chunk.document, chunk.start, chunk.end)
        if chunk.binding is not None:
            # 구간이 확정한 대상으로 덮어써야 조각이 합쳐지며 엉뚱한 대상이 붙던 오류가 사라짐.
            metadata = chunk.binding.apply(metadata)
        required = tuple(self._schema["required"])
        if any(not metadata.get(key) for key in required):
            raise ValueError("필수 메타데이터가 누락되었습니다.")
        metadata.update(
            {
                "pseudonymized": chunk.document.pseudonymized,
                "chunk_index": chunk.ordinal,
                "token_count": token_count,
                "tokenizer_signature": self._counter.signature,
            }
        )
        # 지문은 색인용 텍스트 기준임. 머리말이 바뀌면 벡터를 재사용하지 않고 다시 임베딩해야 하기 때문임.
        text_hash = sha256_text(index_text)
        document_key = re.sub(r"[^A-Za-z0-9_-]+", "_", chunk.document.document_id).strip("_")
        # 같은 본문이 반복되는 경우의 순번 접미사는 문서 전체를 보는 application 단계에서 붙임.
        chunk_id = f"{document_key}_{text_hash[:16]}"
        metadata["chunk_id"] = chunk_id
        self._validate_metadata(metadata)
        return PreparedChunk(
            chunk_id=chunk_id,
            text=text,
            metadata=metadata,
            token_count=token_count,
            text_hash=text_hash,
            metadata_hash=stable_json_hash(metadata),
            index_text=index_text if header else "",
        )

    def _validate_metadata(self, metadata: dict[str, Any]) -> None:
        """메타데이터의 허용 키와 열거형 값을 스키마에 맞춰 검증함."""

        unknown = sorted(set(metadata) - set(self._schema["allowed"]))
        if unknown:
            raise ValueError("허용되지 않은 메타데이터 키가 있습니다: " + ", ".join(unknown))
        for key, allowed in self._schema.get("enums", {}).items():
            if metadata.get(key) not in allowed:
                raise ValueError(f"메타데이터 {key} 값이 허용 목록에 없습니다.")
