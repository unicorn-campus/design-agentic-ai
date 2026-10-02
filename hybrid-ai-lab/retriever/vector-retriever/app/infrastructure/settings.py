"""Retriever 실행에 필요한 설정을 읽고 검증하는 로더."""

from __future__ import annotations

import json
import math
import os
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any, Callable, Mapping

from dotenv import dotenv_values
from pydantic import SecretStr

from app.application.errors import LLMConfigError


APP_DIR = Path(__file__).resolve().parents[2]   # hybrid-ai-lab/retriever/vector-retriever
LAB_ROOT = APP_DIR.parents[1]   # hybrid-ai-lab


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


def _closed_unit_float(name: str, value: Any) -> float:
    parsed = _non_negative_float(name, value)
    if parsed > 1:
        raise LLMConfigError(f"{name}은 0 이상 1 이하여야 함")
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

# Vector DB 경로 — 활성 세대 포인터가 없을 때만 쓰는 고정 배치 기본값
def _default_chroma_path() -> Path:
    return LAB_ROOT / "indexer" / "vector-bm25" / "data" / "chroma"

# 질의 변경 캐시 경로
def _default_transform_cache_path() -> Path:
    return APP_DIR / "data" / "transform_cache.json"

# BM25 인덱스 경로 — 활성 세대 포인터가 없을 때만 쓰는 고정 배치 기본값
def _default_search_index_root() -> Path:
    return LAB_ROOT / "indexer" / "vector-bm25" / "data" / "search_indexes"

# Indexer가 두 색인을 모두 완성한 뒤에만 교체하는 활성 세대 포인터 파일
def _default_generation_pointer() -> Path:
    return LAB_ROOT / "indexer" / "vector-bm25" / "data" / "active_generation.json"

