"""검색 업무에서 오가는 불변 값 객체(조각·후보·하위 질문·판정 근거)를 정의함."""

from __future__ import annotations

from dataclasses import dataclass, field

# 하위 질문 판정 상태(부록 A sub_questions.status)
SUB_PENDING = "pending"  # 아직 검색하지 않음
SUB_SATISFIED = "satisfied"  # 채점 '정확' — 근거 묶음에 들어감
SUB_UNCERTAIN = "uncertain"  # 채점 '불확실' — 변환 1회 기회가 남아 있음
SUB_INSUFFICIENT = "insufficient"  # 근거 부족으로 종료(부정확·재검색 후 불확실·keep·검색 실패)

# 채점 판정(S-R5)
GRADE_CORRECT = "correct"
GRADE_UNCERTAIN = "uncertain"
GRADE_INCORRECT = "incorrect"

# 질문 유형(S-R2)
QTYPE_CHITCHAT = "chitchat"
QTYPE_SIMPLE = "simple"
QTYPE_COMPLEX = "complex"


@dataclass(frozen=True)
class SourceInfo:
    """근거 출처 표시용 메타데이터(설계 ⑥-9 출처 표시). 값이 없는 필드는 None임."""

    source: str = ""  # 문서 파일명
    doc_key: str = ""  # D1·D2·D3
    doc_type: str = ""  # regulation·benefit_guide·consult_log
    page: int | None = None  # 시작 쪽(PDF만)
    page_end: int | None = None  # 끝 쪽(PDF만)
    clause_no: str | None = None  # 조항 번호(D1만)
    card_id: str | None = None  # 카드 코드(D2만)
    card_name: str | None = None  # 카드명(D2만)
    benefit_id: str | None = None  # 혜택 코드
    section_label: str | None = None  # 구역 표시
    record_id: str | None = None  # 상담ID(D3만). 인덱서가 본문 머리말을 지워 메타데이터에만 남음
    consult_date: str | None = None  # 상담 날짜 YYYY-MM-DD(D3만)

    @property
    def title(self) -> str:
        """LLM에 넘길 조각 제목. 문서명과 구역을 이어 사람이 읽을 수 있게 만듦.

        상담 이력은 본문에 날짜가 없어 '첫 상담 · 가장 최근 상담' 질문에 답하려면 제목에 날짜·상담ID가 있어야 함.
        """

        parts = []
        if self.consult_date or self.record_id:
            parts.append(" ".join(p for p in ("상담", self.consult_date, f"({self.record_id})" if self.record_id else "")
                                  if p))
        parts.append(self.source)
        if self.card_name:
            parts.append(self.card_name)
        if self.section_label:
            parts.append(self.section_label)
        return " · ".join(part for part in parts if part)


@dataclass(frozen=True)
class Chunk:
    """색인 말뭉치의 조각 1건.

    text는 표시·인용 대조용 원래 본문이고, index_text는 임베딩·BM25·리랭크에 쓰는 색인용 텍스트임.
    색인 계약: D2 84건은 index_text에만 '[카드: …]' 머리말이 있음. 머리말이 없는 조각은 두 값이 같음.
    """

    chunk_id: str
    text: str
    index_text: str
    access_level: str
    source: SourceInfo = field(default_factory=SourceInfo)
    member_pseudo_id: str | None = None  # 상담 이력 조각의 회원 가명(색인 메타데이터). 출처 표시에는 쓰지 않음


@dataclass(frozen=True)
class ScoredChunk:
    """검색기 하나가 돌려준 조각ID와 원래 점수(코사인 1 − 거리 또는 BM25 점수)."""

    chunk_id: str
    score: float


@dataclass(frozen=True)
class Candidate:
    """S-R4가 만든 검색 후보. 채점·응답에 필요한 점수를 모두 담음."""

    chunk: Chunk
    vector_score: float | None  # 코사인 점수. 벡터 후보에 없으면 None
    bm25_score: float | None  # BM25 원점수. BM25 후보에 없으면 None
    fused_score: float  # 정규화 가중합(질의가 여럿이면 질의 합치기 점수)
    rerank_score: float | None  # 리랭커 0 ~ 1 점수. 리랭크 실패면 None

    @property
    def chunk_id(self) -> str:
        """조각ID를 그대로 돌려줌."""

        return self.chunk.chunk_id


@dataclass(frozen=True)
class SubQuestion:
    """검색 대상 질문 1개(부록 A sub_questions 안쪽 구조).

    qid는 단순 질문이면 q0(원 질문), 복합이면 q1 ~ q3(분해 질문)임.
    """

    qid: str
    text: str
    origin: str  # original·decomposed
    status: str = SUB_PENDING
    transform_count: int = 0  # 0 ~ 1. 1이면 다시 변환하지 않음
    evidence_count: int = 0  # 이 질문으로 근거 묶음에 넣은 조각 수
    note: str = ""  # 근거 부족으로 끝난 이유(사람이 읽을 문장)


@dataclass(frozen=True)
class GradeSignals:
    """S-R5 판정 근거. 코드가 계산한 사실값이며 C-03 입력과 감사 로그에 그대로 씀."""

    result_count: int
    reranked: bool  # 리랭크 성공 여부
    main_score: float | None  # 주 점수 1위(리랭크 점수). 리랭크 실패면 None
    score_band: str  # high(≥ 상한)·middle·low(< 하한)·unknown(리랭크 실패)·none(결과 0건)
    gap: float | None  # 1위 − '다른 대상' 최고 리랭크 점수(grading.build_signals). 경쟁자가 없으면 1위 점수 − 0
    keywords: tuple[str, ...]  # 질문에서 고른 핵심어
    missing_keywords: tuple[str, ...]  # 결과에서 찾지 못한 핵심어
    overlap: int  # 벡터·BM25 상위 k개 조각ID 겹침 수
    # 질문이 카드를 지정했을 때 1위 조각이 그 카드인지. 지정이 없거나 1위가 카드 조각이 아니면 참
    target_match: bool = True

    @property
    def keyword_match(self) -> bool:
        """핵심어를 모두 결과에서 찾았는지 반환함. 고른 핵심어가 없으면 반대 근거가 없으므로 참임."""

        return not self.missing_keywords

    def as_dict(self) -> dict[str, object]:
        """C-03 입력·감사 로그용 dict로 바꿈."""

        return {
            "result_count": self.result_count,
            "reranked": self.reranked,
            "main_score": None if self.main_score is None else round(self.main_score, 4),
            "score_band": self.score_band,
            "gap": None if self.gap is None else round(self.gap, 4),
            "keywords": list(self.keywords),
            "missing_keywords": list(self.missing_keywords),
            "keyword_match": self.keyword_match,
            "retriever_overlap": self.overlap,
            "target_match": self.target_match,
        }
