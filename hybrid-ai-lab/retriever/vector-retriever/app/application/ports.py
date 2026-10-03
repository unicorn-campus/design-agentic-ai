"""응용 계층이 필요로 하는 기능의 약속(포트). 실제 기술 구현은 infrastructure가 이 포트를 상속해 만듦."""

from __future__ import annotations

from abc import abstractmethod
from datetime import date
from typing import Any, Iterable, Mapping, Protocol, Sequence

from app.domain.models import Chunk, ScoredChunk

from .models import (
    ActionInput,
    ActionOutput,
    AnswerInput,
    AnswerOutput,
    IndexLease,
    PlanInput,
    PlanOutput,
    TransformInput,
    TransformOutput,
)


class SearchIndexPort(Protocol):
    """W-1이 게시한 색인 '한 세대'를 읽기 전용으로 검색·분석하는 계약.

    한 인스턴스는 한 세대만 가리킴. 벡터·BM25·말뭉치·사전이 모두 같은 세대여야 함(색인 계약 1).
    """

    @abstractmethod
    def generation_id(self) -> str:
        """이 인스턴스가 가리키는 세대ID를 반환함.

        반환값: active_generation.json의 generation 값임.
        예외: 없음.
        부수효과: 없음.
        """

    @abstractmethod
    def num_docs(self) -> int:
        """세대의 조각 수를 반환함.

        반환값: 말뭉치 줄 수와 같은 정수(현재 218)임.
        예외: 없음.
        부수효과: 없음.
        """

    @abstractmethod
    def vector_search(self, query: str, *, access_levels: Sequence[str], k: int) -> list[ScoredChunk]:
        """질의를 임베딩해 코사인 점수가 높은 조각 k개를 찾음(뜻으로 찾기).

        인자: query는 접두어 없이 그대로 임베딩함(색인 계약 4). access_levels 밖의 조각은 순위 매기기 전에 거름.
        반환값: 점수(1 − 코사인 거리) 내림차순 목록. 후보가 k보다 적으면 있는 만큼만 돌려줌.
        예외: 임베딩·벡터 저장소 실패는 예외를 그대로 올림. 호출한 단계가 '한쪽 실패'로 처리함.
        부수효과: 없음(읽기 전용).
        """

    @abstractmethod
    def keyword_search(self, query: str, *, access_levels: Sequence[str], k: int) -> list[ScoredChunk]:
        """색인과 같은 분석기로 질의를 낱말로 나눠 BM25 점수가 높은 조각 k개를 찾음(낱말로 찾기).

        인자: access_levels 밖의 조각은 점수 계산 뒤 순위를 매기기 전에 버림.
        반환값: BM25 원점수 내림차순 목록. 점수가 0인 조각은 넣지 않음. 낱말이 하나도 없으면 빈 목록임.
        예외: BM25 색인 실패는 예외를 그대로 올림.
        부수효과: 없음(읽기 전용).
        """

    @abstractmethod
    def get_chunks(self, chunk_ids: Iterable[str]) -> dict[str, Chunk]:
        """조각ID로 말뭉치 조각(본문 text·색인용 index_text·출처 메타데이터)을 찾음.

        반환값: 조각ID → Chunk. 없는 ID는 결과에서 빠짐. 본문은 BM25 색인이 아니라 말뭉치에서 읽음.
        예외: 없음.
        부수효과: 없음.
        """

    @abstractmethod
    def tokens(self, text: str) -> list[str]:
        """BM25와 똑같은 분석기(표기 통일·Kiwi·카드명·별칭 사전)로 문장을 낱말 목록으로 바꿈.

        반환값: 출현 횟수만큼 담은 낱말 목록. 빈 문장이면 빈 목록임.
        예외: 없음.
        부수효과: 없음.
        """

    @abstractmethod
    def keyword_candidates(self, text: str) -> list[str]:
        """채점 핵심어 후보로 명사·숫자·코드 낱말만 골라 반환함(사전으로 대상명 통일 포함).

        반환값: 중복을 뺀 낱말 목록(첫 출현 순서). 동사·형용사·부사는 넣지 않음.
        예외: 없음.
        부수효과: 없음.
        """

    @abstractmethod
    def document_frequency(self, terms: Iterable[str]) -> dict[str, int]:
        """낱말마다 그 낱말이 들어 있는 조각 수를 반환함(핵심어 드묾 계산용).

        반환값: 입력 순서를 지킨 낱말 → 조각 수. 색인에 없는 낱말은 0임.
        예외: 없음.
        부수효과: 없음. 문서 빈도는 세대를 올릴 때 1회 계산해 둔 값을 씀.
        """

    @abstractmethod
    def chunk_terms(self, chunk_ids: Iterable[str]) -> frozenset[str]:
        """조각들의 색인용 텍스트를 같은 분석기로 자른 낱말의 합집합을 반환함(핵심어 일치 확인용).

        반환값: 낱말 집합. 없는 조각ID는 무시함.
        예외: 없음.
        부수효과: 없음.
        """

    @abstractmethod
    def target_terms(self, text: str) -> frozenset[str]:
        """문장에 나온 카드 대상명(카드명 사전·별칭 사전으로 통일한 정식 토큰)을 반환함.

        반환값: 정식 카드 토큰 집합. 대상명이 없으면 빈 집합임.
        예외: 없음.
        부수효과: 없음.
        """

    @abstractmethod
    def condition_terms(self, text: str) -> frozenset[str]:
        """문장의 조건 낱말(카드 대상명 + 숫자·날짜·금액·코드)을 반환함(하위 질문 조건 보존 검사용).

        반환값: 분석기로 통일한 낱말 집합임.
        예외: 없음.
        부수효과: 없음.
        """


