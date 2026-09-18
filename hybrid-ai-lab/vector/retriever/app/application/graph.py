"""Retriever 검색·질문 변환·답변 StateGraph 조립과 응용 유스케이스의 경계."""

from __future__ import annotations

import sqlite3
from collections.abc import AsyncIterator
from collections.abc import Callable, Mapping
from pathlib import Path
from time import monotonic
from typing import Any

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from langgraph.graph import END, START, StateGraph
from langgraph.types import RetryPolicy

from .ports import VectorStorePort
from .runtime import append_node_log, run_with_timeout
from .state import HealthResult, Hit, RetrieverRequest, RetrieverState, SearchResult


# --- 그래프 조립(플로니) ---

RETRIEVER_NODE_NAMES = (
    "check_search_readiness",
    "vector_search",
    "assess_transform_gate",
    "plan_query_transform",
    "bm25_search",
    "fuse_scores",
    "complete_original_results",
    "search_transformed",
    "merge_queries",
    "rerank",
    "build_prompt",
    "generate_answer",
    "verify_evidence",
)
DEFAULT_RECURSION_LIMIT = 25
DEFAULT_MAX_REPAIRS = 2
MAX_TRANSMISSION_ATTEMPTS = 3


class MissingNodeDependencyError(RuntimeError):
    """주입되지 않은 노드 서비스를 호출했음을 나탄냄."""


class ForcedNodeError(RuntimeError):
    """체크포인트 재개 시험을 위한 강제 중단임."""


def execution_config(thread_id: str, recursion_limit: int = DEFAULT_RECURSION_LIMIT) -> dict[str, Any]:
    """동결된 thread_id·recursion_limit 실행 설정을 만듦."""

    return {"configurable": {"thread_id": thread_id}, "recursion_limit": recursion_limit}


def open_sqlite_checkpointer(path: str | Path) -> SqliteSaver:
    """WAL 모드의 동기 SQLite 체크포인터를 열음."""

    checkpoint_path = Path(path)
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(checkpoint_path, check_same_thread=False)
    connection.execute("PRAGMA journal_mode=WAL")
    serializer = JsonPlusSerializer(allowed_msgpack_modules=[("app.application.state", "Hit")])
    return SqliteSaver(connection, serde=serializer)


def _lookup(resources: Any, name: str) -> Any:
    if isinstance(resources, Mapping):
        return resources.get(name)
    return getattr(resources, name, None)


def _setting(resources: Any, name: str, default: Any) -> Any:
    settings = _lookup(resources, "settings")
    if settings is None:
        return default
    if isinstance(settings, Mapping):
        return settings.get(name, default)
    values = getattr(settings, "values", None)
    if isinstance(values, Mapping):
        return values.get(name, default)
    return getattr(settings, name, default)


def _handler(resources: Any, node_name: str) -> Callable[..., Mapping[str, Any]]:
    run_node = _lookup(resources, "run_node")
    direct = _lookup(resources, node_name)
    if callable(direct):
        return direct
    if callable(run_node):
        return lambda state, **kwargs: run_node(node_name, state, **kwargs)
    raise MissingNodeDependencyError(f"Retriever 노드 서비스가 없음: {node_name}")


def _retryable(resources: Any, node_name: str, exc: Exception) -> bool:
    predicate = _lookup(resources, "is_retryable")
    if callable(predicate):
        return bool(predicate(node_name, exc))
    return exc.__class__.__name__ in {
        "RetrievalRetryableError",
        "VectorStoreRetryableError",
        "BM25RetryableError",
    }


def _run_node(
    resources: Any,
    node_name: str,
    state: RetrieverState,
    **handler_kwargs: Any,
) -> dict[str, Any]:
    if state.get("force_fail_node") == node_name:
        raise ForcedNodeError(f"강제 중단 노드: {node_name}")
    started = monotonic()
    update = dict(_handler(resources, node_name)(state, **handler_kwargs) or {})
    update.pop("timings", None)
    update["timings"] = {node_name: max(0, round((monotonic() - started) * 1000))}
    return update


def _audited_node(
    resources: Any,
    node_name: str,
    action: Callable[[RetrieverState], dict[str, Any]],
) -> Callable[[RetrieverState], dict[str, Any]]:
    """노드 완료·실패를 안전한 필드만 담은 JSONL로 기록함."""

    def audited(state: RetrieverState) -> dict[str, Any]:
        started = monotonic()
        log_dir = Path(_lookup(resources, "log_dir") or Path(__file__).resolve().parents[2] / "data" / "logs")
        log_path = log_dir / f"{state.get('thread_id', 'unknown')}.jsonl"
        try:
            update = action(state)
        except BaseException as error:
            elapsed = max(0, round((monotonic() - started) * 1000))
            append_node_log(log_path, state.get("thread_id", ""), node_name, "failed", elapsed, type(error).__name__)
            raise
        elapsed = max(0, round((monotonic() - started) * 1000))
        append_node_log(log_path, state.get("thread_id", ""), node_name, "completed", elapsed)
        return update

    return audited


def _hit_field(hit: Hit | Mapping[str, Any], name: str) -> Any:
    return getattr(hit, name) if isinstance(hit, Hit) else hit.get(name)


def _gate_score(hits: list[Hit] | list[dict[str, Any]]) -> float | None:
    if not hits:
        return None
    value = _hit_field(hits[0], "vector_score")
    return None if value is None else float(value)


def remaining_llm_attempts(state: RetrieverState) -> int:
    """요청 예산과 어댑터 재시도 상한 중 작은 값을 구함."""

    remaining = max(0, int(state.get("max_llm_calls", 0)) - int(state.get("llm_calls", 0)))
    return min(MAX_TRANSMISSION_ATTEMPTS, remaining)


