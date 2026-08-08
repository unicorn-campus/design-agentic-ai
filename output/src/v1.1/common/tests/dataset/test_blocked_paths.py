"""반드시 넣을 시험 6 — ⑤가 `경로 불가`로 적은 경로의 접속 코드가 없음."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from common.dataset.paths import PATHS

DATASET_ROOT = Path(__file__).resolve().parents[2] / "dataset"

# ⑤ 8절 「원천 오류율」이 `경로 불가`로 적은 6건.
BLOCKED_ROWS: dict[str, tuple[str, ...]] = {
    "E-4": ("food_tag_master", "카테고리 마스터 원천"),
    "E-6": ("restaurant_ingredient", "menu_ingredient", "알레르겐 판정 원천"),
    "E-8": ("representative_menu", "menu_price", "대표 메뉴 가격 원천"),
    "E-10": ("business_status_api", "mfds", "식약처"),
    "E-12": ("pg_recurring", "payment_gateway", "결제 게이트웨이 호출"),
}

# 이 모듈이 커넥터를 만들지 않았음을 확인하는 낱말. 커넥터는 도구 연동 프롬프트 몫임.
CONNECTOR_WORDS = ("httpx", "requests.get", "requests.post", "aiohttp", "urlopen")


@pytest.mark.parametrize("row", sorted(BLOCKED_ROWS))
def test_no_access_code_for_a_blocked_source(row: str) -> None:
    """시험 6 — 경로 불가로 적힌 원천에 붙는 코드가 소스에 0건임."""
    pattern = re.compile("|".join(re.escape(name) for name in BLOCKED_ROWS[row]), re.IGNORECASE)
    hits: list[str] = []
    for path in DATASET_ROOT.rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        hits.extend(f"{path.name}:{found}" for found in pattern.findall(path.read_text("utf-8")))
    assert not hits, f"{row}는 경로 불가인데 붙는 코드가 있음: {hits}"


def test_blocked_sources_are_absent_from_the_path_table() -> None:
    """경로 표 18행은 전부 우리 내부 저장소임. 경로 불가 원천이 섞이지 않았음."""
    storages = {spec.storage_id for spec in PATHS.values()}
    assert storages <= {"S-1", "S-3", "S-4", "S-5", "S-7"}


@pytest.mark.parametrize("word", CONNECTOR_WORDS)
def test_no_outside_call_in_this_module(word: str) -> None:
    """바깥 시스템을 부르는 코드가 없음 — 커넥터는 다른 프롬프트 몫임."""
    hits = [
        path.name
        for path in DATASET_ROOT.rglob("*.py")
        if "__pycache__" not in path.parts and word in path.read_text("utf-8")
    ]
    assert not hits, f"{word}가 {hits}에 있음"


def test_no_index_or_search_code_in_this_module() -> None:
    """색인 · 검색기 · 재정렬을 여기서 만들지 않았음."""
    banned = ("cosine_similarity", "top_k", "rerank", "build_index", "embed(")
    hits: list[str] = []
    for path in DATASET_ROOT.rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        text = path.read_text("utf-8")
        hits.extend(f"{path.name}:{word}" for word in banned if word in text)
    assert not hits, f"검색 쪽 코드가 섞여 있음: {hits}"
