"""상담 검색 회원 필터 시험 — 가명 계산이 인덱서와 같은지, 요청의 회원번호가 검색 조건으로만 쓰이는지."""

from __future__ import annotations

import pytest

from app.application.models import STATUS_ERROR, ActionOutput, SearchRequest
from app.domain.actions import ACTION_SEARCH
from app.domain.budget import C_04
from app.domain.member import consult_leads, member_allows, member_id_terms, member_pseudonym, validate_member_id
from app.domain.models import Candidate, Chunk, SourceInfo
from tests.fakes import FakeIndex, FakeLLM, FakeReranker, make_corpus
from tests.test_index_store import real_index  # noqa: F401 — 실제 세대 준비 fixture를 같이 씀
from tests.test_workflow import build, last_request_log

QUESTION = "상담 민원 접수 내용을 알려 주세요"
M1042 = "m_59853c3d8e1e3c25"  # 색인 메타데이터의 실제 값(인덱서 text_rules.pseudonym으로 만든 값, 2026-10-04 대조)
M3001 = "m_3cc2d20f17401234"


def test_가명_계산이_인덱서_색인_값과_같음():
    """두 프로그램의 계산이 어긋나면 필터가 오류 없이 빈 결과를 내므로 실제 색인 값으로 묶어 둠."""

    assert member_pseudonym("M-1042") == M1042
    assert member_pseudonym(" M-3001 ") == M3001


@pytest.mark.parametrize("bad", ["", "m-1042", "M1042", "M-10a2", "1042", None, 1042])
def test_회원번호_꼴이_아니면_거부(bad):
    with pytest.raises(ValueError):
        validate_member_id(bad)


def test_회원_범위_판정():
    assert member_allows(None, M1042)  # 회원 가명 없는 조각(약관 · 혜택)은 통과
    assert member_allows(M1042, M1042)
    assert not member_allows(M3001, M1042)  # 다른 회원 상담은 막음
    assert member_allows(M3001, None)  # 필터가 없으면 지금처럼 모두 통과


def member_corpus() -> dict[str, Chunk]:
    """기본 가짜 말뭉치에 회원 둘의 상담 조각을 더함."""

    corpus = make_corpus()
    for chunk_id, member in (("d3m1", M1042), ("d3m2", M3001)):
        corpus[chunk_id] = Chunk(chunk_id, f"상담 민원 접수 내용 {chunk_id} 임", f"상담 민원 접수 내용 {chunk_id} 임",
                                 "restricted", SourceInfo(source="consult.txt", doc_key="D3", doc_type="consult_log"),
                                 member_pseudo_id=member)
    return corpus


def harness(*, leaky: bool = False):
    corpus = member_corpus()
    hits = {QUESTION: [("d3m2", 0.95), ("d3m1", 0.9), ("d1c1", 0.4)]}
    index = FakeIndex(corpus=corpus, hits=hits, leaky=leaky)
    reranker = FakeReranker(corpus=corpus, scores={"d3m2": 0.95, "d3m1": 0.9, "d1c1": 0.4})
    llm = FakeLLM(action=[ActionOutput(ACTION_SEARCH, "q0", "")])  # 다음 행동으로 검색을 고르게 함
    return build(index=index, reranker=reranker, llm=llm)


def ask(h, member_id):
    return h.service.execute(SearchRequest(query=QUESTION, member_id=member_id), "auditor")


def test_회원번호가_가명으로_검색_조건에_실림_원번호는_로그에_없음():
    h = harness()
    response = ask(h, "M-1042")
    assert response.status != STATUS_ERROR
    assert set(h.index.member_filters) == {M1042}
    ids = [item.chunk_id for item in response.evidence]
    assert "d3m2" not in ids  # 다른 회원 상담은 검색기 안에서 빠짐
    log = last_request_log(h)
    assert log["member_pseudo_id"] == M1042
    assert "M-1042" not in str(log)  # 감사 로그에는 원래 회원번호를 남기지 않음


def test_검색기가_조건을_빠뜨려도_다른_회원_상담은_결과에서_빠짐():
    """색인 계약 위반을 흉내(leaky) — 응용 계층의 두 번째 확인이 막는지 봄."""

    h = harness(leaky=True)
    response = ask(h, "M-1042")
    assert "d3m2" not in [item.chunk_id for item in response.evidence]
    assert any("다른 회원 상담 조각" in warning for warning in response.warnings)


def test_회원번호가_없으면_지금처럼_전체_상담에서_찾음():
    h = harness()
    ask(h, None)
    assert set(h.index.member_filters) == {None}


def test_회원번호_꼴이_틀리면_검색하지_않고_오류():
    h = harness()
    response = ask(h, "1042")
    assert response.status == STATUS_ERROR and response.error_code == "invalid_input"
    assert h.index.vector_queries == []


@pytest.mark.integration
def test_실제_색인에서_그_회원_상담만_나옴(real_index):
    """실제 세대: M-1042를 주면 상담 이력 조각은 그 회원 것(4건)만, 약관 · 혜택은 그대로 나옴."""

    index = real_index.acquire().index
    question = "연회비 부담 때문에 카드 해지를 고민한다는 상담"
    levels = ("public", "restricted")
    for search in (index.vector_search, index.keyword_search):
        found = search(question, access_levels=levels, k=40, member_pseudo_id=M1042)
        chunks = index.get_chunks([f.chunk_id for f in found])
        members = {c.member_pseudo_id for c in chunks.values() if c.source.doc_type == "consult_log"}
        assert members <= {M1042}, (search.__name__, members)
    everyone = index.keyword_search(question, access_levels=levels, k=40)
    members = {index.get_chunks([f.chunk_id])[f.chunk_id].member_pseudo_id for f in everyone} - {None}
    assert len(members) > 1  # 필터가 없으면 여러 회원 상담이 섞임(필터가 실제로 범위를 좁혔다는 대조군)


