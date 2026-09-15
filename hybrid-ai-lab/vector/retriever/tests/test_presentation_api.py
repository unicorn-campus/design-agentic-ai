"""Retriever FastAPI·SSE 표현 경계 시험."""

from __future__ import annotations

import time
import unittest

from fastapi.testclient import TestClient

from app.application.state import (
    Answer,
    HealthResult,
    Hit,
    RouteInfo,
    SearchResult,
    Verification,
)
from app.presentation import api


class FakeResources:
    settings = {
        "MAX_LLM_CALLS_TOTAL": 200,
        "MAX_LLM_CALLS_PER_REQUEST": 2,
        "REQUEST_TIMEOUT_SECONDS": 1,
    }


def make_hit() -> Hit:
    return Hit(
        chunk_id="D1_0010",
        score=0.8,
        vector_score=0.8,
        rerank_score=None,
        access_level="public",
        source="D1.pdf",
        location="제4조",
        text="연회비 면제 조건",
        metadata={"access_level": "public"},
    )


def make_result(*, with_answer: bool = False, llm_calls: int = 0) -> SearchResult:
    answer = None
    if with_answer:
        answer = Answer(
            conclusion="조건 충족 시 면제됨",
            caution="상품별 조건 확인 필요",
            evidence=[],
            sources=["D1.pdf"],
            verification=Verification(automatic_valid=True),
        )
    return SearchResult(
        query="연회비 면제 조건은?",
        mode="hybrid",
        transform="off",
        role="agent",
        top_k=5,
        hits=[make_hit()],
        answer=answer,
        route=RouteInfo(action="off", gate_score=0.8),
        status="ok",
        thread_id="api-test",
        llm_calls=llm_calls,
    )


def healthy() -> HealthResult:
    return HealthResult(
        status="ok",
        index_connected=True,
        collection_count=485,
        embedding_dimension=1024,
        llm_provider="groq",
        models={"embed": "KURE", "rerank": "bge", "llm": "gpt-oss"},
    )


