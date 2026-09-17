"""Indexer 실행에 필요한 설정을 읽고 검증하는 로더."""

from __future__ import annotations

import math
import os
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any, Callable, Mapping

from dotenv import dotenv_values
from pydantic import SecretStr


APP_DIR = Path(__file__).resolve().parents[1]
LAB_ROOT = APP_DIR.parents[1]


class LLMConfigError(ValueError):
    """설정값이 없거나 안전하게 변환할 수 없을 때 발생함."""


@dataclass(frozen=True)
class Settings:
    """허용된 설정값과 각 값의 출처를 보관하는 불변 객체."""

    values: Mapping[str, Any]
    sources: Mapping[str, str]

    def __getattr__(self, name: str) -> Any:
        try:
            return self.values[name]
        except KeyError as error:
            raise AttributeError(name) from error

    def get(self, name: str, default: Any = None) -> Any:
        return self.values.get(name, default)


@dataclass(frozen=True)
class _Spec:
    default: Any | Callable[[], Any]
    parser: Callable[[str, Any], Any]
    secret: bool = False
    aliases: tuple[str, ...] = ()


def _text(name: str, value: Any) -> str:
    del name
    return str(value).strip()


def _positive_int(name: str, value: Any) -> int:
    try:
        parsed = int(str(value).strip())
    except (TypeError, ValueError) as error:
        raise LLMConfigError(f"{name}은 양의 정수여야 함") from error
    if parsed <= 0:
        raise LLMConfigError(f"{name}은 양의 정수여야 함")
    return parsed


def _non_negative_int(name: str, value: Any) -> int:
    try:
        parsed = int(str(value).strip())
    except (TypeError, ValueError) as error:
        raise LLMConfigError(f"{name}은 0 이상의 정수여야 함") from error
    if parsed < 0:
        raise LLMConfigError(f"{name}은 0 이상의 정수여야 함")
    return parsed


def _positive_float(name: str, value: Any) -> float:
    try:
        parsed = float(str(value).strip())
    except (TypeError, ValueError) as error:
        raise LLMConfigError(f"{name}은 양수여야 함") from error
    if not math.isfinite(parsed) or parsed <= 0:
        raise LLMConfigError(f"{name}은 양수여야 함")
    return parsed


def _non_negative_float(name: str, value: Any) -> float:
    try:
        parsed = float(str(value).strip())
    except (TypeError, ValueError) as error:
        raise LLMConfigError(f"{name}은 0 이상의 수여야 함") from error
    if not math.isfinite(parsed) or parsed < 0:
        raise LLMConfigError(f"{name}은 0 이상의 수여야 함")
    return parsed


def _unit_float(name: str, value: Any) -> float:
    parsed = _positive_float(name, value)
    if parsed > 1:
        raise LLMConfigError(f"{name}은 0 초과 1 이하여야 함")
    return parsed


def _path(name: str, value: Any) -> Path:
    del name
    path = Path(str(value).strip()).expanduser()
    return path if path.is_absolute() else APP_DIR / path


def _choice(*allowed: str) -> Callable[[str, Any], str]:
    def parse(name: str, value: Any) -> str:
        parsed = str(value).strip().lower()
        if parsed not in allowed:
            raise LLMConfigError(f"{name}은 다음 중 하나여야 함: {', '.join(allowed)}")
        return parsed

    return parse


def _default_chroma_path() -> Path:
    if APP_DIR.name == "indexer":
        return APP_DIR / "data" / "chroma"
    return APP_DIR.parent / "indexer" / "data" / "chroma"


def _default_transform_cache_path() -> Path:
    return APP_DIR / "data" / "transform_cache.json"