def _finalize_hits(
    resources: Any,
    state: RetrieverState,
    update: dict[str, Any],
    *,
    answer_enabled: bool,
) -> dict[str, Any]:
    hits = update.get("hits", state.get("hits", []))
    update["gate_score"] = _gate_score(hits)
    if not answer_enabled:
        update.setdefault("status", "ok")
        return update
    threshold = float(_setting(resources, "ANSWER_GATE_THRESHOLD", 0.62))
    if state.get("route_action") == "clarify" or update["gate_score"] is None:
        update.update(status="needs_check", exit_code=0)
    elif float(update["gate_score"]) < threshold:
        update.update(status="needs_check", exit_code=0)
    else:
        update.setdefault("status", "ok")
    return update


def _check_search_readiness(resources: Any, state: RetrieverState) -> dict[str, Any]:
    # 받은 것: query·role·mode·top_k·dry_run
    # 하는 일: 입력과 인덱스 상태를 확인함
    # 넘기는 것: index_info·status·exit_code
    update = _run_node(resources, "check_search_readiness", state)
    if update.pop("validation_errors", []):
        update.update(status="error", exit_code=1)
    if state.get("dry_run") and update.get("status") != "error":
        update.update(status="dry_run", exit_code=0)
    return update


def _vector_search(resources: Any, state: RetrieverState) -> dict[str, Any]:
    # 받은 것: query·role·top_k
    # 하는 일: 원 질문 벡터 검색과 변환 관문 점수를 계산함
    # 넘기는 것: vector_hits·transform_gate_score·baseline_hits
    return _run_node(resources, "vector_search", state)


def _assess_transform_gate(resources: Any, state: RetrieverState) -> dict[str, Any]:
    # 받은 것: transform_mode·transform_gate_score
    # 하는 일: 캐시·LLM 호출 없이 질문 변환 검토 필요 여부만 판정함
    # 넘기는 것: transform_review_required·route_action
    return _run_node(resources, "assess_transform_gate", state)


def _plan_query_transform(resources: Any, state: RetrieverState) -> dict[str, Any]:
    # 받은 것: query·transform_review_required·llm_calls
    # 하는 일: 검토가 필요할 때만 캐시 또는 LLM으로 변환 계획을 생성함
    # 넘기는 것: route_action·technique·transformed_queries·llm_calls
    if state.get("force_fail_node") == "plan_query_transform":
        raise ForcedNodeError("강제 중단 노드: plan_query_transform")
    if state.get("llm_calls", 0) >= state.get("max_llm_calls", 0):
        return {
            "route_action": "keep",
            "route_error": "LLM 호출 상한에 도달함",
            "transformed_queries": [],
            "timings": {"plan_query_transform": 0},
        }

    update = _run_node(
        resources,
        "plan_query_transform",
        state,
        max_attempts=remaining_llm_attempts(state),
    )
    return update


def _bm25_search(resources: Any, state: RetrieverState) -> dict[str, Any]:
    # 받은 것: query·top_k
    # 하는 일: 원 질문의 BM25 점수를 읽음
    # 넘기는 것: bm25_scores·warnings
    return _run_node(resources, "bm25_search", state)


def _fuse_scores(resources: Any, state: RetrieverState) -> dict[str, Any]:
    # 받은 것: vector_hits·bm25_scores·role·top_k
    # 하는 일: 정규화·가중치·권한 규칙으로 후보를 융합함
    # 넘기는 것: candidates·baseline_hits·hits
    update = _run_node(resources, "fuse_scores", state)
    baseline = update.get("baseline_hits", update.get("candidates", []))
    update.setdefault("baseline_hits", baseline)
    return update


def _complete_original_results(
    resources: Any,
    state: RetrieverState,
    answer_enabled: bool,
) -> dict[str, Any]:
    # 받은 것: 원 질문 vector_hits 또는 융합된 baseline_hits
    # 하는 일: 원 질문 결과를 확정하고 변환 질문 검색 전 기준 결과를 보존함
    # 넘기는 것: baseline_hits·hits·gate_score
    update = _run_node(resources, "complete_original_results", state)
    # hybrid_rerank는 원 질문 기준선도 리랭킹한 뒤 최종 답변 관문을 평가함.
    # 여기서 먼저 확정하면 낮은 원 벡터 점수 때문에 rerank 노드를 건너뛸 수 있음.
    if not state.get("transformed_queries") and state.get("mode") != "hybrid_rerank":
        update = _finalize_hits(resources, state, update, answer_enabled=answer_enabled)
    return update


def _search_transformed(resources: Any, state: RetrieverState) -> dict[str, Any]:
    # 받은 것: transformed_queries·mode·role·top_k
    # 하는 일: 변환 질의를 같은 검색 경로로 순차 실행함
    # 넘기는 것: transformed_hit_groups·warnings
    return _run_node(resources, "search_transformed", state)


def _merge_queries(resources: Any, state: RetrieverState, answer_enabled: bool) -> dict[str, Any]:
    # 받은 것: baseline_hits·transformed_hit_groups·technique·top_k
    # 하는 일: 가중 RRF와 decomposition 커버리지로 결과를 병합함
    # 넘기는 것: hits·gate_score·merge_weights·coverage_applied
    update = _run_node(resources, "merge_queries", state)
    if not update.get("hits"):
        update["hits"] = list(state.get("baseline_hits", []))
        update.setdefault("warnings", ["변환 질의 병합 결과가 없어 원 질문 결과를 사용함"])
    if state.get("mode") != "hybrid_rerank":
        update = _finalize_hits(resources, state, update, answer_enabled=answer_enabled)
    return update


def _rerank(resources: Any, state: RetrieverState, answer_enabled: bool) -> dict[str, Any]:
    # 받은 것: query·baseline_hits·transformed_hit_groups·technique·top_k
    # 하는 일: 질의 그룹별로 리랭킹하고 결과를 병합함
    # 넘기는 것: hits·gate_score·warnings
    update = _run_node(resources, "rerank", state)
    if not update.get("hits"):
        update["hits"] = list(state.get("hits", state.get("baseline_hits", [])))
    return _finalize_hits(resources, state, update, answer_enabled=answer_enabled)


def _build_prompt(resources: Any, state: RetrieverState) -> dict[str, Any]:
    # 받은 것: query·hits·repair_hints·prompt_only
    # 하는 일: 근거 청크를 포함한 시스템·사용자 프롬프트를 조립함
    # 넘기는 것: prompt·status·exit_code
    update = _run_node(resources, "build_prompt", state)
    if state.get("prompt_only"):
        update.update(status="prompt_only", exit_code=0)
    return update


