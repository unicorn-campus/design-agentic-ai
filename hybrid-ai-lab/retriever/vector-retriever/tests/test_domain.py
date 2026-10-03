"""domain 규칙(권한·시간 예산·점수 합치기·채점·인용 대조·행동·변환·분석 규칙)이 설계값대로 동작함을 보증함."""

from __future__ import annotations

import pytest

from app.domain import access, actions, budget, fusion, grading, keywords, plan_rules, transform_rules
from app.domain.models import Candidate, Chunk, SourceInfo, SubQuestion
from app.domain.verification import AnswerSentence, Citation, verify_answer


def _candidate(cid: str, rerank: float | None, card_id: str | None = None) -> Candidate:
    """채점 시험용 후보 1건을 만듦."""

    chunk = Chunk(cid, f"본문 {cid}", f"본문 {cid}", "public", SourceInfo(source="D2.pdf", card_id=card_id))
    return Candidate(chunk, 0.5, 1.0, 0.5, rerank)


# ---------------------------------------------------------------- 권한


def test_role_maps_to_access_levels():
    assert access.access_levels_for("agent") == ("public",)
    assert access.access_levels_for("AUDITOR") == ("public", "restricted")


@pytest.mark.parametrize("role", [None, "", "admin"])
def test_unknown_role_is_rejected(role):
    with pytest.raises(ValueError):
        access.access_levels_for(role)


# ---------------------------------------------------------------- 시간 예산(⑥-10)


def test_remaining_budget_matches_design_example():
    """설계 계산 예: S-R3 진입, 사용 12초, 답변 켬 → 11.3초."""

    value = budget.remaining_budget(budget.BudgetPolicy(), elapsed_seconds=12, step_id="S-R3", generate_answer=True)
    assert value == pytest.approx(11.3)


def test_answer_off_excludes_c04_and_s_r9_always_starts():
    policy = budget.BudgetPolicy()
    on = budget.remaining_budget(policy, elapsed_seconds=0, step_id="S-R2", generate_answer=True)
    off = budget.remaining_budget(policy, elapsed_seconds=0, step_id="S-R2", generate_answer=False)
    assert off - on == pytest.approx(2.5)
    assert budget.can_start(policy, elapsed_seconds=999, step_id="S-R9", generate_answer=True)


def test_can_start_threshold_is_inclusive():
    policy = budget.BudgetPolicy()
    # S-R7 남은 연동 C-04 2.5초: 30 − x − 1.5 − 2.5 ≥ 1.5 → x ≤ 24.5
    assert budget.can_start(policy, elapsed_seconds=24.5, step_id="S-R7", generate_answer=True)
    assert not budget.can_start(policy, elapsed_seconds=24.6, step_id="S-R7", generate_answer=True)


def test_default_limits_follow_design_body():
    policy = budget.BudgetPolicy()
    assert (policy.max_turns, policy.max_llm_calls, policy.max_rewrites) == (6, 16, 2)
    worst = policy.connector_worst_seconds
    assert worst["C-01"] + 6 * worst["C-02"] + 6 * worst["C-03"] + 3 * worst["C-04"] == pytest.approx(26.2)


# ---------------------------------------------------------------- 점수 합치기(⑥-6)


def test_weighted_hybrid_normalizes_each_retriever():
    fused = fusion.weighted_hybrid({"a": 0.9, "b": 0.5}, {"b": 20.0, "c": 10.0}, vector_weight=0.6, keyword_weight=0.4)
    assert fused["a"] == pytest.approx(0.6)  # 벡터 1위, BM25 없음
    assert fused["b"] == pytest.approx(0.4)  # 벡터 꼴찌(0), BM25 1위
    assert fused["c"] == pytest.approx(0.0)


def test_min_max_single_value_does_not_divide_by_zero():
    assert fusion.min_max_normalize({"a": 3.0}) == {"a": 1.0}
    assert fusion.min_max_normalize({}) == {}


