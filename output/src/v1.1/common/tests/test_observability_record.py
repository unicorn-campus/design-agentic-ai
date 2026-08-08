"""관측 계측 — 단계를 합치지 않고 항목 이름을 그대로 쓰는지 확인함(시험 6번)."""

from __future__ import annotations

import pytest

from common.guardrail.errors import ToolErrorClass
from common.observability.exporter import MemorySink, StdoutJsonSink, build_sink, otel_available
from common.observability.record import StepRecorder, UnknownRecordItem


def test_record_count_equals_pattern_step_count(rulebook, sink) -> None:
    """기록을 남긴 단계 수 = ③ 단계 수. 단계를 합치지 않음(숫자로 보임)."""
    recorder = StepRecorder(sink, rulebook)
    for step_id in rulebook.pattern_steps:
        recorder.record(step_id, {})
    coverage = recorder.coverage()
    assert coverage.emitted_steps == coverage.pattern_steps == 90
    assert len(sink.records) == 90
    assert len({r.step_id for r in sink.records}) == 90


def test_declared_record_point_coverage_is_reported_not_merged(rulebook, sink) -> None:
    """⑥이 기록 항목을 적어 준 단계 수와 안 적어 준 단계 수를 숫자로 드러냄.

    ⑥ 「관측 기록 지점」은 `O-1` ~ `O-15` **15묶음**이고 그 묶음이 덮은 단계는 47개임.
    나머지 43단계는 ⑥에 항목이 없음 — 합치지 않고 기록만 남기고 `[확인필요]`를 붙임.
    """
    recorder = StepRecorder(sink, rulebook)
    coverage = recorder.coverage()
    assert coverage.record_point_groups == 15
    assert coverage.steps_with_declared_point == 47
    assert coverage.steps_without_declared_point == 43
    assert coverage.steps_with_declared_point + coverage.steps_without_declared_point == 90


def test_unmapped_step_still_records_with_a_flag(rulebook, sink) -> None:
    recorder = StepRecorder(sink, rulebook)
    record = recorder.record("S-R1", {})
    assert record.record_points == ()
    assert "[확인필요" in record.attributes["note"]


def test_item_names_come_from_design_only(rulebook, sink) -> None:
    """기록 항목 이름은 ⑥에 적힌 것을 그대로 씀. 항목을 더하지 않음."""
    recorder = StepRecorder(sink, rulebook)
    assert recorder.declared_items("S-R2") == (
        "request_id",
        "trigger_kind",
        "deadline_at",
        "접수 시각",
    )
    with pytest.raises(UnknownRecordItem, match="⑥이 안 적은 이름"):
        recorder.record("S-R2", {"내가 만든 항목": 1})


def test_unknown_step_is_refused(rulebook, sink) -> None:
    recorder = StepRecorder(sink, rulebook)
    with pytest.raises(UnknownRecordItem, match="③ 단계 목록에 없음"):
        recorder.record("S-Z1", {})


def test_retry_layers_are_counted_separately(rulebook, sink) -> None:
    """`O-9` — 재시도 5계층을 한 항목으로 합치지 않음(③ 8-3절 5계층)."""
    recorder = StepRecorder(sink, rulebook)
    layers = recorder.retry_layer_items()
    assert len(layers) == len(rulebook.retry_layers) == 5
    record = recorder.record_retry_layers({"단계 재시도": 1, "PG 자동 재시도": 0})
    assert set(record.attributes) == set(layers)
    with pytest.raises(UnknownRecordItem):
        recorder.record_retry_layers({"내가 만든 계층": 1})


def test_failure_reason_uses_connector_error_names(rulebook, sink) -> None:
    """실패 사유 값은 `04-connector.md`의 오류 분류 이름 4종을 그대로 씀."""
    recorder = StepRecorder(sink, rulebook)
    assert [e.value for e in ToolErrorClass] == ["인증 오류", "입력 오류", "일시 장애", "권한 부족"]
    record = recorder.record("S-R7", {"도구명": "C-4"}, error=ToolErrorClass.TRANSIENT)
    assert record.error_type == "일시 장애"


def test_error_stack_substitutes_failed_input(rulebook, sink) -> None:
    """`M-21` — 실패한 입력값을 치환하고 단계 식별자·상관 키만 남김."""
    recorder = StepRecorder(sink, rulebook)
    record = recorder.record_error(
        "S-S9",
        ToolErrorClass.TRANSIENT,
        {"exception_message": "card 4111111111111111 rejected", "stack_trace": "..."},
    )
    assert "4111111111111111" not in str(record.attributes)
    assert record.attributes["exception_message"] == "[가려짐]"
    assert record.error_type == "일시 장애"


def test_access_log_carries_retention_from_design(rulebook, sink) -> None:
    """접근 기록에 보관 기간이 붙음. 기간 값은 ⑥ · ⑤에서 옴(여기서 정하지 않음)."""
    recorder = StepRecorder(sink, rulebook)
    record = recorder.record_access("S-I4", {"accessed_by": "M-000123", "access_purpose": "P-01"})
    assert record.attributes["retention_months"] == rulebook.retention["access_log_months"] == 6
    assert "M-000123" not in str(record.attributes)


def test_exporter_falls_back_without_a_product_name() -> None:
    """`D-11`이 비면 제품 이름 없이 로컬에서 볼 수 있는 대체 방식으로 감."""
    sink = build_sink(endpoint=None, service_name="lunchpick-test", prefer_otel=False)
    assert isinstance(sink, StdoutJsonSink)


def test_memory_sink_is_used_for_tests() -> None:
    """바깥을 부르는 것은 전부 대역으로 바꿈."""
    sink = MemorySink()
    assert sink.records == []


@pytest.mark.live_call
def test_otel_sink_builds_when_sdk_present() -> None:
    """실제 SDK를 붙여 보는 시험. 기본 실행에서 빠져 있고 `-m live_call`로만 돎(D-07)."""
    if not otel_available():
        pytest.skip("관측 SDK가 이 환경에 없음")
    sink = build_sink(endpoint=None, service_name="lunchpick-test", prefer_otel=True)
    from common.observability.exporter import SpanRecord

    sink.emit(SpanRecord(name="test", step_id="S-R2", record_points=("O-1",), attributes={}))
    sink.flush()
