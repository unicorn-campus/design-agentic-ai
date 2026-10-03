"""시험용 가짜 포트 묶음임. 실제 색인·모델·Groq 없이 분기·상한·시간 예산을 재현함.

포트를 상속하지 않고 호출 모양만 맞춤 — 구현체가 아니라 시험 대역이며, 일부는 색인 계약 위반(권한 밖 조각 반환)을
일부러 흉내 내어 응용 계층의 이중 확인이 실제로 막는지 보게 함.
응답·예외는 '대본'(script)으로 주입하고 호출 기록을 남겨, 어느 커넥터가 몇 번 불렸는지로 분기를 확인함.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
import re
from typing import Any, Iterable, Mapping, Sequence

from app.application.models import (
    ActionInput,
    ActionOutput,
    AnswerInput,
    AnswerOutput,
    ConnectorError,
    IndexLease,
    PlanInput,
    PlanOutput,
    TransformInput,
    TransformOutput,
)
from app.domain.budget import C_01, C_02, C_03, C_04
from app.domain.models import QTYPE_SIMPLE, Chunk, ScoredChunk, SourceInfo
from app.domain.transform_rules import KEEP

_WORD = re.compile(r"[0-9A-Za-z가-힣]+")

# 가짜 분석기가 명사·숫자·코드 후보에서 빼는 낱말(조사·동사·부사). 실제 Kiwi 품사 판정 대신 둔 목록임.
STOPWORDS = frozenset(
    {"은", "는", "이", "가", "을", "를", "와", "과", "의", "에", "임", "당",
     "자세히", "알려", "주세요", "무엇", "어떻게", "알고", "싶음"}
)


def tokenize(text: str) -> list[str]:
    """시험용 분석기임. 낱말만 남기고 소문자로 통일해 결과를 손으로 예상할 수 있게 둠."""

    return [match.group(0).lower() for match in _WORD.finditer(str(text))]


def make_corpus() -> dict[str, Chunk]:
    """D1 약관 · D2 혜택 안내 2건 · D3 상담 이력로 이루어진 가짜 말뭉치를 만듦.

    d2a1·d2b1은 index_text에만 '[카드: …]' 머리말이 있음(색인 계약 9) — 인용 대조가 text 기준인지 확인하는 데 씀.
    d3c1은 restricted라 agent 역할에게는 절대 나와서는 안 되는 조각임.
    """

    return {
        "d1c1": Chunk(
            "d1c1",
            "연회비 면제 조건 은 전년도 실적 300만원 이상 임",
            "연회비 면제 조건 은 전년도 실적 300만원 이상 임",
            "public",
            SourceInfo(source="card_terms.pdf", doc_key="D1", doc_type="regulation", page=5, clause_no="제5조"),
        ),
        "d2a1": Chunk(
            "d2a1",
            "스카이카드 마일리지 적립 은 1000원 당 2마일 임",
            "[카드: 스카이카드] 스카이카드 마일리지 적립 은 1000원 당 2마일 임",
            "public",
            SourceInfo(source="benefit_guide.md", doc_key="D2", doc_type="benefit_guide", card_id="A01",
                       card_name="스카이카드", benefit_id="BN-MILE", section_label="마일리지"),
        ),
        "d2b1": Chunk(
            "d2b1",
            "쇼핑카드 할인 은 온라인 쇼핑 5 퍼센트 임",
            "[카드: 쇼핑카드] 쇼핑카드 할인 은 온라인 쇼핑 5 퍼센트 임",
            "public",
            SourceInfo(source="benefit_guide.md", doc_key="D2", doc_type="benefit_guide", card_id="B02",
                       card_name="쇼핑카드", benefit_id="BN-SHOP", section_label="할인"),
        ),
        "d3c1": Chunk(
            "d3c1",
            "상담 이력 민원 접수 내용 임",
            "상담 이력 민원 접수 내용 임",
            "restricted",
            SourceInfo(source="consult_log.csv", doc_key="D3", doc_type="consult_log"),
        ),
    }


@dataclass
class FakeClock:
    """ClockPort 모양의 가짜 시계임. 시간은 스스로 흐르지 않고 advance로만 흘러 분기를 정확히 재현함."""

    seconds: float = 0.0
    date_value: date = date(2026, 10, 3)

    def now(self) -> float:
        """현재 단조 시각(초)을 반환함."""

        return self.seconds

    def today(self) -> date:
        """기준일을 반환함."""

        return self.date_value

    def advance(self, seconds: float) -> None:
        """시간을 원하는 만큼 흘려 남은 시간 예산 분기를 만듦."""

        self.seconds += float(seconds)


@dataclass
class FakeIndex:
    """SearchIndexPort 모양의 가짜 색인임. 질의별 결과·검색기 실패·권한 누락을 대본으로 주입함."""

    corpus: Mapping[str, Chunk] = field(default_factory=make_corpus)
    hits: Mapping[str, Sequence[tuple[str, float]]] = field(default_factory=dict)  # 질의 → (조각ID, 점수)
    default_hits: Sequence[tuple[str, float]] = ()  # 대본에 없는 질의의 결과
    vector_error: Exception | None = None
    keyword_error: Exception | None = None
    leaky: bool = False  # 참이면 권한 밖 조각도 돌려줌(색인 계약 위반 흉내 — 응용 계층 이중 확인 검증용)
    generation: str = "gen-test-0001"
    df: Mapping[str, int] = field(default_factory=dict)  # 낱말 → 문서 빈도. 없는 낱말은 0(드문 낱말)임
    target_vocab: frozenset[str] = frozenset({"스카이카드", "쇼핑카드"})
    condition_vocab: frozenset[str] = frozenset({"스카이카드", "쇼핑카드", "300만원", "2026"})
    clock: FakeClock | None = None
    search_cost_s: float = 0.0  # 검색 1회가 쓰는 시간(초). S-R5·S-R6 착지를 만들 때 씀
    vector_queries: list[str] = field(default_factory=list)
    keyword_queries: list[str] = field(default_factory=list)

    # ------------------------------------------------------------ 검색

    def generation_id(self) -> str:
        """세대ID를 반환함."""

        return self.generation

    def num_docs(self) -> int:
        """조각 수를 반환함."""

        return len(self.corpus)

    def vector_search(self, query: str, *, access_levels: Sequence[str], k: int) -> list[ScoredChunk]:
        """대본에 적힌 조각을 점수 내림차순으로 반환함."""

        self.vector_queries.append(query)
        self._spend()
        if self.vector_error is not None:
            raise self.vector_error
        return self._scored(query, access_levels, k)

    def keyword_search(self, query: str, *, access_levels: Sequence[str], k: int) -> list[ScoredChunk]:
        """벡터 검색과 같은 대본을 쓰되 호출 기록만 따로 남김(두 검색기 겹침 신호가 1 이상이 되게 함)."""

        self.keyword_queries.append(query)
        self._spend()
        if self.keyword_error is not None:
            raise self.keyword_error
        return self._scored(query, access_levels, k)

    def _spend(self) -> None:
        """검색에 쓴 시간을 가짜 시계에 반영함."""

        if self.clock is not None and self.search_cost_s:
            self.clock.advance(self.search_cost_s)

    def _scored(self, query: str, access_levels: Sequence[str], k: int) -> list[ScoredChunk]:
        """대본 결과에 권한 필터를 적용해 상위 k개를 반환함(leaky면 필터를 건너뜀)."""

        allowed = set(access_levels)
        rows = self.hits.get(query, self.default_hits)
        out: list[ScoredChunk] = []
        for chunk_id, score in rows:
            chunk = self.corpus.get(chunk_id)
            if chunk is None:
                continue
            if not self.leaky and chunk.access_level not in allowed:
                continue
            out.append(ScoredChunk(chunk_id, float(score)))
        return out[:k]

    # ------------------------------------------------------------ 말뭉치·사전

    def get_chunks(self, chunk_ids: Iterable[str]) -> dict[str, Chunk]:
        """조각ID로 조각을 찾음. 없는 ID는 결과에서 빠짐."""

        return {cid: self.corpus[cid] for cid in chunk_ids if cid in self.corpus}

    def tokens(self, text: str) -> list[str]:
        """BM25와 같은 분석기 역할임."""

        return tokenize(text)

    def keyword_candidates(self, text: str) -> list[str]:
        """명사·숫자·코드 후보만 중복 없이 반환함(조사·동사·부사는 STOPWORDS로 뺌)."""

        return [term for term in dict.fromkeys(tokenize(text)) if term not in STOPWORDS]

    def document_frequency(self, terms: Iterable[str]) -> dict[str, int]:
        """낱말별 문서 빈도를 입력 순서대로 반환함. 대본에 없으면 0(드문 낱말)임."""

        return {term: int(self.df.get(term, 0)) for term in terms}

    def chunk_terms(self, chunk_ids: Iterable[str]) -> frozenset[str]:
        """조각들의 색인용 텍스트 낱말 합집합을 반환함."""

        terms: set[str] = set()
        for cid in chunk_ids:
            chunk = self.corpus.get(cid)
            if chunk is not None:
                terms.update(tokenize(chunk.index_text))
        return frozenset(terms)

    def target_terms(self, text: str) -> frozenset[str]:
        """문장에 나온 카드 대상명을 반환함."""

        return frozenset(term for term in tokenize(text) if term in self.target_vocab)

    def condition_terms(self, text: str) -> frozenset[str]:
        """문장의 조건 낱말(대상명·숫자·날짜)을 반환함."""

        return frozenset(term for term in tokenize(text) if term in self.condition_vocab)


@dataclass
class FakeIndexProvider:
    """IndexProviderPort 모양의 가짜 색인 공급자임. 세대 없음(index_unavailable)과 적재 시간을 재현함."""

    index: Any = None
    error: Exception | None = None
    warnings: tuple[str, ...] = ()
    clock: FakeClock | None = None
    cost_s: float = 0.0  # 세대를 빌리는 데 쓰는 시간(초). S-R2 착지를 만들 때 씀
    acquire_count: int = 0

    def acquire(self) -> IndexLease:
        """이번 요청이 쓸 세대를 빌려줌. error가 있으면 그대로 올림."""

        self.acquire_count += 1
        if self.clock is not None and self.cost_s:
            self.clock.advance(self.cost_s)
        if self.error is not None:
            raise self.error
        return IndexLease(index=self.index, warnings=self.warnings)

    def status(self) -> dict[str, Any]:
        """상태 확인용 정보를 반환함."""

        ready = self.index is not None and self.error is None
        return {
            "ready": ready,
            "generation": None if self.index is None else self.index.generation_id(),
            "chunk_count": 0 if self.index is None else self.index.num_docs(),
            "loading": False,
            "last_error": None if self.error is None else type(self.error).__name__,
        }


@dataclass
class FakeReranker:
    """RerankerPort 모양의 가짜 리랭커임. 조각ID별 점수를 주고, 질의별로 다른 점수도 줄 수 있음.

    질의별 점수(by_query)는 '질문 변환 후 재검색에서는 점수가 올라감' 같은 시나리오를 만드는 데 씀.
    """

    corpus: Mapping[str, Chunk] = field(default_factory=make_corpus)
    scores: Mapping[str, float] = field(default_factory=dict)  # 조각ID → 점수
    by_query: Mapping[str, Mapping[str, float]] = field(default_factory=dict)  # 질의 → (조각ID → 점수)
    default: float = 0.5
    error: Exception | None = None
    calls: list[tuple[str, int]] = field(default_factory=list)  # (질의, 조각 수)

    def score(self, query: str, texts: Sequence[str]) -> list[float]:
        """질의-조각 쌍 점수를 texts와 같은 순서로 반환함."""

        self.calls.append((query, len(texts)))
        if self.error is not None:
            raise self.error
        # 리랭커는 색인용 텍스트(index_text)를 받음. 그 텍스트로 조각ID를 되찾아 미리 정한 점수를 돌려줌
        text_to_id = {chunk.index_text: cid for cid, chunk in self.corpus.items()}
        per_query = self.by_query.get(query, {})
        out: list[float] = []
        for text in texts:
            chunk_id = text_to_id.get(text, "")
            if chunk_id in per_query:
                out.append(float(per_query[chunk_id]))
            else:
                out.append(float(self.scores.get(chunk_id, self.default)))
        return out


class FakeLLM:
    """LanguageModelPort 모양의 가짜 LLM임. 커넥터별 응답·예외를 대본 순서대로 돌려줌.

    대본이 바닥나면 마지막 항목을 되풀이함 — 시험이 호출 횟수를 정확히 맞추지 않아도 되게 함.
    항목이 Exception이면 그대로 올려 커넥터 실패(ConnectorError)를 재현함.
    """

    def __init__(
        self,
        *,
        plan: Sequence[Any] = (),
        action: Sequence[Any] = (),
        transform: Sequence[Any] = (),
        answer: Sequence[Any] = (),
        clock: FakeClock | None = None,
        costs: Mapping[str, float] | None = None,
    ) -> None:
        """커넥터별 대본과 호출 1회가 쓰는 시간을 받음. 부수효과 없음."""

        self._scripts: dict[str, list[Any]] = {
            C_01: list(plan) or [PlanOutput(QTYPE_SIMPLE, (), "", "시험 기본값: 단순 질문")],
            C_02: list(action) or [ActionOutput("finish", "", "시험 기본값: 수집 종료")],
            C_03: list(transform) or [TransformOutput(KEEP, (), False, "", "시험 기본값: keep")],
            C_04: list(answer) or [AnswerOutput((), (), "시험 기본값: 답변 없음")],
        }
        self._positions: dict[str, int] = {key: 0 for key in self._scripts}
        self.clock = clock
        self.costs = dict(costs or {})
        self.calls: list[str] = []  # 부른 커넥터ID 순서
        self.payloads: list[tuple[str, Any]] = []  # (커넥터ID, 입력)

    def _take(self, connector_id: str, payload: Any) -> Any:
        """대본에서 다음 항목을 꺼내고 호출 기록·소요 시간을 남김. 예외 항목이면 올림."""

        self.calls.append(connector_id)
        self.payloads.append((connector_id, payload))
        cost = self.costs.get(connector_id, 0.0)
        if self.clock is not None and cost:
            # 실패해도 시간은 쓰이므로 예외를 올리기 전에 시계를 흘림
            self.clock.advance(cost)
        script = self._scripts[connector_id]
        position = min(self._positions[connector_id], len(script) - 1)
        self._positions[connector_id] += 1
        item = script[position]
        if isinstance(item, Exception):
            raise item
        return item

    def analyze_question(self, payload: PlanInput) -> PlanOutput:
        """C-01 질문 분석 대본을 돌려줌."""

        return self._take(C_01, payload)

    def choose_action(self, payload: ActionInput) -> ActionOutput:
        """C-02 행동 선택 대본을 돌려줌."""

        return self._take(C_02, payload)

    def transform_query(self, payload: TransformInput) -> TransformOutput:
        """C-03 질문 변환 대본을 돌려줌."""

        return self._take(C_03, payload)

    def generate_answer(self, payload: AnswerInput) -> AnswerOutput:
        """C-04 답변 생성 대본을 돌려줌."""

        return self._take(C_04, payload)

    def count(self, connector_id: str) -> int:
        """커넥터별 호출 횟수를 반환함(실패 호출도 셈)."""

        return self.calls.count(connector_id)

    def payloads_of(self, connector_id: str) -> list[Any]:
        """커넥터별 입력 목록을 호출 순서대로 반환함."""

        return [payload for cid, payload in self.payloads if cid == connector_id]


@dataclass
class FakeAuditLog:
    """AuditLogPort 모양의 가짜 감사 로그임. 기록을 메모리에 모아 질문 원문 유출을 검사함."""

    records: list[Mapping[str, Any]] = field(default_factory=list)

    def write(self, record: Mapping[str, Any]) -> None:
        """감사 레코드 1건을 모아 둠."""

        self.records.append(dict(record))

    def of_type(self, record_type: str) -> list[Mapping[str, Any]]:
        """종류별 레코드 목록을 반환함(request·connector_error·internal_error)."""

        return [record for record in self.records if record.get("type") == record_type]


def connector_error(connector_id: str, kind: str = "timeout") -> ConnectorError:
    """커넥터 실패 대본을 짧게 만드는 도우미임."""

    return ConnectorError(connector_id, kind, f"{connector_id} 시험용 실패", status_code=None, elapsed_seconds=0.0)