def test_rrf_and_equal_weight_merge():
    rrf = fusion.rrf_merge([["a", "b"], ["b", "c"]])
    assert fusion.rank_keys(rrf)[0] == "b"
    merged = fusion.equal_weight_merge([{"a": 1.0}, {"a": 0.5, "b": 1.0}])
    assert merged == {"a": pytest.approx(0.75), "b": pytest.approx(0.5)}


def test_rank_keys_breaks_ties_by_secondary_then_id():
    assert fusion.rank_keys({"b": 1.0, "a": 1.0}) == ["a", "b"]
    assert fusion.rank_keys({"b": 1.0, "a": 1.0}, ({"b": 0.9, "a": 0.1},)) == ["b", "a"]


# ---------------------------------------------------------------- 채점(⑥-8)


def _signals(cands, *, kw=("한빛모아생활",), terms=("한빛모아생활",), vec=("a",), bm=("a",)):
    return grading.build_signals(cands, keywords=kw, result_terms=set(terms), vector_top_ids=list(vec),
                                 keyword_top_ids=list(bm), top_k=5, thresholds=grading.GradeThresholds())


def test_grade_correct_requires_all_conditions():
    th = grading.GradeThresholds()
    good = _signals([_candidate("a", 0.9), _candidate("b", 0.5)])
    assert grading.grade(good, th) == "correct"
    assert good.score_band == "high" and good.gap == pytest.approx(0.4)


@pytest.mark.parametrize(
    "case",
    ["keyword_missing", "small_gap", "no_overlap", "middle_score", "rerank_failed"],
)
def test_grade_uncertain_cases(case):
    th = grading.GradeThresholds()
    cands = [_candidate("a", 0.9), _candidate("b", 0.5)]
    kwargs = {}
    if case == "keyword_missing":
        kwargs["terms"] = ()
    elif case == "small_gap":
        cands = [_candidate("a", 0.9), _candidate("b", 0.88)]
    elif case == "no_overlap":
        kwargs["bm"] = ("z",)
    elif case == "middle_score":
        cands = [_candidate("a", 0.5)]
    else:
        cands = [_candidate("a", None), _candidate("b", None)]
    assert grading.grade(_signals(cands, **kwargs), th) == "uncertain"


def test_grade_incorrect_on_empty_or_low_score():
    th = grading.GradeThresholds()
    assert grading.grade(_signals([]), th) == "incorrect"
    assert grading.grade(_signals([_candidate("a", 0.2)]), th) == "incorrect"


def test_rare_terms_keep_low_document_frequency_and_unknown_words():
    picked = keywords.select_rare_terms({"카드": 150, "한빛모아생활": 4, "d2-c999": 0}, num_docs=218, max_df_ratio=0.1)
    assert picked == ("한빛모아생활", "d2-c999")


# ---------------------------------------------------------------- 인용 대조(⑥-9)


def test_verify_answer_passes_exact_quote_only():
    texts = {"c1": "연회비는 전월 실적 30만원 이상이면 면제됨."}
    ok = [AnswerSentence("면제 기준은 30만원임", (Citation("c1", "전월 실적 30만원 이상"),))]
    assert verify_answer(ok, texts) == []
    bad = [
        AnswerSentence("요약 인용", (Citation("c1", "전월실적 30만원 이상"),)),  # 띄어쓰기 수정
        AnswerSentence("없는 조각", (Citation("c9", "연회비"),)),
        AnswerSentence("인용 없음", ()),
    ]
    assert len(verify_answer(bad, texts)) == 3
    assert verify_answer([], texts) == ["답변 문장이 하나도 없습니다."]


# ---------------------------------------------------------------- 행동 선택(S-R3)


def test_allowed_actions_and_validation():
    subs = [SubQuestion("q1", "가", "decomposed"),
            SubQuestion("q2", "나", "decomposed", status="uncertain")]
    assert actions.allowed_actions(subs) == ["search_docs", "transform_query", "finish"]
    assert actions.validate_choice(subs, action="search_docs", target_qid="q2", reason="") is None
    assert actions.validate_choice(subs, action="transform_query", target_qid="q2", reason="").target_qid == "q2"
    assert actions.validate_choice(subs, action="web_search", target_qid="q1", reason="") is None
    assert actions.default_action(subs, "x").action == "search_docs"
    done = [SubQuestion("q0", "가", "original", status="satisfied")]
    assert actions.allowed_actions(done) == ["finish"]
    assert actions.default_action(done, "x").action == "finish"


