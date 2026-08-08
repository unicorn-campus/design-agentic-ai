"""`R-4` 취향 벡터 커밋 처리기 — ④ 3-4절.

맡은 ③ 단계 1개 — `S-B7`.
사용 모델 — **모델 미사용(결정론적 실행).**
사용 도구 — `S-4` 취향 벡터 인덱스 적재 **`쓰기(되돌림 불가)`** · `S-6` 감사 로그 적재.

**커밋 앞의 사람 승인 노드가 ③에 없음**(④ 9절 1번 변경요청 · ③ 12절 2번이 `반영하지 않음`으로 판정).
그래서 여기서 노드를 만들지 않고, ⑥이 `R-4`에 걸어 둔 **제한 장치 5개**를 승인 문으로 씀 —
`quality_threshold_passed` · `idempotency_key` · `run_lock` · `commit_count_cap` ·
`operator_post_notice`.
"""

from __future__ import annotations

from typing import Any, Sequence

__all__ = ["OWNER_ID", "STEP_IDS", "GUARD_NAMES", "commit_preference_vector"]

OWNER_ID = "R-4"
STEP_IDS = ("S-B7",)

GUARD_NAMES = (
    "quality_threshold_passed",
    "idempotency_key",
    "run_lock",
    "commit_count_cap",
    "operator_post_notice",
)
"""⑥ 3-1절 `R-4` 행의 `guards` 5개. 이름을 여기서 짓지 않고 ⑥ 값을 인용함."""


def commit_preference_vector(
    *,
    member_id: str,
    candidate_vector: Sequence[float],
    vector_model_version: str,
    quality_passed: bool,
    target_date: str,
    idempotency_key: str,
    committed_at: int,
) -> dict[str, Any]:
    """④ 「입출력 형식」의 입력 6키를 받아 출력 3키를 냄.

    ④ 중단 조건 ⓐ — `quality_passed`가 거짓이면 커밋하지 않고 멈춤(이전 벡터 유지 · ⑥ `B-7`).
    ④ 중단 조건 ⓑ — 중복 방지 키가 이미 처리된 건이면 커밋하지 않고 멈춤.
      (이미 처리됐는지 보는 것은 흐름 쪽 중복 방지 키 저장소가 함 — 여기서 저장소를 만들지 않음.)
    """
    if not quality_passed:
        raise ValueError("품질 미통과 — 커밋하지 않음(이전 벡터 유지)")
    if not idempotency_key:
        raise ValueError("중복 방지 키가 빔 — 커밋하지 않음")
    if not candidate_vector:
        raise ValueError("갱신 벡터 후보가 빔 — 커밋하지 않음")
    # 출력 키는 ④ 「입출력 형식」의 3개뿐임 — 키를 더하지 않음.
    return {
        "commit_result": "커밋",
        "committed_at": committed_at,
        "member_id": member_id,
    }
