from __future__ import annotations

import json
import stat
from pathlib import Path

import pytest

from app.application.state import RouteDecision
from app.infrastructure.transform_cache import TransformCache, TransformCacheError


def _decision(reason: str = "명확한 질문") -> RouteDecision:
    return RouteDecision(
        action="transform",
        technique="rewrite",
        queries=["공식 문서 표현 질문"],
        reason=reason,
        clarification="",
    )


def test_missing_cache_returns_none(tmp_path: Path) -> None:
    cache = TransformCache(tmp_path / "injected/cache.json")
    assert cache.get("질문") is None


def test_round_trip_and_overwrite_leave_no_temporary_file(tmp_path: Path) -> None:
    path = tmp_path / "custom/location/cache.json"
    cache = TransformCache(path)
    cache.put(" 질문 ", _decision())
    assert cache.get("질문") == _decision()

    changed = _decision("새 결정")
    cache.put("질문", changed)
    assert cache.get("질문") == changed
    assert list(path.parent.glob(f".{path.name}.*.tmp")) == []
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert json.loads(path.read_text(encoding="utf-8"))["질문"]["reason"] == "새 결정"


def test_multiple_questions_are_preserved(tmp_path: Path) -> None:
    cache = TransformCache(tmp_path / "cache.json")
    cache.put("첫 질문", _decision("첫째"))
    cache.put("둘째 질문", _decision("둘째"))
    assert cache.get("첫 질문").reason == "첫째"
    assert cache.get("둘째 질문").reason == "둘째"


@pytest.mark.parametrize("content", ["[]", "{broken"])
def test_corrupt_cache_fails_closed(tmp_path: Path, content: str) -> None:
    path = tmp_path / "cache.json"
    path.write_text(content, encoding="utf-8")
    with pytest.raises(TransformCacheError):
        TransformCache(path).get("질문")


def test_invalid_cached_decision_fails_closed(tmp_path: Path) -> None:
    path = tmp_path / "cache.json"
    path.write_text('{"질문": {"action": "unknown"}}', encoding="utf-8")
    with pytest.raises(TransformCacheError):
        TransformCache(path).get("질문")


def test_empty_query_is_rejected_before_file_access(tmp_path: Path) -> None:
    cache = TransformCache(tmp_path / "cache.json")
    with pytest.raises(ValueError):
        cache.get("  ")