# ---------------------------------------------------------------- 질문 변환 금지 규칙(⑥-3)


def _tokens(text: str) -> list[str]:
    """날짜 표기 통일을 흉내 낸 가짜 분석기."""

    return text.replace("2026년 2월", "2026-02").split()


def _apply(**overrides):
    params = dict(technique="rewrite", queries=["모아생활 연회비 면제 조건"], include_original=False,
                  clarify_question="", reason="r", target_question="모아생활 연회비", previous_queries=[],
                  tokens_of=_tokens, forced_clarify=None)
    params.update(overrides)
    return transform_rules.apply_transform_rules(**params)


def test_transform_rules():
    assert _apply().technique == "rewrite"
    assert _apply(technique="web").technique == "keep"
    assert _apply(queries=["모아생활 연회비"]).technique == "keep"  # 같은 질의 반복
    date_only = _apply(target_question="2026년 2월 혜택", queries=["2026-02 혜택"])
    assert date_only.technique == "keep"  # 날짜 표기만 바꿈
    assert _apply(technique="hyde", include_original=False).include_original is True
    assert _apply(forced_clarify="어느 카드인가요?").technique == "clarify"
    assert _apply(technique="clarify", clarify_question="").technique == "keep"
    assert len(_apply(technique="multi", queries=["a", "b", "c", "d"]).queries) == 3


def test_mixed_target_clarify():
    assert transform_rules.mixed_target_clarify(question_has_target=False, result_card_ids=["C1", "C2"],
                                                result_card_names=["가", "나"])
    assert transform_rules.mixed_target_clarify(question_has_target=True, result_card_ids=["C1", "C2"],
                                                result_card_names=[]) is None
    assert transform_rules.mixed_target_clarify(question_has_target=False, result_card_ids=["C1", "C1", ""],
                                                result_card_names=[]) is None
    # 1위가 약관처럼 카드 없는 조각이면 카드 질문이 아니므로 뒤에 카드가 섞여도 되묻지 않음(평가셋 E12)
    assert transform_rules.mixed_target_clarify(question_has_target=False, result_card_ids=["", "C1", "C2"],
                                                result_card_names=["", "가", "나"]) is None
    assert transform_rules.mixed_target_clarify(question_has_target=False, result_card_ids=[],
                                                result_card_names=[]) is None


# ---------------------------------------------------------------- 질문 분석 규칙(S-R2)


def _conditions(text: str) -> set[str]:
    return {word for word in text.split() if any(ch.isdigit() for ch in word) or word.startswith("모아")}


def _plan(**overrides):
    params = dict(question="모아생활 연회비와 30만원 실적", question_type="complex",
                  sub_questions=["모아생활 연회비", "모아생활 30만원 실적"], chitchat_reply="",
                  max_sub_questions=3, condition_terms_of=_conditions)
    params.update(overrides)
    return plan_rules.apply_plan_rules(**params)


def test_plan_rules():
    assert _plan().question_type == "complex"
    assert _plan(sub_questions=["모아생활 연회비", "모아생활 50만원 실적"]).question_type == "simple"  # 새 조건
    assert _plan(sub_questions=["모아생활 연회비", "30만원 실적"]).question_type == "complex"  # 조건은 합집합으로 보존
    assert _plan(sub_questions=["연회비", "실적"]).question_type == "simple"  # 30만원·모아생활 누락
    four = _plan(question="a b c d", sub_questions=["a", "b", "c", "d"])
    assert len(four.sub_question_texts) == 3 and four.warnings
    assert _plan(question_type="chitchat", chitchat_reply="안녕하세요").chitchat_reply == "안녕하세요"
    assert _plan(question_type="chitchat", chitchat_reply=" ").question_type == "simple"
    assert _plan(question_type="other").question_type == "simple"
