"""감사 기록 — 되돌릴 수 없는 일마다 1행이 남고 전후 값에 원문이 없는지 확인함."""

from __future__ import annotations

from common.observability.audit import AuditLog
from common.guardrail.tool_guard import ApprovalEvidence

NOW = 1_000_000


def _evidence() -> ApprovalEvidence:
    return ApprovalEvidence(
        approval_id="AP-1",
        approver_ref="회원해시12자리",
        approved_at_ms=NOW,
        subject="C-9:월 4900원 정기",
        shown_items=("청약철회 7일", "자동 갱신·다음 결제일", "해지 방법"),
    )


def test_audit_row_has_all_six_columns(rulebook, sink) -> None:
    """`언제 / 누가 / 어떤 도구 / 승인 표시 / 결과 / 중복 방지 키` 6칸이 다 있음."""
    log = AuditLog(sink, rulebook)
    row = log.append(
        occurred_at_ms=NOW,
        actor="M-000123",
        tool_id="C-9",
        result="성공",
        evidence=_evidence(),
        idempotency_key="IDEM-1",
        step_id="S-S9",
    )
    record = row.as_record()
    for column in ("언제", "누가", "어떤 도구", "승인 표시", "결과", "중복 방지 키"):
        assert column in record


def test_actor_and_key_are_masked(rulebook, sink) -> None:
    log = AuditLog(sink, rulebook)
    row = log.append(
        occurred_at_ms=NOW,
        actor="M-000123",
        tool_id="C-9",
        result="성공",
        evidence=_evidence(),
        idempotency_key="M-000123:2026-08-08",
    )
    assert "M-000123" not in row.actor_ref
    assert "M-000123" not in str(row.idempotency_key_hash)
    assert "AP-1" not in str(row.approval)


def test_before_after_keeps_no_original(rulebook, sink) -> None:
    """`M-23` — 변경 전후 값에 원문을 남기지 않음. 필드명 + 전후 해시만."""
    log = AuditLog(sink, rulebook)
    row = log.append(
        occurred_at_ms=NOW,
        actor="배치:S-X",
        tool_id="R-11",
        result="성공",
        before={"user_email": "hong@example.com"},
        after={"user_email": "gil@example.com"},
    )
    text = str(row.before_after)
    assert "hong@example.com" not in text
    assert "gil@example.com" not in text


def test_retention_comes_from_design(rulebook, sink) -> None:
    """보관 기간은 ⑥ 11절 · ⑤ 7절 값을 그대로 씀. 개발이 규정 기간을 정하지 않음."""
    log = AuditLog(sink, rulebook)
    assert log.retention_months == rulebook.retention["audit_record_months"] == 6


def test_audit_log_has_no_delete_function(rulebook, sink) -> None:
    """감사 기록은 지워지지 않게 둠. 만료 삭제는 `08-deploy.md` 몫임."""
    log = AuditLog(sink, rulebook)
    for name in ("delete", "remove", "purge", "clear", "truncate"):
        assert not hasattr(log, name), f"AuditLog에 {name}이 있음 — 지워질 수 있게 됨"


def test_denied_call_is_also_recorded(rulebook, sink) -> None:
    """막힌 건도 기록에 남김 — 낮춰 보고하지 않음."""
    log = AuditLog(sink, rulebook)
    log.append(
        occurred_at_ms=NOW,
        actor="M-000123",
        tool_id="C-9",
        result="거부:approval_evidence_absent",
        evidence=None,
    )
    assert log.rows()[0].approval["있음"] is False
    assert log.rows()[0].result.startswith("거부")


def test_hooks_fill_the_runtime_slots(rulebook, sink) -> None:
    """`01-runtime`이 비워 둔 `HookSet` 자리를 그대로 채움 — 새 이름을 짓지 않음."""
    from common.guardrail_hooks import HookSet
    from common.guardrail.hooks import build_guardrail_hooks
    from common.observability.record import StepRecorder

    hooks = build_guardrail_hooks(
        recorder=StepRecorder(sink, rulebook),
        audit=AuditLog(sink, rulebook),
        book=rulebook,
        boundary="TB-2",
    )
    assert isinstance(hooks, HookSet)
    kept = hooks.inspector.inspect("S-R7", {"place_name": "김밥천국", "email": "a@b.c"})
    assert "email" not in kept
    hooks.recorder.record("S-R2", {"request_id": "REQ-1"})
    assert sink.records[-1].step_id == "S-R2"
