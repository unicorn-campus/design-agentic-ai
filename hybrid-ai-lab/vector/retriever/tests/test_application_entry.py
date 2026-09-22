"""Retriever 응용 진입 함수와 SSE 변환 시험."""

import asyncio
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from app.application.graph import (
    RetrieverResources,
    build_graph,
    check_health,
    execution_config,
    stream_answer,
)
from app.application.state import Hit, RetrieverRequest


class FakeStreamGraph:
    async def astream_events(self, _state, _config, *, version):
        assert version == "v2"
        yield {
            "event": "on_chain_start",
            "name": "vector_search",
            "metadata": {"langgraph_node": "vector_search"},
            "data": {},
        }
        yield {
            "event": "on_chain_end",
            "name": "vector_search",
            "metadata": {"langgraph_node": "vector_search"},
            "data": {"output": {"vector_hits": [{}, {}]}},
        }
        yield {
            "event": "on_chain_end",
            "name": "LangGraph",
            "metadata": {},
            "data": {
                "output": {
                    "query": "질문",
                    "role": "agent",
                    "mode": "vector",
                    "top_k": 5,
                    "transform_mode": "off",
                    "hits": [],
                    "route_action": "off",
                    "status": "needs_check",
                    "thread_id": "api-stream",
                    "llm_calls": 0,
                    "timings": {},
                }
            },
        }


class FakeVectorStore:
    def describe(self):
        return {"count": self.count(), "dimension": 4, "signature": "signature"}

    def count(self):
        return 1

    def check_signature(self, _signature):
        return True

def candidate_hit(index: int) -> Hit:
    return Hit(
        chunk_id=f"D1_{index:04d}",
        score=1.0 - index / 100,
        vector_score=1.0 - index / 100,
        access_level="public",
        source="D1.pdf",
        location=f"제{index}조",
        text=f"후보 {index}",
        metadata={"access_level": "public"},
    )


class CandidateVectorStore(FakeVectorStore):
    def __init__(self) -> None:
        self.hits = [candidate_hit(index) for index in range(40)]
        self.requested_sizes: list[int] = []

    def count(self):
        return len(self.hits)

    def search(self, _embedding, size, _metadata_filter, _options=None):
        self.requested_sizes.append(size)
        return self.hits[:size]


class CandidateBm25:
    def keyword_search(self, _query, *, allowed_access_levels=None, k=10):
        del allowed_access_levels
        del k
        return {}

    def chunks(self):
        return {}


class RecordingReranker:
    def __init__(self) -> None:
        self.batch_sizes: list[int] = []

    def score(self, _query, texts):
        self.batch_sizes.append(len(texts))
        return [float(index) for index, _text in enumerate(texts)]


def candidate_resources() -> RetrieverResources:
    settings = SimpleNamespace(
        CHROMA_COLLECTION="test",
        CANDIDATE_MULTIPLIER=4,
        HYBRID_WEIGHT_BM25=0.3,
        HYBRID_WEIGHT_VECTOR=0.7,
        TRANSFORM_RRF_K=60,
        TRANSFORM_ORIGINAL_WEIGHT=0.5,
        TRANSFORM_ORIGINAL_WEIGHT_DECOMPOSITION=0.1,
        TRANSFORM_PER_QUERY_TOP_K=3,
    )
    return RetrieverResources(
        settings=settings,
        embedder=SimpleNamespace(signature="signature", dimension=4, embed_query=lambda _query: [0.0] * 4),
        vector_store=CandidateVectorStore(),
        bm25=CandidateBm25(),
        reranker=RecordingReranker(),
        llm=None,
        transform_cache=None,
    )


def candidate_state(mode: str) -> dict:
    return {
        "query": "질문",
        "role": "agent",
        "mode": mode,
        "top_k": 5,
        "dry_run": False,
        "prompt_only": False,
        "max_llm_calls": 8,
        "thread_id": f"ret-{mode}",
        "transform_mode": "off",
        "repair_count": 0,
        "llm_calls": 0,
        "status": "ok",
        "exit_code": 0,
    }


