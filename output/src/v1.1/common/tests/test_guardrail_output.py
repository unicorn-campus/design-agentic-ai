"""출력측 검사 — 위반 유형마다 표본을 넣으면 차단·가림이 일어나는지 확인함(시험 2번)."""

from __future__ import annotations

import pytest

from common.guardrail.masking import MaskPath
from common.guardrail.output_guard import OutputGuard

# ⑥ 5절 위반 유형별 표본 — 행 하나에 표본 하나씩. 못 막은 건은 낮춰 보고하지 않고 그대로 적음
SAMPLES: dict[str, dict] = {
    "O-C1": {
        "step": "S-R13",
        "payload": {"reason_line": "새우가 들어간 메뉴라 추천했어요"},
        "labels": {"state:excluded_ingredient_codes": ["새우", "땅콩"]},
    },
    "O-C3": {
        "step": "S-R13",
        "payload": {"reason_detail": "문의는 hong@example.com 으로 주세요"},
    },
    "O-C4": {
        "step": "S-B8",
        "payload": {"learning_message": "1,000명 반영"},
        "truth": {"learning_message": "980명 반영"},
    },
    "O-C5": {
        "step": "S-I10",
        "payload": {"summary_sentence": "화요일에 한식을 가장 많이 먹었어요"},
        "truth": {"summary_sentence": "수요일에 한식을 가장 많이 먹었어요"},
    },
    "O-C6": {
        "step": "C-10",
        "payload": {"preview_line": "오늘은 hong@example.com 님께 추천"},
    },
    "O-C7": {
        "step": "S-R8",
        "payload": {"business_status": "폐업"},
    },
    "O-C8": {
        "step": "S-S6",
        "payload": {"disclosure_items": ["청약철회 7일", "해지 방법"]},  # 자동 갱신 고지 빠짐
    },
    "O-C9": {
        "step": "S-C5",
        "payload": {"remaining_days": "", "transition_date": "2026-09-08"},
    },
    "O-C11": {
        "step": "S-S12",
        "payload": {"payment_id": "PAY-20260808-0001"},
    },
}

# ⑥이 `[확인필요]`로 목록을 못 채워 **미가동**인 검사. 통과로 세지 않고 여기에 적어 둠
DISABLED_CHECKS = {"O-C2", "O-C10"}


@pytest.mark.parametrize("check_id", sorted(SAMPLES))
def test_each_violation_sample_is_blocked_or_masked(rulebook, check_id) -> None:
    spec = SAMPLES[check_id]
    guard = OutputGuard(rulebook)
    verdict = guard.redact(
        spec["step"],
        spec["payload"],
        labels=spec.get("labels"),
        truth=spec.get("truth"),
    )
    failed = verdict.failed_checks()
    assert check_id in failed, f"{check_id} 표본을 못 막았음 — 걸린 검사: {failed}"


def test_sample_count_covers_every_enabled_row(rulebook) -> None:
    """가동 중인 출력측 검사 전건에 표본이 있음. 미가동 행은 숫자로 따로 적음."""
    enabled = {str(row["id"]) for row in rulebook.output_checks if row.get("enabled", True)}
    disabled = {str(row["id"]) for row in rulebook.output_checks if not row.get("enabled", True)}
    assert disabled == DISABLED_CHECKS
    assert set(SAMPLES) == enabled
    assert len(enabled) + len(disabled) == rulebook.counts["output_check"] == 11


def test_disabled_check_is_reported_as_not_running(rulebook) -> None:
    """목록이 비면 검사 미가동임을 기록에 남김 — 통과로 낮춰 적지 않음."""
    guard = OutputGuard(rulebook)
    verdict = guard.redact("S-R13", {"reason_line": "괜찮은 집이에요"})
    assert "O-C2" in verdict.checks_disabled
    assert "O-C2" in verdict.failed_checks()


def test_discarded_sentence_does_not_leave_the_system(rulebook) -> None:
    """`O-C3` 적중 → 문장 폐기 + 감사 기록. 밖으로 나가는 값에 그 칸이 없음."""
    guard = OutputGuard(rulebook)
    verdict = guard.redact("S-R13", {"reason_detail": "hong@example.com 참고"})
    assert "reason_detail" not in verdict.payload
    assert verdict.audit_required


def test_payment_id_is_masked_to_last_four(rulebook) -> None:
    """`O-C11` — 결제 식별자는 뒤 4자리만 남김(`M-8`)."""
    guard = OutputGuard(rulebook)
    verdict = guard.redact("S-S12", {"payment_id": "PAY-20260808-0001"})
    assert "PAY-20260808-0001" not in str(verdict.payload)
    assert str(verdict.payload.get("payment_id", "")).endswith("0001")


def test_card_number_in_completion_screen_is_discarded(rulebook) -> None:
    """`O-C11` 카드번호 적중은 뒤 4자리가 아니라 **폐기**임."""
    guard = OutputGuard(rulebook)
    verdict = guard.redact("S-S12", {"card_text": "4111 1111 1111 1111"})
    assert "card_text" not in verdict.payload
    assert verdict.audit_required


def test_missing_disclosure_stops_the_approval_screen(rulebook) -> None:
    """`O-C8` — 고지 3항목 중 하나라도 없으면 승인 화면을 띄우지 않고 안전 종료(`B-21`)."""
    guard = OutputGuard(rulebook)
    verdict = guard.redact("S-S6", {"disclosure_items": ["청약철회 7일", "해지 방법"]})
    assert verdict.payload == {}  # 아무것도 내보내지 않음
    assert "O-C8" in verdict.failed_checks()


def test_complete_disclosure_passes(rulebook) -> None:
    guard = OutputGuard(rulebook)
    verdict = guard.redact(
        "S-S6",
        {"disclosure_items": ["청약철회 7일", "자동 갱신·다음 결제일", "해지 방법"]},
    )
    assert "O-C8" not in verdict.failed_checks()


def test_streaming_path_uses_the_same_check(rulebook) -> None:
    """부분 전송 경로도 예외로 두지 않음 — 같은 함수·같은 규칙을 지남."""
    guard = OutputGuard(rulebook)
    chunks = ["오늘은", " hong@example.com", " 추천"]
    blocked = 0
    for chunk in chunks:
        verdict = guard.redact("S-R13", {"reason_detail": chunk}, path=MaskPath.RESPONSE)
        if "O-C3" in verdict.failed_checks():
            blocked += 1
    assert blocked == 1


def test_reused_conditions_are_not_duplicated(rulebook) -> None:
    """`O-C6`은 `O-C1`·`O-C3` 조건을 **가져다 씀** — 같은 조건을 두 번 적지 않음."""
    row = rulebook.output_check("O-C6")
    assert row["reuse"] == ["O-C1", "O-C3"]
    assert not row.get("patterns"), "O-C6이 정규식을 따로 또 적었음"
