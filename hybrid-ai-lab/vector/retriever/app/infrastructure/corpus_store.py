"""활성 세대 포인터에서 검증된 corpus 스냅샷을 읽음."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from ..domain.corpus import CorpusSnapshot
from ..domain.korean_tokenizer import KoreanTokenizer


class VersionedCorpusStore:
    """`active_index.json`만 신뢰해 완성된 세대만 노출함."""

    def __init__(self, index_root: Path) -> None:
        self.index_root = Path(index_root)

    def _resolve(self, relative: str, *, directory: bool = False) -> Path:
        path = (self.index_root / relative).resolve()
        if not path.is_relative_to(self.index_root.resolve()):
            raise ValueError("검색 색인 경로가 루트 밖을 가리킴")
        exists = path.is_dir() if directory else path.is_file()
        if not exists:
            raise ValueError(f"검색 색인 파일이 없음: {relative}")
        return path

    def active_generation(self) -> str | None:
        pointer_path = self.index_root / "active_index.json"
        if not pointer_path.exists():
            return None
        pointer = json.loads(pointer_path.read_text(encoding="utf-8-sig"))
        return str(pointer["generation"])

    def _load_card_dictionary(
        self,
        pointer: dict[str, Any],
        manifest: dict[str, Any],
    ) -> tuple[tuple[tuple[str, str, float], ...], str | None]:
        relative = pointer.get("card_dictionary")
        manifest_info = manifest.get("card_dictionary")
        pointer_metadata_present = any(
            key in pointer
            for key in (
                "card_dictionary",
                "card_dictionary_sha256",
                "card_dictionary_count",
            )
        )
        if not pointer_metadata_present:
            if manifest_info is not None:
                raise ValueError("manifest에만 카드명 사전 정보가 있음")
            # 자동 카드명 사전 도입 전 포인터는 빈 자동 사전으로 읽음.
            return (), None
        if not relative or not isinstance(manifest_info, dict):
            raise ValueError("카드명 사전 경로 또는 manifest 정보가 불완전함")
        if "card_dictionary_sha256" not in pointer or "card_dictionary_count" not in pointer:
            raise ValueError("활성 포인터의 카드명 사전 검증 정보가 불완전함")

        dictionary_path = self._resolve(str(relative))
        payload = dictionary_path.read_bytes()
        actual_hash = hashlib.sha256(payload).hexdigest()
        expected_hash = str(pointer["card_dictionary_sha256"])
        if actual_hash != expected_hash:
            raise ValueError("활성 카드명 사전 SHA-256이 포인터와 일치하지 않음")

        expected_manifest = {
            "path": str(relative),
            "sha256": actual_hash,
            "count": int(pointer["card_dictionary_count"]),
            "source": "D2.metadata.card_name",
            "tag": "NNP",
            "score": 0.0,
        }
        if manifest_info != expected_manifest:
            raise ValueError("활성 포인터와 manifest의 카드명 사전 정보가 일치하지 않음")

        words: list[tuple[str, str, float]] = []
        for line_number, raw_line in enumerate(
            payload.decode("utf-8").splitlines(),
            start=1,
        ):
            if not raw_line.strip():
                continue
            parts = raw_line.split("\t")
            if len(parts) != 3:
                raise ValueError(f"카드명 사전 {line_number}행 형식이 올바르지 않음")
            form, tag, raw_score = parts
            try:
                score = float(raw_score)
            except ValueError as error:
                raise ValueError(
                    f"카드명 사전 {line_number}행 점수가 숫자가 아님"
                ) from error
            if tag != "NNP" or score != 0.0:
                raise ValueError("카드명 사전의 품사 또는 점수 정책이 manifest와 다름")
            words.append((form, tag, score))

        expected_count = int(pointer["card_dictionary_count"])
        if len(words) != expected_count:
            raise ValueError("활성 카드명 사전 항목 수가 포인터와 일치하지 않음")
        canonical_payload = KoreanTokenizer.additional_user_words_payload(words)
        if canonical_payload != payload:
            raise ValueError("활성 카드명 사전이 정렬·중복 제거된 표준 형식이 아님")
        return tuple(words), actual_hash

    def load_active(self) -> CorpusSnapshot | None:
        pointer_path = self.index_root / "active_index.json"
        if not pointer_path.exists():
            return None
        pointer = json.loads(pointer_path.read_text(encoding="utf-8-sig"))
        corpus_path = self._resolve(str(pointer["corpus"]))
        manifest_path = self._resolve(str(pointer["manifest"]))
        bm25_path = self._resolve(str(pointer["bm25"]), directory=True)
        payload = corpus_path.read_bytes()
        actual_hash = hashlib.sha256(payload).hexdigest()
        expected_hash = str(pointer.get("corpus_sha256", ""))
        if actual_hash != expected_hash:
            raise ValueError("활성 corpus SHA-256이 포인터와 일치하지 않음")
        records = tuple(
            json.loads(line)
            for line in payload.decode("utf-8-sig").splitlines()
            if line.strip()
        )
        if len(records) != int(pointer.get("chunk_count", -1)):
            raise ValueError("활성 corpus 청크 수가 포인터와 일치하지 않음")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
        if manifest.get("generation") != pointer.get("generation"):
            raise ValueError("활성 포인터와 manifest 세대가 일치하지 않음")
        card_dictionary_words, card_dictionary_sha256 = self._load_card_dictionary(
            pointer,
            manifest,
        )
        return CorpusSnapshot(
            generation=str(pointer["generation"]),
            corpus_sha256=actual_hash,
            records=records,
            bm25_path=bm25_path,
            manifest=manifest,
            card_dictionary_words=card_dictionary_words,
            card_dictionary_sha256=card_dictionary_sha256,
        )
