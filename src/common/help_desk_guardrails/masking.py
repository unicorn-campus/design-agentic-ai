from __future__ import annotations

import hashlib
import json
import re
from copy import deepcopy
from typing import Any, Callable

from .policy import GuardrailPolicy, load_policy


FIELD_KEYS = {
    "F-1": {"card_number", "pan"},
    "F-2": {"cvc", "cvv"},
    "F-3": {"password"},
    "F-4": {"resident_number", "rrn"},
    "F-5": {"auth_token", "token"},
    "F-6": {"customer_id", "customer_ref"},
    "F-7": {"transcript", "raw_transcript", "safe_inquiry_text", "masked_transcript"},
}


class SensitiveDataMasker:
    def __init__(
        self,
        salt: str,
        checkpoint_encryptor: Callable[[Any], Any] | None = None,
        policy: GuardrailPolicy | None = None,
    ) -> None:
        if not salt:
            raise ValueError("해싱 솔트가 필요함")
        self._salt = salt
        self._checkpoint_encryptor = checkpoint_encryptor
        selected = policy or load_policy()
        self._sensitive_patterns = tuple({
            row.model_extra["pattern"]
            for row in selected.output_rules
            if row.model_extra["kind"] == "pattern"
        })

    def sanitize(self, value: Any, path: str) -> Any:
        if path not in {"error", "audit", "access", "checkpoint"}:
            raise ValueError(f"지원하지 않는 가리기 경로: {path}")
        return self._walk(deepcopy(value), checkpoint=path == "checkpoint")

    def _walk(self, value: Any, checkpoint: bool) -> Any:
        if isinstance(value, dict):
            clean: dict[str, Any] = {}
            for key, item in value.items():
                field_id = next((fid for fid, keys in FIELD_KEYS.items() if key in keys), None)
                if field_id in {"F-1", "F-2", "F-3", "F-4", "F-5"}:
                    continue
                if field_id == "F-6":
                    if checkpoint:
                        if self._checkpoint_encryptor is None:
                            raise ValueError("체크포인트 암호화 어댑터가 필요함")
                        clean[key] = self._checkpoint_encryptor(item)
                    else:
                        clean[key] = hashlib.sha256(f"{item}{self._salt}".encode()).hexdigest()
                    continue
                if field_id == "F-7":
                    if checkpoint:
                        continue
                    clean[key] = "[상담 원문 마스킹됨]"
                    continue
                clean[key] = self._walk(item, checkpoint)
            return clean
        if isinstance(value, list):
            return [self._walk(item, checkpoint) for item in value]
        if isinstance(value, str):
            for pattern in self._sensitive_patterns:
                value = re.sub(pattern, "[민감정보 가림]", value)
        return value

    def contains_sensitive_pattern(self, value: Any) -> bool:
        text = json.dumps(value, ensure_ascii=False, sort_keys=True)
        return any(re.search(pattern, text) for pattern in self._sensitive_patterns)
