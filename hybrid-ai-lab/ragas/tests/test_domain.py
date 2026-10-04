"""domain 규칙 시험 — 평가셋 변환 · 검증 · 계획 검사 · 채점 집계 · 비교 판정."""

from __future__ import annotations

import pytest

from app.domain.comparison import direction_match, judge_code, judge_ragas
from app.domain.eval_set import EvalSetFormatError, eval_set_hash, parse_eval_set_markdown
from app.domain.plan import check_plan, leaf_differences, ordered_versions, parse_target, set_json_path
from app.domain.scoring import agreement, describe, split_rows, to_ragas_row
from app.domain.text import normalize, numbers_in
from app.domain.verification import Chunk, check_against_index, check_structure

SAMPLE_MD = """# 평가셋

| 번호 | 질문 |
|---|---|
| Q01 | 표 줄은 건너뜀 |

### Q01. 연회비 면제 기준은?

- **정답**: 직전 12개월 이용금액이 3,000,000원 이상이면 면제합니다.
- **근거**: D1 개인회원 약관 `D1_약관.pdf` · 제10조①
  - 「직전 12개월 이용금액이 3,000,000원 이상」
- **사람 검토 메모**:
  - 이 불릿은 근거가 아님

### Q02. 상담 변화는?

- **정답**: 처음엔 비교, 나중엔 확인 단계였습니다.
- **근거**: D3 상담 이력 `D3_S02.txt` · M-1042(장기 보유) · C-001
  - 「비교해 주세요」
- **근거**: D3 상담 이력 `D3_S02.txt` · M-1042(장기 보유) · C-003
  - 「확인부터 하려는 거예요」
  - 「아직 신청 안 했어요」
- **filters**: `[{"member_pseudo_id": "m_1"}]`

### Q03. 포인트로 연회비를 낼 수 있나요?

- **정답**: 확인 필요(문서에 답이 없음)
- **답이 없음을 확인한 기준**: 아래 낱말 묶음을 모두 담은 색인 조각이 없음
  - 연회비 + 포인트로 납부
"""


def parsed() -> list[dict]:
    return parse_eval_set_markdown(SAMPLE_MD)


def test_markdown_becomes_questions_with_units_filters_and_no_answer_terms():
    """근거 줄 1개 = 근거 단위 1개, 위치는 마지막 ' · ' 뒤 조각, 답 없음은 낱말 묶음으로 바뀜."""

    q1, q2, q3 = parsed()
    assert q1["relevance"] == [{"source": "D1_약관.pdf", "location": "제10조①",
                                "any_of": ["직전 12개월 이용금액이 3,000,000원 이상"]}]
    assert [u["location"] for u in q2["relevance"]] == ["C-001", "C-003"]
    assert q2["relevance"][1]["any_of"] == ["확인부터 하려는 거예요", "아직 신청 안 했어요"]
    assert q2["filters"] == [{"member_pseudo_id": "m_1"}]
    assert q3["answerable"] is False and q3["ground_truth"] == "확인 필요" and q3["relevance"] == []
    assert q3["no_answer_terms"] == [["연회비", "포인트로 납부"]]


def test_question_without_answer_line_is_rejected():
    with pytest.raises(EvalSetFormatError):
        parse_eval_set_markdown("### Q01. 질문만 있음\n")


def test_eval_set_hash_is_stable_and_sensitive_to_content():
    questions = parsed()
    assert eval_set_hash(questions) == eval_set_hash(parse_eval_set_markdown(SAMPLE_MD))
    questions[0]["ground_truth"] += "!"
    assert eval_set_hash(questions) != eval_set_hash(parsed())
    assert len(eval_set_hash(questions)) == 12


def test_normalize_and_numbers():
    assert normalize("직전 12개월\n이용") == "직전12개월이용"
    assert numbers_in("3,000,000원 · 1.2%를 적립함.") == ["3000000", "1.2"]


CHUNKS = [
    Chunk("c1", "D1_약관.pdf", "제10조① 직전 12개월 이용금액이 3,000,000원 이상이고 연체가 없으면"),
    Chunk("c2", "D3_S02.txt", "C-001 비교해 주세요"),
    Chunk("c3", "D3_S02.txt", "C-003 확인부터 하려는 거예요. 아직 신청 안 했어요"),
    Chunk("d1", "D2_혜택.pdf", "D2-C001-B01 | 생활 포인트\n대상 결제액의 1.2%를 적립함.\nD2-C001-B02 | 재충전\n700P를 리필함"),
]


def test_index_checks_pass_for_matching_corpus():
    assert check_against_index(parsed(), CHUNKS) == []
    assert check_structure(parsed()) == []


def test_index_checks_catch_missing_fragment_wrong_block_number_and_no_answer_leak():
    questions = parsed()
    questions[0]["relevance"][0]["any_of"] = ["없는 문장"]
    questions[1]["ground_truth"] = "45일 이내"  # 근거 조각에 없는 숫자
    questions.append({"id": "Q04", "question": "리필?", "answerable": True, "ground_truth": "1.2%",
                      "filters": [], "relevance": [{"source": "D2_혜택.pdf", "location": "D2-C001-B02",
                                                    "any_of": ["대상 결제액의 1.2%를 적립함"]}]})
    leak = [*CHUNKS, Chunk("x", "D1_약관.pdf", "연회비는 포인트로 납부 가능")]
    checks = sorted({issue.check for issue in check_against_index(questions, leak)})
    assert checks == [1, 2, 3, 4]


