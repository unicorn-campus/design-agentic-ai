"""`R-1` 추천 문장 생성 담당자 — ④ 3-1절 계약 1장 = 모듈 1개.

맡은 ③ 단계 — `S-R11` 1개.
사용 모델 — ④ 「사용 모델」이 정한 값을 **설정에서** 받아 씀. 모델 이름이 이 파일에 없음.
사용 도구 — `C-2` 추천 생성 커넥터 1개(⑤ 6절). 다른 도구 0건.

**16명 중 모델을 쓰는 담당자는 이 1명뿐임**(④ 2-5절). 나머지 15명은 순수 함수임.

프롬프트는 코드 문자열이 아니라 `prompts/` 아래 파일 2개에 있음 —
`r1_recommendation_system.md` · `r1_recommendation_user.md`.
"""

from __future__ import annotations

import functools
import json
from pathlib import Path
from typing import Any, Mapping

from common.guardrail import wrap_external_text
from toolkit.runner import CallContext, ConnectorResult, ConnectorTool

__all__ = [
    "OWNER_ID",
    "STEP_IDS",
    "CONNECTOR_ID",
    "K6_KEYS",
    "PROMPT_DIR",
    "SYSTEM_PROMPT_FILE",
    "USER_PROMPT_FILE",
    "load_system_prompt",
    "render_user_prompt",
    "generate_recommendation_set",
]

OWNER_ID = "R-1"
STEP_IDS = ("S-R11",)
CONNECTOR_ID = "C-2"

PROMPT_DIR = Path(__file__).with_name("prompts")
SYSTEM_PROMPT_FILE = PROMPT_DIR / "r1_recommendation_system.md"
USER_PROMPT_FILE = PROMPT_DIR / "r1_recommendation_user.md"

# ④ 5-1절 `K-6` 키 10개. 이름을 줄이거나 바꾸지 않음.
K6_KEYS = (
    "context_tags",
    "region_label",
    "weekday",
    "time_slot",
    "weather_temp_c",
    "recent_menu_names",
    "preference_vector",
    "candidate_places",
    "excluded_ingredient_codes",
    "correlation_key",
)
_K6_OPTIONAL = frozenset({"weather_temp_c", "recent_menu_names"})

# 바깥에서 온 문자열을 유저 프롬프트에 끼워 넣을 때 감싸는 자리 이름.
_EXTERNAL_SLOTS = {
    "candidate_places": "kakao_map",
    "recent_menu_names": "meal_history",
    "context_tags": "context_tags",
}


@functools.lru_cache(maxsize=1)
def load_system_prompt() -> str:
    """시스템 프롬프트를 파일에서 읽음. 코드 안에 문장을 두지 않음."""
    return SYSTEM_PROMPT_FILE.read_text(encoding="utf-8")


@functools.lru_cache(maxsize=1)
def _user_prompt_template() -> str:
    return USER_PROMPT_FILE.read_text(encoding="utf-8")


def render_user_prompt(payload: Mapping[str, Any]) -> str:
    """유저 프롬프트를 파일 틀에 채움. 바깥에서 온 문자열은 **태그로 감싸** 지시문과 가름."""
    filled: dict[str, str] = {}
    for key in K6_KEYS:
        value = payload.get(key)
        text = "(없음)" if value is None else json.dumps(value, ensure_ascii=False)
        slot = _EXTERNAL_SLOTS.get(key)
        filled[key] = wrap_external_text(slot, text) if slot else text
    return _user_prompt_template().format(**filled)


def _validate_k6(payload: Mapping[str, Any]) -> dict[str, Any]:
    """④ 「접근 가능한 정보 항목」에 없는 값은 모델에 넘기지 않음 — 칸 자체를 만들지 않음."""
    missing = [
        key for key in K6_KEYS if key not in _K6_OPTIONAL and payload.get(key) is None
    ]
    if missing:
        raise ValueError(f"`K-6` 필수 키가 비어 있음: {missing}")
    return {key: payload.get(key) for key in K6_KEYS}


def excluded_overlap(
    candidate_places: list[Mapping[str, Any]],
    excluded_ingredient_codes: list[str],
) -> tuple[str, ...]:
    """④ 3-1절 중단 조건 ⓐ — 제외 코드와 겹치는 후보가 남았는지 봄(⑥ `B-1` 신호)."""
    if not excluded_ingredient_codes:
        return ()
    banned = set(excluded_ingredient_codes)
    hits: list[str] = []
    for place in candidate_places or ():
        codes = set(place.get("ingredient_codes", ()) or ())
        if codes & banned:
            hits.append(str(place.get("place_id", "")))
    return tuple(hits)


async def generate_recommendation_set(
    *,
    context_tags: list[str],
    region_label: str,
    weekday: str,
    time_slot: str,
    preference_vector: list[float],
    candidate_places: list[Mapping[str, Any]],
    excluded_ingredient_codes: list[str],
    correlation_key: str,
    weather_temp_c: float | None = None,
    recent_menu_names: list[str] | None = None,
    tool: ConnectorTool,
    call_context: CallContext,
) -> ConnectorResult:
    """④ `K-6`을 받아 `K-7`을 냄. 모델 호출은 `C-2` 커넥터 1곳으로만 나감.

    재시도를 여기서 걸지 않음 — 커넥터 계층이 ③ 4-1절 `S-R11`의 조건부 1회를 이미 가짐.
    """
    payload = _validate_k6(
        {
            "context_tags": context_tags,
            "region_label": region_label,
            "weekday": weekday,
            "time_slot": time_slot,
            "weather_temp_c": weather_temp_c,
            "recent_menu_names": recent_menu_names,
            "preference_vector": preference_vector,
            "candidate_places": candidate_places,
            "excluded_ingredient_codes": excluded_ingredient_codes,
            "correlation_key": correlation_key,
        }
    )
    return await tool.call(payload, call_context)
