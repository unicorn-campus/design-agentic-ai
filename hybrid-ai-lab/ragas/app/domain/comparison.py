"""버전 비교표의 기준선 대비 차이(Δ)와 개선 판정 규칙."""

from __future__ import annotations

IMPROVED, WORSE, NO_DIFF, UNKNOWN = "개선", "악화", "차이 없음", "—"


def delta(value: float | None, baseline: float | None) -> float | None:
    """그 버전 값 − 기준 버전 값. 어느 한쪽이 없으면 None."""

    if value is None or baseline is None:
        return None
    return round(value - baseline, 4)


def judge_code(diff: float | None) -> str:
    """코드 지표 판정 — 같은 입력에 같은 값이 나오므로 Δ가 0이 아니면 부호대로 판정함."""

    if diff is None:
        return UNKNOWN
    if diff == 0:
        return NO_DIFF
    return IMPROVED if diff > 0 else WORSE


def judge_ragas(diff: float | None, band: float | None) -> str:
    """RAGAS 지표 판정 — |Δ|가 기준 버전의 반복 흔들림 폭보다 클 때만 개선 · 악화로 봄.

    흔들림 폭 = 기준 버전을 같은 조건으로 반복 채점한 평균들의 (최대 − 최소). 0.8 같은 고정 합격선은 쓰지 않음.
    """

    if diff is None:
        return UNKNOWN
    if abs(diff) <= (band or 0.0):
        return NO_DIFF
    return IMPROVED if diff > 0 else WORSE


def direction_match(code_diff: float | None, ragas_diff: float | None) -> str:
    """코드 지표와 RAGAS 지표가 같은 방향으로 움직였는지 봄. 반대면 평가셋 정답 · 근거 표기를 점검할 신호임."""

    if code_diff is None or ragas_diff is None or code_diff == 0 or ragas_diff == 0:
        return UNKNOWN
    return "일치" if (code_diff > 0) == (ragas_diff > 0) else "반대 — 원인 확인"
