"""업무 흐름이 소유하고 외부 기술이 구현할 포트 계약을 정의함."""

from __future__ import annotations

from abc import abstractmethod
from typing import Any, Protocol

from app.domain.models import (
    IndexSnapshot, LoadedDocument, PreparedChunk, Publication, RawChunk, SourceRef, SplitPolicy,
)


class SourceCatalogPort(Protocol):
    """입력 경로에서 처리 대상 원천 문서를 찾는 계약임."""

    @abstractmethod
    def discover(self, input_path: str, doc: str, segment: int | None) -> list[SourceRef]:
        """선택 조건에 맞는 원천 문서와 내용 지문을 반환함.

        인자: input_path는 읽을 수 있는 입력 경로이며, doc은 D1·D2·D3·all 중 하나임.
        인자: segment는 D3 상담 세그먼트 번호이며, None이면 세그먼트를 제한하지 않음.
        반환값: 원천 경로·논리 이름·문서 유형·SHA-256 지문을 담은 목록임. 없으면 빈 목록임.
        예외: 경로 접근이나 원천 지문 계산에 실패한 예외를 호출자에게 전달함.
        부수효과: 파일 내용을 읽지만 변경하지 않음.
        """
        ...


class DocumentLoaderPort(Protocol):
    """원천 파일을 분할 가능한 문서와 위치 정보로 읽는 계약임."""

    @abstractmethod
    def load(self, source: SourceRef) -> list[LoadedDocument]:
        """원천 하나를 문서 유형에 맞게 추출함.

        인자: source는 발견 단계에서 내용 지문까지 계산된 원천 참조임.
        반환값: 추출 본문과 페이지·정제·개인정보 위치 정보를 담은 문서 목록임.
        예외: 지원하지 않는 형식, 파싱 실패, 파일 접근 오류를 호출자에게 전달함.
        부수효과: 원천 파일을 읽지만 변경하지 않음.
        """
        ...


class TextSplitterPort(Protocol):
    """문서를 정책별 토큰 크기와 구분자로 나누는 계약임."""

    @abstractmethod
    def split(self, document: LoadedDocument, policy: SplitPolicy) -> list[RawChunk]:
        """원문 위치를 보존하면서 문서를 겹치는 청크로 분할함.

        인자: document는 추출이 끝난 문서이며, policy의 마지막 구분자는 빈 문자열이어야 함.
        반환값: 정제 전 텍스트와 원문 시작·끝 위치를 담은 청크 목록임.
        예외: 토큰 계산이나 분할 정책 적용에 실패한 예외를 호출자에게 전달함.
        부수효과: 원문은 변경하지 않음. 주입된 토큰 계산기의 초기화·메모리 캐시 사용은 발생 가능함.
        """
        ...


class TokenCounterPort(Protocol):
    """임베딩 모델과 같은 토크나이저로 입력 길이를 계산하는 계약임."""

    @property
    @abstractmethod
    def signature(self) -> str:
        """토큰 계산 방식의 변경을 판별할 안정적인 서명을 반환함.

        반환값: 토크나이저와 길이 계산 설정을 식별하는 문자열임.
        예외: 구현체가 서명을 만들 수 없을 때 발생한 예외를 호출자에게 전달함.
        부수효과: 없음.
        """
        ...

    @property
    @abstractmethod
    def max_tokens(self) -> int:
        """임베딩에 전달할 수 있는 청크 한 개의 토큰 상한을 반환함.

        반환값: 특수 토큰을 포함해 허용하는 최대 입력 토큰 수임.
        예외: 설정이 유효하지 않을 때 발생한 예외를 호출자에게 전달함.
        부수효과: 없음.
        """
        ...

    @abstractmethod
    def count(self, text: str) -> int:
        """임베딩 입력과 같은 규칙으로 본문의 토큰 수를 계산함.

        인자: text는 분할 크기 계산용 원문이거나 임베딩 직전의 정제 완료 본문임.
        반환값: 특수 토큰을 포함하고 길이를 자르지 않은 토큰 수임. 빈 본문의 처리 방식은 구현체 계약을 따름.
        예외: 토크나이저 실행에 실패한 예외를 호출자에게 전달함.
        부수효과: 토크나이저를 지연 로드하는 구현체는 최초 호출 시 메모리와 로컬 캐시를 사용할 수 있음.
        """
        ...


