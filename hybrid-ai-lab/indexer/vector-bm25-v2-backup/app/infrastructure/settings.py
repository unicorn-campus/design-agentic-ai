"""실행 경로와 분할·모델 설정을 읽어 조립 지점에 전달함."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import os
from pathlib import Path
from typing import Any, Mapping

from dotenv import dotenv_values

from app.domain.models import SplitPolicy

APP_ROOT = Path(__file__).resolve().parents[2]  # 실행한 터미널 위치와 무관하게 상대 설정 경로를 해석할 기준


@dataclass(frozen=True)
class Settings:
    """검증한 실행 설정과 처리 정책의 지문을 제공함.

    설정 로더에서 해석한 값을 받으며, 자체적으로 모델을 읽거나 인덱싱을 실행하지 않음.
    속성 재할당은 막지만 내부 딕셔너리까지 불변으로 바꾸지는 않음.
    """

    input_path: Path  # 원천 파일 또는 디렉터리의 절대 경로
    output_path: Path  # 체크포인트·산출물·색인 세대를 저장할 절대 경로
    policies: dict[str, Any]  # 문서별 파일 선택 규칙과 구분자·청크 길이 설정
    profiles: dict[str, Any]  # 문서 유형별 공통 메타데이터 보강값
    metadata_schema: dict[str, Any]  # 필수·허용 필드와 열거값 검증 규칙
    model_name: str  # 문서·질문 임베딩의 호환 기준이 되는 모델 이름
    model_revision: str  # 같은 이름의 모델이 바뀌어도 재현할 수 있게 고정한 revision
    max_tokens: int  # 특수토큰을 포함한 모델 입력 상한(토큰)
    embedding_dimension: int  # 로딩한 모델의 실제 출력과 대조할 예상 벡터 차원
    batch_size: int  # 체크포인트 한 단계에서 임베딩할 최대 청크 수
    device: str  # 모델 계산 장치(cpu·cuda·mps). auto이면 지정하지 않고 라이브러리가 자동 선택함
    local_files_only: bool  # 참이면 로컬 캐시에 없는 모델 파일의 다운로드를 허용하지 않음
    collection: str = "card_docs"  # 검색기와 공유할 벡터 컬렉션 이름

    @property
    def embedding_contract(self) -> dict[str, Any]:
        """기존 벡터를 재사용해도 되는지 판단할 모델·입력 상한·변환 방식의 계약을 반환함."""
        return {"model": self.model_name, "revision": self.model_revision,
                "max_seq_length": self.max_tokens, "dimension": self.embedding_dimension,
                "normalize_embeddings": True,
                "pooling": "sentence-transformers-colbert-conversion-single-vector"}

    @property
    def split_policies(self) -> dict[str, SplitPolicy]:
        """공통 길이와 문서별 구분자를 결합한 정책을 반환하고 잘못된 길이는 ValueError로 거부함."""
        defaults = self.policies["defaults"]
        return {key: SplitPolicy(int(defaults["chunk_size"]), int(defaults["chunk_overlap"]),
                                 tuple(value["separators"]))
                for key, value in self.policies["documents"].items()}

    @property
    def policy_signature(self) -> str:
        """파이프라인 버전·분할 정책·모델 계약의 변경을 감지할 지문을 반환함."""
        # 버전 2는 원문 위치 정렬과 안정적인 문서 식별자를 사용하는 처리 규칙을 구분함.
        return digest({"pipeline_version": 2, "policies": self.policies,
                       "embedding": self.embedding_contract})

    @property
    def profile_signature(self) -> str:
        """보강값이나 허용 메타데이터 규칙이 바뀌면 원문 처리 결과를 다시 검증하도록 지문을 반환함."""
        return digest({"profiles": self.profiles, "metadata_schema": self.metadata_schema})


def digest(value: Any) -> str:
    """설정 딕셔너리의 키 순서에 영향받지 않는 SHA-256 지문을 반환함."""
    return sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def load_settings(overrides: Mapping[str, Any] | None = None) -> Settings:
    """명시한 값·환경변수·앱 .env·기본값 순으로 설정을 선택하고 길이·경로를 검증함.

    인자: overrides의 None 값은 기존 설정을 덮어쓰지 않음. 상대 경로는 앱 루트를 기준으로 해석함.
    반환값: 문서 정책·프로필·메타데이터 스키마를 함께 담은 설정임.
    예외: 잘못된 수치·정책·동일 입출력 경로는 ValueError, 설정 키 누락은 KeyError가 발생할 수 있음.
    예외: JSON 구문 오류는 JSONDecodeError, 파일 읽기 실패는 OSError 계열 예외로 전달됨.
    부수효과: 환경변수와 설정 파일을 읽음. 파일 저장이나 모델 다운로드는 수행하지 않음.
    """
    values = {**dotenv_values(APP_ROOT / ".env"), **os.environ,
              **{key: value for key, value in (overrides or {}).items() if value is not None}}
    def resolve(name: str, default: str | Path) -> Path:
        """호출자의 작업 디렉터리가 달라도 같은 앱 상대 경로를 선택하도록 절대 경로로 변환함."""
        path = Path(str(values.get(name, default))).expanduser()
        return (path if path.is_absolute() else APP_ROOT / path).resolve()
    
    # 청킹 정책: 청킹 최대 크기, 오버랩 사이즈
    # 소스 문서 별 규칙: 파일명 규칙, 문서유형, 접근등급, 머릿말/꼬리말 제거 기준, 청킹 구분자   
    policies = json.loads(resolve("POLICIES_PATH", "config/document_policies.json").read_text(encoding="utf-8-sig"))
    
    # 소스 문서 별 프로파일: 관리부서, 작성일, 시행일, 버전, 이전버전, 합성여부, 
    profiles = json.loads(resolve("PROFILES_PATH", "config/document_profiles.json").read_text(encoding="utf-8-sig"))
    
    # 문서 메타데이터 규칙: 필수 필드, 허용 필드, 선택옵션(문서유형 Key, 문서유형, 접근등급, 관리부서)  
    metadata_schema = json.loads(resolve("METADATA_SCHEMA_PATH", "config/metadata_schema.json").read_text(encoding="utf-8-sig"))
    
    settings = Settings(
        # 소스문서 경로  
        input_path=resolve("INPUT_PATH", "../../docs"),
        # 인덱싱 저장 경로 
        output_path=resolve("OUTPUT_PATH", "data"), policies=policies, profiles=profiles, metadata_schema=metadata_schema,
        # 임베딩 모델 
        model_name=str(values.get("EMBED_MODEL", "nlpai-lab/KURE-v2")),
        # 모델의 Commit ID(버전 역할) 
        # 허깅페이스 저장소에서 확인-> https://huggingface.co/nlpai-lab/KURE-v2 에서 Files and versions → History
        model_revision=str(values.get("EMBED_REVISION", "3431f86d399d666083890dbb882aced6708873bc")),
        # 청크 최대 크기 
        max_tokens=int(values.get("EMBED_MAX_TOKENS", 800)),
        # 청크를 임베딩한 각 벡터의 차원 수(숫자 개수)
        embedding_dimension=int(values.get("EMBED_DIMENSION", 768)),
        # 한번에 임베딩 하는 최대 청크 수
        batch_size=int(values.get("EMBED_BATCH_SIZE", 8)),
        # 임베딩 처리 장치(cpu/cuda/mps/auto): auto로 지정하면 임베딩 수행 시 device 인자 안넘겨 자동으로 지정하도록 함
        device=str(values.get("EMBED_DEVICE", "auto")),
        # 로컬에 캐시된 임베딩 모델만 사용할지 여부
        # true이면 최초 download 필요: hf download nlpai-lab/KURE-v2 --revision 3431f86d399d666083890dbb882aced6708873bc
        local_files_only=str(values.get("HF_LOCAL_FILES_ONLY", "true")).lower() in {"1", "true", "yes"},
    )
    if settings.batch_size <= 0 or settings.max_tokens <= 0 or settings.embedding_dimension <= 0:
        raise ValueError("배치 크기와 토큰 상한은 양수여야 합니다.")
    if any(policy.chunk_size > settings.max_tokens for policy in settings.split_policies.values()):
        raise ValueError("청크 크기는 임베딩 입력 토큰 상한보다 클 수 없습니다.")
    if settings.output_path == settings.input_path:
        raise ValueError("원문 경로와 결과 경로는 서로 달라야 합니다.")
    return settings
