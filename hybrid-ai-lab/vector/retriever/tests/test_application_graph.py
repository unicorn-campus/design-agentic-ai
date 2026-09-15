"""Retriever StateGraph의 mode 분기·루프·체크포인트 시험."""

from __future__ import annotations

import tempfile
import json
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace

from app.application.graph import (
    RETRIEVER_NODE_NAMES,
    ForcedNodeError,
    RetrieverResources,
    build_graph,
    execution_config,
    open_sqlite_checkpointer,
    remaining_llm_attempts,
)
from app.application.runtime import OperationTimeoutError
from app.application.state import Hit, build_search_result, merge_timings


def hit(chunk_id: str = "D1_0000", vector_score: float = 0.8) -> Hit:
    return Hit(
        chunk_id=chunk_id,
        score=vector_score,
        vector_score=vector_score,
        access_level="public",
        source="D1.pdf",
        location="제1조",
        text="연회비 면제 조건",
    )


class FakeRetrieverResources:
    settings = {
        "ANSWER_GATE_THRESHOLD": 0.62,
        "TRANSFORM_GATE_THRESHOLD": 0.70,
        "MAX_REPAIRS": 2,
    }

    def __init__(self, *, score: float = 0.8, transform: bool = False, always_invalid: bool = False) -> None:
        self.calls: list[str] = []
        self.score = score
        self.transform = transform
        self.always_invalid = always_invalid
        self.attempt_budgets: list[tuple[str, int]] = []

    def run_node(self, name: str, state: dict, **kwargs: object) -> dict:
        self.calls.append(name)
        if "max_attempts" in kwargs:
            self.attempt_budgets.append((name, int(kwargs["max_attempts"])))
        if name == "check_query":
            return {"index_info": {"collection": "card_docs", "count": 1, "dimension": 1024, "signature_ok": True}}
        if name == "vector_search":
            return {"vector_hits": [hit(vector_score=self.score)]}
        if name == "route_query":
            if self.transform:
                return {
                    "route_action": "transform",
                    "technique": "rewrite",
                    "transformed_queries": ["연회비 면제"],
                    "llm_calls": 1,
                }
            return {"route_action": "keep", "transformed_queries": [], "llm_calls": 1}
        if name == "bm25_search":
            return {"bm25_scores": {"D1_0000": 1.0}}
        if name == "fuse_scores":
            return {"candidates": [hit(vector_score=self.score)], "baseline_hits": [hit(vector_score=self.score)]}
        if name == "search_transformed":
            return {"transformed_hit_groups": [[hit("D1_0001", self.score)]]}
        if name == "merge_queries":
            return {
                "hits": [hit("D1_0001", self.score)],
                "merge_weights": {"original": 0.5, "transformed_each": 0.5},
                "coverage_applied": False,
            }
        if name == "rerank":
            source = state.get("hits") or state.get("baseline_hits")
            return {"hits": source}
        if name == "build_prompt":
            return {"prompt": "system\nuser\n[D1_0000]"}
        if name == "generate_answer":
            return {
                "raw_answer": {
                    "conclusion": "면제 가능함",
                    "caution": "조건 확인 필요",
                    "evidence": [{"ref": 1, "quote": "연회비 면제 조건"}],
                },
                "llm_calls": 1,
            }
        if name == "verify_evidence":
            valid = not self.always_invalid
            return {
                "answer": {
                    "conclusion": "면제 가능함",
                    "caution": "조건 확인 필요",
                    "evidence": [],
                    "sources": ["D1.pdf"],
                    "verification": {"automatic_valid": valid},
                },
                "repair_hints": [] if valid else ["발췌을 원문과 맞춤"],
            }
        raise AssertionError(name)


class RetrievalRetryableError(RuntimeError):
    pass


class RetryingRetrieverResources(FakeRetrieverResources):
    def __init__(self) -> None:
        super().__init__()
        self.vector_attempts = 0

    def run_node(self, name: str, state: dict, **kwargs: object) -> dict:
        if name == "vector_search":
            self.calls.append(name)
            self.vector_attempts += 1
            if self.vector_attempts < 3:
                raise RetrievalRetryableError("벡터 검색 일시 오류")
            return {"vector_hits": [hit(vector_score=self.score)]}
        return super().run_node(name, state, **kwargs)