def test_structure_check_catches_duplicate_id_and_answerable_without_evidence():
    questions = parsed()
    questions[1]["id"] = "Q01"
    questions[2]["answerable"] = True
    reasons = [issue.reason for issue in check_structure(questions)]
    assert "id가 겹침" in reasons and "답 있음 문항인데 근거가 없음" in reasons


def plan(**changes) -> dict:
    base = {"hyperparameter": "chunk_size", "apply": "config_file", "reindex": True,
            "target": "indexer:config:config/document_policies.json#defaults.chunk_size", "baseline": 800,
            "versions": [{"id": "800", "value": 800}, {"id": "600", "value": 600}]}
    return {**base, **changes}


def test_valid_plan_has_no_rejects():
    assert check_plan(plan()) == ([], [])


@pytest.mark.parametrize("changes, code", [
    ({"versions": [{"id": "800", "value": 800}, {"id": "900", "value": 900}]}, "V10"),
    ({"baseline": 700}, "V2"),
    ({"versions": [{"id": "800", "value": 800}, {"id": "800", "value": 600}]}, "V3"),
    ({"apply": "env"}, "V4"),
    ({"target": "잘못된 주소"}, "V4"),
])
def test_plan_rejects(changes, code):
    rejects, _ = check_plan(plan(**changes))
    assert any(r.startswith(code) for r in rejects)


def test_top_k_range_and_unsupported_targets():
    top_k = {"hyperparameter": "top_k", "apply": "code_arg", "reindex": False, "target": "retriever:arg:--top-k",
             "baseline": 5, "versions": [{"id": "5", "value": 5}, {"id": "11", "value": 11}]}
    assert any(r.startswith("V10") for r in check_plan(top_k)[0])
    _, unsupported = check_plan(plan(target="indexer:config:config/document_policies.json#documents.D1.chunk_size"))
    assert unsupported and unsupported[0].startswith("V7-1")
    _, unsupported = check_plan({**top_k, "apply": "code_arg", "target": "retriever:code:steps.py#rrf_k",
                                 "versions": [{"id": "5", "value": 5}]})
    assert unsupported and unsupported[0].startswith("V9")


def test_baseline_runs_first_and_only_keeps_baseline():
    versions = ordered_versions({"baseline": 5, "versions": [{"id": "3", "value": 3}, {"id": "5", "value": 5},
                                                            {"id": "10", "value": 10}]}, only=["3"])
    assert [v["id"] for v in versions] == ["5", "3"]


def test_json_path_change_differs_in_one_place_and_unknown_key_fails():
    original = {"defaults": {"chunk_size": 800, "chunk_overlap": 200}, "documents": {}}
    changed = set_json_path(original, "defaults.chunk_size", 600)
    assert original["defaults"]["chunk_size"] == 800
    assert leaf_differences(original, changed) == ["defaults.chunk_size"]
    with pytest.raises(KeyError):
        set_json_path(original, "defaults.new_key", 1)
    assert parse_target("retriever:arg:--top-k").key == "--top-k"


def retriever_row(**changes) -> dict:
    row = {"id": "Q01", "question": "질문", "answerable": True, "status": "answered",
           "evidence": [{"text": "근거"}], "answer": ["답", "변"], "ground_truth": "정답"}
    return {**row, **changes}


def test_split_rows_reasons_in_order():
    rows = [retriever_row(), retriever_row(id="Q02", answerable=False), retriever_row(id="Q03", status="needs_confirmation"),
            retriever_row(id="Q04", evidence=[]), retriever_row(id="Q05", answer=[])]
    eligible, excluded = split_rows(rows)
    assert [r["id"] for r in eligible] == ["Q01"]
    assert [e["reason"] for e in excluded] == ["no_answer_question", "status_not_answered", "empty_evidence",
                                               "empty_response"]
    assert to_ragas_row(rows[0]) == {"user_input": "질문", "retrieved_contexts": ["근거"], "response": "답 변",
                                     "reference": "정답"}


def test_describe_handles_one_and_zero_values():
    assert describe([0.5])["std"] is None
    assert describe([])["n"] == 0
    assert describe([0.78, 0.81, 0.79])["max"] == 0.81


def test_agreement_matches_textbook_example():
    """교재 예시(TP 12 · FP 4 · FN 1 · TN 3) — 일치율 0.75 · F1 0.83 · kappa 0.39."""

    pairs = [(0.9, True)] * 12 + [(0.9, False)] * 4 + [(0.1, True)] + [(0.1, False)] * 3
    result = agreement("faithfulness", pairs, 0.5)
    assert (result.tp, result.fp, result.fn, result.tn) == (12, 4, 1, 3)
    assert result.agreement == 0.75 and round(result.f1, 2) == 0.83 and round(result.kappa, 2) == 0.39


def test_comparison_judgements():
    assert judge_code(0.0) == "차이 없음" and judge_code(0.1) == "개선" and judge_code(None) == "—"
    assert judge_ragas(0.02, 0.03) == "차이 없음" and judge_ragas(-0.05, 0.03) == "악화"
    assert direction_match(0.1, -0.2).startswith("반대") and direction_match(0.1, 0.2) == "일치"


def test_structure_check_catches_member_pseudonym_mismatch():
    """filters의 회원번호와 가명이 어긋나면 ⑤ 구조 검사가 잡음(인덱서 값 M-1042 → m_59853c3d8e1e3c25)."""

    questions = parsed()
    questions[1]["filters"] = [{"member_id": "M-1042", "member_pseudo_id": "m_59853c3d8e1e3c25"}]
    assert check_structure(questions) == []
    questions[1]["filters"] = [{"member_id": "M-3001", "member_pseudo_id": "m_59853c3d8e1e3c25"}]
    assert any("가명" in issue.reason for issue in check_structure(questions))