def _generate_answer(resources: Any, state: RetrieverState) -> dict[str, Any]:
    # 받은 것: prompt·max_llm_calls·llm_calls
    # 하는 일: 호출 상한 안에서 구조화 답변을 생성함
    # 넘기는 것: raw_answer·llm_calls·status
    if state.get("force_fail_node") == "generate_answer":
        raise ForcedNodeError("강제 중단 노드: generate_answer")
    if state.get("llm_calls", 0) >= state.get("max_llm_calls", 0):
        return {"status": "halted_by_limit", "exit_code": 0, "timings": {"generate_answer": 0}}
    update = _run_node(
        resources,
        "generate_answer",
        state,
        max_attempts=remaining_llm_attempts(state),
    )
    update.setdefault("llm_calls", 1)
    return update


def _answer_is_valid(update: Mapping[str, Any]) -> bool:
    answer = update.get("answer") or {}
    if hasattr(answer, "model_dump"):
        answer = answer.model_dump()
    verification = answer.get("verification", {}) if isinstance(answer, Mapping) else {}
    return bool(verification.get("automatic_valid"))


def _verify_evidence(resources: Any, state: RetrieverState) -> dict[str, Any]:
    # 받은 것: raw_answer·hits·repair_count
    # 하는 일: 참조·발췌·위치를 원문과 대조함
    # 넘기는 것: answer·repair_hints·repair_count·status
    update = _run_node(resources, "verify_evidence", state)
    if _answer_is_valid(update):
        update.setdefault("status", "ok")
        update.setdefault("exit_code", 0)
        return update
    update.setdefault("repair_count", 1)
    max_repairs = int(_setting(resources, "MAX_REPAIRS", DEFAULT_MAX_REPAIRS))
    if state.get("repair_count", 0) >= max_repairs:
        update.update(status="halted_by_limit", exit_code=0)
    return update


def _after_search_readiness(state: RetrieverState) -> str:
    return "end" if state.get("status") in {"error", "dry_run"} else "continue"


def _original_search_path(state: RetrieverState) -> str:
    return "vector" if state.get("mode") == "vector" else "hybrid"


def _after_transform_gate(state: RetrieverState) -> str:
    if state.get("transform_review_required"):
        return "review"
    return _original_search_path(state)


def _after_transform_plan(state: RetrieverState) -> str:
    return _original_search_path(state)


def _after_original_results(state: RetrieverState) -> str:
    if state.get("status") in {"error", "needs_check", "halted_by_limit"}:
        return "end"
    if state.get("route_action") == "transform" and state.get("transformed_queries"):
        return "transform"
    if state.get("mode") == "hybrid_rerank":
        return "rerank"
    return "complete"


def _after_merge(state: RetrieverState) -> str:
    if state.get("status") in {"error", "needs_check", "halted_by_limit"}:
        return "end"
    return "rerank" if state.get("mode") == "hybrid_rerank" else "complete"


def _after_search(state: RetrieverState) -> str:
    return "end" if state.get("status") in {"error", "needs_check", "halted_by_limit"} else "answer"


def _after_prompt(state: RetrieverState) -> str:
    return "end" if state.get("status") == "prompt_only" else "continue"


def _after_generate(state: RetrieverState) -> str:
    return "end" if state.get("status") == "halted_by_limit" else "continue"


def _after_verify(state: RetrieverState) -> str:
    answer = state.get("answer", {})
    if hasattr(answer, "model_dump"):
        answer = answer.model_dump()
    verification = answer.get("verification", {}) if isinstance(answer, Mapping) else {}
    if verification.get("automatic_valid") or state.get("status") == "halted_by_limit":
        return "end"
    return "repair"


