"""⑥ 8절 출력 측 노출 검사 규칙 L-1 ~ L-4.

검사 시점은 전부 **추천 카드 반환 직전**(`S-R12`)이며 알림 문구는 `S-E6`
발송 직전에 같은 규칙을 씀. 검사 방식 3종을 모두 씀 —
필드 지정 2건(L-1·L-4) · 라벨 목록 1건(L-2) · 패턴 1건(L-3).

이 검사가 ⑥ G-8의 실행 자리임: 위반 시 근거 문장을 기본 추천 이유로
**교체하고** 관측 기록에 위반 사유를 남김.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .codes import find_allergen_label
from .masking import EMAIL_RE


@dataclass
class CheckResult:
    payload: dict[str, Any]
    violations: list[str] = field(default_factory=list)

    @property
    def clean(self) -> bool:
        return not self.violations


# L-1 좌표 필드 키 경로 — 응답에 존재하면 키 자체를 제거함
_COORD_KEYS = ("lat", "lng", "latitude", "longitude", "geo_point")
# L-4 회원 닉네임 키 경로
_NICKNAME_KEYS = ("nickname", "member_nickname")


def _strip_keys(node: Any, keys: tuple[str, ...], found: list[str], label: str) -> Any:
    if isinstance(node, dict):
        out = {}
        for key, value in node.items():
            if key in keys:
                found.append(label)
                continue
            out[key] = _strip_keys(value, keys, found, label)
        return out
    if isinstance(node, list):
        return [_strip_keys(v, keys, found, label) for v in node]
    return node


def check_recommendation_payload(
    payload: dict[str, Any], *, default_reason_for: dict[str, str] | None = None
) -> CheckResult:
    """추천 카드 반환 직전 검사. ⑥ 8절 L-1 ~ L-4를 순서대로 적용함.

    Args:
        payload: ④ 11절 최종 출력 형식(`items[]` 등)
        default_reason_for: restaurant_id → 기본 추천 이유(거리·평점) 문장.
            L-2 위반 시 그 카드의 근거 문장을 이 값으로 **교체**함.
    """
    violations: list[str] = []

    # L-1 GPS 좌표 필드 — 필드 지정. 키 자체를 제거하고 distance_m·walk_min만 남김
    payload = _strip_keys(payload, _COORD_KEYS, violations, "L-1:coordinate_key")

    # L-4 회원 닉네임 — 필드 지정. 키 제거
    payload = _strip_keys(payload, _NICKNAME_KEYS, violations, "L-4:nickname_key")

    for item in payload.get("items", []):
        reason = item.get("reason_text", "") or ""
        evidence = " ".join(str(e) for e in item.get("evidence", []) or [])
        blob = f"{reason} {evidence}"

        # L-2 알레르기·식이제한 항목명 — 라벨 목록(낱말 경계 적용)
        hit = find_allergen_label(blob)
        if hit is not None:
            violations.append("L-2:allergen_label")
            fallback = (default_reason_for or {}).get(item.get("restaurant_id", ""))
            item["reason_text"] = fallback or _distance_reason(item)
            item["evidence"] = ["거리"]
            item["reason_replaced"] = True

        # L-3 이메일 — 패턴
        if EMAIL_RE.search(item.get("reason_text", "") or ""):
            violations.append("L-3:email_pattern")
            item["reason_text"] = EMAIL_RE.sub("[가림]", item["reason_text"])
            item["reason_replaced"] = True

    return CheckResult(payload=payload, violations=violations)


def check_push_message(message: str) -> tuple[str, list[str]]:
    """`S-E6` 알림 문구 발송 직전 — L-2·L-3만 적용함(⑥ 8절 검사 시점 열)."""
    violations: list[str] = []
    out = message
    hit = find_allergen_label(out)
    if hit is not None:
        violations.append("L-2:allergen_label")
        out = "점심 드셨나요? 오늘 식사를 기록해보세요"
    if EMAIL_RE.search(out):
        violations.append("L-3:email_pattern")
        out = EMAIL_RE.sub("[가림]", out)
    return out, violations


def _distance_reason(item: dict[str, Any]) -> str:
    """L-2 폴백 문구 — 기본 추천 이유(거리·평점). `US:UFR-REC-020#처리결과`."""
    walk = item.get("walk_min")
    if walk is None:
        return "가까운 거리에 있어 빠르게 다녀올 수 있어요"
    return f"걸어서 {walk}분 거리라 점심시간에 다녀오기 좋아요"