# 계획서 1-3절과 1-3-2절의 모든 키를 한 곳에서만 허용함.
_SPECS: dict[str, _Spec] = {
    "VECTOR_STORE_BACKEND": _Spec("chroma", _choice("chroma", "memory")),  # 벡터 저장소 어댑터
    "CHROMA_PATH": _Spec(_default_chroma_path, _path),  # Chroma 벡터 DB가 저장된 디렉터리
    "CHROMA_COLLECTION": _Spec("card_docs", _text),  # 검색할 Chroma 컬렉션 이름
    "EMBED_MODEL": _Spec("nlpai-lab/KURE-v2", _text),  # 질문을 벡터로 변환할 임베딩 모델
    "SEARCH_INDEX_ROOT": _Spec(_default_search_index_root, _path),  # 활성 corpus·BM25S 세대 루트
    "ACTIVE_GENERATION_POINTER": _Spec(_default_generation_pointer, _path),  # 두 색인 경로를 고를 활성 세대 포인터
    "KOREAN_USER_DICTIONARY": _Spec(None, _path),  # 카드명·상품명 한국어 사용자 사전
    "KOREAN_TOKENIZER_WORKERS": _Spec(1, _positive_int),  # 실시간 질의 Kiwi 작업자 수
    "BM25_K1": _Spec(1.5, _positive_float),  # Indexer와 공유하는 BM25 단어 빈도 포화 계수
    "BM25_B": _Spec(0.75, _unit_float),  # Indexer와 공유하는 BM25 문서 길이 보정 계수
    # 핵심어 유무 판정 기준 — 전체 청크 중 이 비율 이상에 나오는 말은 흔한 말로 보고 핵심어에서 뺌.
    # 기본값 0.80은 평가 질문 13건(keyword_check v3)에서 고른 값임. 후보값별 13건 평균은
    # 1.0 → 0.65/0.89, 0.8 → 0.65/0.82, 0.7 → 0.67/0.75, 0.6 → 0.56/0.49(정밀도/재현율)로
    # 0.7과 0.6 사이에서 재현율이 급락하므로 그 절벽에서 떨어진 0.8을 기본값으로 둠.
    # 0.8은 불용어표를 손으로 관리하던 이전 방식(0.66/0.81)과 같은 수준을 사전 없이 냄.
    # 이 수치는 현재 문서 묶음 195청크에서 측정한 값이며, 문서가 바뀌면 평가셋으로 다시 보정해야 함.
    "KEYWORD_MAX_DOC_RATIO": _Spec(0.80, _unit_float),  # 핵심어에서 제외할 문서빈도 비율 하한
    "KEYWORD_TOP_N": _Spec(3, _positive_int),  # "상위 핵심어 미포함" 판정에 볼 상위 핵심어 개수
    "RERANK_MODEL": _Spec("BAAI/bge-reranker-v2-m3", _text),  # 후보 문서 순위를 다시 매길 모델
    "LLM_PROVIDER": _Spec("groq", _choice("groq", "claude", "openai")),  # 답변에 사용할 LLM 제공자
    "GROQ_API_KEY": _Spec(None, _text, True),  # Groq 인증 키이며 로그에서 가리는 비밀값
    "GROQ_MODEL": _Spec("openai/gpt-oss-120b", _text),  # Groq를 선택했을 때 호출할 모델
    "CLAUDE_API_KEY": _Spec(None, _text, True, ("ANTHROPIC_API_KEY",)),  # Claude 인증 키와 대체 환경변수
    "CLAUDE_MODEL": _Spec("claude-opus-5", _text),  # Claude를 선택했을 때 호출할 모델
    "OPENAI_API_KEY": _Spec(None, _text, True),  # OpenAI 인증 키이며 로그에서 가리는 비밀값
    "OPENAI_MODEL": _Spec(None, _text),  # OpenAI를 선택했을 때 호출할 모델
    "LLM_TIMEOUT_SECONDS": _Spec(60, _positive_float),  # LLM 호출 한 번의 제한 시간(초)
    # 추론형 모델은 추론 토큰도 같은 예산을 쓰므로 근거 인용이 붙은 답변에는 2000이 부족함.
    "LLM_MAX_TOKENS_ANSWER": _Spec(8000, _positive_int),  # 최종 답변이 생성할 최대 토큰 수
    "MAX_LLM_CALLS_CLI": _Spec(8, _positive_int),  # CLI 실행 한 번에 허용할 LLM 호출 상한
    "MAX_LLM_CALLS_PER_REQUEST": _Spec(2, _positive_int),  # API 요청 한 건의 LLM 호출 상한
    "MAX_LLM_CALLS_TOTAL": _Spec(200, _positive_int),  # 서버 프로세스 전체의 누적 LLM 호출 상한
    "REQUEST_TIMEOUT_SECONDS": _Spec(120, _positive_float),  # Retriever 요청 전체의 제한 시간(초)
    "API_HOST": _Spec("127.0.0.1", _text),  # API 서버가 접속을 받을 호스트 주소
    "API_PORT": _Spec(8001, _positive_int),  # API 서버가 사용할 포트 번호
    "TOP_K_DEFAULT": _Spec(5, _positive_int),  # 별도 지정이 없을 때 반환할 최종 문서 수
    "CANDIDATE_MULTIPLIER": _Spec(4, _positive_int),  # 최종 문서 수 대비 먼저 가져올 후보 배수
    "VECTOR_SEARCH_STRATEGY": _Spec("similarity", _choice("similarity", "mmr")),  # 벡터 후보 선택 방식
    "MMR_FETCH_MULTIPLIER": _Spec(2, _positive_int),  # MMR 반환 수 대비 Chroma에서 먼저 조회할 후보 배수
    "MMR_LAMBDA_MULT": _Spec(0.5, _closed_unit_float),  # 1은 질의 유사도, 0은 후보 다양성을 우선함
    "HYBRID_WEIGHT_BM25": _Spec(0.4, _non_negative_float),  # 하이브리드 검색의 BM25 점수 비중
    "HYBRID_WEIGHT_VECTOR": _Spec(0.6, _non_negative_float),  # 하이브리드 검색의 벡터 점수 비중
    "ANSWER_GATE_THRESHOLD": _Spec(0.62, _unit_float),  # 답변에 쓸 근거가 충분한지 판단할 점수 기준
    "RERANK_MAX_LENGTH": _Spec(512, _positive_int),  # 리랭커에 넣을 질문·문서의 최대 토큰 길이
    "TRANSFORM_MODE": _Spec("off", _choice("off", "auto")),  # 질문 변환 사용 여부
    "TRANSFORM_GATE_THRESHOLD": _Spec(0.86, _unit_float),  # 이 점수보다 낮을 때 질문 변환을 검토
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
    "TIMEOUT_VECTOR_SEARCH": _Spec(10, _positive_float),  # 벡터 검색 한 번의 제한 시간(초)
    "TIMEOUT_RERANK": _Spec(60, _positive_float),  # 후보 문서 리랭킹 한 번의 제한 시간(초)
}


