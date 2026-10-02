"""로딩부터 게시까지 공유하는 문서·청크·세대 데이터를 정의함."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class SourceRef:
    """발견한 원천의 위치와 변경 판단에 쓸 지문을 보관함.

    원천 탐색 포트에서 만든 값을 받으며, 파일을 읽거나 변경 여부를 직접 판정하지 않음.
    """

    path: str  # 로더가 읽을 원천 파일의 절대 경로
    source: str  # 세대가 달라도 원천을 식별하는 파일명
    doc_key: str  # 적용할 문서 정책의 키(D1 약관·D2 혜택·D3 상담)
    sha256: str  # 원천 바이트의 SHA-256 지문으로 내용 변경을 확인함


@dataclass(frozen=True)
class TextSpan:
    """원문의 문자 구간과 그 구간에 적용할 값을 보관함.

    로더가 계산한 좌표를 받으며, 텍스트를 직접 자르거나 치환하지 않음.
    """

    start: int  # 원문에서 포함할 첫 문자 위치(0부터 시작)
    end: int  # 포함하지 않을 끝 위치로 Python 슬라이스와 같은 기준임
    value: Any = None  # 페이지 번호·문맥 정보·개인정보 대체 문자열 등 구간의 용도별 값


@dataclass(frozen=True)
class LoadedDocument:
    """정제·가명처리를 마친 본문과 메타데이터 계산용 위치 정보를 메모리 안에서 전달함.

    로더의 결과를 받음. 위치 정보는 정제된 본문 기준이며 청크 메타데이터를 계산할 때만 쓰고 저장하지 않음.
    """

    document_id: str  # 원문 내용이 바뀌어도 유지할 문서 식별자
    source: str  # 검색 결과의 출처를 표시할 원천 파일명
    doc_key: str  # 적용할 문서 유형별 정책의 키
    text: str  # 여백 제거·줄 잇기·표 변환·개인정보 치환을 마친 본문
    metadata: dict[str, Any] = field(default_factory=dict)  # 문서 전체에 공통인 출처·접근 범위 정보
    page_spans: tuple[TextSpan, ...] = ()  # 정제된 본문의 문자 위치와 페이지 번호의 대응
    context_spans: tuple[TextSpan, ...] = ()  # 조항·카드·상담 건의 문맥이 유효한 정제 본문 구간
    pseudonymized: bool = False  # 로드 단계에서 개인정보를 치환·일반화했는지 여부


@dataclass(frozen=True)
class SplitPolicy:
    """문서 유형별로 공통 분할기에 적용할 경계와 길이 조건을 보관함.

    조립 지점이 설정에서 만든 값을 받으며, 토큰 계산이나 실제 분할은 수행하지 않음.
    """

    chunk_size: int = 800  # 사용자 확정 청크 상한(임베딩 특수토큰을 포함한 토큰 수)
    chunk_overlap: int = 200  # 사용자 확정 중첩 상한으로 실제 중첩은 분할 경계에 따라 달라짐
    separators: tuple[str, ...] = (r"\n\n", r"\n", " ", "")  # 먼저 시도할 정규식 경계부터 나열함

    def __post_init__(self) -> None:
        """분할이 앞으로 진행할 수 없는 크기·중첩·최후 구분자 조합을 ValueError로 거부함."""
        if self.chunk_size <= 0 or not 0 <= self.chunk_overlap < self.chunk_size:
            raise ValueError("청크 크기는 양수이고 중첩은 크기보다 작아야 합니다.")
        if not self.separators or self.separators[-1] != "":
            raise ValueError("구분자의 마지막에는 긴 문자열을 나눌 빈 문자열이 필요합니다.")


@dataclass(frozen=True)
class RawChunk:
    """분할 결과와 문서 본문의 대응 위치를 검증 단계에 전달함.

    분할 포트의 출력을 받음. 로더가 정제를 마친 본문을 나눈 것이지만 저장 전 잔존 검사는 별도로 필요함.
    """

    document: LoadedDocument  # 쪽·조항 메타데이터를 계산할 정제 본문 문서
    text: str  # 분할 텍스트. 표가 잘려 이어지는 청크는 앞에 표 머리글 행이 덧붙어 본문 구간과 다를 수 있음
    start: int  # 정제 본문 기준 첫 문자 위치(포함). 메타데이터 계산에만 쓰고 저장하지 않음
    end: int  # 정제 본문 기준 끝 문자 위치(미포함). 메타데이터 계산에만 쓰고 저장하지 않음
    ordinal: int  # 해당 문서에서 분할된 순서(0부터 시작)
    # 하드 경계로 나눈 구간이 이 청크에 강제할 메타데이터·머리말 규칙(domain.segments.SegmentBinding).
    # 순환 import를 피하려고 타입을 Any로 두며, None이면 경계 분할을 쓰지 않는 문서임.
    binding: Any = None


@dataclass(frozen=True)
class PreparedChunk:
    """정제·개인정보 검사 후 저장할 청크와 변경 판단용 지문을 보관함.

    처리 포트가 만든 값을 받으며, 벡터 생성과 저장소 적재는 수행하지 않음.
    """

    chunk_id: str  # 처리 직후 기본 ID이며 응용 계층에서 동일 본문 발생 순번을 붙여 확정함
    text: str  # 저장·표시·인용 검증에 쓰는 원래 본문. 색인용 머리말은 들어 있지 않음
    metadata: dict[str, Any]  # 검색 필터·출처 표시와 재실행 검증에 사용할 정보
    token_count: int  # 색인용 텍스트를 실제 임베딩 토크나이저로 센 특수토큰 포함 길이
    text_hash: str  # 색인용 텍스트가 같으면 기존 벡터를 재사용하기 위한 지문
    metadata_hash: str  # 본문과 구분하여 메타데이터 변경을 확인하기 위한 지문
    # 임베딩 입력과 BM25 토큰화에 쓰는 텍스트. 머리말이 없으면 빈 문자열이고 이때는 text와 같음
    index_text: str = ""

    @property
    def embedding_text(self) -> str:
        """임베딩·BM25에 넣을 색인용 텍스트를 반환함. 머리말이 없으면 원래 본문임."""

        return self.index_text or self.text


@dataclass(frozen=True)
class IndexSnapshot:
    """활성 세대의 청크와 구축 조건을 한 묶음으로 전달함.

    저장소 포트가 읽은 값을 받으며, 다른 세대로의 전환이나 파일 접근은 수행하지 않음.
    """

    chunks: tuple[PreparedChunk, ...]  # 현재 게시된 청크 전체
    manifest: dict[str, Any]  # 원천 지문·정책·모델 계약·게시 경로 등 해당 세대의 구축 기록


@dataclass(frozen=True)
class Publication:
    """검증을 마친 벡터·키워드 인덱스의 게시 위치를 전달함.

    저장소 포트의 게시 결과를 받으며, 경로를 직접 전환하거나 검색기를 재시작하지 않음.
    """

    generation: str  # 벡터와 키워드 인덱스를 함께 식별하는 세대 ID
    chroma_path: str  # 게시된 벡터 저장소의 절대 경로
    search_index_root: str  # 같은 세대의 corpus·BM25 파일 묶음이 있는 절대 경로
    collection: str  # 검색기가 열어야 할 벡터 컬렉션 이름
    chunk_count: int  # 두 인덱스에서 일치함을 확인한 청크 건수