class ChunkProcessorPort(Protocol):
    """분할 청크를 정제하고 개인정보를 제거해 저장 가능한 형태로 만드는 계약임."""

    @abstractmethod
    def process(self, chunk: RawChunk) -> PreparedChunk | None:
        """머리말·꼬리말 제거와 개인정보 처리를 순서대로 적용함.

        인자: chunk는 원문 위치를 가진 정제 전 청크임.
        반환값: 저장 가능한 청크이며, 정제 뒤 본문이 비면 None임.
        예외: 개인정보 잔존이나 메타데이터 검증 실패 예외를 호출자에게 전달함.
        부수효과: 원문은 변경하지 않음. 주입된 토큰 계산기의 초기화·메모리 캐시 사용은 발생 가능함.
        개인정보 처리 전 원문을 외부에 저장하지 않음.
        """
        ...


class EmbedderPort(Protocol):
    """정제된 청크 본문을 정규화된 단일 벡터로 바꾸는 계약임."""

    @property
    @abstractmethod
    def signature(self) -> str:
        """모델과 변환 방식의 변경을 판별할 안정적인 서명을 반환함.

        반환값: 모델 이름과 임베딩 용도를 식별하는 문자열임. 세부 변환 설정은 별도 계약에서 관리함.
        예외: 구현체가 서명을 만들 수 없을 때 발생한 예외를 호출자에게 전달함.
        부수효과: 없음.
        """
        ...

    @property
    @abstractmethod
    def dimension(self) -> int:
        """본문 한 건에서 생성되는 벡터의 고정 차원을 반환함.

        반환값: 벡터 원소 수임.
        예외: 모델 초기화나 차원 확인 실패 예외를 호출자에게 전달함.
        부수효과: 모델을 지연 로드하는 구현체는 최초 접근 시 메모리와 캐시를 사용할 수 있음.
        """
        ...

    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]:
        """입력 순서를 유지해 본문 목록을 벡터 목록으로 변환함.

        인자: 각 본문은 토큰 상한 검사를 통과한 정제 완료 텍스트임.
        반환값: 입력과 같은 개수·순서의 벡터 목록임.
        예외: 모델 로드, 입력 변환, 추론 실패 예외를 호출자에게 전달함.
        부수효과: 모델 추론과 로컬 모델 캐시 사용이 발생할 수 있음.
        """
        ...


class IndexRepositoryPort(Protocol):
    """벡터·키워드 색인을 세대 단위로 준비하고 원자적으로 게시하는 계약임."""

    @abstractmethod
    def load_active(self) -> IndexSnapshot | None:
        """현재 활성 세대의 청크와 매니페스트를 읽음.

        반환값: 활성 세대 스냅샷이며, 한 번도 게시되지 않았으면 None임.
        예외: 활성 포인터나 색인 파일을 읽거나 검증하지 못한 예외를 호출자에게 전달함.
        부수효과: 색인 파일을 읽지만 활성 세대를 변경하지 않음.
        """
        ...

    @abstractmethod
    def get_vectors(self, chunk_ids: list[str]) -> dict[str, list[float]]:
        """활성 세대에서 재사용할 벡터를 청크 ID로 조회함.

        인자: chunk_ids는 중복을 제거한 활성 세대의 청크 ID 목록임.
        반환값: 찾은 청크 ID와 벡터의 매핑임. 없는 ID는 결과에서 빠짐.
        예외: 벡터 저장소 조회에 실패한 예외를 호출자에게 전달함.
        부수효과: 벡터 DB 클라이언트 초기화 과정에서 로컬 관리 파일이 갱신될 수 있음.
        """
        ...

    @abstractmethod
    def begin(self, generation: str, embedding_signature: str) -> None:
        """활성 세대와 분리된 대상 세대를 멱등하게 준비함.

        인자: generation은 이번 실행 전용 세대이며, embedding_signature는 벡터 계약 식별자임.
        반환값: 없음.
        예외: 기존 대상 세대의 임베딩 서명이 다르거나 저장소 준비에 실패하면 예외가 발생함.
        부수효과: 대상 세대 디렉터리와 벡터 저장소를 만들거나 기존 동일 세대를 재사용함.
        """
        ...

    @abstractmethod
    def upsert(self, generation: str, chunks: list[PreparedChunk], vectors: list[list[float]]) -> None:
        """청크와 벡터의 대응 순서를 유지해 대상 세대에 멱등 적재함.

        인자: generation은 begin으로 준비된 세대이며, chunks와 vectors의 개수·순서가 같아야 함.
        반환값: 없음.
        예외: 개수·차원 불일치나 벡터 저장소 쓰기 실패 예외를 호출자에게 전달함.
        부수효과: 대상 세대의 벡터 저장소를 갱신하며 활성 세대는 바꾸지 않음.
        """
        ...

    @abstractmethod
    def build_text_index(
        self,
        generation: str,
        chunks: list[PreparedChunk],
        manifest: dict[str, Any],
    ) -> dict[str, Any]:
        """키워드 검색용 BM25 색인을 비활성 세대에 준비하고 검증함.

        인자: generation은 벡터 적재가 끝난 대상 세대이며, chunks와 manifest는 게시 예정 내용임.
        반환값: generation·chunk_count·manifest_sha256·corpus_sha256를 포함한 검증 증거임.
        예외: 벡터 건수·청크 내용·BM25 산출물 검증이나 파일 쓰기 실패 예외를 호출자에게 전달함.
        부수효과: 대상 세대에 BM25 산출물과 매니페스트를 쓰지만 활성 세대는 변경하지 않음.
        """
        ...

    @abstractmethod
    def publish(
        self,
        generation: str,
        chunks: list[PreparedChunk],
        manifest: dict[str, Any],
        text_index_stage: dict[str, Any],
    ) -> Publication:
        """준비된 벡터와 BM25 색인을 검증한 뒤 활성 세대를 전환함.

        인자: generation은 준비가 끝난 대상 세대이며, chunks와 manifest는 최종 게시 기준임.
        인자: text_index_stage는 build_text_index가 반환한 세대·건수·해시 검증 증거임.
        반환값: 게시된 경로·컬렉션·청크 수를 담은 Publication임.
        예외: 건수·해시·색인 검증 또는 활성 포인터 교체 실패 예외를 호출자에게 전달함.
        부수효과: BM25를 다시 만들지 않고 준비된 두 색인의 활성 세대 포인터를 원자적으로 교체함.
        """
        ...