class IndexProviderPort(Protocol):
    """'사용 중 세대'를 골라 검색할 수 있는 상태로 올려 두고 요청마다 빌려주는 계약(S-R1 ④ ⑤)."""

    @abstractmethod
    def acquire(self) -> IndexLease:
        """이번 요청이 쓸 세대를 돌려줌.

        방법: 사용 중 세대 표시 파일을 읽어 올려 둔 세대와 다르면 새 세대를 따로 올리고 서명·해시를 대조함.
        대조가 끝나기 전에는 올려 둔 세대를 돌려주고, 통과하면 다음 요청부터 새 세대를 씀.
        반환값: IndexLease(index=SearchIndexPort, warnings). 경고에는 '새 세대 적재 중'·'새 세대 대조 실패' 등이 담김.
        예외: 올려 둔 세대도 없고 새로 올릴 수도 없으면 IndexUnavailableError를 발생시킴.
        부수효과: 새 세대를 백그라운드에서 적재할 수 있음.
        """

    @abstractmethod
    def status(self) -> dict[str, Any]:
        """상태 확인(health)용 정보를 반환함.

        반환값: ready(bool)·generation·chunk_count·loading(bool)·last_error 키를 가진 dict임.
        예외: 없음.
        부수효과: 없음.
        """


class RerankerPort(Protocol):
    """질의와 조각을 함께 읽어 관련도를 다시 매기는 Cross-Encoder 계약(설계 ⑥-7)."""

    @abstractmethod
    def score(self, query: str, texts: Sequence[str]) -> list[float]:
        """질의-조각 쌍마다 0 ~ 1 관련도 점수를 반환함.

        인자: texts는 조각의 색인용 텍스트(index_text)이며 설정한 입력 상한 토큰까지만 읽음(설계 ⑥-7).
        반환값: texts와 같은 길이·같은 순서의 점수 목록임. texts가 비면 빈 목록임.
        예외: 모델 실패는 예외를 그대로 올림. 호출한 단계가 융합 결과로 대신하고 경고를 남김.
        부수효과: 없음.
        """


