"""답변 LLM을 제외한 Retriever 검색 워크플로우 조건 조합 시험."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from app.application.graph import RetrieverResources, build_graph, execution_config
from app.application.state import Hit, RouteDecision


ORIGINAL_QUERY = "원 질문"
TRANSFORMED_QUERIES = ["변환 질문 1", "변환 질문 2"]


def _hit(index: int, vector_score: float) -> Hit:
    return Hit(
        chunk_id=f"D1_{index:04d}",
        score=vector_score,
        vector_score=vector_score,
        access_level="public",
        source="D1.pdf",
        location=f"제{index + 1}조",
        text=f"검색 후보 {index}",
        metadata={"access_level": "public"},
    )


class RecordingEmbedder:
    signature = "test-signature"
    dimension = 4

    def __init__(self, events: list[str]) -> None:
        self.events = events
        self.queries: list[str] = []

    def embed_query(self, query: str) -> list[float]:
        self.queries.append(query)
        self.events.append(f"vector:{query}")
        return [float(len(self.queries)), 0.0, 0.0, 0.0]


class RecordingVectorStore:
    def __init__(self, original_score: float) -> None:
        self.original_score = original_score
        self.search_calls: list[int] = []

    def count(self) -> int:
        return 8

    def check_signature(self, signature: str) -> bool:
        return signature == "test-signature"

    def get_all(self) -> dict[str, list[list[float]]]:
        return {"embeddings": [[0.0, 0.0, 0.0, 0.0]]}

    def search(self, _embedding: list[float], size: int, _where: dict) -> list[Hit]:
        self.search_calls.append(size)
        top_score = self.original_score if len(self.search_calls) == 1 else 0.88
        return [_hit(index, max(0.01, top_score - index * 0.01)) for index in range(min(size, 8))]


class RecordingBm25:
    def __init__(self, events: list[str]) -> None:
        self.events = events
        self.queries: list[str] = []
        self._chunks = {hit.chunk_id: hit for hit in [_hit(index, 0.8 - index * 0.01) for index in range(8)]}

    def scores(self, query: str) -> dict[str, float]:
        self.queries.append(query)
        self.events.append(f"bm25:{query}")
        return {chunk_id: float(len(self._chunks) - index) for index, chunk_id in enumerate(self._chunks)}

    def chunks(self) -> dict[str, Hit]:
        return self._chunks


class RecordingReranker:
    def __init__(self, events: list[str]) -> None:
        self.events = events
        self.queries: list[str] = []

    def score(self, query: str, texts: list[str]) -> list[float]:
        self.queries.append(query)
        self.events.append(f"rerank:{query}")
        return [1.0 - index * 0.01 for index, _text in enumerate(texts)]


class RouterOnlyLLM:
    """질문 변환 계획만 허용하고 답변 생성 호출은 즉시 실패시킴."""

    def __init__(self, action: str, events: list[str]) -> None:
        self.action = action
        self.events = events
        self.calls = 0

    def complete_structured(self, _system: str, _user: str, schema, **_kwargs):
        if schema is not RouteDecision:
            raise AssertionError("검색 전용 시험에서 답변 LLM이 호출됨")
        self.calls += 1
        self.events.append("router")
        if self.action == "transform":
            return RouteDecision(
                action="transform",
                technique="decomposition",
                queries=TRANSFORMED_QUERIES,
                reason="복합 질문",
                clarification="",
            )
        return RouteDecision(
            action="keep",
            technique=None,
            queries=[],
            reason="원 질문 유지",
            clarification="",
        )


def _settings() -> SimpleNamespace:
    return SimpleNamespace(
        CHROMA_COLLECTION="test",
        CANDIDATE_MULTIPLIER=2,
        HYBRID_WEIGHT_BM25=0.3,
        HYBRID_WEIGHT_VECTOR=0.7,
        TRANSFORM_GATE_THRESHOLD=0.70,
        TRANSFORM_MULTI_COUNT=3,
        TRANSFORM_DECOMPOSITION_MIN=2,
        TRANSFORM_DECOMPOSITION_MAX=4,
        TRANSFORM_RRF_K=60,
        TRANSFORM_ORIGINAL_WEIGHT=0.5,
        TRANSFORM_ORIGINAL_WEIGHT_DECOMPOSITION=0.1,
        TRANSFORM_PER_QUERY_TOP_K=3,
        LLM_MAX_TOKENS_ROUTER=200,
        ANSWER_GATE_THRESHOLD=0.5,
        TIMEOUT_VECTOR_SEARCH=2,
        TIMEOUT_RERANK=2,
        REQUEST_TIMEOUT_SECONDS=30,
    )


def _state(mode: str, transform_mode: str, thread_id: str) -> dict:
    return {
        "query": ORIGINAL_QUERY,
        "role": "agent",
        "mode": mode,
        "top_k": 3,
        "dry_run": False,
        "prompt_only": False,
        "max_llm_calls": 4,
        "thread_id": thread_id,
        "force_fail_node": None,
        "transform_mode": transform_mode,
        "repair_count": 0,
        "llm_calls": 0,
        "status": "ok",
        "exit_code": 0,
    }


def _resources(
    *,
    original_score: float,
    router_action: str,
    events: list[str],
    log_dir: Path,
) -> tuple[RetrieverResources, RecordingEmbedder, RecordingVectorStore, RecordingBm25, RecordingReranker, RouterOnlyLLM]:
    embedder = RecordingEmbedder(events)
    vector_store = RecordingVectorStore(original_score)
    bm25 = RecordingBm25(events)
    reranker = RecordingReranker(events)
    llm = RouterOnlyLLM(router_action, events)
    resources = RetrieverResources(
        settings=_settings(),
        embedder=embedder,
        vector_store=vector_store,
        bm25=bm25,
        reranker=reranker,
        llm=llm,
        transform_cache=None,
    )
    resources.log_dir = log_dir
    return resources, embedder, vector_store, bm25, reranker, llm


class SearchWorkflowMatrixTest(unittest.TestCase):
    def test_search_only_matrix_excludes_answer_llm_and_reuses_original_vector_search(self) -> None:
        scenarios = [
            ("off", "off", 0.40, "keep", "off", 0),
            ("gate_pass", "auto", 0.70, "keep", "gate_pass", 0),
            ("keep", "auto", 0.69, "keep", "keep", 0),
            ("transform", "auto", 0.69, "transform", "transform", 2),
        ]

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for mode in ("vector", "hybrid", "hybrid_rerank"):
                for variant, transform_mode, score, router_action, expected_action, transformed_count in scenarios:
                    name = f"{mode}-{variant}"
                    with self.subTest(case=name):
                        events: list[str] = []
                        resources, embedder, vector_store, bm25, reranker, llm = _resources(
                            original_score=score,
                            router_action=router_action,
                            events=events,
                            log_dir=root / name,
                        )
                        result = build_graph(resources, None, answer_enabled=False).invoke(
                            _state(mode, transform_mode, name),
                            execution_config(name),
                        )

                        expected_queries = [ORIGINAL_QUERY] + (
                            TRANSFORMED_QUERIES if transformed_count else []
                        )
                        self.assertEqual(expected_queries, embedder.queries)
                        self.assertEqual(1 + transformed_count, len(vector_store.search_calls))
                        self.assertEqual(1, embedder.queries.count(ORIGINAL_QUERY))

                        expected_bm25 = [] if mode == "vector" else [ORIGINAL_QUERY] + (
                            TRANSFORMED_QUERIES if transformed_count else []
                        )
                        self.assertEqual(expected_bm25, bm25.queries)
                        self.assertEqual(1 if variant in {"keep", "transform"} else 0, llm.calls)

                        expected_reranks = 0
                        if mode == "hybrid_rerank":
                            expected_reranks = 1 + transformed_count
                        self.assertEqual(expected_reranks, len(reranker.queries))

                        self.assertEqual(expected_action, result["route_action"])
                        self.assertEqual("ok", result["status"])
                        self.assertTrue(result["hits"])
                        self.assertLessEqual(len(result["hits"]), result["top_k"])

                        timings = result.get("timings", {})
                        self.assertIn("assess_transform_gate", timings)
                        self.assertIn("complete_original_results", timings)
                        self.assertEqual(variant in {"keep", "transform"}, "plan_query_transform" in timings)
                        self.assertEqual(bool(transformed_count), "search_transformed" in timings)
                        self.assertEqual(bool(transformed_count), "merge_queries" in timings)
                        self.assertEqual(mode == "hybrid_rerank", "rerank" in timings)
                        self.assertNotIn("build_prompt", timings)
                        self.assertNotIn("generate_answer", timings)
                        self.assertNotIn("verify_evidence", timings)
                        self.assertNotIn("prompt", result)
                        self.assertNotIn("raw_answer", result)
                        self.assertNotIn("answer", result)

                        if transformed_count:
                            self.assertLess(events.index("vector:원 질문"), events.index("router"))
                            self.assertLess(events.index("router"), events.index("vector:변환 질문 1"))
                            if mode != "vector":
                                self.assertLess(
                                    events.index("bm25:원 질문"),
                                    events.index("vector:변환 질문 1"),
                                )


if __name__ == "__main__":
    unittest.main()
