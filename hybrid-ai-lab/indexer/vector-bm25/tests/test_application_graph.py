"""Indexer StateGraph의 분기·체크포인트·재개 시험."""

from __future__ import annotations

import tempfile
import json
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from langchain_core.documents import Document

from app.application.graph import (
    INDEXER_NODE_NAMES,
    ForcedNodeError,
    IndexerResources,
    build_graph,
    execution_config,
    open_sqlite_checkpointer,
)
from app.application.runtime import OperationTimeoutError
from app.application.state import build_index_result, merge_timings


class FakeIndexerResources:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def run_node(self, name: str, state: dict) -> dict:
        self.calls.append(name)
        if name == "select_sources":
            return {"sources": ["D1.pdf"]}
        if name == "extract":
            return {
                "documents": [Document(page_content="약관", metadata={"doc_type": "terms", "doc_key": "D1"})],
                "reports": [{"source": "D1.pdf"}],
                "fingerprints": {"D1.pdf": "abc"},
            }
        if name == "apply_profile":
            return {"documents": state["documents"]}
        if name == "validate_metadata":
            return {"validation": {"checked": 1, "invalid": 0, "errors": []}}
        if name == "chunk":
            return {
                "chunks": [Document(page_content="약관", metadata={"doc_type": "terms", "doc_key": "D1"})],
                "input_units": 1,
            }
        if name == "embed":
            return {"pending_ids": ["D1_0000"], "vectors_path": "vectors.npy", "newly_embedded": 1}
        if name == "upsert":
            return {"ok_ids": ["D1_0000"], "count_before": 0}
        if name == "finalize_index":
            return {"count_after": 1, "accounting_ok": True, "embedding_dimension": 384}
        raise AssertionError(name)


class EmbedRetryableError(RuntimeError):
    pass


class RetryingIndexerResources(FakeIndexerResources):
    def __init__(self) -> None:
        super().__init__()
        self.embed_attempts = 0

    def run_node(self, name: str, state: dict) -> dict:
        if name == "embed":
            self.calls.append(name)
            self.embed_attempts += 1
            if self.embed_attempts < 3:
                raise EmbedRetryableError("임베딩 일시 오류")
            return {"pending_ids": ["D1_0000"], "vectors_path": "vectors.npy", "newly_embedded": 1}
        return super().run_node(name, state)


def initial_state(**overrides: object) -> dict:
    state = {
        "input_path": "/tmp/docs",
        "output_path": "/tmp/out",
        "doc": "all",
        "segment": None,
        "embedding_backend": "smoke",
        "dry_run": False,
        "full_reindex": False,
        "thread_id": "idx-test",
        "profiles": {},
        "schema": {},
        "force_fail_node": None,
        "llm_calls": 0,
        "status": "ok",
        "exit_code": 0,
    }
    state.update(overrides)
    return state


