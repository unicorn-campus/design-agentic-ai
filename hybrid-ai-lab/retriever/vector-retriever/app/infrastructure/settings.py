"""환경변수와 .env 파일에서 실행 설정을 읽어 불변 Settings로 담는 설정 로더임."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import dotenv_values

from app.domain.budget import C_01, C_02, C_03, C_04, BudgetPolicy
from app.domain.grading import GradeThresholds

ROOT = Path(__file__).resolve().parents[2]  # vector-retriever 프로젝트 루트
LAB_ROOT = ROOT.parents[1]  # hybrid-ai-lab 루트. 공용 .env(GROQ_API_KEY)를 여기에 둠

# 기본값 상수. 값의 근거는 Settings 필드의 줄 끝 주석에 적음
DEFAULT_DATA_ROOT = "../../indexer/vector-bm25/data"
DEFAULT_EMBED_MODEL = "nlpai-lab/KURE-v2"
DEFAULT_EMBED_REVISION = "3431f86d399d666083890dbb882aced6708873bc"
DEFAULT_RERANK_MODEL = "BAAI/bge-reranker-v2-m3"
DEFAULT_RERANK_REVISION = "953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e"
DEFAULT_GROQ_MODEL = "openai/gpt-oss-120b"
DEFAULT_AUDIT_LOG_PATH = "logs/audit.jsonl"

# .env 값이 참으로 인정되는 표기. 대소문자는 가리지 않음
_TRUE_WORDS = frozenset({"1", "true", "yes", "y", "on"})


@dataclass(frozen=True)
class Settings:
    """리트리버 1개 프로세스의 실행 설정값. 조립은 bootstrap이 하고 이 객체는 값만 담음.

    비밀값(groq_api_key)은 repr에서 가림. 값 검증은 load_settings가 끝낸 뒤 이 객체를 만듦.
    """

    data_root: Path  # 색인 세대 폴더의 뿌리(W-1 indexer/vector-bm25/data). 절대 경로로 해석해 둠
    audit_log_path: Path  # 감사 로그 파일 경로. 절대 경로로 해석해 둠(설계 S-R9 ④)
    groq_api_key: str = field(default="", repr=False)  # Groq 비밀키. 비면 LLM 단계가 대체 경로로 감
    embed_model: str = DEFAULT_EMBED_MODEL  # 질의 임베딩 모델. 색인과 같은 모델이어야 함(색인 계약 4)
    embed_revision: str = DEFAULT_EMBED_REVISION  # 임베딩 모델 revision 고정값(색인 계약 4·5)
    embed_device: str = "auto"  # 임베딩 실행 장치. auto·cpu·cuda·mps 중 하나(설계 ⑥-5)
    embed_max_tokens: int = 800  # 임베딩 입력 상한 토큰 수(색인 계약, 조각 생성 기준과 동일)
    embed_dimension: int = 768  # 임베딩 차원. 다르면 S-R1이 검색을 거부함(색인 계약 3)
    hf_local_files_only: bool = True  # 참이면 모델 파일을 내려받지 않고 로컬 캐시만 씀(망 차단 환경 기본)
    rerank_model: str = DEFAULT_RERANK_MODEL  # Cross-Encoder 리랭커 모델(설계 ⑥-7)
    rerank_revision: str = DEFAULT_RERANK_REVISION  # 리랭커 revision 고정값
    rerank_max_length: int = 1024  # 리랭커 입력 상한 토큰 수. 설계 512 → 1024 변경(사용자 결정, 2026-10-03)
    groq_model: str = DEFAULT_GROQ_MODEL  # C-01 ~ C-04가 쓰는 Groq 모델(설계 ③)
    groq_reasoning_effort: str = "low"  # Groq 추론 강도. 지연을 낮추려고 low로 둠(설계 가정)
    timeout_c01: float = 2.5  # C-01 질문 분석 타임아웃(초, 설계 ③)
    timeout_c02: float = 1.5  # C-02 행동 선택 타임아웃(초, 설계 ③)
    timeout_c03: float = 1.2  # C-03 질문 변환 타임아웃(초, 설계 ③)
    timeout_c04: float = 2.5  # C-04 답변 생성 타임아웃(초, 설계 ③)
    time_budget_seconds: float = 30.0  # 요청 1건의 총 시간 예산(초, 설계 ⑤)
    closing_seconds: float = 1.5  # S-R9 몫으로 떼어 두는 종료 처리 시간(초, 설계 ⑥-10)
    start_threshold_seconds: float = 1.5  # 단계 시작 기준(초). 남은 예산이 이 값 미만이면 착지(설계 ⑥-10)
    max_turns: int = 6  # L-1 회전 상한. S-R3 진입 횟수로 셈(설계 ④)
    max_llm_calls: int = 16  # 요청당 LLM 호출 상한 = C-01 1 + C-02 6 + C-03 6 + C-04 3(설계 ③)
    max_rewrites: int = 2  # L-2 답변 재작성 상한(설계 ④)
    grade_upper: float = 0.7  # 채점 주 점수 상한. 이상이면 정확 후보(설계 ⑥-8, 설계 가정)
    grade_lower: float = 0.3  # 채점 주 점수 하한. 미만이면 부정확(설계 ⑥-8, 설계 가정)
    grade_min_gap: float = 0.05  # 1·2위 최소 격차(설계 ⑥-8, 설계 가정)
    grade_min_overlap: int = 1  # 벡터·BM25 상위 k 최소 겹침 수(설계 ⑥-8, 설계 가정)
    hybrid_vector_weight: float = 0.6  # 하이브리드 합치기의 벡터 비중(설계 ⑥-6, 재검증 대상)
    hybrid_bm25_weight: float = 0.4  # 하이브리드 합치기의 BM25 비중(설계 ⑥-6, 재검증 대상)
    keyword_max_df_ratio: float = 0.1  # 채점 핵심어로 쓸 낱말의 문서 빈도 상한 비율(설계 ⑥-8)
    api_host: str = "127.0.0.1"  # API 서버가 듣는 주소. 기본은 로컬만 염(설계 ⑦)
    api_port: int = 8020  # API 서버 포트. 코드에 박지 않고 설정으로 바꿀 수 있게 둠

    def budget_policy(self) -> BudgetPolicy:
        """시간 예산·반복 상한 설정값을 도메인 규칙이 쓰는 BudgetPolicy로 바꿈.

        방법: 커넥터 최악값은 '타임아웃 × (재시도 0 + 1)'이라 타임아웃 값을 그대로 넣음(설계 ③).
        반환값: BudgetPolicy. 설정 항목이 없는 max_sub_questions·max_search_fail_streak는 도메인 기본값을 씀.
        """

        return BudgetPolicy(
            total_seconds=self.time_budget_seconds,
            closing_seconds=self.closing_seconds,
            start_threshold_seconds=self.start_threshold_seconds,
            max_turns=self.max_turns,
            max_llm_calls=self.max_llm_calls,
            max_rewrites=self.max_rewrites,
            connector_worst_seconds={
                C_01: self.timeout_c01,
                C_02: self.timeout_c02,
                C_03: self.timeout_c03,
                C_04: self.timeout_c04,
            },
        )

    def grade_thresholds(self) -> GradeThresholds:
        """채점 기준값 설정을 도메인 규칙이 쓰는 GradeThresholds로 바꿈."""

        return GradeThresholds(
            upper=self.grade_upper,
            lower=self.grade_lower,
            min_gap=self.grade_min_gap,
            min_overlap=self.grade_min_overlap,
        )


def _read_env_files(env_path: Path | None) -> dict[str, str]:
    """.env 파일을 읽어 합침. 먼저 읽은 파일의 값을 우선함(프로젝트 .env > 공용 .env)."""

    files = [env_path] if env_path is not None else [ROOT / ".env", LAB_ROOT / ".env"]
    merged: dict[str, str] = {}
    for path in files:
        if path is None or not path.is_file():
            continue
        for key, value in dotenv_values(path, interpolate=False).items():
            if value is not None and key not in merged:
                merged[key] = value
    return merged


def _resolve_path(raw: str, default: str) -> Path:
    """상대 경로를 프로젝트 루트 기준 절대 경로로 바꿈.

    목적: 실행 작업 디렉터리가 달라도 같은 색인·로그를 가리키게 함.
    반환값: 절대 경로. 값이 비면 default를 씀.
    """

    text = raw.strip() or default
    candidate = Path(text).expanduser()
    if not candidate.is_absolute():
        candidate = ROOT / candidate
    return Path(os.path.normpath(candidate))


def load_settings(env_path: Path | None = None) -> Settings:
    """환경변수와 .env에서 설정을 읽어 Settings를 만듦.

    목적: 비밀값과 환경별 값(경로·포트·모델)을 코드에서 떼어 냄.
    방법: 프로젝트 .env → 공용 .env 순으로 읽고, 같은 키는 환경변수를 가장 우선함.
    인자: env_path를 주면 그 파일만 읽음(시험에서 격리용).
    반환값: 값 검증을 마친 불변 Settings임.
    예외: 숫자로 읽을 수 없거나 허용 범위를 벗어난 값이 있으면 ValueError를 발생시킴(값은 메시지에 넣지 않음).
    """

    values = _read_env_files(env_path)

    def text(key: str, default: str = "") -> str:
        """문자열 설정값을 환경변수 → .env 순서로 찾아 반환함."""
        # 환경변수가 최우선. 빈 문자열은 '설정하지 않음'으로 보고 다음 출처로 넘어감
        return os.environ.get(key) or values.get(key) or default

    def flag(key: str, default: bool) -> bool:
        """참·거짓 설정값을 읽음."""
        raw = text(key)
        return raw.strip().lower() in _TRUE_WORDS if raw else default

    def number(key: str, default: float, *, minimum: float, maximum: float) -> float:
        """실수 설정값을 읽고 허용 범위를 확인함."""
        raw = text(key)
        if not raw:
            return default
        try:
            parsed = float(raw)
        except ValueError as error:
            raise ValueError(f"{key} 값을 숫자로 읽을 수 없습니다.") from error
        if not minimum <= parsed <= maximum:
            raise ValueError(f"{key} 값이 허용 범위({minimum} ~ {maximum})를 벗어났습니다.")
        return parsed

    def count(key: str, default: int, *, minimum: int, maximum: int) -> int:
        """정수 설정값을 읽고 허용 범위를 확인함."""
        return int(number(key, default, minimum=minimum, maximum=maximum))

    return Settings(
        data_root=_resolve_path(text("DATA_ROOT"), DEFAULT_DATA_ROOT),
        audit_log_path=_resolve_path(text("AUDIT_LOG_PATH"), DEFAULT_AUDIT_LOG_PATH),
        groq_api_key=text("GROQ_API_KEY"),
        embed_model=text("EMBED_MODEL", DEFAULT_EMBED_MODEL),
        embed_revision=text("EMBED_REVISION", DEFAULT_EMBED_REVISION),
        embed_device=text("EMBED_DEVICE", "auto"),
        embed_max_tokens=count("EMBED_MAX_TOKENS", 800, minimum=1, maximum=8192),
        embed_dimension=count("EMBED_DIMENSION", 768, minimum=1, maximum=8192),
        hf_local_files_only=flag("HF_LOCAL_FILES_ONLY", True),
        rerank_model=text("RERANK_MODEL", DEFAULT_RERANK_MODEL),
        rerank_revision=text("RERANK_REVISION", DEFAULT_RERANK_REVISION),
        rerank_max_length=count("RERANK_MAX_LENGTH", 1024, minimum=1, maximum=8192),
        groq_model=text("GROQ_MODEL", DEFAULT_GROQ_MODEL),
        groq_reasoning_effort=text("GROQ_REASONING_EFFORT", "low"),
        timeout_c01=number("TIMEOUT_C01", 2.5, minimum=0.1, maximum=60.0),
        timeout_c02=number("TIMEOUT_C02", 1.5, minimum=0.1, maximum=60.0),
        timeout_c03=number("TIMEOUT_C03", 1.2, minimum=0.1, maximum=60.0),
        timeout_c04=number("TIMEOUT_C04", 2.5, minimum=0.1, maximum=60.0),
        time_budget_seconds=number("TIME_BUDGET_SECONDS", 30.0, minimum=1.0, maximum=600.0),
        closing_seconds=number("CLOSING_SECONDS", 1.5, minimum=0.1, maximum=60.0),
        start_threshold_seconds=number("START_THRESHOLD_SECONDS", 1.5, minimum=0.1, maximum=60.0),
        max_turns=count("MAX_TURNS", 6, minimum=1, maximum=50),
        max_llm_calls=count("MAX_LLM_CALLS", 16, minimum=1, maximum=200),
        max_rewrites=count("MAX_REWRITES", 2, minimum=0, maximum=10),
        grade_upper=number("GRADE_UPPER", 0.7, minimum=0.0, maximum=1.0),
        grade_lower=number("GRADE_LOWER", 0.3, minimum=0.0, maximum=1.0),
        grade_min_gap=number("GRADE_MIN_GAP", 0.05, minimum=0.0, maximum=1.0),
        grade_min_overlap=count("GRADE_MIN_OVERLAP", 1, minimum=0, maximum=50),
        hybrid_vector_weight=number("HYBRID_VECTOR_WEIGHT", 0.6, minimum=0.0, maximum=1.0),
        hybrid_bm25_weight=number("HYBRID_BM25_WEIGHT", 0.4, minimum=0.0, maximum=1.0),
        keyword_max_df_ratio=number("KEYWORD_MAX_DF_RATIO", 0.1, minimum=0.0, maximum=1.0),
        api_host=text("API_HOST", "127.0.0.1"),
        api_port=count("API_PORT", 8020, minimum=1, maximum=65535),
    )