class RetrieverApplicationEntryTest(unittest.TestCase):
    def test_vector_rerank_expands_vector_candidates_before_reranking(self) -> None:
        resources = candidate_resources()
        result = build_graph(resources, None, answer_enabled=False).invoke(
            candidate_state("vector_rerank"),
            execution_config("ret-candidate-vector-rerank"),
        )
        self.assertEqual([40], resources.vector_store.requested_sizes)
        self.assertEqual([10], resources.reranker.batch_sizes)
        self.assertEqual(5, len(result["hits"]))

    def test_vector_rerank_failure_keeps_vector_top_k(self) -> None:
        class FailingReranker:
            @staticmethod
            def score(_query, _texts):
                raise RuntimeError("리랭크 실패")

        resources = candidate_resources()
        resources.reranker = FailingReranker()
        result = build_graph(resources, None, answer_enabled=False).invoke(
            candidate_state("vector_rerank"),
            execution_config("ret-candidate-vector-rerank-fallback"),
        )
        self.assertEqual(
            [f"D1_{index:04d}" for index in range(5)],
            [hit.chunk_id for hit in result["hits"]],
        )
        self.assertIn("리랭킹 실패로 직전 결과 사용", result["warnings"][-1])

    def test_hybrid_rerank_restores_baseline_candidate_contract(self) -> None:
        resources = candidate_resources()
        result = build_graph(resources, None, answer_enabled=False).invoke(
            candidate_state("hybrid_rerank"),
            execution_config("ret-candidate-rerank"),
        )
        self.assertEqual([40], resources.vector_store.requested_sizes)
        self.assertEqual([10], resources.reranker.batch_sizes)
        self.assertEqual(5, len(result["hits"]))

    def test_vector_and_hybrid_keep_top_k_final_hits(self) -> None:
        for mode in ("vector", "hybrid"):
            with self.subTest(mode=mode):
                resources = candidate_resources()
                result = build_graph(resources, None, answer_enabled=False).invoke(
                    candidate_state(mode),
                    execution_config(f"ret-candidate-{mode}"),
                )
                self.assertEqual([20], resources.vector_store.requested_sizes)
                self.assertEqual([], resources.reranker.batch_sizes)
                self.assertEqual(5, len(result["hits"]))

    def test_transformed_rerank_keeps_candidate_size_per_query(self) -> None:
        resources = candidate_resources()
        state = {
            **candidate_state("hybrid_rerank"),
            "query": "원 질문",
            "technique": "rewrite",
            "transformed_queries": ["변환 질문 1", "변환 질문 2"],
        }
        baseline = resources._search_one("원 질문", state)
        state.update(baseline_hits=baseline, hits=baseline[:5])
        transformed = resources._run_search_transformed(state)
        groups = transformed["transformed_hit_groups"]
        self.assertEqual([40, 40, 40], resources.vector_store.requested_sizes)
        self.assertEqual([10, 10], [len(group) for group in groups])

        result = resources._run_rerank({**state, **transformed})
        self.assertEqual([10, 10, 10], resources.reranker.batch_sizes)
        self.assertEqual(5, len(result["hits"]))

    def test_search_merge_top_one_and_rerank_top_three_are_distinct(self) -> None:
        resources = candidate_resources()
        state = {
            **candidate_state("hybrid_rerank"),
            "query": "원 질문",
            "technique": "decomposition",
            "transformed_queries": ["하위 질문 1", "하위 질문 2"],
        }
        baseline = resources._search_one("원 질문", state)
        state.update(
            baseline_hits=baseline,
            hits=baseline[:5],
            transformed_hit_groups=[baseline, baseline],
        )
        with patch(
            "app.domain.query_transform.merge_query_groups",
            return_value=(baseline[:5], {}, True),
        ) as merge:
            resources._run_merge_queries(state)
        self.assertEqual(1, merge.call_args.kwargs["decomposition_per_query_top_k"])

        with patch(
            "app.domain.query_transform.rerank_each_query_and_merge",
            return_value=baseline[:5],
        ) as rerank:
            resources._run_rerank(state)
        self.assertEqual(3, rerank.call_args.kwargs["decomposition_per_query_top_k"])

    def test_stream_maps_v2_events_and_final_once(self) -> None:
        request = RetrieverRequest(
            query="질문",
            role="agent",
            mode="vector",
            transform="off",
            thread_id="api-stream",
        )
        resources = {"settings": {"RECURSION_LIMIT": 25}}

        async def collect():
            with patch("app.application.graph.build_graph", return_value=FakeStreamGraph()):
                return [item async for item in stream_answer(request, resources)]

        events = asyncio.run(collect())
        self.assertEqual(["node_start", "node_end", "final"], [item["event"] for item in events])
        self.assertEqual(2, events[1]["data"]["hit_count"])
        self.assertEqual(1, sum(item["event"] == "final" for item in events))

    def test_health_uses_wired_resources_without_loading_models(self) -> None:
        settings = SimpleNamespace(
            LLM_PROVIDER="groq",
            EMBED_MODEL="KURE",
            RERANK_MODEL="bge",
            GROQ_MODEL="gpt-oss",
            get=lambda name, default=None: {
                "GROQ_MODEL": "gpt-oss",
            }.get(name, default),
        )
        resources = SimpleNamespace(
            settings=settings,
            vector_store=FakeVectorStore(),
            embedder=SimpleNamespace(signature="signature", dimension=0),
        )
        result = check_health(resources)
        self.assertTrue(result.index_connected)
        self.assertEqual(4, result.embedding_dimension)
        self.assertEqual("gpt-oss", result.models["llm"])


if __name__ == "__main__":
    unittest.main()
