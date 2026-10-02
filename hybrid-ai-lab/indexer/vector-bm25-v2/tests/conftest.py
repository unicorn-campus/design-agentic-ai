"""여러 테스트가 공유하는 가짜 토큰 계산기를 제공함."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class FakeTokenCounter:
    """특수 토큰을 포함한 길이 제한을 외부 모델 없이 재현함."""

    signature = "fake-special-token-counter-v1"
    max_tokens = 800

    def count(self, text: str) -> int:
        """본문 길이에 시작·종료 특수 토큰 두 개를 더해 반환함."""
        return len(text) + 2