def initial_state(**overrides: object) -> dict:
    state = {
        "query": "연회비 면제 조건은?",
        "role": "agent",
        "mode": "hybrid_rerank",
        "top_k": 5,
        "dry_run": False,
        "prompt_only": False,
        "max_llm_calls": 8,
        "thread_id": "ret-test",
        "force_fail_node": None,
        "transform_mode": "off",
        "repair_count": 0,
        "llm_calls": 0,
        "status": "ok",
        "exit_code": 0,
    }
    state.update(overrides)
    return state


class RetrieverGraphTest(unittest.TestCase):
    def test_builder_has_exact_eleven_nodes(self) -> None:
        graph = build_graph(FakeRetrieverResources())
        names = set(graph.get_graph().nodes) - {"__start__", "__end__"}
        self.assertEqual(set(RETRIEVER_NODE_NAMES), names)

    def test_mode_paths_are_deterministic(self) -> None:
        expected = {
            "vector": ["check_query", "vector_search", "build_prompt", "generate_answer", "verify_evidence"],
            "hybrid": [
                "check_query",
                "vector_search",
                "bm25_search",
                "fuse_scores",
                "build_prompt",
                "generate_answer",
                "verify_evidence",
            ],
            "hybrid_rerank": [
                "check_query",
                "vector_search",
                "bm25_search",
                "fuse_scores",
                "rerank",
                "build_prompt",
                "generate_answer",
                "verify_evidence",
            ],
        }
        for mode, calls in expected.items():
            with self.subTest(mode=mode):
                resources = FakeRetrieverResources()
                build_graph(resources).invoke(initial_state(mode=mode), execution_config(f"ret-{mode}"))
                self.assertEqual(calls, resources.calls)

    def test_transform_path_runs_search_and_merge(self) -> None:
        resources = FakeRetrieverResources(score=0.8, transform=True)
        resources.settings = {**resources.settings, "TRANSFORM_GATE_THRESHOLD": 0.9}
        state = initial_state(transform_mode="auto", mode="hybrid")
        result = build_graph(resources).invoke(state, execution_config("ret-transform"))
        self.assertIn("search_transformed", resources.calls)
        self.assertIn("merge_queries", resources.calls)
        self.assertEqual("transform", result["route_action"])
        self.assertEqual(2, result["llm_calls"])

    def test_answer_gate_uses_final_first_hit_vector_score(self) -> None:
        resources = FakeRetrieverResources(score=0.61)
        result = build_graph(resources).invoke(initial_state(mode="vector"), execution_config("ret-gate"))
        self.assertEqual("needs_check", result["status"])
        self.assertNotIn("generate_answer", resources.calls)
        self.assertEqual(0.61, result["gate_score"])

    def test_vector_search_retry_is_bounded_to_two_retries(self) -> None:
        resources = RetryingRetrieverResources()
        result = build_graph(resources).invoke(initial_state(mode="vector"), execution_config("ret-retry"))
        self.assertEqual(3, resources.vector_attempts)
        self.assertEqual("ok", result["status"])

    def test_llm_nodes_receive_remaining_attempt_budget(self) -> None:
        resources = FakeRetrieverResources(score=0.8, transform=True)
        resources.settings = {**resources.settings, "TRANSFORM_GATE_THRESHOLD": 0.9}
        state = initial_state(transform_mode="auto", mode="vector", max_llm_calls=2)
        result = build_graph(resources).invoke(state, execution_config("ret-budget"))
        self.assertEqual([("route_query", 2), ("generate_answer", 1)], resources.attempt_budgets)
        self.assertEqual(2, result["llm_calls"])
        self.assertEqual(0, remaining_llm_attempts(result))

    def test_verify_loop_halts_after_two_repairs(self) -> None:
        resources = FakeRetrieverResources(always_invalid=True)
        result = build_graph(resources).invoke(initial_state(), execution_config("ret-loop"))
        self.assertEqual(3, resources.calls.count("verify_evidence"))
        self.assertEqual(3, result["repair_count"])
        self.assertEqual("halted_by_limit", result["status"])
        self.assertLessEqual(len(resources.calls), 25)

    def test_stream_variant_compiles_without_checkpointer(self) -> None:
        resources = FakeRetrieverResources()
        result = build_graph(resources, None, answer_enabled=False).invoke(initial_state(mode="hybrid"))
        self.assertNotIn("build_prompt", resources.calls)
        self.assertEqual("ok", result["status"])

    def test_sqlite_checkpoint_resumes_at_failed_generate_answer(self) -> None:
        resources = FakeRetrieverResources()
        with tempfile.TemporaryDirectory() as directory:
            resources.log_dir = Path(directory) / "logs"
            saver = open_sqlite_checkpointer(Path(directory) / "retriever.sqlite")
            graph = build_graph(resources, saver)
            config = execution_config("ret-resume")
            with self.assertRaises(ForcedNodeError):
                graph.invoke(initial_state(force_fail_node="generate_answer", thread_id="ret-resume"), config)
            graph.update_state(config, {"force_fail_node": None})
            result = graph.invoke(None, config)
            saver.conn.close()

            rows = [
                json.loads(line)
                for line in (resources.log_dir / "ret-resume.jsonl").read_text(encoding="utf-8").splitlines()
            ]

        self.assertEqual(1, resources.calls.count("check_query"))
        self.assertEqual(1, resources.calls.count("build_prompt"))
        self.assertEqual(1, resources.calls.count("generate_answer"))
        self.assertEqual("ok", result["status"])
        self.assertEqual(1, sum(row["node"] == "generate_answer" and row["event"] == "failed" for row in rows))
        self.assertEqual(1, sum(row["node"] == "check_query" and row["event"] == "completed" for row in rows))
        self.assertTrue(all("query" not in row and "text" not in row for row in rows))

    def test_vector_search_timeout_uses_setting(self) -> None:
        release = threading.Event()

        class Embedder:
            signature = "test"
            dimension = 1

            @staticmethod
            def embed_query(_query: str) -> list[float]:
                release.wait(1)
                return [1.0]

        settings = SimpleNamespace(TIMEOUT_VECTOR_SEARCH=0.01, CANDIDATE_MULTIPLIER=4)
        store = SimpleNamespace(search=lambda *_args: [])
        resources = RetrieverResources(settings, Embedder(), store, None, None, None, None)
        try:
            with self.assertRaises(OperationTimeoutError):
                resources._search_vector("질문", "agent", 20)
        finally:
            release.set()

    def test_rerank_timeout_falls_back_without_model_download(self) -> None:
        release = threading.Event()

        class Reranker:
            @staticmethod
            def score(_query: str, _texts: list[str]) -> list[float]:
                release.wait(1)
                return [1.0]

        settings = SimpleNamespace(TIMEOUT_RERANK=0.01)
        resources = RetrieverResources(settings, None, None, None, Reranker(), None, None)
        baseline = [hit()]
        try:
            result = resources._run_rerank(
                {"query": "질문", "baseline_hits": baseline, "hits": baseline, "top_k": 1}
            )
        finally:
            release.set()
        self.assertEqual(baseline, result["hits"])
        self.assertIn("OperationTimeoutError", result["warnings"][0])

    def test_transformed_search_timeout_is_applied_per_query(self) -> None:
        release = threading.Event()

        class Embedder:
            @staticmethod
            def embed_query(_query: str) -> list[float]:
                release.wait(1)
                return [1.0]

        settings = SimpleNamespace(TIMEOUT_VECTOR_SEARCH=0.01, CANDIDATE_MULTIPLIER=4)
        store = SimpleNamespace(search=lambda *_args: [])
        resources = RetrieverResources(settings, Embedder(), store, None, None, None, None)
        try:
            result = resources._run_search_transformed(
                {
                    "transformed_queries": ["질문 1", "질문 2"],
                    "mode": "vector",
                    "role": "agent",
                    "top_k": 5,
                }
            )
        finally:
            release.set()
        self.assertEqual([[], []], result["transformed_hit_groups"])
        self.assertEqual(2, len(result["warnings"]))
        self.assertTrue(all("OperationTimeoutError" in warning for warning in result["warnings"]))

    def test_result_builder_preserves_route_contract(self) -> None:
        resources = FakeRetrieverResources()
        state = build_graph(resources).invoke(initial_state(), execution_config("ret-result"))
        result = build_search_result(state)
        self.assertEqual("off", result.route.action)
        self.assertEqual(0.8, result.route.gate_score)
        self.assertTrue(result.answer.verification.automatic_valid)

    def test_timing_reducer_accumulates_loop_values(self) -> None:
        self.assertEqual({"build_prompt": 13}, merge_timings({"build_prompt": 5}, {"build_prompt": 8}))


if __name__ == "__main__":
    unittest.main()