# 계획서 1-3절과 1-3-2절의 모든 키를 한 곳에서만 허용함.
_SPECS: dict[str, _Spec] = {
    "CHROMA_PATH": _Spec(_default_chroma_path, _path),  # Chroma 벡터 DB가 저장된 디렉터리
    "CHROMA_COLLECTION": _Spec("card_docs", _text),  # 검색할 Chroma 컬렉션 이름
    "EMBED_MODEL": _Spec("nlpai-lab/KURE-v2", _text),  # 질문을 벡터로 변환할 임베딩 모델
    "RERANK_MODEL": _Spec("BAAI/bge-reranker-v2-m3", _text),  # 후보 문서 순위를 다시 매길 모델
    "LLM_PROVIDER": _Spec("groq", _choice("groq", "claude", "openai")),  # 답변에 사용할 LLM 제공자
    "GROQ_API_KEY": _Spec(None, _text, True),  # Groq 인증 키이며 로그에서 가리는 비밀값
    "GROQ_MODEL": _Spec("openai/gpt-oss-120b", _text),  # Groq를 선택했을 때 호출할 모델
    "CLAUDE_API_KEY": _Spec(None, _text, True, ("ANTHROPIC_API_KEY",)),  # Claude 인증 키와 대체 환경변수
    "CLAUDE_MODEL": _Spec("claude-opus-5", _text),  # Claude를 선택했을 때 호출할 모델
    "OPENAI_API_KEY": _Spec(None, _text, True),  # OpenAI 인증 키이며 로그에서 가리는 비밀값
    "OPENAI_MODEL": _Spec(None, _text),  # OpenAI를 선택했을 때 호출할 모델
    "LLM_TIMEOUT_SECONDS": _Spec(60, _positive_float),  # LLM 호출 한 번의 제한 시간(초)
    "LLM_MAX_TOKENS_ANSWER": _Spec(2000, _positive_int),  # 최종 답변이 생성할 최대 토큰 수
    "MAX_LLM_CALLS_CLI": _Spec(8, _positive_int),  # CLI 실행 한 번에 허용할 LLM 호출 상한
    "MAX_LLM_CALLS_PER_REQUEST": _Spec(2, _positive_int),  # API 요청 한 건의 LLM 호출 상한
    "MAX_LLM_CALLS_TOTAL": _Spec(200, _positive_int),  # 서버 프로세스 전체의 누적 LLM 호출 상한
    "REQUEST_TIMEOUT_SECONDS": _Spec(120, _positive_float),  # Retriever 요청 전체의 제한 시간(초)
    "API_HOST": _Spec("127.0.0.1", _text),  # API 서버가 접속을 받을 호스트 주소
    "API_PORT": _Spec(8001, _positive_int),  # API 서버가 사용할 포트 번호
    "TOP_K_DEFAULT": _Spec(5, _positive_int),  # 별도 지정이 없을 때 반환할 최종 문서 수
    "CANDIDATE_MULTIPLIER": _Spec(4, _positive_int),  # 최종 문서 수 대비 먼저 가져올 후보 배수
    "HYBRID_WEIGHT_BM25": _Spec(0.4, _non_negative_float),  # 하이브리드 검색의 BM25 점수 비중
    "HYBRID_WEIGHT_VECTOR": _Spec(0.6, _non_negative_float),  # 하이브리드 검색의 벡터 점수 비중
    "ANSWER_GATE_THRESHOLD": _Spec(0.62, _unit_float),  # 답변에 쓸 근거가 충분한지 판단할 점수 기준
    "RERANK_MAX_LENGTH": _Spec(512, _positive_int),  # 리랭커에 넣을 질문·문서의 최대 토큰 길이
    "TRANSFORM_MODE": _Spec("off", _choice("off", "auto")),  # 질문 변환 사용 여부
    "TRANSFORM_GATE_THRESHOLD": _Spec(0.70, _unit_float),  # 이 점수보다 낮을 때 질문 변환을 검토
    "TRANSFORM_RRF_K": _Spec(60, _positive_int),  # RRF 순위 병합에서 상위 편중을 조절하는 상수
    "TRANSFORM_ORIGINAL_WEIGHT": _Spec(0.5, _unit_float),  # 변환 검색 병합 시 원 질문의 가중치
    "TRANSFORM_ORIGINAL_WEIGHT_DECOMPOSITION": _Spec(0.1, _unit_float),  # 질문 분해 시 원 질문 가중치
    "TRANSFORM_PER_QUERY_TOP_K": _Spec(3, _positive_int),  # 변환된 질문 하나당 가져올 문서 수
    "TRANSFORM_MULTI_COUNT": _Spec(3, _positive_int),  # 다중 질문 변환으로 만들 질문 개수
    "TRANSFORM_DECOMPOSITION_MIN": _Spec(2, _positive_int),  # 질문 분해 결과의 최소 하위 질문 수
    "TRANSFORM_DECOMPOSITION_MAX": _Spec(4, _positive_int),  # 질문 분해 결과의 최대 하위 질문 수
    "TRANSFORM_CACHE_PATH": _Spec(_default_transform_cache_path, _path),  # 질문 변환 결과 캐시 파일 경로
    "LLM_MAX_TOKENS_ROUTER": _Spec(500, _positive_int),  # 질문 변환 라우터가 생성할 최대 토큰 수
    "RECURSION_LIMIT": _Spec(25, _positive_int),  # LangGraph 한 실행에서 허용할 최대 진행 단계 수
    # 3 이상이면 Retriever 최악 경로가 recursion_limit 25를 넘음.
    "MAX_REPAIRS": _Spec(2, _positive_int),  # 근거 검증 실패 후 답변을 다시 만드는 최대 횟수
    "EMBED_BATCH_SIZE": _Spec(32, _positive_int),  # 임베딩·벡터 저장에서 한 번에 처리할 청크 수
    "CHUNK_MAX_CHARS": _Spec(600, _positive_int),  # 청크 하나의 최대 글자 수
    "CHUNK_OVERLAP": _Spec(80, _positive_int),  # 일반 청크 사이에 겹쳐 넣을 글자 수
    "CHUNK_D2_OVERLAP": _Spec(0, _non_negative_int),  # D2 청크 사이에 겹쳐 넣을 글자 수
    "CHUNK_TURNS_PER_CHUNK": _Spec(4, _positive_int),  # 상담 청크 하나에 넣을 대화 턴 수
    "CHUNK_OVERLAP_TURNS": _Spec(1, _positive_int),  # 상담 청크 사이에 겹쳐 넣을 대화 턴 수
    "MAX_INPUT_TOKENS": _Spec(8192, _positive_int),  # 청크 하나에 허용할 최대 입력 토큰 수
    "TIMEOUT_PDF_PER_FILE": _Spec(60, _positive_float),  # PDF 파일 하나의 추출 제한 시간(초)
    "TIMEOUT_CHUNK_PER_DOC": _Spec(30, _positive_float),  # 입력 문서 하나의 청킹 제한 시간(초)
    "TIMEOUT_EMBED_BATCH": _Spec(120, _positive_float),  # 임베딩·벡터 저장 배치의 제한 시간(초)
    "TIMEOUT_VECTOR_SEARCH": _Spec(10, _positive_float),  # 벡터 검색 한 번의 제한 시간(초)
    "TIMEOUT_RERANK": _Spec(60, _positive_float),  # 후보 문서 리랭킹 한 번의 제한 시간(초)
}