def test_회원번호의_핵심어_꼴():
    assert member_id_terms("M-1042") == frozenset({"m-1042", "1042"})


def test_회원_필터가_있으면_회원번호를_채점_핵심어에서_뺌():
    """상담 본문에는 가명만 있어 회원번호를 핵심어로 두면 항상 '불확실'이 됨(실측 Q15 · Q16, 2026-10-05)."""

    question = "M-1042 상담 민원 접수 내용을 알려 주세요"
    corpus = member_corpus()
    index = FakeIndex(corpus=corpus, hits={question: [("d3m1", 0.9), ("d1c1", 0.4)]},
                      condition_vocab=frozenset({"1042"}))
    reranker = FakeReranker(corpus=corpus, scores={"d3m1": 0.9, "d1c1": 0.4})
    h = build(index=index, reranker=reranker, llm=FakeLLM(action=[ActionOutput(ACTION_SEARCH, "q0", "")]))
    h.service.execute(SearchRequest(query=question, member_id="M-1042"), "auditor")
    signals = next(iter(last_request_log(h)["grade_signals"].values()))
    assert "1042" not in signals["keywords"] and signals["keyword_match"] is True
    assert signals["grade"] == "correct"


CONSULT_Q = "M-1042 회원이 원하지 않은 설명은 무엇인가요"


def dated_consult(chunk_id: str, member: str, day: str) -> Chunk:
    text = f"고객: 그런 설명은 하지 마세요 {chunk_id}"
    return Chunk(chunk_id, text, text, "restricted",
                 SourceInfo(source="consult.txt", doc_key="D3", doc_type="consult_log",
                            record_id=f"C-{day.replace('-', '')}-001", consult_date=day),
                 member_pseudo_id=member)


def consult_harness():
    """정답 상담(d3a)이 융합 1위지만 리랭크는 0점대 — 해석형 상담 질문의 실측 모양(Q17 0.002)을 흉내."""

    corpus = make_corpus()
    corpus.update({"d3a": dated_consult("d3a", M1042, "2026-03-02"), "d3b": dated_consult("d3b", M1042, "2026-02-01"),
                   "d3x": dated_consult("d3x", M3001, "2026-01-05")})
    index = FakeIndex(corpus=corpus, hits={CONSULT_Q: [("d3a", 0.95), ("d1c1", 0.9), ("d3x", 0.8)]})
    reranker = FakeReranker(corpus=corpus, scores={"d3a": 0.01, "d1c1": 0.02, "d3x": 0.9})
    return build(index=index, reranker=reranker, llm=FakeLLM(action=[ActionOutput(ACTION_SEARCH, "q0", "")]))


def test_상담_제목에_날짜와_상담ID가_붙음():
    assert dated_consult("d3a", M1042, "2026-03-02").source.title == "상담 2026-03-02 (C-20260302-001) · consult.txt"


def test_융합_1위가_그_회원_상담이면_리랭크가_낮아도_통과하고_상담_전체를_날짜순으로_넘김():
    h = consult_harness()
    h.service.execute(SearchRequest(query=CONSULT_Q, member_id="M-1042", generate_answer=True), "auditor")
    log = last_request_log(h)
    signals = next(iter(log["grade_signals"].values()))
    assert signals["grade"] == "correct" and signals["rule"] == "member_consult"
    # 검색에 안 나온 d3b도 이력으로 들어오고, 리랭크 하한 미만 약관(d1c1) · 다른 회원(d3x)은 빠짐
    assert set(log["evidence_ids"]) == {"d3a", "d3b"}
    answer_input = [p for cid, p in h.llm.payloads if cid == C_04][-1]
    assert [c["chunk_id"] for c in answer_input.evidence_chunks] == ["d3b", "d3a"]  # 날짜순
    assert answer_input.evidence_chunks[0]["title"].startswith("상담 2026-02-01")


def test_회원_필터가_없으면_상담_규칙을_쓰지_않음():
    h = consult_harness()
    h.service.execute(SearchRequest(query=CONSULT_Q, member_id=None), "auditor")
    signals = next(iter(last_request_log(h)["grade_signals"].values()))
    assert "rule" not in signals  # 필터가 없으면 다른 회원 상담(d3x 0.9)까지 보여 점수 규칙으로만 판정함


def test_융합_1위가_상담이_아니면_점수_규칙_그대로():
    def cand(chunk_id, fused, member=None, doc_type="regulation"):
        chunk = Chunk(chunk_id, "본문", "본문", "public", SourceInfo(doc_type=doc_type), member_pseudo_id=member)
        return Candidate(chunk, None, None, fused, 0.01)

    consult = cand("c", 0.5, M1042, "consult_log")
    assert consult_leads([consult, cand("r", 0.4)], M1042)
    assert not consult_leads([consult, cand("r", 0.6)], M1042)  # 약관이 1위면 상담 질문이 아님
    assert not consult_leads([consult], None) and not consult_leads([], M1042)
