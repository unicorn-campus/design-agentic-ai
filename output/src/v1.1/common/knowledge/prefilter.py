"""결정론 선행 필터 — 되돌릴 수 없는 판정을 **검색보다 먼저** 규칙으로 거름.

⑤가 「되돌림 예」로 적은 3자리만 만들었음.

| 필터 | ⑤의 어느 판정 | 왜 앞에 두나 |
|------|-------------|------------|
| 알레르겐 하드 필터 | 판정 2 `Q6` | 못 먹는 재료를 확률에 맡기지 않음 |
| 해지 확인 통과 검사 | 판정 2-B `Q12` | 해지는 되돌릴 수 없는 금전 작업임 |
| 만료 전환 사전 조건 | 판정 2-B `Q13` | 잘못 뽑으면 결제 중인 사용자를 강등함 |

세 함수 모두 **입력 → 통과·차단 → 사유** 3가지만 돌려주는 순수 함수임. 모델을 부르지 않음.
필터를 지나가지 못한 요청은 검색기를 **부르지 않고** 그대로 착지함.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum

__all__ = [
    "PREFILTERS",
    "FilterOutcome",
    "PrefilterVerdict",
    "allergen_hard_filter",
    "cancel_confirm_filter",
    "expiry_downgrade_filter",
]


class FilterOutcome(StrEnum):
    PASS = "통과"
    BLOCK = "차단"


@dataclass(frozen=True, slots=True)
class PrefilterVerdict:
    """필터 1회의 판정. 이 3칸 밖으로 값을 흘리지 않음."""

    filter_id: str
    outcome: FilterOutcome
    reason: str

    @property
    def passed(self) -> bool:
        return self.outcome is FilterOutcome.PASS


def allergen_hard_filter(
    excluded_ingredient_codes: Iterable[str],
    place_ingredient_codes: Iterable[str] | None,
    mapping_failsafe: bool,
) -> PrefilterVerdict:
    """식당 1곳을 후보에 남길지 규칙으로만 판정함.

    - 라벨을 코드로 못 바꿨으면(`mapping_failsafe`) **차단** — 페일세이프임
    - 식당의 재료를 알려 주는 값이 없으면(`None`) **차단** — 추측하지 않음
    - 제외 코드와 겹치면 **차단**
    """
    filter_id = "PF-1"
    if mapping_failsafe:
        return PrefilterVerdict(
            filter_id,
            FilterOutcome.BLOCK,
            "알레르겐 라벨을 제외 식재료 코드로 바꾸지 못했음 — 페일세이프로 제외함",
        )
    if place_ingredient_codes is None:
        return PrefilterVerdict(
            filter_id,
            FilterOutcome.BLOCK,
            "식당·메뉴 재료를 알려 주는 원천이 없음 — [확인필요: 알레르겐 판정 데이터 원천]",
        )
    excluded = {str(code) for code in excluded_ingredient_codes}
    used = {str(code) for code in place_ingredient_codes}
    overlap = sorted(excluded & used)
    if overlap:
        return PrefilterVerdict(
            filter_id, FilterOutcome.BLOCK, f"제외 식재료 코드와 겹침 — {overlap}"
        )
    return PrefilterVerdict(filter_id, FilterOutcome.PASS, "제외 식재료와 겹치지 않음")


def cancel_confirm_filter(
    cancel_confirm_id: str | None,
    confirmed_at: str | None,
) -> PrefilterVerdict:
    """해지 예약 경로에 들어갈 수 있나. 확인 통과 증거 2칸만 봄."""
    filter_id = "PF-2"
    if not cancel_confirm_id or not confirmed_at:
        return PrefilterVerdict(
            filter_id,
            FilterOutcome.BLOCK,
            "해지 확인 통과 증거가 없음 — 확인 없이 예약 경로에 들어가지 않음",
        )
    return PrefilterVerdict(filter_id, FilterOutcome.PASS, "해지 확인 통과 증거가 있음")


def expiry_downgrade_filter(
    downgrade_scheduled_on: str | None,
    run_on: str | None,
    cancel_withdrawn: bool | None,
    payment_grace_elapsed: bool | None,
) -> PrefilterVerdict:
    """만료 전환 대상인가. 판정할 수 없으면 강등하지 않고 그대로 둠."""
    filter_id = "PF-3"
    if downgrade_scheduled_on is None or run_on is None:
        return PrefilterVerdict(
            filter_id,
            FilterOutcome.BLOCK,
            "전환 예정일 또는 실행일이 없어 판정 불가 — 강등하지 않고 현 상태를 유지함",
        )
    if cancel_withdrawn is None or payment_grace_elapsed is None:
        return PrefilterVerdict(
            filter_id,
            FilterOutcome.BLOCK,
            "해지 철회 여부 또는 유예 경과 판정이 없어 판정 불가 — 현 상태를 유지함",
        )
    if cancel_withdrawn:
        return PrefilterVerdict(filter_id, FilterOutcome.BLOCK, "해지를 철회했음 — 대상 아님")
    if not payment_grace_elapsed:
        return PrefilterVerdict(
            filter_id, FilterOutcome.BLOCK, "결제 실패 유예가 아직 지나지 않았음 — 대상 아님"
        )
    if downgrade_scheduled_on > run_on:
        return PrefilterVerdict(
            filter_id, FilterOutcome.BLOCK, "전환 예정일이 아직 오지 않았음 — 대상 아님"
        )
    return PrefilterVerdict(filter_id, FilterOutcome.PASS, "전환 예정일이 도달했고 철회가 없음")


PREFILTERS: dict[str, str] = {
    "PF-1": "알레르겐 하드 필터 — ⑤ 판정 2 Q6",
    "PF-2": "해지 확인 통과 검사 — ⑤ 판정 2-B Q12",
    "PF-3": "만료 전환 사전 조건 — ⑤ 판정 2-B Q13",
}
