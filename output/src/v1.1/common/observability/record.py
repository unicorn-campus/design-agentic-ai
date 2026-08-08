"""관측 계측 — ③이 나눈 단계를 합치지 않고 단계마다 1개씩 남김.

기록 항목 이름은 ⑥ 10절에 적힌 것을 **그대로** 씀. 항목을 빼거나 더하지 않음 —
설정에 없는 항목 이름을 넣으면 실패로 처리함.

실패 사유 값은 `04-connector.md`의 오류 분류 이름을 그대로 씀(`guardrail.errors.ToolErrorClass`).
새 이름을 짓지 않음.

남기는 값은 **가리기 매핑을 지난 뒤**에만 담김. 원문이 기록에 남을 자리가 없음.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from ..guardrail.errors import ToolErrorClass
from ..guardrail.masking import MaskPath, Masker, get_masker
from ..guardrail.rules import RuleBook, get_rulebook
from .exporter import SpanRecord, SpanSink

__all__ = ["UnknownRecordItem", "StepCoverage", "StepRecorder"]

_UNMAPPED_SPAN_NAME = "step"
_UNMAPPED_NOTE = "[확인필요: ⑥ 관측 기록 지점 미지정 단계]"


class UnknownRecordItem(RuntimeError):
    """⑥에 없는 기록 항목 이름을 넣으려 함. 항목을 더하지 않으므로 실패로 처리함."""


@dataclass(frozen=True, slots=True)
class StepCoverage:
    """숫자로 보이는 대조값. 자가 점검이 이 값을 그대로 씀."""

    pattern_steps: int
    """③이 나눈 단계 수."""
    record_point_groups: int
    """⑥ 「관측 기록 지점」 묶음 수(`O-n`)."""
    steps_with_declared_point: int
    """⑥이 기록 항목을 적어 준 단계 수."""
    steps_without_declared_point: int
    """⑥에 기록 지점이 안 적힌 단계 수. 그래도 기록은 남김(단계를 합치지 않음)."""
    emitted_steps: int
    """코드가 실제로 기록을 남긴 단계 수."""


class StepRecorder:
    """단계마다 기록 1개. ⑥ `O-n`이 그 단계의 **항목 이름**을 정함."""

    def __init__(
        self,
        sink: SpanSink,
        book: RuleBook | None = None,
        masker: Masker | None = None,
    ) -> None:
        self._book = book or get_rulebook()
        self._masker = masker or get_masker(self._book)
        self._sink = sink
        self._emitted: set[str] = set()
        self._steps = frozenset(self._book.pattern_steps)

    # --- 조회 -------------------------------------------------------------
    def declared_items(self, step_id: str) -> tuple[str, ...]:
        items: list[str] = []
        for row in self._book.record_points_for_step(step_id):
            for item in row.get("items", ()):
                if item not in items:
                    items.append(str(item))
        return tuple(items)

    def record_point_ids(self, step_id: str) -> tuple[str, ...]:
        return tuple(str(row["id"]) for row in self._book.record_points_for_step(step_id))

    def span_name(self, step_id: str) -> str:
        points = self._book.record_points_for_step(step_id)
        return str(points[0]["span_name"]) if points else _UNMAPPED_SPAN_NAME

    def retry_layer_items(self) -> tuple[str, ...]:
        """`O-9`의 5계층 항목. 단계에 걸리지 않으므로 따로 내놓음."""
        return tuple(self._book.record_point("O-9")["items"])

    def coverage(self) -> StepCoverage:
        with_point = [s for s in self._book.pattern_steps if self._book.record_points_for_step(s)]
        return StepCoverage(
            pattern_steps=len(self._book.pattern_steps),
            record_point_groups=len(self._book.record_points),
            steps_with_declared_point=len(with_point),
            steps_without_declared_point=len(self._book.pattern_steps) - len(with_point),
            emitted_steps=len(self._emitted),
        )

    def emitted_steps(self) -> frozenset[str]:
        return frozenset(self._emitted)

    # --- 기록 -------------------------------------------------------------
    def record(
        self,
        step_id: str,
        fields: Mapping[str, Any],
        *,
        error: ToolErrorClass | None = None,
        path: MaskPath = MaskPath.OBSERVABILITY,
    ) -> SpanRecord:
        """단계 1개의 기록을 남김. 다른 단계와 합치지 않음."""
        if step_id not in self._steps:
            raise UnknownRecordItem(
                f"단계 {step_id}이 ③ 단계 목록에 없음 — 단계를 지어내지 않음"
            )
        declared = self.declared_items(step_id)
        if declared:
            unknown = [k for k in fields if k not in declared]
            if unknown:
                raise UnknownRecordItem(
                    f"단계 {step_id}의 기록 항목에 ⑥이 안 적은 이름이 있음: {sorted(unknown)}"
                    f" — 적힌 항목은 {list(declared)}"
                )
        attributes = self._masker.mask_mapping(dict(fields), path)
        if not declared:
            attributes["note"] = _UNMAPPED_NOTE
        record = SpanRecord(
            name=self.span_name(step_id),
            step_id=step_id,
            record_points=self.record_point_ids(step_id),
            attributes=attributes,
            error_type=error.value if error is not None else None,
        )
        self._sink.emit(record)
        self._emitted.add(step_id)
        return record

    def record_error(
        self,
        step_id: str,
        error: ToolErrorClass,
        raw: Mapping[str, Any],
    ) -> SpanRecord:
        """오류 메시지·스택 경로. `M-21`대로 실패한 입력값을 치환하고 `error.type`만 남김."""
        attributes = self._masker.mask_mapping(dict(raw), MaskPath.ERROR_STACK)
        record = SpanRecord(
            name=self.span_name(step_id),
            step_id=step_id,
            record_points=self.record_point_ids(step_id),
            attributes=attributes,
            error_type=error.value,
        )
        self._sink.emit(record)
        self._emitted.add(step_id)
        return record

    def record_access(self, step_id: str, raw: Mapping[str, Any]) -> SpanRecord:
        """개인정보 접근 기록 경로. `M-24`대로 회원ID 해시 + 접근 목적 코드만 남음."""
        attributes = self._masker.mask_mapping(dict(raw), MaskPath.ACCESS_LOG)
        attributes["retention_months"] = self._book.retention["access_log_months"]
        record = SpanRecord(
            name="개인정보 접근 로그",
            step_id=step_id,
            record_points=self.record_point_ids(step_id),
            attributes=attributes,
        )
        self._sink.emit(record)
        return record

    def record_retry_layers(self, counts: Mapping[str, int]) -> SpanRecord:
        """`O-9` — 재시도 5계층을 한 항목으로 합치지 않고 계층마다 세어 남김."""
        allowed = set(self.retry_layer_items())
        unknown = [k for k in counts if k not in allowed]
        if unknown:
            raise UnknownRecordItem(
                f"재시도 계층 이름에 ③·⑥이 안 쓴 이름이 있음: {sorted(unknown)}"
            )
        record = SpanRecord(
            name=str(self._book.record_point("O-9")["span_name"]),
            step_id=None,
            record_points=("O-9",),
            attributes={layer: counts.get(layer, 0) for layer in self.retry_layer_items()},
        )
        self._sink.emit(record)
        return record

    def flush(self) -> None:
        self._sink.flush()
