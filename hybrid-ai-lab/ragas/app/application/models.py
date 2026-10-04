"""계층 사이를 오가는 계획 파일 · 실행 상태 · 경로 · 오류 모델."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

# 단계 상태 6종 — state.json에 그대로 기록됨(설계서 「공통 원칙」)
WAITING, RUNNING, SUCCESS, FAILED, UNSUPPORTED, SKIPPED = "대기", "실행 중", "성공", "실패", "미지원", "건너뜀"
STEP_NAMES = {
    "F1": "설정 적용", "F2": "색인", "F3": "검색 · 코드 채점", "F4": "되돌리기",
    "F5": "RAGAS 채점", "F6": "검토표",
}
# 리트리버가 실제로 읽는 환경변수(.env.example) — 이 밖의 이름을 env로 바꾸면 효과가 없어 미지원(V8)
RETRIEVER_ENV_NAMES = frozenset({
    "GROQ_MODEL", "GROQ_REASONING_EFFORT", "RERANK_MODEL", "RERANK_REVISION", "RERANK_MAX_LENGTH",
    "TIMEOUT_C01", "TIMEOUT_C02", "TIMEOUT_C03", "TIMEOUT_C04", "TIME_BUDGET_SECONDS", "MAX_TURNS",
    "MAX_LLM_CALLS", "MAX_REWRITES", "GRADE_UPPER", "GRADE_LOWER", "GRADE_MIN_GAP", "GRADE_MIN_OVERLAP",
    "GRADE_OVERLAP_WAIVER", "HYBRID_VECTOR_WEIGHT", "HYBRID_BM25_WEIGHT", "KEYWORD_MAX_DF_RATIO",
    "DOMAIN_TERM_MIN_DF_RATIO",
})
# 인덱서 설정 파일 이름 → 복사본 경로를 넘기는 환경변수(인덱서 load_settings가 읽는 이름)
INDEXER_CONFIG_ENV = {
    "document_policies.json": "POLICIES_PATH",
    "document_profiles.json": "PROFILES_PATH",
    "metadata_schema.json": "METADATA_SCHEMA_PATH",
    "card_alias_rules.json": "CARD_ALIAS_RULES_PATH",
    "card_alias_overrides.json": "CARD_ALIAS_OVERRIDES_PATH",
}


class QualityError(Exception):
    """품질평가 도구 공통 오류. code로 분류하고 exit_code로 명령행 종료 코드를 정함.

    exit_code: 2 = 실행 전 검사 거부(아무것도 바꾸지 않음), 1 = 실행 중 오류, 130 = 사람이 중단.
    """

    def __init__(self, code: str, message: str, exit_code: int = 1):
        super().__init__(message)
        self.code, self.message, self.exit_code = code, message, exit_code


class StepError(QualityError):
    """단계 하나의 실패. code는 실패 분류 E-CFG · E-EXIT · E-OUT · E-INT · E-API · E-TIME 중 하나임."""


class VersionSpec(BaseModel):
    """버전 하나 — 폴더 이름(id)과 그 버전의 값."""

    id: str = Field(pattern=r"^[A-Za-z0-9_.-]{1,40}$", description="버전 폴더 이름")
    value: int | float | str = Field(description="이 버전에서 쓸 하이퍼 파라미터 값")
    note: str | None = Field(default=None, description="사람용 메모")


class EvalSetSpec(BaseModel):
    """실험에 쓸 평가셋과 그 지문 — 지문이 다르면 실행을 거부함(같은 조건)."""

    path: str = Field(description="평가셋 JSON 경로(ragas 폴더 기준 상대 경로 가능)")
    sha256: str = Field(description="eval_set_hash 값(questions 블록 SHA-256 앞 12자)")


class ScoringSpec(BaseModel):
    """실험 끝까지 고정하는 채점 조건."""

    ragas_provider: Literal["local", "anthropic", "groq"] = Field(description="RAGAS 평가자")
    ragas_repeat: int = Field(ge=1, le=10, description="RAGAS 반복 채점 수")
    human_pass_threshold: float = Field(ge=0.0, le=1.0, description="LLM 점수 합격 기준값(설계 가정 0.5)")


class PlanSpec(BaseModel):
    """계획 파일(plans/{하이퍼 파라미터}.yaml) 한 개 = 하이퍼 파라미터 한 개."""

    schema_version: int = Field(default=1, description="파일 형식 번호")
    hyperparameter: str = Field(pattern=r"^[a-z0-9_]{1,40}$", description="하이퍼 파라미터 이름 = 실험 폴더 이름")
    apply: str = Field(description="바꾸는 종류: config_file · env · code_arg")
    target: str = Field(description="대상 키 한 줄 주소 '{도구}:{종류}:{대상}'")
    reindex: bool = Field(description="재색인이 필요한 계획인지")
    baseline: int | float | str = Field(description="기준 버전 값 = 지금 값")
    versions: list[VersionSpec] = Field(min_length=1, description="기준을 포함한 버전 목록")
    eval_set: EvalSetSpec
    scoring: ScoringSpec


@dataclass(frozen=True)
class RunnerPaths:
    """실행기가 읽고 쓰는 위치. bootstrap이 설정에서 만들어 주입함."""

    ragas_root: Path  # 품질평가 프로그램 폴더(계획 · 실험 · 평가셋 상대 경로의 기준)
    experiments_root: Path  # experiments/ — 하이퍼 파라미터별 폴더가 생김
    indexer_dir: Path  # 인덱서 프로젝트 폴더(설정 원본 config/가 있음)
    data_root: Path  # 인덱서 결과 폴더(active_generation.json이 있음) — 리트리버 DATA_ROOT로도 넘김


def json_safe(value: Any) -> Any:
    """Path처럼 JSON에 바로 못 넣는 값을 글자로 바꿈."""

    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {k: json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(v) for v in value]
    return value
