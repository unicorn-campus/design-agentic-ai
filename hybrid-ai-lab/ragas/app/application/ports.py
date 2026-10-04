"""서비스가 필요로 하는 바깥 기능의 약속(포트). 구현은 infrastructure, 조립은 bootstrap이 맡음."""

from __future__ import annotations

from abc import abstractmethod
from pathlib import Path
from typing import Any, Protocol

from app.domain.verification import Chunk


class ArtifactStorePort(Protocol):
    """평가셋 · 로그 · 상태 파일을 읽고 쓰는 계약."""

    @abstractmethod
    def exists(self, path: Path) -> bool:
        """파일이 있는지 봄. 부수효과: 없음."""

    @abstractmethod
    def read_text(self, path: Path) -> str:
        """UTF-8 글자로 읽음(BOM은 떼어 냄). 예외: 파일이 없으면 FileNotFoundError."""

    @abstractmethod
    def read_json(self, path: Path) -> Any:
        """JSON을 읽음. 예외: 파일이 없으면 FileNotFoundError, 형식 오류면 ValueError."""

    @abstractmethod
    def read_yaml(self, path: Path) -> Any:
        """YAML(계획 파일)을 읽음. 예외: 파일이 없으면 FileNotFoundError, 형식 오류면 ValueError."""

    @abstractmethod
    def write_text(self, path: Path, text: str) -> None:
        """임시 파일에 쓴 뒤 바꿔치기함 — 반쯤 쓰다 끊긴 파일이 남지 않음. 부수효과: 상위 폴더를 만듦."""

    @abstractmethod
    def write_json(self, path: Path, value: Any) -> None:
        """JSON을 들여쓰기 2칸 · 한글 그대로 원자적으로 씀. 부수효과: 상위 폴더를 만듦."""

    @abstractmethod
    def append_text(self, path: Path, text: str) -> None:
        """파일 끝에 글자를 덧붙임(실험 세대 목록용). 부수효과: 파일 · 상위 폴더를 만듦."""

    @abstractmethod
    def read_csv(self, path: Path) -> list[dict[str, str]]:
        """머리 행이 있는 CSV를 행 dict 목록으로 읽음(UTF-8, BOM 허용)."""

    @abstractmethod
    def write_csv(self, path: Path, header: list[str], rows: list[dict[str, Any]]) -> None:
        """엑셀에서 한글이 깨지지 않게 BOM 붙은 UTF-8 CSV로 씀."""


class CorpusPort(Protocol):
    """사용 중 색인 세대의 조각 본문을 읽는 계약(평가셋 검증 ① ② ④용)."""

    @abstractmethod
    def active_generation(self) -> str:
        """사용 중 세대 이름. 예외: 포인터가 없거나 깨졌으면 QualityError("index_unavailable")."""

    @abstractmethod
    def chunks(self) -> list[Chunk]:
        """사용 중 세대의 조각 전부. 반환값: 출처 · 본문 · 혜택 코드를 담은 Chunk 목록.

        예외: 말뭉치 파일을 못 찾으면 QualityError("index_unavailable"). 부수효과: 없음(읽기 전용).
        """


class JudgePort(Protocol):
    """RAGAS 지표 하나를 평가자 LLM으로 채점하는 계약."""

    @abstractmethod
    def describe(self) -> dict[str, str]:
        """같은 조건 확인용 평가자 정보 — provider · model · embedding_model 키를 가진 dict."""

    @abstractmethod
    async def score(self, metric: str, fields: dict[str, Any]) -> tuple[float, str | None]:
        """지표 이름과 그 지표가 읽는 칸만 담은 fields로 채점함.

        인자: metric은 scoring.METRICS 중 하나. fields 키는 scoring.METRIC_FIELDS[metric]과 같음.
        반환값: (0 ~ 1 점수, 판정 이유 또는 None).
        예외: 평가자 호출 · 구조화 출력 실패는 그대로 올림 — 서비스가 failed_scores에 기록함.
        부수효과: 평가자 LLM · 임베딩 모델 호출.
        """


