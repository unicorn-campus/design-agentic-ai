"""출처 · 재사용 · 합치기 규칙 시험.

- 결과에 출처가 빠진 건수 0건
- 데이터 준비 묶음의 읽기 함수를 **가져다 쓰는지**(다시 만들지 않았는지)
- 되묻기 3 — 경로가 여럿이면 합치지 않고 따로 돌려줌
- 되묻기 4 — 검색 결과를 잠시 저장하지 않음
"""

from __future__ import annotations

from pathlib import Path

import pytest

from common.config import Settings
from common.dataset import PATH_IDS
from common.dataset.readers import READ_FUNCTIONS
from common.knowledge import (
    Candidate,
    LOOKUP_FUNCTIONS,
    MissingProvenance,
    lookup,
    lookup_result_of,
    record_retrieval,
    retrieval_fields,
)

KNOWLEDGE_ROOT = Path(__file__).resolve().parents[2] / "knowledge"


def test_one_lookup_function_per_design_row() -> None:
    """⑤ 3절 18행 = 조회 함수 18개."""
    assert len(LOOKUP_FUNCTIONS) == len(PATH_IDS) == 18
    assert set(LOOKUP_FUNCTIONS) == set(PATH_IDS)


def test_lookup_functions_have_names_from_the_design_row() -> None:
    assert LOOKUP_FUNCTIONS["T-1"].__name__ == "lookup_t1"
    assert "⑤ 3절 T-1" in (LOOKUP_FUNCTIONS["T-1"].__doc__ or "")


def test_every_path_reuses_the_dataset_read_function() -> None:
    """읽기 함수를 다시 만들지 않았음 — 데이터 준비 묶음의 것과 짝임."""
    for path_id in PATH_IDS:
        assert lookup_result_of(path_id) is LOOKUP_FUNCTIONS[path_id]
        assert path_id in READ_FUNCTIONS


def test_knowledge_layer_has_no_source_connection_code() -> None:
    """원천에 붙는 코드를 이 묶음에 다시 만들지 않았음."""
    for path in sorted(KNOWLEDGE_ROOT.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        text = path.read_text(encoding="utf-8")
        assert "psycopg" not in text, f"{path.name}이 원천에 직접 붙음"


def test_every_candidate_carries_a_source(knowledge_settings: Settings, seed_reader) -> None:
    """결과에 출처가 빠진 건수 0건."""
    missing = 0
    for path_id, agent_id in (("T-1", "R-14"), ("T-5", "R-14"), ("T-9", "R-14")):
        result = lookup(path_id, agent_id, seed_reader, params={"member_id": "M000000"},
                        settings=knowledge_settings)
        for candidate in result.candidates:
            if candidate.source is None:  # pragma: no cover - 만들 수 없음
                missing += 1
            assert candidate.source.design_row
            assert candidate.source.origin
            assert candidate.source.locator
    assert missing == 0


def test_candidate_without_a_source_cannot_be_made() -> None:
    with pytest.raises(MissingProvenance):
        Candidate(payload={"member_id": "M000000"}, source=None)  # type: ignore[arg-type]


def test_results_of_two_routes_are_returned_separately(
    knowledge_settings: Settings, seed_reader
) -> None:
    """되묻기 3 — 경로별 결과를 합치는 함수가 0건임."""
    import common.knowledge as knowledge

    merge_like = [
        name
        for name in knowledge.__all__
        if any(word in name.lower() for word in ("merge", "fuse", "combine", "union"))
    ]
    assert merge_like == []
    assert knowledge_settings.knowledge_result_merge == "합치지 않고 경로별로 따로 돌려줌"

    first = lookup("T-1", "R-14", seed_reader, params={"member_id": "M000000"},
                   settings=knowledge_settings)
    second = lookup("T-9", "R-14", seed_reader, params={"member_id": "M000000"},
                    settings=knowledge_settings)
    assert first.route_id != second.route_id


def test_no_result_cache_is_kept(knowledge_settings: Settings) -> None:
    """되묻기 4 — 검색 결과를 잠시 저장하지 않음."""
    assert knowledge_settings.knowledge_result_cache_ttl_s is None
    import common.knowledge as knowledge

    cache_like = [name for name in knowledge.__all__ if "cache" in name.lower()]
    assert cache_like == []


def test_trace_fields_carry_sources_but_not_payloads(
    knowledge_settings: Settings, seed_reader
) -> None:
    """기록 자리에는 자리와 개수·사유만 넘기고 내용은 넘기지 않음."""
    result = lookup("T-1", "R-14", seed_reader, params={"member_id": "M000000"},
                    settings=knowledge_settings)
    fields = retrieval_fields(result)
    assert fields["candidate_count"] == result.candidate_count
    assert fields["sources"]
    assert "payload" not in fields
    assert "candidates" not in fields


def test_record_retrieval_uses_the_hook_seam(knowledge_settings: Settings, seed_reader) -> None:
    """실제 기록은 검사·기록 묶음이 끼움 — 여기서는 자리에 넘기기만 함."""
    seen: list[tuple[str, dict]] = []

    class Recorder:
        def record(self, step_id: str, fields: dict) -> None:
            seen.append((step_id, fields))

    class Hooks:
        recorder = Recorder()

    result = lookup("T-1", "R-14", seed_reader, params={"member_id": "M000000"},
                    settings=knowledge_settings)
    record_retrieval(Hooks(), "S-R4", result)  # type: ignore[arg-type]
    assert seen and seen[0][0] == "S-R4"