class IndexerGraphTest(unittest.TestCase):
    def test_builder_has_exact_eight_nodes(self) -> None:
        resources = FakeIndexerResources()
        graph = build_graph(resources)
        names = set(graph.get_graph().nodes) - {"__start__", "__end__"}
        self.assertEqual(set(INDEXER_NODE_NAMES), names)

    def test_normal_path_runs_eight_nodes_in_order(self) -> None:
        resources = FakeIndexerResources()
        result = build_graph(resources).invoke(initial_state(), execution_config("idx-normal"))
        self.assertEqual(list(INDEXER_NODE_NAMES), resources.calls)
        self.assertEqual("ok", result["status"])
        self.assertEqual(0, result["exit_code"])
        self.assertEqual(1, result["count_after"])

    def test_dry_run_stops_after_chunk(self) -> None:
        resources = FakeIndexerResources()
        result = build_graph(resources).invoke(initial_state(dry_run=True), execution_config("idx-dry"))
        self.assertEqual(list(INDEXER_NODE_NAMES[:5]), resources.calls)
        self.assertEqual("dry_run", result["status"])

    def test_embed_retry_is_bounded_to_two_retries(self) -> None:
        resources = RetryingIndexerResources()
        result = build_graph(resources).invoke(initial_state(), execution_config("idx-retry"))
        self.assertEqual(3, resources.embed_attempts)
        self.assertEqual("ok", result["status"])

    def test_sqlite_checkpoint_resumes_at_failed_embed(self) -> None:
        resources = FakeIndexerResources()
        with tempfile.TemporaryDirectory() as directory:
            resources.log_dir = Path(directory) / "logs"
            saver = open_sqlite_checkpointer(Path(directory) / "indexer.sqlite")
            graph = build_graph(resources, saver)
            config = execution_config("idx-resume")
            with self.assertRaises(ForcedNodeError):
                graph.invoke(initial_state(force_fail_node="embed", thread_id="idx-resume"), config)
            graph.update_state(config, {"force_fail_node": None})
            result = graph.invoke(None, config)
            saver.conn.close()

            rows = [
                json.loads(line)
                for line in (resources.log_dir / "idx-resume.jsonl").read_text(encoding="utf-8").splitlines()
            ]

        self.assertEqual(1, resources.calls.count("select_sources"))
        self.assertEqual(1, resources.calls.count("chunk"))
        self.assertEqual(1, resources.calls.count("embed"))
        self.assertEqual(1, len(result["chunks"]))
        self.assertEqual(1, result["count_after"])
        completed = [row["node"] for row in rows if row["event"] == "completed"]
        self.assertEqual(list(INDEXER_NODE_NAMES), completed)
        self.assertEqual(1, sum(row["node"] == "embed" and row["event"] == "failed" for row in rows))
        allowed_log_fields = {
            "timestamp", "thread_id", "node", "event", "elapsed_ms", "error_type",
        }
        self.assertTrue(all(set(row) <= allowed_log_fields for row in rows))

    def test_pdf_timeout_is_applied_per_file(self) -> None:
        release = threading.Event()

        class Reader:
            @staticmethod
            def read(*_args: object, **_kwargs: object) -> tuple[list, dict]:
                release.wait(1)
                return [], {}

        file_store = SimpleNamespace(sha256=lambda _path: "hash")
        settings = SimpleNamespace(TIMEOUT_PDF_PER_FILE=0.01)
        resources = IndexerResources(settings, Reader(), file_store, None, None)
        try:
            with self.assertRaises(OperationTimeoutError):
                resources._run_extract({"sources": ["D1_slow.pdf"]})
        finally:
            release.set()

    def test_chunk_timeout_is_applied_per_input_unit(self) -> None:
        release = threading.Event()
        settings = SimpleNamespace(
            TIMEOUT_CHUNK_PER_DOC=0.01,
            CHUNK_MAX_CHARS=600,
            CHUNK_OVERLAP=80,
            CHUNK_D2_OVERLAP=0,
            CHUNK_TURNS_PER_CHUNK=4,
            CHUNK_OVERLAP_TURNS=1,
            MAX_INPUT_TOKENS=8192,
        )
        resources = IndexerResources(settings, None, None, None, None)

        def slow_chunk(*_args: object, **_kwargs: object) -> tuple[list, list]:
            release.wait(1)
            return [], []

        unit = {"text": "제1조", "meta": {"doc_key": "D1"}, "key": "D1"}
        try:
            with patch("app.domain.chunking.prepare_units", return_value=([unit], [])):
                with patch("app.domain.chunking.chunk_units", side_effect=slow_chunk):
                    with self.assertRaises(OperationTimeoutError):
                        resources._run_chunk({"documents": [], "doc": "all", "output_path": "/tmp"})
        finally:
            release.set()

    def test_chunk_assigns_global_ids_after_processing_each_input_unit(self) -> None:
        settings = SimpleNamespace(
            TIMEOUT_CHUNK_PER_DOC=30,
            CHUNK_MAX_CHARS=600,
            CHUNK_OVERLAP=80,
            CHUNK_D2_OVERLAP=0,
            CHUNK_TURNS_PER_CHUNK=4,
            CHUNK_OVERLAP_TURNS=1,
            MAX_INPUT_TOKENS=8192,
        )
        file_store = SimpleNamespace(
            save_jsonl=lambda *_args: None,
            save_json=lambda *_args: None,
        )
        resources = IndexerResources(settings, None, file_store, None, None)
        units = [
            {"text": "제1조(첫째)\n본문", "meta": {"doc_key": "D1"}, "key": "D1"},
            {"text": "제2조(둘째)\n본문", "meta": {"doc_key": "D1"}, "key": "D1"},
        ]

        with patch("app.domain.chunking.prepare_units", return_value=(units, [])):
            result = resources._run_chunk(
                {"documents": [], "doc": "all", "output_path": "/tmp"}
            )

        self.assertEqual(
            [item.id for item in result["chunks"]],
            ["D1_0000", "D1_0001"],
        )

    def test_embed_timeout_is_applied_per_batch(self) -> None:
        release = threading.Event()

        class Embedder:
            signature = "test-signature"
            dimension = 1

            @staticmethod
            def embed(_texts: list[str], *, kind: str) -> list[list[float]]:
                del kind
                release.wait(1)
                return [[1.0]]

        settings = SimpleNamespace(
            EMBED_BATCH_SIZE=1,
            TIMEOUT_EMBED_BATCH=0.01,
            CHUNK_MAX_CHARS=600,
            CHUNK_OVERLAP=80,
            CHUNK_D2_OVERLAP=0,
            CHUNK_TURNS_PER_CHUNK=4,
            CHUNK_OVERLAP_TURNS=1,
        )
        with tempfile.TemporaryDirectory() as directory:
            resources = IndexerResources(settings, None, None, Embedder(), None)
            chunk = Document(id="D1_0000", page_content="약관", metadata={"doc_key": "D1"})
            try:
                result = resources._run_embed(
                    {
                        "thread_id": "idx-embed-timeout",
                        "output_path": directory,
                        "chunks": [chunk],
                        "full_reindex": False,
                    }
                )
            finally:
                release.set()
        self.assertEqual([], result["pending_ids"])
        self.assertEqual("OperationTimeoutError", result["failed"][0]["reason"])

    def test_finalize_index_detects_count_mismatch_when_no_ids_were_written(self) -> None:
        settings = SimpleNamespace(CHROMA_COLLECTION="test", EMBED_MODEL="test-model")
        file_store = SimpleNamespace(save_json=lambda *_args: None)
        embedder = SimpleNamespace(signature="test-signature", dimension=384)
        vector_store = SimpleNamespace(
            count=lambda: 9,
            describe=lambda: {"count": 9, "dimension": 384, "signature": "test-signature"},
        )
        resources = IndexerResources(settings, None, file_store, embedder, vector_store)

        result = resources._run_finalize_index(
            {
                "thread_id": "idx-count-mismatch",
                "output_path": "/tmp",
                "embedding_backend": "smoke",
                "count_before": 10,
                "ok_ids": [],
                "fingerprints": {},
            }
        )

        self.assertFalse(result["accounting_ok"])

    def test_result_builder_uses_shared_state_fields(self) -> None:
        resources = FakeIndexerResources()
        state = build_graph(resources).invoke(initial_state(), execution_config("idx-result"))
        result = build_index_result(state)
        self.assertEqual(1, result.sources)
        self.assertEqual(1, result.extract.document_count)
        self.assertEqual(1, result.chunk.chunk_count)
        self.assertEqual(384, result.index.embedding_dimension)

    def test_result_builder_reports_every_node_timing(self) -> None:
        timings = {
            "select_sources": 1,
            "extract": 2,
            "apply_profile": 3,
            "validate_metadata": 4,
            "chunk": 5,
            "embed": 6,
            "upsert": 7,
            "finalize_index": 8,
            "total_ms": 40,
        }

        result = build_index_result(initial_state(timings=timings))

        self.assertEqual(
            {
                "select_sources_ms": 1,
                "extract_ms": 2,
                "apply_profile_ms": 3,
                "validate_metadata_ms": 4,
                "chunk_ms": 5,
                "embed_ms": 6,
                "upsert_ms": 7,
                "finalize_index_ms": 8,
                "total_ms": 40,
            },
            result.timings.model_dump(),
        )

    def test_timing_reducer_accumulates_loop_values(self) -> None:
        self.assertEqual({"verify_evidence": 12}, merge_timings({"verify_evidence": 5}, {"verify_evidence": 7}))


if __name__ == "__main__":
    unittest.main()