class LanguageModelPort(Protocol):
    """Groq LLM 커넥터 4종(C-01 ~ C-04)의 계약. 모두 동기 1회 호출·재시도 0회·구조화 출력임."""

    @abstractmethod
    def analyze_question(self, payload: PlanInput) -> PlanOutput:
        """C-01: 질문 유형(chitchat·simple·complex)과 하위 질문을 받음.

        반환값: 스키마를 통과한 PlanOutput. 서버 규칙 검사는 호출한 단계가 따로 함.
        예외: 시간 초과(2.5초)·HTTP 오류·응답 형식 오류는 ConnectorError를 발생시킴.
        부수효과: 외부 API 호출 1회.
        """

    @abstractmethod
    def choose_action(self, payload: ActionInput) -> ActionOutput:
        """C-02: 허용 행동 목록 안에서 다음 행동 1개와 대상·이유를 받음.

        반환값: 스키마를 통과한 ActionOutput. 목록 밖 행동 검사는 호출한 단계가 함.
        예외: 시간 초과(1.5초)·HTTP 오류·응답 형식 오류는 ConnectorError를 발생시킴.
        부수효과: 외부 API 호출 1회.
        """

    @abstractmethod
    def transform_query(self, payload: TransformInput) -> TransformOutput:
        """C-03: 변환 기법 1개와 검색용 질의를 받음.

        반환값: 스키마를 통과한 TransformOutput. 금지 규칙 검사는 호출한 단계가 함.
        예외: 시간 초과(1.2초)·HTTP 오류·응답 형식 오류는 ConnectorError를 발생시킴.
        부수효과: 외부 API 호출 1회.
        """

    @abstractmethod
    def generate_answer(self, payload: AnswerInput) -> AnswerOutput:
        """C-04: 근거 묶음만으로 문장마다 인용이 달린 답변 초안을 받음.

        반환값: 스키마를 통과한 AnswerOutput. 인용 대조는 S-R8이 따로 함.
        예외: 시간 초과(2.5초)·HTTP 오류·응답 형식 오류는 ConnectorError를 발생시킴.
        부수효과: 외부 API 호출 1회.
        """


class AuditLogPort(Protocol):
    """판단 과정(행동 기록·판정 근거·단계별 시간·커넥터 오류)을 남기는 감사 로그 계약."""

    @abstractmethod
    def write(self, record: Mapping[str, Any]) -> None:
        """감사 레코드 1건을 남김.

        인자: record에는 질문 원문을 넣지 않음(해시 또는 앞 20자만). API 키도 넣지 않음.
        반환값: 없음.
        예외: 기록 실패는 삼키고 응답을 막지 않음(감사 로그 실패로 검색 응답을 실패시키지 않음).
        부수효과: 파일 등에 한 줄을 덧붙임.
        """


class ClockPort(Protocol):
    """경과 시간과 기준일을 주는 시계 계약. 시험에서는 가짜 시계로 시간 예산 분기를 재현함."""

    @abstractmethod
    def now(self) -> float:
        """단조 증가 시각(초)을 반환함.

        반환값: 두 값의 차가 경과 초인 실수. 벽시계 시각이 아님.
        예외: 없음.
        부수효과: 없음.
        """

    @abstractmethod
    def today(self) -> date:
        """C-01의 상대 날짜 해석에 쓸 기준일을 반환함.

        반환값: 서버 지역 날짜임.
        예외: 없음.
        부수효과: 없음.
        """


class RetrieverWorkflowPort(Protocol):
    """S-R1 ~ S-R9 단계를 정해진 분기·반복대로 실행하는 워크플로우 실행기 계약."""

    @abstractmethod
    def run(self, state: Mapping[str, Any]) -> dict[str, Any]:
        """초기 상태로 워크플로우를 끝(S-R9)까지 실행하고 최종 상태를 반환함.

        인자: state는 RetrieverService가 만든 초기 RetrieverState임.
        반환값: S-R9가 채운 response 키를 가진 최종 상태 dict임.
        예외: 단계 상한을 넘는 비정상 반복은 RuntimeError로 올림(상한 장치가 막으므로 정상 흐름에서는 없음).
        부수효과: 단계가 부르는 포트의 부수효과(LLM 호출·감사 로그)를 그대로 가짐.
        """