class ArtifactStorePort(Protocol):
    """체크포인트에 넣기 큰 중간 산출물을 참조로 보관하는 계약임."""

    @abstractmethod
    def save(self, run_id: str, name: str, value: Any) -> str:
        """직렬화 가능한 실행 산출물을 원자적으로 저장함.

        인자: run_id는 실행 범위 식별자이며, name은 같은 실행 안의 산출물 이름임.
        반환값: 이후 load에 그대로 전달할 저장소 참조임.
        예외: 값 직렬화나 파일 쓰기에 실패한 예외를 호출자에게 전달함.
        부수효과: 실행 전용 저장소에 파일을 만들거나 같은 이름의 산출물을 교체함.
        """
        ...

    @abstractmethod
    def load(self, reference: str) -> Any:
        """저장소 참조가 가리키는 실행 산출물을 읽음.

        인자: reference는 같은 ArtifactStorePort가 save에서 반환한 값이어야 함.
        반환값: 저장할 때 전달한 직렬화 가능 값임.
        예외: 허용 경로 밖 참조, 파일 누락, 역직렬화 실패 예외를 호출자에게 전달함.
        부수효과: 산출물 파일을 읽지만 변경하지 않음.
        """
        ...


class ProgressReporterPort(Protocol):
    """그래프 노드가 끝날 때마다 진행 상황을 실행자에게 알리는 계약임."""

    @abstractmethod
    def node_completed(self, node: str, node_seconds: float, total_seconds: float) -> None:
        """성공한 노드 하나의 이름과 소요 시간, 이번 실행의 누적 경과 시간을 알림.

        인자: node_seconds는 이 노드 호출 한 번의 시간이며 배치 노드는 호출마다 따로 알림.
        인자: total_seconds는 이번 run 호출 시작부터의 경과 시간이며 재시도 대기와 노드 사이 처리도 포함함.
        반환값: 없음.
        예외: 알림 실패가 색인 작업을 중단시키지 않도록 구현체는 예외를 호출자에게 전달하지 않아야 함.
        부수효과: 구현체에 따라 화면·로그에 진행 상황을 기록함.
        """
        ...


class PipelineRunnerPort(Protocol):
    """체크포인트를 사용해 인덱싱 단계의 실행과 재개를 제어하는 계약임."""

    @abstractmethod
    def run(self, initial_state: dict[str, Any], thread_id: str) -> dict[str, Any]:
        """새 실행을 시작하거나 동일 요청의 저장된 실행을 이어 감.

        인자: initial_state는 새 실행에 필요한 전체 초기값이며, thread_id는 체크포인트 식별자임.
        반환값: 정상 완료 또는 건식 실행의 단계 결과를 합친 최종 상태임.
        예외: 같은 thread_id의 요청 지문이 다르거나 노드 실행이 실패하면 해당 예외를 전달함.
        부수효과: 체크포인트와 중간 산출물, 대상 색인 세대, 활성 세대를 단계에 따라 변경함.
        """
        ...
