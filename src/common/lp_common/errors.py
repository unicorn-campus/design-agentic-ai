"""⑥ 6절 실패 사유 코드 10종. **전부 US `[처리 결과] 실패 시` 원문 인용임.**

지어낸 유형은 0건임(⑥ 6절 머리말).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ReasonCode:
    code: str
    user_message: str
    steps: tuple[str, ...]
    source: str


REASON_CODES: dict[str, ReasonCode] = {
    "AUTH_FAIL": ReasonCode(
        "AUTH_FAIL",
        "인증에 실패했어요. 다시 시도해주세요",
        ("S-R1",),
        "US:UFR-MBR-010#처리결과",
    ),
    "NETWORK": ReasonCode(
        "NETWORK",
        "인터넷 연결을 확인해주세요",
        ("S-R1", "S-E1"),
        "US:UFR-MBR-010#처리결과",
    ),
    "LOCATION_UNKNOWN": ReasonCode(
        "LOCATION_UNKNOWN",
        "위치를 설정해주세요",
        ("S-R1", "S-R2"),
        "US:UFR-REC-010#처리결과",
    ),
    "EXTERNAL_API_ERROR": ReasonCode(
        "EXTERNAL_API_ERROR",
        "최신 추천을 불러오고 있어요",
        ("S-R4", "S-R5", "S-R6"),
        "US:UFR-REC-010#처리결과",
    ),
    "REASON_GEN_FAIL": ReasonCode(
        "REASON_GEN_FAIL",
        "추천 이유를 준비 중이에요",
        ("S-R9", "S-R10"),
        "US:UFR-REC-020#처리결과",
    ),
    "NO_CANDIDATE": ReasonCode(
        "NO_CANDIDATE",
        "주변에 더 추천할 곳이 없어요. 거리를 넓혀볼까요?",
        ("S-R7", "S-R8", "S-R10"),
        "US:UFR-REC-050#처리결과",
    ),
    "NO_DATA": ReasonCode(
        "NO_DATA",
        "이 근처에서 인기 있는 메뉴를 보여드려요",
        ("S-B7",),
        "US:UFR-REC-030#처리결과",
    ),
    "DUPLICATE_RECORD": ReasonCode(
        "DUPLICATE_RECORD",
        "이미 기록되었어요. 수정하시겠어요?",
        ("S-E2",),
        "US:UFR-REC-070#처리결과",
    ),
    "FEEDBACK_SKIP": ReasonCode(
        "FEEDBACK_SKIP",
        "괜찮아요. 다음에 알려주세요",
        ("S-E4",),
        "US:UFR-REC-090#처리결과",
    ),
    "LEARNING_FAIL": ReasonCode(
        "LEARNING_FAIL",
        "이전 취향을 그대로 유지했어요",
        ("S-B3",),
        "US:UFR-REC-100#처리결과",
    ),
    # 동의 없음 착지 — ④ 5-1절 · ⑥ B-8. 원문 문구는 위치 설정 안내를 씀
    "CONSENT_REQUIRED": ReasonCode(
        "CONSENT_REQUIRED",
        "위치 정보 동의가 필요해요. 지역을 직접 선택해주세요",
        ("S-R2",),
        "US:UFR-MBR-030#처리결과",
    ),
    "SENSITIVE_CONSENT_REQUIRED": ReasonCode(
        "SENSITIVE_CONSENT_REQUIRED",
        "알레르기 정보 사용 동의가 필요해요. 동의 없이는 안전한 추천을 드릴 수 없어요",
        ("S-R2",),
        "US:UFR-MBR-040#검증요구사항",
    ),
    "FILTER_NOT_APPLIED": ReasonCode(
        "FILTER_NOT_APPLIED",
        "안전 확인이 끝나지 않아 추천을 준비하지 못했어요",
        ("S-R9",),
        "설계판단(④ 5-2절 · ⑥ B-6)",
    ),
}


class LunchpickError(Exception):
    """사유 코드를 달고 다니는 예외. 관측 기록 O-5에 그대로 실림."""

    def __init__(self, code: str, detail: str = "") -> None:
        if code not in REASON_CODES:
            raise KeyError(f"⑥ 6절 사유 코드 표에 없는 코드임: {code}")
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {REASON_CODES[code].user_message}")

    @property
    def user_message(self) -> str:
        return REASON_CODES[self.code].user_message
