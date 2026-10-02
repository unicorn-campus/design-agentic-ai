"""새 application·repository 객체로 배치 실행을 재개하는 조건을 검증함."""

from __future__ import annotations

from tempfile import TemporaryDirectory

import pytest

from app.application.models import IndexingError, ThreadReuseError
from app.domain.models import SourceRef

from test_service import Backend, Repository, components


class FailAfterWriteRepository(Repository):
    """첫 저장의 부수효과가 끝난 직후 장애를 발생시키는 시험용 저장소임."""

    def __init__(self, backend: Backend) -> None:
        """공유 저장 상태를 받고 첫 저장 실패 여부를 초기화함."""
        super().__init__(backend)
        self.failed = False

    def upsert(self, generation, chunks, vectors):
        """청크와 벡터를 저장한 뒤 최초 호출에서만 프로세스 중단을 재현함."""
        super().upsert(generation, chunks, vectors)
        if not self.failed:
            self.failed = True
            raise RuntimeError("process stopped after write")


def test_new_resources_resume_same_generation_after_upsert_side_effect() -> None:
    """저장 직후 중단되어도 같은 세대를 이어서 게시하며 중복 작업을 피함을 보증함."""
    with TemporaryDirectory() as directory:
        backend = Backend()
        first = components(directory, backend, thread_id="resume")
        failing = FailAfterWriteRepository(backend)
        first[0].runner.workflow.repository = failing

        with pytest.raises(RuntimeError, match="process stopped after write"):
            first[0].run(first[1])
        assert backend.active_generation is None
        target_generation = first[0].build_initial_state(first[1])["target_generation"]
        assert len(backend.staging_chunks[target_generation]) == 1

        resumed = components(directory, backend, thread_id="resume")
        result = resumed[0].run(resumed[1])

        assert result.status == "ok"
        assert result.index.collection_count == 1
        assert backend.active_generation == target_generation
        assert resumed[3].calls == 0
        assert resumed[6].calls == []


def test_publish_resume_does_not_rebuild_completed_text_index() -> None:
    """게시 전 실패 후 재개할 때 체크포인트가 끝난 BM25 준비를 반복하지 않음을 보증함."""
    with TemporaryDirectory() as directory:
        backend = Backend()
        first = components(directory, backend, thread_id="publish-resume")
        first[7].fail_publish = True

        with pytest.raises(RuntimeError, match="publish failed"):
            first[0].run(first[1])
        assert first[7].build_text_index_calls == 1
        assert backend.active_generation is None

        resumed = components(directory, backend, thread_id="publish-resume")
        result = resumed[0].run(resumed[1])

        assert result.status == "ok"
        assert resumed[7].build_text_index_calls == 0
        assert resumed[7].publish_calls == 1


def test_same_thread_rejects_different_request() -> None:
    """같은 체크포인트 thread_id를 다른 요청에 재사용하면 거부됨을 보증함."""
    with TemporaryDirectory() as directory:
        backend = Backend()
        first = components(directory, backend, thread_id="same")
        first[0].run(first[1])

        second = components(directory, backend, thread_id="same")
        changed = second[1].model_copy(update={"doc": "D2"})
        with pytest.raises(ThreadReuseError, match="새 thread_id"):
            second[0].run(changed)


class FailSecondEmbedder:
    """두 번째 임베딩 배치에서 장애를 재현하는 시험용 임베더임."""

    signature = "embed-v1"
    dimension = 2

    def __init__(self) -> None:
        """호출별 입력을 기록할 빈 목록을 준비함."""
        self.calls: list[list[str]] = []

    def embed(self, texts):
        """호출 입력을 기록하고 두 번째 호출에서만 장애를 발생시킴."""
        self.calls.append(list(texts))
        if len(self.calls) == 2:
            raise RuntimeError("second embed failed")
        return [[float(len(text)), 1.0] for text in texts]


def test_new_embedder_resumes_without_repeating_completed_batch() -> None:
    """임베딩 재개 시 완료된 첫 배치는 반복하지 않고 실패한 배치부터 처리함을 보증함."""
    with TemporaryDirectory() as directory:
        backend = Backend()
        first = components(directory, backend, thread_id="embed-resume")
        first[2].refs = [
            SourceRef("D1-a.pdf", "D1-a.pdf", "D1", "a"),
            SourceRef("D1-b.pdf", "D1-b.pdf", "D1", "b"),
        ]
        failing = FailSecondEmbedder()
        first[0].runner.workflow.embedder = failing

        with pytest.raises(RuntimeError, match="second embed failed"):
            first[0].run(first[1])
        assert len(failing.calls) == 2

        resumed = components(directory, backend, thread_id="embed-resume")
        resumed[2].refs = list(first[2].refs)
        result = resumed[0].run(resumed[1])

        assert result.status == "ok"
        assert len(resumed[6].calls) == 1
        assert resumed[6].calls[0] == ["text:b"]


class ChangingSources:
    """탐색 시점마다 같은 파일의 지문을 바꾸는 원천 목록 가짜 구현임."""

    def __init__(self) -> None:
        """원천 탐색 횟수를 0으로 초기화함."""
        self.calls = 0

    def discover(self, input_path, doc, segment):
        """첫 탐색과 다음 탐색에 서로 다른 원천 지문을 반환함."""
        del input_path, doc, segment
        self.calls += 1
        digest = "before" if self.calls == 1 else "after"
        return [SourceRef("D1.pdf", "D1.pdf", "D1", digest)]


def test_source_change_between_discovery_and_loading_requires_new_thread() -> None:
    """탐색 후 원천이 바뀌면 기존 체크포인트를 이어 쓰지 않고 새 실행을 요구함을 보증함."""
    with TemporaryDirectory() as directory:
        backend = Backend()
        value = components(directory, backend, thread_id="source-race")
        value[0].runner.workflow.sources = ChangingSources()

        with pytest.raises(IndexingError, match="새 실행"):
            value[0].run(value[1])

