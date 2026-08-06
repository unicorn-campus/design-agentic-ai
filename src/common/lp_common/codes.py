"""K-5 용어사전(코드 매핑 표) — ⑤ 2절·4절 `용어사전·온톨로지` 채택 결과.

낱말을 코드값으로 1:1 고정함. 알레르기 판정을 확률에 맡기지 않는 이유는
① 4절 Q-3 `위반 0건`이 결정론 매칭만으로 달성 가능하기 때문임(⑤ 2절 K-5).

이 표가 `filter_ruleset_version`의 실체임. 표가 바뀌면 버전이 올라가고,
같은 입력에 다른 결과가 나온 사실이 추천 이력에 남음(⑤ 5절 신설 키 2종).
"""

from __future__ import annotations

# 사전 버전 — 표를 고치면 반드시 올림. A-1 출력 `filter_ruleset_version`으로 나감.
FILTER_RULESET_VERSION = "lex-2026.08.06-1"

# ── 음식 카테고리 코드 (② 3절 TB-2 통과 형태 `취향 카테고리 코드`) ────────────
CATEGORY_CODES: dict[str, str] = {
    "KOR-SOUP": "한식-국물",
    "KOR-RICE": "한식-밥",
    "KOR-MEAT": "한식-고기",
    "CHN-NOODLE": "중식-면",
    "CHN-RICE": "중식-밥",
    "JPN-SUSHI": "일식-초밥",
    "JPN-DON": "일식-덮밥",
    "JPN-RAMEN": "일식-라멘",
    "WST-PASTA": "양식-파스타",
    "WST-BURGER": "양식-버거",
    "ASN-CURRY": "아시안-커리",
    "ASN-PHO": "아시안-쌀국수",
    "SAL-BOWL": "샐러드-볼",
    "SNK-GIMBAP": "분식-김밥",
}

# ── 알레르기 항목명 ↔ 식재료 코드 매핑 (F-1을 코드로 고정) ───────────────────
# 좌변(항목명)은 회원이 고른 8대 알레르겐 + 식이 유형이고,
# 우변은 식당 캐시의 `allergen_codes` 에 실리는 원재료 코드 집합임.
ALLERGEN_NAME_TO_CODES: dict[str, frozenset[str]] = {
    "난류": frozenset({"ING-EGG"}),
    "우유": frozenset({"ING-MILK", "ING-CHEESE", "ING-BUTTER"}),
    "땅콩": frozenset({"ING-PEANUT"}),
    "호두": frozenset({"ING-WALNUT", "ING-NUT"}),
    "대두": frozenset({"ING-SOY", "ING-TOFU"}),
    "밀": frozenset({"ING-WHEAT", "ING-FLOUR"}),
    "고등어": frozenset({"ING-MACKEREL", "ING-FISH"}),
    "게": frozenset({"ING-CRAB", "ING-SHELLFISH"}),
    "새우": frozenset({"ING-SHRIMP", "ING-SHELLFISH"}),
    "돼지고기": frozenset({"ING-PORK"}),
    "쇠고기": frozenset({"ING-BEEF"}),
}

# 식이 유형(비건·채식·할랄)이 막는 식재료 코드 — `US:UFR-MBR-040`
DIET_TYPE_TO_CODES: dict[str, frozenset[str]] = {
    "비건": frozenset(
        {
            "ING-BEEF",
            "ING-PORK",
            "ING-CHICKEN",
            "ING-FISH",
            "ING-MACKEREL",
            "ING-SHRIMP",
            "ING-CRAB",
            "ING-SHELLFISH",
            "ING-EGG",
            "ING-MILK",
            "ING-CHEESE",
            "ING-BUTTER",
        }
    ),
    "채식": frozenset(
        {
            "ING-BEEF",
            "ING-PORK",
            "ING-CHICKEN",
            "ING-FISH",
            "ING-MACKEREL",
            "ING-SHRIMP",
            "ING-CRAB",
            "ING-SHELLFISH",
        }
    ),
    "할랄": frozenset({"ING-PORK", "ING-ALCOHOL"}),
}

# ⑥ 8절 L-2 라벨 목록 — 출력측 노출 검사 대상 문자열
ALLERGEN_LABELS: tuple[str, ...] = tuple(ALLERGEN_NAME_TO_CODES) + tuple(DIET_TYPE_TO_CODES)


