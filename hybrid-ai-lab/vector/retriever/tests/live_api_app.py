"""모델 없이 로컬 HTTP 경계를 검증하기 위한 ASGI 시험 조립."""

from __future__ import annotations

from app.application.state import HealthResult, RouteInfo, SearchResult
from app.presentation import api


class FakeResources:
    """실기동 검증용 경량 자원."""

    settings = {
        "MAX_LLM_CALLS_TOTAL": 200,
        "MAX_LLM_CALLS_PER_REQUEST": 2,
        "REQUEST_TIMEOUT_SECONDS": 5,
    }


def _health(_resources: FakeResources) -> HealthResult:
    return HealthResult(
        status="ok",
        index_connected=True,
        collection_count=485,
        embedding_dimension=1024,
        llm_provider="fake",
        models={"embed": "fake", "rerank": "fake", "llm": "fake"},
    )


def _result(request, *, answer=None) -> SearchResult:
    return SearchResult(
        query=request.query,
        mode=request.mode,
        transform=request.transform,
        role=request.role,
        top_k=request.top_k,
        answer=answer,
        route=RouteInfo(action="off", gate_score=0.8),
        status="ok",
        thread_id=request.thread_id,
    )


def _search(request, _resources: FakeResources) -> SearchResult:
    return _result(request)


def _answer(request, _resources: FakeResources) -> SearchResult:
    return _result(request)


async def _stream(request, _resources: FakeResources):
    nodes = (
        "check_search_readiness",
        "vector_search",
        "route_query",
        "bm25_search",
        "fuse_scores",
        "build_prompt",
        "generate_answer",
        "verify_evidence",
    )
    for node in nodes:
        yield {"event": "node_start", "data": {"node": node, "elapsed_ms": 0}}
        yield {"event": "node_end", "data": {"node": node, "elapsed_ms": 1}}
    yield {"event": "final", "data": _result(request).model_dump(mode="json")}


api.app.state.resource_loader = FakeResources
api.app.dependency_overrides[api.get_health_fn] = lambda: _health
api.app.dependency_overrides[api.get_search_fn] = lambda: _search
api.app.dependency_overrides[api.get_answer_fn] = lambda: _answer
api.app.dependency_overrides[api.get_stream_fn] = lambda: _stream

app = api.app
