"""I-2가 쓰는 입력측 가드레일 — **규칙은 공용 패키지 한 벌뿐임.**

⑥ 10-1절이 `S-B11`(적재 전)과 `S-R5`(읽기 시점) 두 지점에 같은 규칙을
걸라고 적었으므로, 규칙 본문은 `lp_common.guardrails`에 한 번만 두고
I-2와 I-5가 같은 함수를 부름. 사본을 두면 두 지점이 조용히 갈라짐.
"""

from lp_common.guardrails import (  # noqa: F401
    block_low_confidence,
    inspect_external_string,
    is_fresh,
    shallow_read_check,
)

__all__ = [
    "block_low_confidence",
    "inspect_external_string",
    "is_fresh",
    "shallow_read_check",
]
