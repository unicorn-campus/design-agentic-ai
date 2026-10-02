"""색인 실행 서비스가 포트만으로 동작하는지 가짜 구현으로 시험."""

from __future__ import annotations

from pathlib import Path
import unittest

from app.application.indexing_service import IndexingService
from app.application.ports import IndexConfigPort, IndexingPipelineFactoryPort, IndexingPipelinePort
from app.application.state import IndexRequest


class FakePipeline(IndexingPipelinePort):
    def __init__(self, calls: list[str]) -> None:
        self.calls = calls
        self.received: tuple[dict, str] | None = None

    def run(self, initial_state, thread_id):
        self.calls.append("run")
        self.received = (dict(initial_state), thread_id)
        return {**initial_state, "sources": ["D1.pdf"], "timings": {"select_sources": 3}}


class FakePipelineFactory(IndexingPipelineFactoryPort):
    def __init__(self, calls: list[str]) -> None:
        self.calls = calls
        self.pipeline = FakePipeline(calls)
        self.requests: list[IndexRequest] = []

    def create(self, request):
        self.calls.append("create")
        self.requests.append(request)
        return self.pipeline


class FakeConfig(IndexConfigPort):
    def __init__(self, calls: list[str]) -> None:
        self.calls = calls

    def load_profiles(self):
        self.calls.append("profiles")
        return {"D1.pdf": {"owner_dept": "product_planning"}}

    def load_schema(self):
        self.calls.append("schema")
        return {"enums": {}}


class IndexingServiceTest(unittest.TestCase):
    def test_service_prepares_resources_then_reads_config_and_runs_pipeline(self) -> None:
        calls: list[str] = []
        factory = FakePipelineFactory(calls)
        service = IndexingService(factory, FakeConfig(calls))
        request = IndexRequest(
            input_path=Path("docs"),
            output_path=Path("out"),
            thread_id="idx-service",
            embedding_backend="smoke",
            dry_run=True,
        )

        result = service.run(request)

        # 기존 run_indexing과 같은 순서: 자원 준비 → 프로필 → 규칙 → 그래프 실행
        self.assertEqual(["create", "profiles", "schema", "run"], calls)
        self.assertEqual([request], factory.requests)
        initial, thread_id = factory.pipeline.received
        self.assertEqual("idx-service", thread_id)
        self.assertEqual({"D1.pdf": {"owner_dept": "product_planning"}}, initial["profiles"])
        self.assertEqual({"enums": {}}, initial["schema"])
        self.assertTrue(initial["dry_run"])
        self.assertEqual("smoke", initial["embedding_backend"])
        self.assertEqual(1, result.sources)
        self.assertEqual(3, result.timings.select_sources_ms)
        self.assertGreaterEqual(result.timings.total_ms, 0)
        self.assertEqual("idx-service", result.thread_id)


if __name__ == "__main__":
    unittest.main()