def _label_pattern() -> "re.Pattern[str]":
    """L-2 라벨을 **낱말 경계와 함께** 찾는 패턴을 만듦.

    단순 부분 문자열 대조는 한국어에서 오탐이 남 — `게`는 `있게`·`하게`에,
    `밀`은 `비밀`에 들어감. 실제로 실물 모델이 쓴 "든든하게"가 `게`로 걸려
    멀쩡한 근거 문장이 기본 문구로 교체되는 일이 관측됨(2026-08-06).

    오탐은 그냥 성가신 것이 아님 — ① Q-2 설명가능성을 깎음. 근거 문장이
    이유 없이 거리 문구로 바뀌면 "나를 위한 추천인지 알 수 없다"는 킹핀
    문제 P2로 되돌아감. 그래서 경계를 붙임:
      · 앞: 한글 음절이 바로 앞에 오면 다른 낱말임 → 매칭하지 않음
      · 뒤: 한글이 아니거나, 조사·서술 어미로 이어질 때만 낱말로 봄

    안전 쪽 기울기는 유지함 — 경계가 애매하면 **매칭하는 쪽**을 택함.
    """
    import re as _re

    # 뒤에 붙어도 같은 낱말로 보는 조사·어미·접미
    tail = r"(?:이|가|은|는|을|를|와|과|도|만|에|의|로|으로|랑|이랑|류|알레르기|알러지|프리|성분|함유|포함|없|있|무)"
    parts = []
    for label in sorted(ALLERGEN_LABELS, key=len, reverse=True):
        esc = _re.escape(label)
        parts.append(rf"(?<![가-힣]){esc}(?![가-힣])")          # 양쪽이 낱말 경계
        parts.append(rf"(?<![가-힣]){esc}(?={tail})")            # 뒤가 조사·어미
    return _re.compile("|".join(parts))


import re  # noqa: E402  (패턴 컴파일에만 씀)

ALLERGEN_LABEL_RE = _label_pattern()


def find_allergen_label(text: str) -> str | None:
    """문자열에 알레르겐 항목명이 **낱말로** 들어 있으면 그 낱말을 돌려줌."""
    match = ALLERGEN_LABEL_RE.search(text)
    return match.group(0) if match else None

# ── 날씨 코드 (C-3 출력 규격 `weather_code`) ──────────────────────────────────
WEATHER_CODES: tuple[str, ...] = ("CLEAR", "CLOUD", "RAIN", "SNOW", "HOT", "COLD")

# ── 요일·시간대 코드 (J-8 — `US:UFR-REC-020`의 `요일/시간`을 2개로 실음) ──────
WEEKDAY_CODES: tuple[str, ...] = ("MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN")
DAYPART_CODES: tuple[str, ...] = ("EARLY_LUNCH", "PEAK_LUNCH", "LATE_LUNCH", "OFF_HOURS")

# 직군 클러스터 코드 — `[확인필요: 직군 데이터 수집 경로]`(③ 8절)
# 원천이 없어 합성 데이터에서만 채움. 없으면 콜드스타트가 지역 인기로만 동작함.
JOB_CLUSTER_CODES: tuple[str, ...] = ("DEV", "SALES", "FINANCE", "DESIGN", "UNKNOWN")


def resolve_blocked_ingredients(
    allergen_names: list[str], diet_types: list[str]
) -> tuple[frozenset[str], list[str]]:
    """항목명·식이유형을 막을 식재료 코드 집합으로 고정함.

    Returns:
        (막을 식재료 코드 집합, 사전에 없어 해석 못 한 낱말 목록)

    사전에 없는 낱말은 **임의 매칭하지 않고** 미해석으로 돌려줌
    (⑥ M-Q8 · 골든셋 GS-24 `임의 매칭 0건`).
    """
    blocked: set[str] = set()
    unresolved: list[str] = []
    for name in allergen_names:
        codes = ALLERGEN_NAME_TO_CODES.get(name)
        if codes is None:
            unresolved.append(name)
        else:
            blocked |= codes
    for diet in diet_types:
        codes = DIET_TYPE_TO_CODES.get(diet)
        if codes is None:
            unresolved.append(diet)
        else:
            blocked |= codes
    return frozenset(blocked), unresolved


def daypart_of(hour: int) -> str:
    """시각을 시간대 코드로 고정함. 점심 11 ~ 13시가 서비스 구간임(① 4절 Q-1)."""
    if 11 <= hour < 12:
        return "EARLY_LUNCH"
    if 12 <= hour < 13:
        return "PEAK_LUNCH"
    if 13 <= hour < 14:
        return "LATE_LUNCH"
    return "OFF_HOURS"
