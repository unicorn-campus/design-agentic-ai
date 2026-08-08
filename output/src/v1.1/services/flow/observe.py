"""⑥ 「관측 기록 지점」을 노드마다 붙이는 자리. **기록 단계 수 = ③이 나눈 단계 수(90)** 임.

기록 구현체는 `05-guardrail.md`가 만든 `common.observability.StepRecorder`를 부르기만 함.
여기서 기록기를 다시 만들지 않음.

⑥이 항목 이름을 적어 준 단계(47개)는 **그 이름만** 남김 — 이름을 더하면 `UnknownRecordItem`으로
실패하기 때문임. ⑥이 항목을 안 적어 준 43단계는 기록기가 `[확인필요]` 표를 스스로 붙임.
"""

from __future__ import annotations

from typing import Any, Mapping

from common.observability.record import StepRecorder

__all__ = ["record_step", "UNDECLARED_STEP_TAG"]

UNDECLARED_STEP_TAG = "[확인필요: ⑥ 관측 기록 지점 미지정 단계]"


def record_step(
    recorder: StepRecorder,
    step_id: str,
    fields: Mapping[str, Any],
) -> None:
    """단계 1개의 기록을 남김. 단계를 합치지 않음.

    ⑥이 이름을 적어 준 단계에서는 적힌 이름만 골라 넘김 — ⑥에 없는 이름을 넣지 않기 위함임
    (항목을 **더하지 않는다**는 ⑥ 규칙을 코드로 지킴).
    """
    declared = recorder.declared_items(step_id)
    payload = (
        {name: fields[name] for name in declared if name in fields}
        if declared
        else dict(fields)
    )
    recorder.record(step_id, payload)