def _present(value: Any) -> bool:
    return value is not None and (not isinstance(value, str) or bool(value.strip()))


def _cli_value(overrides: Mapping[str, Any], name: str) -> Any:
    for candidate in (name, name.lower(), name.lower().replace("_", "-")):
        value = overrides.get(candidate)
        if _present(value):
            return value
    return None


def _source_value(values: Mapping[str, Any], name: str, aliases: tuple[str, ...]) -> tuple[Any, str]:
    for candidate in (name, *aliases):
        value = values.get(candidate)
        if _present(value):
            return value, candidate
    return None, name


def load_settings(cli_overrides: Mapping[str, Any] | None = None) -> Settings:
    """CLI → 환경변수 → 앱 .env → Lab .env → 기본값 순으로 값을 선택함."""

    overrides = cli_overrides or {}
    app_env = dotenv_values(APP_DIR / ".env")
    lab_env = dotenv_values(LAB_ROOT / ".env")
    selected: dict[str, Any] = {}
    sources: dict[str, str] = {}

    for name, spec in _SPECS.items():
        raw = _cli_value(overrides, name)
        source, source_name = "cli", name
        if not _present(raw):
            raw, source_name = _source_value(os.environ, name, spec.aliases)
            source = "environment"
        if not _present(raw):
            raw, source_name = _source_value(app_env, name, spec.aliases)
            source = "app_env"
        if not _present(raw):
            raw, source_name = _source_value(lab_env, name, spec.aliases)
            source = "lab_env"
        if not _present(raw):
            raw = spec.default() if callable(spec.default) else spec.default
            source, source_name = "default", name

        parsed = None if raw is None else spec.parser(name, raw)
        selected[name] = SecretStr(parsed) if parsed is not None and spec.secret else parsed
        sources[name] = source if source_name == name else f"{source}:{source_name}"

    if selected["TRANSFORM_DECOMPOSITION_MIN"] > selected["TRANSFORM_DECOMPOSITION_MAX"]:
        raise LLMConfigError(
            "TRANSFORM_DECOMPOSITION_MIN은 TRANSFORM_DECOMPOSITION_MAX 이하여야 함"
        )
    if selected["HYBRID_WEIGHT_BM25"] + selected["HYBRID_WEIGHT_VECTOR"] <= 0:
        raise LLMConfigError("HYBRID_WEIGHT_BM25와 HYBRID_WEIGHT_VECTOR의 합은 양수여야 함")
    if selected["MAX_REPAIRS"] >= 3:
        raise LLMConfigError("MAX_REPAIRS는 RECURSION_LIMIT=25에서 2 이하여야 함")

    return Settings(MappingProxyType(selected), MappingProxyType(sources))
