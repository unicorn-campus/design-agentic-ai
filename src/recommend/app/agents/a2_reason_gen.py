"""A-2 「추천 근거 생성」 — ③ 4-2절 계약 7칸. **유일한 LLM 에이전트임.**

사용 모델: `claude-sonnet-5`
호출 설정(③ 4-2절 D-11 확정): thinking=disabled · effort=low · max_tokens=1024

접근 가능한 정보 항목에서 **제외**된 것(⑤ 8절 대조 결과):
  F-1 알레르기·식이제한 항목명 — C-1 입력 규격에 칸 자체가 없음
  F-2 정확 좌표 — 거리값(distance_m)만 받음
  F-3 회원 이메일·닉네임 / F-9 회원 참조키
  F-4 식당명·메뉴명 원문 이력 — 카테고리 코드만

중단 조건 4건(③ 4-2절):
  ① candidates 0건 → 중단
  ② filter_applied가 true가 아니거나 ruleset_version이 빔 → **LLM 호출 없이** 중단
  ③ 근거 문장 또는 확신 스코어가 빠진 카드 발생 → 기본 추천 이유 경로로 넘김
  ④ 출력에 알레르기 항목명·좌표·이메일이 섞임 → 즉시 중단(⑥ L-1~L-4가 실행)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from lp_common.errors import LunchpickError

from ..connectors.c1_reason import C1Input, C1Output, ReasonConnector

log = logging.getLogger("lp.a2")


@dataclass
class A2Output:
    """③ 4-2절 출력 형식. `picks`·`generation_status` 2종이 `공유` 키임."""

    picks: list[dict[str, Any]] = field(default_factory=list)  # 공유 · 3건
    generation_status: str = ""  # 공유
    llm_calls: int = 0
    model: str = ""
    input_tokens: int = 0
    output_tokens: int = 0


# 커넥터 출력 키 → 에이전트 출력 키 대응 (③ 4-2절 아래 소절)
#   confidence_score(⑤ 초안) → confidence  ← J-8로 ⑤가 ③에 맞춤
_PICK_KEYS = ("restaurant_id", "reason_text", "confidence", "context_tags")


async def generate_picks(
    connector: ReasonConnector,
    *,
    candidates: list[dict[str, Any]],
    filter_applied: bool,
    filter_ruleset_version: str,
    context_tags: list[str],
    preference_codes: list[str],
    recent_category_codes: list[str],
    weather_code: str,
    weekday_code: str,
    daypart_code: str,
    coldstart: bool,
    timeout_sec: float,
) -> A2Output:
    """`S-R10` 근거·스코어 생성. 실패는 예외로 던지고 폴백은 ④ 그래프가 정함."""
    # 중단 조건 ① — 후보 0건
    if not candidates:
        raise LunchpickError("NO_CANDIDATE", "A-2 입력 candidates가 0건임")

    # 중단 조건 ② — LLM 호출 **직전**에 검사함(③ 4-2절 판정 시점)
    if filter_applied is not True or not filter_ruleset_version:
        raise LunchpickError(
            "FILTER_NOT_APPLIED",
            "filter_applied·filter_ruleset_version이 유효하지 않아 C-1을 부르지 않음",
        )

    payload = C1Input(
        preference_codes=preference_codes,
        recent_category_codes=recent_category_codes,
        weather_code=weather_code,
        weekday_code=weekday_code,
        daypart_code=daypart_code,
        coldstart=coldstart,
        # C-1에는 restaurant_id·display_name만 넘김. 좌표·알레르겐은 넘기지 않음
        candidates=[
            {"restaurant_id": c["restaurant_id"], "display_name": c["display_name"]}
            for c in candidates
        ],
        filter_applied=filter_applied,
        filter_ruleset_version=filter_ruleset_version,
    )

    result: C1Output = await connector.generate(payload, timeout_sec=timeout_sec)

    picks: list[dict[str, Any]] = []
    for raw in result.picks:
        # 중단 조건 ③ — 근거 문장·확신 스코어가 빠진 카드는 받지 않음
        if not raw.get("reason_text") or raw.get("confidence") is None:
            raise LunchpickError("REASON_GEN_FAIL", "근거 문장 또는 확신 스코어가 빠진 카드임")
        pick = {k: raw.get(k) for k in _PICK_KEYS}
        # 태그는 A-1이 확정한 집합 안으로 제한함 — 입력에 없는 것을 말하면 불합격(⑥ M-Q3)
        pick["context_tags"] = [t for t in (pick["context_tags"] or []) if t in context_tags]
        picks.append(pick)

    if len(picks) < 3:
        raise LunchpickError(
            "REASON_GEN_FAIL", f"추천 카드가 3건에 못 미침(생성 {len(picks)}건)"
        )

    return A2Output(
        picks=picks[:3],
        generation_status="OK",
        llm_calls=1,
        model=result.model,
        input_tokens=result.input_tokens,
        output_tokens=result.output_tokens,
    )


def build_fallback_picks(
    candidates: list[dict[str, Any]], *, reason: str
) -> A2Output:
    """L-2 경로 폴백 — 기본 추천 이유(거리·평점)로 대체함. 추천 자체는 살림.

    `US:UFR-REC-020#처리결과` "기본 추천 이유(거리·평점)를 대신 표시함".
    조립 시간 150ms를 ④ 9-1절이 배정했고 저장소 재조회가 없음(D-2).
    """
    picks = []
    for cand in candidates[:3]:
        picks.append(
            {
                "restaurant_id": cand["restaurant_id"],
                "reason_text": (
                    f"걸어서 {cand['walk_minutes']}분 · 평점 {cand['rating']}점으로 "
                    "가까이서 만족도가 높은 곳임"
                ),
                # 폴백 카드도 확신 스코어를 반드시 달고 나감(① G-2 동반 노출 100%)
                "confidence": 0.30,
                "context_tags": ["거리"],
            }
        )
    return A2Output(picks=picks, generation_status=f"FALLBACK:{reason}", llm_calls=0)