def create_graph_builder(resources: Any, *, answer_enabled: bool = True) -> StateGraph:
    """변환 검토와 원 질문 결과 완성을 분리한 검색 그래프 빌더를 만듦."""

    builder = StateGraph(RetrieverState)

    # LangGraph는 노드를 실행할 때 현재 상태인 state 하나만 인자로 전달함.
    # 그러나 실제 노드 함수는 공통 실행 객체인 resources와 일부 노드의 answer_enabled도 함께 받아야 함.
    # lambda는 LangGraph가 요구하는 `state -> 결과 딕셔너리` 형태의 짧은 중간 함수를 만들어 이 차이를 맞춤.
    # 예: `lambda state: _vector_search(resources, state, answer_enabled)`는 state를 새로 받고,
    # 그래프 생성 시점의 resources와 answer_enabled를 기억했다가 _vector_search()에 함께 전달함.
    # lambda는 이 딕셔너리를 만들 때 실행되지 않고, 해당 LangGraph 노드가 수행될 때 호출됨.
    nodes: dict[str, Callable[[RetrieverState], dict[str, Any]]] = {
        "check_search_readiness": lambda state: _check_search_readiness(resources, state),
        "vector_search": lambda state: _vector_search(resources, state),
        "assess_transform_gate": lambda state: _assess_transform_gate(resources, state),
        "plan_query_transform": lambda state: _plan_query_transform(resources, state),
        "bm25_search": lambda state: _bm25_search(resources, state),
        "fuse_scores": lambda state: _fuse_scores(resources, state),
        "complete_original_results": lambda state: _complete_original_results(
            resources,
            state,
            answer_enabled,
        ),
        "search_transformed": lambda state: _search_transformed(resources, state),
        "merge_queries": lambda state: _merge_queries(resources, state, answer_enabled),
        "rerank": lambda state: _rerank(resources, state, answer_enabled),
        "build_prompt": lambda state: _build_prompt(resources, state),
        "generate_answer": lambda state: _generate_answer(resources, state),
        "verify_evidence": lambda state: _verify_evidence(resources, state),
    }

    # 노드별 재시도 정책을 준비함. 기본값 None은 실패할 때 이 노드 자체를 다시 실행하지 않는다는 뜻임.
    retry_attempts = {"vector_search": 3, "bm25_search": 2}
    for name, node in nodes.items():
        retry_policy = None
        if name in retry_attempts:
            # max_attempts는 최초 실행을 포함한 최대 시도 횟수임: vector_search 3회, bm25_search 2회.
            # retry_on은 발생한 예외를 _retryable()에 전달하고, True인 예외만 다시 시도하도록 결정함.
            # node_name=name은 각 lambda가 현재 반복의 노드 이름을 기억하게 하여 마지막 이름으로 바뀌는 것을 막음.
            # 대기 시간 관련 값을 생략했으므로 LangGraph 기본 지수 백오프와 임의 지연(jitter)을 사용함.
            retry_policy = RetryPolicy(
                max_attempts=retry_attempts[name],
                retry_on=lambda exc, node_name=name: _retryable(resources, node_name, exc),
            )

        # add_node()의 첫 번째 인자 name은 그래프에서 노드를 식별할 이름임.
        # 두 번째 인자는 해당 노드에 도착했을 때 실행할 함수이며, 여기서는 _audited_node()의 반환 함수임.
        # _audited_node()는 그래프 생성 시 resources·name·node를 기억하는 audited(state) 함수를 만들어 반환함.
        # 실행 시 audited()는 시작 시간 측정 → 원래 node(state) 호출 → 성공·실패 JSONL 로그 기록을 수행함.
        # 실패하면 로그를 남긴 뒤 예외를 다시 발생시켜 LangGraph가 retry_policy 적용 여부를 판단하게 함.
        # 세 번째 인자 retry_policy는 재시도 대상·최대 시도 횟수를 정하며, None이면 재시도 정책을 붙이지 않음.
        builder.add_node(name, _audited_node(resources, name, node), retry_policy=retry_policy)

    # Node 간 연결
    builder.add_edge(START, "check_search_readiness")
    builder.add_conditional_edges(
        "check_search_readiness",
        _after_search_readiness,
        {"continue": "vector_search", "end": END},
    )
    builder.add_edge("vector_search", "assess_transform_gate")
    builder.add_conditional_edges(
        "assess_transform_gate",
        _after_transform_gate,
        {
            "review": "plan_query_transform",
            "hybrid": "bm25_search",
            "vector": "complete_original_results",
        },
    )
    builder.add_conditional_edges(
        "plan_query_transform",
        _after_transform_plan,
        {"hybrid": "bm25_search", "vector": "complete_original_results"},
    )
    builder.add_edge("bm25_search", "fuse_scores")
    builder.add_edge("fuse_scores", "complete_original_results")
    builder.add_conditional_edges(
        "complete_original_results",
        _after_original_results,
        {
            "transform": "search_transformed",
            "rerank": "rerank",
            "complete": "build_prompt" if answer_enabled else END,
            "end": END,
        },
    )
    builder.add_edge("search_transformed", "merge_queries")
    builder.add_conditional_edges(
        "merge_queries",
        _after_merge,
        {"rerank": "rerank", "complete": "build_prompt" if answer_enabled else END, "end": END},
    )
    builder.add_conditional_edges(
        "rerank",
        _after_search,
        {"answer": "build_prompt" if answer_enabled else END, "end": END},
    )
    builder.add_conditional_edges("build_prompt", _after_prompt, {"continue": "generate_answer", "end": END})
    builder.add_conditional_edges("generate_answer", _after_generate, {"continue": "verify_evidence", "end": END})
    builder.add_conditional_edges("verify_evidence", _after_verify, {"repair": "build_prompt", "end": END})
    return builder


def build_graph(resources: Any, checkpointer: SqliteSaver | None = None, *, answer_enabled: bool = True) -> Any:
    """같은 빌더를 CLI·POST용 SQLite 또는 stream용 None으로 컴파일함."""

    return create_graph_builder(resources, answer_enabled=answer_enabled).compile(checkpointer=checkpointer)


# --- 응용 함수(스택니) ---
from dataclasses import dataclass

from .state import AnswerDraft, build_search_result


MERGE_DECOMPOSITION_PER_QUERY_TOP_K = 1
HYBRID_RERANK_FUSION_MULTIPLIER = 2


@dataclass(frozen=True)
class CandidateSizes:
    """최종 결과 수에서 계산한 검색·융합 후보 수 계약임."""

    raw_k: int
    fused_k: int


def candidate_sizes(mode: str, top_k: int, candidate_multiplier: int) -> CandidateSizes:
    """모드별 원시 검색 후보와 질문별 융합 후보 수를 계산함."""

    fused_k = (
        top_k * HYBRID_RERANK_FUSION_MULTIPLIER
        if mode == "hybrid_rerank"
        else top_k
    )
    return CandidateSizes(
        raw_k=fused_k * candidate_multiplier,
        fused_k=fused_k,
    )


class IndexUnavailableError(RuntimeError):
    """컬렉션이 비었거나 임베딩 서명이 맞지 않음을 나타냄."""


class _LazyHuggingFaceEmbedder:
    """질의가 들어올 때까지 임베딩 모델 적재를 미룸."""

    def __init__(self, model_name: str) -> None:
        self.model_name = model_name
        self.signature = f"sentence-transformers:{model_name}:prompt-policy-v2"
        self.dimension = 0
        self._model = None

    def _load(self) -> Any:
        if self._model is None:
            from langchain_huggingface import HuggingFaceEmbeddings

            self._model = HuggingFaceEmbeddings(
                model_name=self.model_name,
                model_kwargs={"device": "cpu"},
                encode_kwargs={"normalize_embeddings": True},
            )
        return self._model

    def embed_query(self, text: str) -> list[float]:
        values = list(self._load().embed_query(text))
        self.dimension = len(values)
        return values


class _BudgetedLLM:
    """노드가 넘긴 전송 상한과 마감을 LLM 어댑터에 전달함."""

    def __init__(
        self,
        client: Any,
        *,
        max_attempts: int,
        deadline_seconds: float | None,
    ) -> None:
        self.client = client
        self.max_attempts = max_attempts
        self.deadline_seconds = deadline_seconds

    def complete_structured(self, *args: Any, **kwargs: Any) -> Any:
        kwargs["max_attempts"] = self.max_attempts
        kwargs["deadline_seconds"] = self.deadline_seconds
        return self.client.complete_structured(*args, **kwargs)