_INDEX_PATH_KEYS = ("CHROMA_PATH", "SEARCH_INDEX_ROOT")


def _apply_generation_pointer(selected: dict[str, Any], sources: dict[str, str]) -> None:
    """두 색인 경로를 지정하지 않았으면 활성 세대 포인터에서 같은 세대의 경로를 채움.

    입력 전제: `selected`·`sources`는 키마다 값과 출처를 고른 직후의 사전임.
    부수효과: 포인터를 쓰면 두 경로와 컬렉션 이름의 값·출처(`pointer:<파일명>`)를 바꿈.
    예외: 두 경로 중 하나만 지정했거나 포인터가 손상됐으면 `LLMConfigError`.
    포인터 파일이 없으면 고정 기본 경로를 그대로 둠 — 세대 포인터 이전 배치와 호환하기 위함.
    """

    # 한쪽만 바꾸면 벡터와 BM25가 서로 다른 세대의 청크를 가리켜 검색 결과가 어긋남
    explicit = [key for key in _INDEX_PATH_KEYS if sources[key] != "default"]
    if len(explicit) == 1:
        raise LLMConfigError("CHROMA_PATH와 SEARCH_INDEX_ROOT는 같은 세대 경로로 함께 지정해야 함")
    if explicit:
        return

    pointer_path: Path = selected["ACTIVE_GENERATION_POINTER"]
    if not pointer_path.is_file():
        return
    try:
        pointer = json.loads(pointer_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise LLMConfigError(f"활성 세대 포인터를 읽을 수 없음: {pointer_path}") from error
    if not isinstance(pointer, dict) or pointer.get("format_version") != 1:
        raise LLMConfigError(f"활성 세대 포인터 형식이 올바르지 않음: {pointer_path}")

    origin = f"pointer:{pointer_path.name}"
    for key, field in (("CHROMA_PATH", "chroma_path"), ("SEARCH_INDEX_ROOT", "search_index_root")):
        relative = pointer.get(field)
        if not isinstance(relative, str) or not relative.strip():
            raise LLMConfigError(f"활성 세대 포인터에 {field}가 없음: {pointer_path}")
        # 포인터 안의 경로는 포인터 파일이 있는 data 폴더 기준 상대 경로임
        selected[key] = (pointer_path.parent / relative).resolve()
        sources[key] = origin
    collection = pointer.get("collection")
    if sources["CHROMA_COLLECTION"] == "default" and isinstance(collection, str) and collection.strip():
        selected["CHROMA_COLLECTION"] = collection.strip()
        sources["CHROMA_COLLECTION"] = origin


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

    _apply_generation_pointer(selected, sources)
    if selected["TRANSFORM_DECOMPOSITION_MIN"] > selected["TRANSFORM_DECOMPOSITION_MAX"]:
        raise LLMConfigError(
            "TRANSFORM_DECOMPOSITION_MIN은 TRANSFORM_DECOMPOSITION_MAX 이하여야 함"
        )
    if selected["HYBRID_WEIGHT_BM25"] + selected["HYBRID_WEIGHT_VECTOR"] <= 0:
        raise LLMConfigError("HYBRID_WEIGHT_BM25와 HYBRID_WEIGHT_VECTOR의 합은 양수여야 함")
    if selected["MAX_REPAIRS"] >= 3:
        raise LLMConfigError("MAX_REPAIRS는 RECURSION_LIMIT=25에서 2 이하여야 함")

    return Settings(MappingProxyType(selected), MappingProxyType(sources))