class RetrieverApiTest(unittest.TestCase):
    def setUp(self) -> None:
        api.app.dependency_overrides.clear()
        api.app.state.resource_loader = FakeResources
        api.app.dependency_overrides[api.get_health_fn] = lambda: lambda _resources: healthy()

    def tearDown(self) -> None:
        api.app.dependency_overrides.clear()

    def client(self) -> TestClient:
        return TestClient(api.app, raise_server_exceptions=False)

    def test_health_ok(self) -> None:
        with self.client() as client:
            response = client.get("/health", headers={"X-Role": "agent"})
        self.assertEqual(200, response.status_code)
        self.assertEqual(1024, response.json()["embedding_dimension"])
        self.assertEqual({"embed", "rerank", "llm"}, set(response.json()["models"]))

    def test_search_agent_ok(self) -> None:
        api.app.dependency_overrides[api.get_search_fn] = lambda: (
            lambda _request, _resources: make_result()
        )
        with self.client() as client:
            response = client.post(
                "/search",
                headers={"X-Role": "agent"},
                json={"query": "연회비 면제 조건은?", "mode": "hybrid"},
            )
        body = response.json()
        self.assertEqual(200, response.status_code)
        self.assertIsNone(body["answer"])
        self.assertEqual(0, body["llm_calls"])
        self.assertEqual(32, len(body["request_id"]))
        self.assertEqual(9, len(body["hits"][0]))

    def test_answer_ok(self) -> None:
        api.app.dependency_overrides[api.get_answer_fn] = lambda: (
            lambda _request, _resources: make_result(with_answer=True, llm_calls=1)
        )
        with self.client() as client:
            response = client.post(
                "/answer",
                headers={"X-Role": "agent"},
                json={"query": "연회비 면제 조건은?", "mode": "hybrid"},
            )
            self.assertEqual(1, api.app.state.llm_counter.used)
        self.assertEqual(200, response.status_code)
        self.assertTrue(response.json()["answer"]["verification"]["automatic_valid"])

    def test_missing_role_400(self) -> None:
        with self.client() as client:
            response = client.get("/health")
        self.assertEqual(400, response.status_code)
        self.assertEqual("invalid_role", response.json()["error_code"])
        self.assertEqual({"error_code", "message", "detail"}, set(response.json()))

    def test_unknown_role_400_without_reflection(self) -> None:
        with self.client() as client:
            response = client.get("/health", headers={"X-Role": "root-secret"})
        self.assertEqual(400, response.status_code)
        self.assertEqual("invalid_role", response.json()["error_code"])
        self.assertNotIn("root-secret", response.text)

    def test_invalid_body_400_instead_of_422(self) -> None:
        with self.client() as client:
            response = client.post(
                "/search",
                headers={"X-Role": "agent"},
                json={"query": "", "top_k": 0},
            )
        self.assertEqual(400, response.status_code)
        self.assertEqual("invalid_request", response.json()["error_code"])

    def test_openapi_exposes_four_routes(self) -> None:
        with self.client() as client:
            self.assertEqual(200, client.get("/docs").status_code)
            paths = client.get("/openapi.json").json()["paths"]
        self.assertEqual({"/health", "/search", "/answer", "/answer/stream"}, set(paths))

    def test_llm_call_limit_429(self) -> None:
        api.app.dependency_overrides[api.get_answer_fn] = lambda: (
            lambda _request, _resources: make_result(with_answer=True)
        )
        with self.client() as client:
            api.app.state.llm_counter.add(api.app.state.llm_counter.limit)
            response = client.post(
                "/answer",
                headers={"X-Role": "agent"},
                json={"query": "질문"},
            )
        self.assertEqual(429, response.status_code)
        self.assertEqual("llm_call_limit", response.json()["error_code"])

    def test_answer_without_first_draft_at_request_limit_is_429(self) -> None:
        limited = make_result(llm_calls=2).model_copy(update={"status": "halted_by_limit"})
        api.app.dependency_overrides[api.get_answer_fn] = lambda: (
            lambda _request, _resources: limited
        )
        with self.client() as client:
            response = client.post(
                "/answer",
                headers={"X-Role": "agent"},
                json={"query": "질문"},
            )
        self.assertEqual(429, response.status_code)
        self.assertEqual("llm_call_limit", response.json()["error_code"])

    def test_request_timeout_504(self) -> None:
        resources = FakeResources()
        resources.settings = {**resources.settings, "REQUEST_TIMEOUT_SECONDS": 0.001}
        api.app.state.resource_loader = lambda: resources

        def slow_answer(_request, _resources):
            time.sleep(0.02)
            return make_result()

        api.app.dependency_overrides[api.get_answer_fn] = lambda: slow_answer
        with self.client() as client:
            response = client.post(
                "/answer",
                headers={"X-Role": "agent"},
                json={"query": "질문"},
            )
        self.assertEqual(504, response.status_code)
        self.assertEqual("timeout", response.json()["error_code"])

    def test_index_unavailable_503(self) -> None:
        unavailable = healthy().model_copy(
            update={"status": "error", "index_connected": False, "collection_count": 0}
        )
        api.app.dependency_overrides[api.get_health_fn] = lambda: (
            lambda _resources: unavailable
        )
        with self.client() as client:
            response = client.get("/health", headers={"X-Role": "agent"})
        self.assertEqual(503, response.status_code)
        self.assertEqual("index_unavailable", response.json()["error_code"])

    def test_internal_error_500(self) -> None:
        def broken(_request, _resources):
            raise RuntimeError("내부 상세")

        api.app.dependency_overrides[api.get_answer_fn] = lambda: broken
        with self.client() as client:
            response = client.post(
                "/answer",
                headers={"X-Role": "agent"},
                json={"query": "질문"},
            )
        self.assertEqual(500, response.status_code)
        self.assertEqual("internal_error", response.json()["error_code"])
        self.assertNotIn("내부 상세", response.text)

    def test_stream_event_order_and_single_final(self) -> None:
        nodes = [
            "check_query",
            "vector_search",
            "route_query",
            "bm25_search",
            "fuse_scores",
            "build_prompt",
            "generate_answer",
            "verify_evidence",
        ]

        async def fake_stream(_request, _resources):
            for node in nodes:
                yield {"event": "node_start", "data": {"node": node, "elapsed_ms": 0}}
                yield {"event": "node_end", "data": {"node": node, "elapsed_ms": 1}}
            yield {"event": "final", "data": make_result(with_answer=True).model_dump()}

        api.app.dependency_overrides[api.get_stream_fn] = lambda: fake_stream
        with self.client() as client:
            response = client.get(
                "/answer/stream",
                headers={"X-Role": "agent"},
                params={"query": "연회비 면제 조건은?", "mode": "hybrid"},
            )
        self.assertEqual(200, response.status_code)
        self.assertEqual("text/event-stream", response.headers["content-type"].split(";")[0])
        self.assertEqual(8, response.text.count("event: node_start"))
        self.assertEqual(8, response.text.count("event: node_end"))
        self.assertEqual(1, response.text.count("event: final"))
        self.assertIn('"request_id"', response.text)


if __name__ == "__main__":
    unittest.main()
