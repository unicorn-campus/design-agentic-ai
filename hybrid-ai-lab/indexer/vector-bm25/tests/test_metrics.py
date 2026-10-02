"""원문 근거 기반 검색 품질 지표의 경계 조건을 검증함."""

import importlib.util
from pathlib import Path

import pytest

path = Path(__file__).resolve().parents[1] / "evaluation" / "metrics.py"
spec = importlib.util.spec_from_file_location("metrics", path)
assert spec and spec.loader
metrics = importlib.util.module_from_spec(spec)
spec.loader.exec_module(metrics)


def test_overlap_does_not_inflate_evidence_recall():
    """중첩 청크가 같은 근거를 반복해도 근거 회수율이 부풀지 않음을 보증함."""
    question = {"id": "x", "answerable": True,
                "relevance": [{"source": "D1", "any_of": ["첫 근거"]},
                              {"source": "D1", "any_of": ["두번째 근거"]}]}
    hits = [{"source": "D1.pdf", "text": "첫\n근거"}] * 5
    result = metrics.score(question, hits)
    assert result["evidence_recall_at_5"] == 0.5
    assert result["mrr_at_5"] == 1


def test_no_answer_is_not_treated_as_failed_recall():
    """근거 없음 문항을 정답 근거 회수 실패의 분모에 포함하지 않음을 보증함."""
    result = metrics.score({"answerable": False, "relevance": []}, [{"text": "관련 없는 문서"}])
    assert result["hit_at_5"] is None
    assert result["returned_count"] == 1


def test_source_must_match_and_rank_is_measured():
    """본문이 같아도 출처가 다른 청크는 제외하고 첫 근거 순위를 계산함을 보증함."""
    question = {"answerable": True, "relevance": [{"source": "D1", "any_of": ["근거"]}]}
    result = metrics.score(question, [{"source": "D2", "text": "근거"}, {"source": "D1", "text": "근거"}])
    assert result["mrr_at_5"] == pytest.approx(0.5)