class IndexerPort(Protocol):
    """인덱서를 하위 프로세스로 돌려 새 색인 세대를 만드는 계약."""

    @abstractmethod
    def reindex(self, thread_id: str, env: dict[str, str], log_dir: Path) -> str:
        """전체 재색인을 돌리고 게시된 세대 이름을 돌려줌.

        인자: env는 하위 프로세스에만 얹는 환경변수(설정 복사본 경로 등). 원본 .env는 건드리지 않음.
        반환값: 게시된 세대 이름(gen-…). 성공하면 사용 중 세대 포인터가 이 세대로 바뀌어 있음.
        예외: 종료 코드가 0이 아니면 StepError("E-EXIT"), 결과 JSON을 못 읽으면 StepError("E-OUT"),
              중단(130)이면 StepError("E-INT").
        부수효과: 세대 폴더 · 체크포인트 · 포인터 변경, log_dir에 표준 출력 · 오류 기록.
        """


class RetrieverEvalPort(Protocol):
    """리트리버 평가 스크립트(검색 · 코드 채점)를 하위 프로세스로 돌리는 계약."""

    @abstractmethod
    def supports(self, argument: str) -> bool:
        """평가 스크립트가 그 인자를 아는지 --help로 확인함(V9). 부수효과: 하위 프로세스 1회."""

    @abstractmethod
    def run(self, args: list[str], env: dict[str, str], log_dir: Path) -> None:
        """평가 스크립트를 돌림. 결과 파일 위치는 args의 --out이 정함.

        예외: 종료 코드가 0이 아니면 StepError("E-EXIT"), 중단이면 StepError("E-INT").
        부수효과: Groq 호출 · 감사 로그 · 결과 파일 생성, log_dir에 표준 출력 · 오류 기록.
        """


class PointerPort(Protocol):
    """사용 중 세대 포인터(active_generation.json) 한 개를 읽고 바꾸는 계약."""

    @abstractmethod
    def read(self) -> dict[str, Any]:
        """포인터 내용. 예외: 파일이 없거나 깨졌으면 QualityError("pointer_unavailable")."""

    @abstractmethod
    def sha256(self) -> str:
        """포인터 파일 바이트의 SHA-256 — 복원 확인에 씀."""

    @abstractmethod
    def write(self, content: dict[str, Any]) -> str:
        """포인터를 원자적으로 바꾸고 새 SHA-256을 돌려줌.

        부수효과: 인덱서와 같은 게시 잠금을 잡고 바꿈 — 떠 있는 리트리버는 다음 요청부터 그 세대를 씀.
        예외: 게시 잠금을 못 얻으면 QualityError("lock_unavailable").
        """


class LockPort(Protocol):
    """실행기 한 개만 실험하게 막는 잠금 계약(포인터가 실험 세대인 동안 다른 실행이 끼어들지 못하게 함)."""

    @abstractmethod
    def acquire(self) -> None:
        """기다리지 않고 잠금을 얻음. 예외: 다른 실행이 잡고 있으면 QualityError("lock_unavailable", exit 2)."""

    @abstractmethod
    def release(self) -> None:
        """잠금을 놓음. 잡지 않았으면 아무것도 하지 않음."""


class ServerProbePort(Protocol):
    """같은 DATA_ROOT를 보는 검색 API 서버가 떠 있는지 보는 계약(V14)."""

    @abstractmethod
    def running_servers(self) -> list[str]:
        """응답한 서버 주소 목록. 비어 있으면 실험해도 됨. 부수효과: 짧은 HTTP 요청."""


class EnvironmentPort(Protocol):
    """설정 스냅샷에 넣을 재현 정보를 모으는 계약."""

    @abstractmethod
    def snapshot(self) -> dict[str, Any]:
        """git 커밋 · 가상환경 python 판 · 장치 · 비밀값 설정 여부(값은 넣지 않음)를 담은 dict."""