# @dataclass는 필드를 바탕으로 __init__(), __repr__(), __eq__() 같은 기본 메서드의 코드를 자동 생성함.
# 객체 자체를 자동 생성하거나 의존성을 주입하지는 않으며, load_resources()가 RetrieverResources(...)를 직접 호출하여 생성함.
@dataclass
class RetrieverResources:
    """Retriever 노드가 사용하는 구현체 묶음.

    그래프의 전체 흐름::

        START → check_search_readiness → vector_search(원 질문 벡터 검색 1회)
          → assess_transform_gate
              ├─ off 또는 점수 >= 기준값: 변환 계획 생략
              └─ 점수 < 기준값 또는 검색 결과 없음: plan_query_transform
          → 원 질문 결과 완성
              ├─ vector: 앞에서 얻은 vector_hits 재사용
              └─ hybrid 계열: bm25_search → fuse_scores
          → complete_original_results
              ├─ 변환 질문 있음: search_transformed → merge_queries
              ├─ 변환 질문 없음 + hybrid_rerank: rerank
              └─ 변환 질문 없음 + 나머지 모드: 검색 완료

        search_transformed의 모드별 내부 검색:
              ├─ vector: 변환 질문 벡터 검색
              └─ hybrid 계열: 변환 질문 벡터 검색 + BM25 검색 + 점수 융합

        merge_queries
              ├─ vector 또는 hybrid: 가중 RRF 병합 결과 확정
              └─ hybrid_rerank: 원 질문·변환 질문 후보군별 rerank 후 병합

        검색 완료 → build_prompt → generate_answer → verify_evidence
                                                     ├─ repair → build_prompt
                                                     └─ END

    ``answer_enabled=False``인 검색 전용 실행은 검색 결과가 완성되면 build_prompt 대신 END로 이동함.

    핵심 계약:
        - vector_search는 원 질문에 대해 정확히 한 번만 실행함.
        - 0.7 미만 점수는 변환 확정이 아니라 변환 계획 검토 조건임.
        - 원 질문 결과를 완성한 뒤에만 변환 질문 검색을 실행함.
        - 변환 질문이 없으면 search_transformed와 merge_queries를 실행하지 않음.
        - answer_enabled=False이면 검색 결과 확정 후 답변 LLM 노드를 실행하지 않음.
    """

    settings: Any
    embedder: Any
    vector_store: VectorStorePort
    bm25: Any
    reranker: Any
    llm: Any
    transform_cache: Any

    def run_node(
        self,
        name: str,
        state: RetrieverState,
        **kwargs: Any,
    ) -> dict[str, Any]:
        return getattr(self, f"_run_{name}")(state, **kwargs)

    def _run_check_search_readiness(
        self,
        state: RetrieverState,
        **_kwargs: Any,
    ) -> dict[str, Any]:
        validation_errors = []
        if not str(state.get("query", "")).strip():
            validation_errors.append("query는 비어 있을 수 없음")
        try:
            top_k_valid = int(state.get("top_k", 0)) > 0
        except (TypeError, ValueError):
            top_k_valid = False
        if not top_k_valid:
            validation_errors.append("top_k는 양수여야 함")
        if state.get("role") not in {"agent", "auditor"}:
            validation_errors.append("지원하지 않는 role임")
        if state.get("mode") not in {"vector", "hybrid", "hybrid_rerank"}:
            validation_errors.append("지원하지 않는 mode임")
        if validation_errors:
            return {"validation_errors": validation_errors}

        description = self.vector_store.describe()
        count = int(description.get("count", 0))
        signature_ok = description.get("signature") == self.embedder.signature
        dimension = int(description.get("dimension") or getattr(self.embedder, "dimension", 0))
        if count <= 0 or not signature_ok:
            raise IndexUnavailableError("컬렉션이 비었거나 임베딩 서명이 일치하지 않음")
        return {
            "index_info": {
                "collection": self.settings.CHROMA_COLLECTION,
                "count": count,
                "dimension": dimension,
                "signature_ok": signature_ok,
            },
            "validation_errors": [],
        }

    def _search_vector(self, query: str, role: str, raw_k: int) -> list[Hit]:
        from app.domain.access import build_filter

        # Embedding 모델 로딩
        loader = getattr(self.embedder, "_load", None)
        if callable(loader):
            loader()

        def search() -> list[Hit]:
            embedding = self.embedder.embed_query(query)  # 질문 임베딩
            return self.vector_store.search(embedding, raw_k, build_filter(role))  # 벡터 검색

        return run_with_timeout(
            search,
            timeout_seconds=float(_setting(self, "TIMEOUT_VECTOR_SEARCH", 10)),
            operation="벡터 검색",
        )

    def _run_vector_search(self, state: RetrieverState, **_kwargs: Any) -> dict[str, Any]:
        sizes = self._candidate_sizes(state)
        vector_hits = self._search_vector(
            state["query"],
            state["role"],
            sizes.raw_k,
        )
        update: dict[str, Any] = {
            "vector_hits": vector_hits,
            "transform_gate_score": _gate_score(vector_hits),
        }
        if state.get("mode") == "vector":
            final_hits = list(vector_hits[: int(state.get("top_k", len(vector_hits)))])
            update.update(baseline_hits=final_hits, hits=final_hits)
        return update

    def _run_assess_transform_gate(
        self,
        state: RetrieverState,
        **_kwargs: Any,
    ) -> dict[str, Any]:
        from app.domain.query_transform import assess_transform_gate

        return assess_transform_gate(
            transform_mode=state.get("transform_mode", "off"),
            gate_score=state.get("transform_gate_score"),
            gate_threshold=float(_setting(self, "TRANSFORM_GATE_THRESHOLD", 0.70)),
        )

    def _run_plan_query_transform(
        self,
        state: RetrieverState,
        *,
        max_attempts: int = 1,
        **_kwargs: Any,
    ) -> dict[str, Any]:
        from app.domain.query_transform import plan_query_transform

        api_deadline = None
        if str(state.get("thread_id", "")).startswith("api-"):
            api_deadline = max(0.0, float(self.settings.REQUEST_TIMEOUT_SECONDS) - 8.0)
        router = _BudgetedLLM(
            self.llm,
            max_attempts=max_attempts,
            deadline_seconds=api_deadline,
        )
        update = plan_query_transform(
            state["query"],
            router=router,
            cache=self.transform_cache,
            max_tokens=int(self.settings.LLM_MAX_TOKENS_ROUTER),
        )
        action = update.get("route_action", update.get("action", "keep"))
        technique = update.get("technique")
        queries = list(update.get("transformed_queries", update.get("queries", [])))
        valid_count = True
        if action == "transform":
            if technique == "multi":
                valid_count = len(queries) == int(_setting(self, "TRANSFORM_MULTI_COUNT", 3))
            elif technique == "decomposition":
                minimum = int(_setting(self, "TRANSFORM_DECOMPOSITION_MIN", 2))
                maximum = int(_setting(self, "TRANSFORM_DECOMPOSITION_MAX", 4))
                valid_count = minimum <= len(queries) <= maximum
            else:
                valid_count = technique in {"rewrite", "hyde", "stepback"} and len(queries) == 1
        if action == "transform" and not valid_count:
            action = "keep"
            queries = []
            update["route_error"] = "질문 변환 질의 개수 규칙을 위반함"
        update.update(route_action=action, technique=technique, transformed_queries=queries)
        update.pop("action", None)
        update.pop("queries", None)
        return update

    def _run_route_query(
        self,
        state: RetrieverState,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """기존 직접 호출자를 위한 노드명 호환 처리임."""

        return self._run_plan_query_transform(state, **kwargs)

    def _run_bm25_search(self, state: RetrieverState, **_kwargs: Any) -> dict[str, Any]:
        from app.domain.access import allowed_levels

        sizes = self._candidate_sizes(state)
        scores = self.bm25.scores(
            state["query"],
            allowed_access_levels=allowed_levels(state["role"]),
            k=sizes.raw_k,
        )
        return {
            "bm25_scores": scores,
            "warnings": [] if scores else ["BM25 양수 일치 결과가 없어 벡터 검색만 사용함"],
        }

    def _fuse(
        self,
        vector_hits: list[Hit],
        bm25_scores: dict[str, float],
        role: str,
        result_size: int,
    ) -> list[Hit]:
        from app.domain.access import filter_candidates
        from app.domain.scoring import fuse

        hits = fuse(
            vector_hits,
            bm25_scores,
            self.bm25.chunks(),
            weight_bm25=float(self.settings.HYBRID_WEIGHT_BM25),
            weight_vector=float(self.settings.HYBRID_WEIGHT_VECTOR),
            top_k=result_size,
        )
        return filter_candidates(hits, role)

    def _candidate_sizes(self, state: RetrieverState) -> CandidateSizes:
        return candidate_sizes(
            state["mode"],
            int(state["top_k"]),
            int(self.settings.CANDIDATE_MULTIPLIER),
        )

    def _run_fuse_scores(self, state: RetrieverState, **_kwargs: Any) -> dict[str, Any]:
        hits = self._fuse(
            state.get("vector_hits", []),
            state.get("bm25_scores", {}),
            state["role"],
            self._candidate_sizes(state).fused_k,
        )
        return {"candidates": hits, "baseline_hits": hits}

    def _run_complete_original_results(
        self,
        state: RetrieverState,
        **_kwargs: Any,
    ) -> dict[str, Any]:
        if state.get("mode") == "vector":
            baseline = list(state.get("vector_hits", []))[: int(state.get("top_k", 0))]
        else:
            baseline = list(state.get("baseline_hits", state.get("candidates", [])))
        return {
            "baseline_hits": baseline,
            "hits": list(baseline[: int(state.get("top_k", len(baseline)))]),
        }

    def _search_one(self, query: str, state: RetrieverState) -> list[Hit]:
        from app.domain.access import allowed_levels

        sizes = self._candidate_sizes(state)
        vector_hits = self._search_vector(query, state["role"], sizes.raw_k)
        if state["mode"] == "vector":
            return vector_hits[: state["top_k"]]
        return self._fuse(
            vector_hits,
            self.bm25.scores(
                query,
                allowed_access_levels=allowed_levels(state["role"]),
                k=sizes.raw_k,
            ),
            state["role"],
            sizes.fused_k,
        )

    def _run_search_transformed(self, state: RetrieverState, **_kwargs: Any) -> dict[str, Any]:
        groups, warnings = [], []
        for query in state.get("transformed_queries", []):
            try:
                groups.append(self._search_one(query, state))
            except Exception as error:
                groups.append([])
                warnings.append(f"변환 질의 검색 실패: {type(error).__name__}")
        return {"transformed_hit_groups": groups, "warnings": warnings}

    def _run_merge_queries(self, state: RetrieverState, **_kwargs: Any) -> dict[str, Any]:
        from app.domain.query_transform import merge_query_groups

        # 검색 RRF 병합은 기존 adaptive_search 계약에 따라 하위 질의별 Top1 예약.
        # 리랭크 병합의 Top3 설정과 별도 계약.
        hits, weights, coverage = merge_query_groups(
            state.get("baseline_hits", []),
            state.get("transformed_hit_groups", []),
            technique=state.get("technique"),
            rrf_k=int(self.settings.TRANSFORM_RRF_K),
            original_weight=float(self.settings.TRANSFORM_ORIGINAL_WEIGHT),
            decomposition_original_weight=float(
                self.settings.TRANSFORM_ORIGINAL_WEIGHT_DECOMPOSITION
            ),
            decomposition_per_query_top_k=MERGE_DECOMPOSITION_PER_QUERY_TOP_K,
            top_k=state["top_k"],
        )
        return {
            "hits": hits,
            "merge_weights": weights,
            "coverage_applied": coverage,
        }

    def _run_rerank(self, state: RetrieverState, **_kwargs: Any) -> dict[str, Any]:
        from app.domain.query_transform import rerank_each_query_and_merge
        from app.domain.scoring import apply_rerank

        transformed = state.get("transformed_hit_groups", [])
        fallback = list(state.get("hits") or state.get("baseline_hits", []))
        loader = getattr(self.reranker, "_load", None)
        if callable(loader):
            loader()

        def score(query: str, texts: list[str]) -> list[float]:
            return run_with_timeout(
                self.reranker.score,
                query,
                texts,
                timeout_seconds=float(_setting(self, "TIMEOUT_RERANK", 60)),
                operation="리랭커 호출",
            )

        try:
            if not transformed:
                candidates = list(state.get("baseline_hits", []))
                scores = score(state["query"], [hit.text for hit in candidates])
                return {"hits": apply_rerank(candidates, scores, state["top_k"])}

            technique = state.get("technique")
            original_weight = (
                float(self.settings.TRANSFORM_ORIGINAL_WEIGHT_DECOMPOSITION)
                if technique == "decomposition"
                else float(self.settings.TRANSFORM_ORIGINAL_WEIGHT)
            )
            transformed_weight = (1.0 - original_weight) / len(transformed)
            groups = [("original", state["query"], state.get("baseline_hits", []), original_weight)]
            groups.extend(
                (f"transformed_{index}", query, hits, transformed_weight)
                for index, (query, hits) in enumerate(
                    zip(state.get("transformed_queries", []), transformed),
                    start=1,
                )
            )

            class TimedReranker:
                @staticmethod
                def score(query: str, texts: list[str]) -> list[float]:
                    return score(query, texts)

            return {
                "hits": rerank_each_query_and_merge(
                    groups,
                    TimedReranker(),
                    technique=technique,
                    top_n=state["top_k"],
                    rrf_k=int(self.settings.TRANSFORM_RRF_K),
                    decomposition_original_weight=float(
                        self.settings.TRANSFORM_ORIGINAL_WEIGHT_DECOMPOSITION
                    ),
                    decomposition_per_query_top_k=int(
                        self.settings.TRANSFORM_PER_QUERY_TOP_K
                    ),
                )
            }
        except Exception as error:
            return {
                "hits": fallback,
                "warnings": [f"리랭킹 실패로 직전 결과 사용: {type(error).__name__}"],
            }

    def _run_build_prompt(self, state: RetrieverState, **_kwargs: Any) -> dict[str, Any]:
        blocks = []
        for index, hit in enumerate(state.get("hits", []), start=1):
            blocks.append(
                f"[검색결과 {index}]\n"
                f"청크 ID: {hit.chunk_id}\n"
                f"원본 문서: {hit.source}\n"
                f"위치: {hit.location}\n"
                f"본문: {hit.text}"
            )
        evidence = "\n\n".join(blocks)
        hints = "\n".join(state.get("repair_hints", []))
        prompt = f"[검색결과 목록]\n{evidence}\n\n[질문]\n{state['query']}"
        if hints:
            prompt += f"\n\n[수정 지침]\n{hints}"
        return {"prompt": prompt}

    def _run_generate_answer(
        self,
        state: RetrieverState,
        *,
        max_attempts: int = 1,
        **_kwargs: Any,
    ) -> dict[str, Any]:
        deadline = None
        if str(state.get("thread_id", "")).startswith("api-"):
            deadline = max(0.0, float(self.settings.REQUEST_TIMEOUT_SECONDS) - 8.0)
        result = self.llm.complete_structured(
            "검색 근거만 사용하여 결론·주의사항·근거 인용을 구조화 출력함.",
            state["prompt"],
            AnswerDraft,
            max_tokens=int(self.settings.LLM_MAX_TOKENS_ANSWER),
            deadline_seconds=deadline,
            max_attempts=max_attempts,
        )
        raw = result.parsed.model_dump() if result.parsed is not None else {
            "conclusion": "",
            "caution": "",
            "evidence": [],
            "parsing_error": result.parsing_error,
        }
        return {"raw_answer": raw, "llm_calls": result.attempts}

    def _run_verify_evidence(self, state: RetrieverState, **_kwargs: Any) -> dict[str, Any]:
        from app.domain.scoring import build_answer

        answer = build_answer(state.get("raw_answer", {}), state.get("hits", []))
        verification = answer.verification
        hints = [
            *verification.schema_errors,
            *(item.get("reason", "") for item in verification.quote_failures),
            *(item.get("reason", "") for item in verification.location_failures),
        ]
        return {
            "answer": answer.model_dump(),
            "repair_hints": [hint for hint in hints if hint],
        }


def load_resources(
    *,
    settings: Any = None,
    embedder: Any = None,
    vector_store: Any = None,
    bm25: Any = None,
    reranker: Any = None,
    llm: Any = None,
    transform_cache: Any = None,
) -> RetrieverResources:
    """기본 구현체를 조립하되 시험에서는 모든 포트를 교체 가능하게 함."""

    from app.infrastructure.bm25_index import BM25Index
    from app.infrastructure.chroma_store import create_vector_store
    from app.infrastructure.corpus_store import VersionedCorpusStore
    from app.infrastructure.llm_client import LangChainLLMClient
    from app.infrastructure.reranker import CrossEncoderReranker
    from app.infrastructure.transform_cache import TransformCache
    from app.domain.korean_tokenizer import KoreanTokenizer
    from app.settings import load_settings

    loaded = settings or load_settings()
    actual_embedder = embedder or _LazyHuggingFaceEmbedder(loaded.EMBED_MODEL)
    actual_store = vector_store or create_vector_store(
        backend=getattr(loaded, "VECTOR_STORE_BACKEND", "chroma"),
        path=Path(loaded.CHROMA_PATH),
        collection=loaded.CHROMA_COLLECTION,
        signature=actual_embedder.signature,
    )
    actual_bm25 = bm25 or BM25Index(
        VersionedCorpusStore(Path(loaded.SEARCH_INDEX_ROOT)),
        KoreanTokenizer(
            getattr(loaded, "KOREAN_USER_DICTIONARY", None),
            num_workers=int(getattr(loaded, "KOREAN_TOKENIZER_WORKERS", 1)),
        ),
    )
    if bm25 is None:
        actual_bm25.warm()
    return RetrieverResources(
        settings=loaded,
        embedder=actual_embedder,
        vector_store=actual_store,
        bm25=actual_bm25,
        reranker=reranker
        or CrossEncoderReranker(
            loaded.RERANK_MODEL,
            max_length=int(loaded.RERANK_MAX_LENGTH),
        ),
        llm=llm or LangChainLLMClient(loaded),
        transform_cache=transform_cache or TransformCache(loaded.TRANSFORM_CACHE_PATH),
    )


def _initial_state(request: RetrieverRequest) -> RetrieverState:
    return {
        "query": request.query,
        "role": request.role,
        "mode": request.mode,
        "top_k": request.top_k,
        "dry_run": request.dry_run,
        "prompt_only": request.prompt_only,
        "max_llm_calls": request.max_llm_calls,
        "thread_id": request.thread_id,
        "force_fail_node": None,
        "transform_mode": request.transform,
        "repair_count": 0,
        "llm_calls": 0,
        "status": "ok",
        "exit_code": 0,
    }


def _invoke(
    # request: CLI·API에서 받은 검색 요청을 검증해 만든 RetrieverRequest 객체임.
    # - query: 검색할 질문, top_k: 최종 문서 수, mode: vector·hybrid·hybrid_rerank 검색 방식
    # - transform: 질문 변환 방식, role: 문서 접근 역할, thread_id: 실행·체크포인트 식별값
    # - dry_run: 인덱스 확인만 할지 여부, prompt_only: LLM 호출 전 멈출지 여부
    # - max_llm_calls: 이번 요청에서 허용할 최대 LLM 호출 횟수
    request: RetrieverRequest,
    # resources: Retriever의 각 노드가 실제 작업에 사용하는 RetrieverResources 객체임.
    # - settings: 설정값, embedder: 질문 벡터 변환기, vector_store: Chroma 검색·조회 객체
    # - bm25: 키워드 검색기, reranker: 후보 재정렬기, llm: 질문 변환·답변 생성기
    # - transform_cache: 같은 질문의 변환 결과를 저장·조회하는 캐시
    resources: Any,
    *,
    answer_enabled: bool,
) -> SearchResult:
    started = monotonic()
    checkpoint = Path(__file__).resolve().parents[2] / "data" / "checkpoints" / "retriever.sqlite"
    saver = open_sqlite_checkpointer(checkpoint)
    try:
        graph = build_graph(resources, saver, answer_enabled=answer_enabled)
        config = execution_config(request.thread_id, int(_setting(resources, "RECURSION_LIMIT", 25)))
        existing = saver.get_tuple(config)
        final_state = graph.invoke(None if existing else _initial_state(request), config)
    finally:
        saver.conn.close()
    final_state["timings"] = {
        **final_state.get("timings", {}),
        "total_ms": max(0, round((monotonic() - started) * 1000)),
    }
    return build_search_result(final_state)


def search_documents(
    request: RetrieverRequest,
    resources: Any = None,
) -> SearchResult:
    """검색 유스케이스 한 건을 실행함."""

    return _invoke(
        request,
        resources or load_resources(),
        answer_enabled=False,
    )


def answer_question(
    request: RetrieverRequest,
    resources: Any = None,
) -> SearchResult:
    """답변 유스케이스 한 건을 실행함."""

    return _invoke(
        request,
        resources or load_resources(),
        answer_enabled=True,
    )


async def stream_answer(
    request: RetrieverRequest,
    resources: Any = None,
) -> AsyncIterator[dict[str, Any]]:
    """그래프 이벤트와 최종 결과를 순서대로 전달함."""

    actual = resources or load_resources()
    graph = build_graph(actual, None, answer_enabled=True)
    config = execution_config(request.thread_id, int(_setting(actual, "RECURSION_LIMIT", 25)))
    started = monotonic()
    async for item in graph.astream_events(_initial_state(request), config, version="v2"):
        metadata = item.get("metadata", {})
        node = metadata.get("langgraph_node")
        name = item.get("name")
        elapsed = max(0, round((monotonic() - started) * 1000))
        if node and name == node and item["event"] == "on_chain_start":
            yield {"event": "node_start", "data": {"node": node, "elapsed_ms": elapsed}}
        elif node and name == node and item["event"] == "on_chain_end":
            data = {"node": node, "elapsed_ms": elapsed}
            output = item.get("data", {}).get("output") or {}
            hit_keys = {
                "vector_search": "vector_hits",
                "bm25_search": "bm25_scores",
                "fuse_scores": "candidates",
                "rerank": "hits",
            }
            if node in hit_keys:
                data["hit_count"] = len(output.get(hit_keys[node], []))
            yield {"event": "node_end", "data": data}
        elif (
            item["event"] == "on_chain_end"
            and name == "LangGraph"
            and not node
        ):
            state = item.get("data", {}).get("output") or {}
            state["timings"] = {
                **state.get("timings", {}),
                "total_ms": elapsed,
            }
            yield {
                "event": "final",
                "data": build_search_result(state).model_dump(mode="json"),
            }


def check_health(resources: Any = None) -> HealthResult:
    """준비된 검색 자원의 상태를 확인함."""

    actual = resources or load_resources()
    description = actual.vector_store.describe()
    count = int(description.get("count", 0))
    signature_ok = description.get("signature") == actual.embedder.signature
    dimension = int(description.get("dimension") or getattr(actual.embedder, "dimension", 0))
    return HealthResult(
        status="ok" if count > 0 and signature_ok else "error",
        index_connected=count > 0 and signature_ok,
        collection_count=count,
        embedding_dimension=dimension,
        llm_provider=str(actual.settings.LLM_PROVIDER),
        models={
            "embed": str(actual.settings.EMBED_MODEL),
            "rerank": str(actual.settings.RERANK_MODEL),
            "llm": str(
                actual.settings.get(f"{str(actual.settings.LLM_PROVIDER).upper()}_MODEL", "")
            ),
        },
    )
