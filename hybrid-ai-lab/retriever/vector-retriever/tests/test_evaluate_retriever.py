"""평가 스크립트의 버전 실험용 인자 시험 — 인자 없이 돌리면 지금과 같은 @5 값이 나오는지, k가 분모를 바꾸는지."""

from __future__ import annotations

import pytest

import evaluate_retriever as er

QUESTION = {"id": "Q01", "answerable": True,
            "relevance": [{"source": "D1.pdf", "location": "제10조", "any_of": ["정답 문장"]},
                          {"source": "D1.pdf", "location": "제11조", "any_of": ["둘째 근거"]}]}
HITS = [("D1.pdf", "무관", None), ("D1.pdf", "정답 문장 포함", None), ("D1.pdf", "무관", None),
        ("D1.pdf", "무관", None), ("D1.pdf", "무관", None), ("D1.pdf", "둘째 근거", None)]


def test_default_k_is_five_as_before():
    assert er.score_hits(QUESTION, HITS) == er.score_hits(QUESTION, HITS, 5)
    assert er.score_hits(QUESTION, HITS)["precision"] == 1 / 5


def test_k_changes_cut_and_denominator():
    at3 = er.score_hits(QUESTION, HITS[:3], 3)
    at10 = er.score_hits(QUESTION, HITS, 10)
    assert at3["precision"] == 1 / 3 and at3["recall"] == 0.5
    assert at10["recall"] == 1.0 and at10["precision"] == 2 / 10  # 6위 근거까지 찾지만 분모가 커짐
    # 조각이 3개뿐이어도 @5의 분모는 5 — 5칸을 쓸 수 있는데 덜 채운 것도 정밀도에 반영함
    assert er.score_hits(QUESTION, HITS[:3], 5)["precision"] == 1 / 5


def test_no_answer_question_has_no_metrics():
    assert set(er.score_hits({"answerable": False}, HITS, 3).values()) == {None}


@pytest.mark.parametrize("argv", [["--top-k", "11"], ["--metric-k", "0"], ["--fixed-k", "12"]])
def test_out_of_range_k_is_rejected_before_service_assembly(argv):
    with pytest.raises(SystemExit) as error:
        er.main(argv)
    assert error.value.code == 2
