"""동등성 평가 채점·변환 캐시 준비 시험."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import eval_equivalence as evaluation


def test_build_transform_cache_converts_saved_decision(tmp_path: Path):
    source = tmp_path / "source.json"
    output = tmp_path / "cache.json"
    source.write_text(
        json.dumps(
            {
                "rows": [
                    {
                        "question": "원 질문",
                        "route_action": "transform",
                        "technique": "rewrite",
                        "transformed_queries": ["변환 질문"],
                        "route_reason": "검색어 명확화",
                        "clarification": "",
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    cache = evaluation.build_transform_cache(source, output)
    assert cache["원 질문"]["action"] == "transform"
    assert cache["원 질문"]["queries"] == ["변환 질문"]
    assert json.loads(output.read_text(encoding="utf-8")) == cache


def test_make_row_and_summarize_apply_missing_rank_penalty():
    def hit(chunk_id: str):
        return SimpleNamespace(
            chunk_id=chunk_id,
            score=0.8,
            vector_score=0.8,
            rerank_score=None,
            source="source.pdf",
            location="제10조",
        )

    route = SimpleNamespace(
        technique=None,
        transformed_queries=[],
        model_dump=lambda **_kwargs: {},
    )
    result = SimpleNamespace(
        hits=[hit("A")],
        route=route,
        timings={},
        llm_calls=0,
        status="prompt_only",
    )
    row = evaluation.make_row(
        {"id": "q", "question": "질문", "expected_chunk_ids": ["A", "B"]},
        result,
        10.0,
    )
    summary = evaluation.summarize([row], baseline_passed=1, baseline_rank=3.5)
    assert row["ranks"] == {"A": 1, "B": None}
    assert summary["mean_expected_chunk_rank"] == 3.5
    assert summary["passed_count"] == 0
    assert summary["meets_baseline"] is False
