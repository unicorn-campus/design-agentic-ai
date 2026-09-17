"""외부 모델 없이 실행하는 Indexer 지식 경로 시험."""

from __future__ import annotations

from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace

from langchain_core.documents import Document

from app.domain.chunking import Chunk, ChunkIntegrityError, assign_storage_ids, chunk_by_clause, chunk_by_turn, chunk_units
from app.domain.validation import MetadataError, ProfileOverrideError, apply_profile, sanitize_metadata
from app.application.graph import IndexerResources
from app.infrastructure.embedder import SmokeEmbedder, plan_incremental
from app.infrastructure.chroma_store import ChromaVectorStore, MemoryVectorStore


def document(chunk_id: str, text: str, access: str = "public") -> Document:
    return Document(
        id=chunk_id,
        page_content=text,
        metadata={"chunk_id": chunk_id, "source": "D1_test.pdf", "doc_type": "regulation", "access_level": access},
    )


class ChunkingTests(unittest.TestCase):
    def test_d1_id_and_integrity(self):
        chunks = chunk_by_clause("제10조 (안내)\n(1) 첫 조건\n(2) 둘째 조건", {"doc_key": "D1"}, max_chars=40, overlap=5)
        docs = assign_storage_ids(chunks)
        self.assertTrue(docs[0].id.startswith("D1_"))
        self.assertEqual(docs[0].id, docs[0].metadata["chunk_id"])

    def test_d3_id_preserves_record_id(self):
        metadata = {"doc_key": "D3", "record_id": "C-20260302-002"}
        chunks = chunk_by_turn("고객: 문의\n상담사: 답변", metadata)
        self.assertEqual(chunks[0].chunk_id, "D3_C-20260302-002_0000")

    def test_duplicate_id_raises(self):
        chunk = Chunk("본문", "D1_0000", {"char_len": 2})
        with self.assertRaises(ChunkIntegrityError):
            assign_storage_ids([chunk, chunk])

    def test_multiple_units_return_chunks_before_global_id_assignment(self):
        units = [
            {"text": "제1조 (첫째)\n본문", "meta": {"doc_key": "D1"}, "key": "D1"},
            {"text": "제2조 (둘째)\n본문", "meta": {"doc_key": "D1"}, "key": "D1"},
        ]
        chunks, reviews = chunk_units(units)
        self.assertTrue(all(isinstance(item, Chunk) for item in chunks))
        self.assertEqual([item.chunk_id for item in chunks], ["D1_0000", "D1_0000"])
        self.assertEqual(reviews, [])


class MetadataTests(unittest.TestCase):
    def test_profile_forbidden_key_raises(self):
        with self.assertRaises(ProfileOverrideError):
            apply_profile(Document(page_content="본문", metadata={}), {"source": "변경"})

    def test_invalid_access_level_raises(self):
        with self.assertRaises(MetadataError):
            sanitize_metadata({"doc_type": "regulation", "access_level": "secret"})


class SmokeEmbeddingBackendTests(unittest.TestCase):
    def test_smoke_embedding_is_deterministic_and_normalized(self):
        embedder = SmokeEmbedder()
        first, second = embedder.embed(["같은 문장", "같은 문장"])
        self.assertEqual(first, second)
        self.assertEqual(len(first), 384)
        self.assertAlmostEqual(sum(value * value for value in first), 1.0)

    def test_upsert_is_incremental_by_id_and_cosine(self):
        embedder = SmokeEmbedder()
        store = MemoryVectorStore(embedder.signature)
        rows = [document("D1_0000", "포인트 적립"), document("D1_0001", "연회비")]
        vectors = embedder.embed([row.page_content for row in rows])
        store.upsert([row.id for row in rows], [row.page_content for row in rows], vectors, [row.metadata for row in rows])
        store.upsert([rows[0].id], [rows[0].page_content], [vectors[0]], [rows[0].metadata])
        self.assertEqual(store.count(), 2)
        self.assertEqual(store.search(vectors[0], 1, {})[0]["chunk_id"], "D1_0000")

    def test_embed_skips_unchanged_hash(self):
        row = document("D1_0000", "포인트 적립")
        first = plan_incremental(
            [row], None, embedding_signature="smoke", chunk_params={"max_chars": 600}
        )
        manifest = {
            "embedding_signature": "smoke",
            "chunk_params": {"max_chars": 600},
            "chunks": first["hashes"],
        }
        second = plan_incremental(
            [row], manifest, embedding_signature="smoke", chunk_params={"max_chars": 600}
        )
        self.assertEqual(second["pending_ids"], [])
        self.assertEqual(second["skipped_ids"], ["D1_0000"])

    @staticmethod
    def _settings():
        return SimpleNamespace(
            CHUNK_MAX_CHARS=600,
            CHUNK_OVERLAP=80,
            CHUNK_D2_OVERLAP=0,
            CHUNK_TURNS_PER_CHUNK=4,
            CHUNK_OVERLAP_TURNS=1,
            EMBED_BATCH_SIZE=32,
            MAX_INPUT_TOKENS=8192,
        )

    def test_full_reindex_resets_once_before_embedding_and_removes_extra_id(self):
        class CountingStore(MemoryVectorStore):
            def __init__(self, signature):
                super().__init__(signature)
                self.reset_calls = 0

            def reset(self):
                self.reset_calls += 1
                super().reset()

        embedder = SmokeEmbedder()
        store = CountingStore(embedder.signature)
        extra = document("EXTRA", "삭제되어야 하는 과거 청크")
        store.upsert(
            [extra.id],
            [extra.page_content],
            embedder.embed([extra.page_content]),
            [extra.metadata],
        )
        rows = [document("D1_0000", "현재 청크 1"), document("D1_0001", "현재 청크 2")]

        class ResetAwareEmbedder(SmokeEmbedder):
            def embed(self, texts, *, kind="passage"):
                self.assert_reset_before_embed()
                return super().embed(texts, kind=kind)

            @staticmethod
            def assert_reset_before_embed():
                if store.count() != 0:
                    raise AssertionError("reset이 임베딩보다 먼저 실행되지 않음")

        actual_embedder = ResetAwareEmbedder()
        resources = IndexerResources(
            settings=self._settings(),
            pdf_reader=None,
            file_store=None,
            embedder=actual_embedder,
            vector_store=store,
        )
        with tempfile.TemporaryDirectory() as directory:
            state = {
                "chunks": rows,
                "output_path": directory,
                "thread_id": "full-reset",
                "full_reindex": True,
            }
            embedded = resources._run_embed(state)
            self.assertEqual(store.reset_calls, 1)
            self.assertEqual(store.count(), 0)
            upserted = resources._run_upsert({**state, **embedded})
            self.assertEqual(set(upserted["ok_ids"]), {"D1_0000", "D1_0001"})
            self.assertEqual(set(store.get_all()["ids"]), {"D1_0000", "D1_0001"})

            # LangGraph의 embed 재시도에서도 성공한 reset을 중복 호출하지 않음.
            resources._run_embed(state)
            self.assertEqual(store.reset_calls, 1)

    def test_incremental_run_never_resets_and_keeps_existing_extra_id(self):
        class CountingStore(MemoryVectorStore):
            def __init__(self, signature):
                super().__init__(signature)
                self.reset_calls = 0

            def reset(self):
                self.reset_calls += 1
                super().reset()

        embedder = SmokeEmbedder()
        store = CountingStore(embedder.signature)
        extra = document("EXTRA", "기존 청크")
        store.upsert(
            [extra.id],
            [extra.page_content],
            embedder.embed([extra.page_content]),
            [extra.metadata],
        )
        resources = IndexerResources(
            settings=self._settings(),
            pdf_reader=None,
            file_store=None,
            embedder=embedder,
            vector_store=store,
        )
        with tempfile.TemporaryDirectory() as directory:
            state = {
                "chunks": [document("D1_0000", "현재 청크")],
                "output_path": directory,
                "thread_id": "incremental-no-reset",
                "full_reindex": False,
            }
            embedded = resources._run_embed(state)
            resources._run_upsert({**state, **embedded})
        self.assertEqual(store.reset_calls, 0)
        self.assertEqual(set(store.get_all()["ids"]), {"EXTRA", "D1_0000"})

    def test_chroma_reset_recreates_cosine_signature_and_removes_extra_id(self):
        embedder = SmokeEmbedder()
        rows = [document("D1_0000", "현재 청크 1"), document("D1_0001", "현재 청크 2")]
        extra = document("EXTRA", "삭제되어야 하는 과거 청크")
        with tempfile.TemporaryDirectory() as directory:
            store = ChromaVectorStore(
                Path(directory),
                "reset_contract",
                embedder.signature,
            )
            store.upsert(
                [extra.id],
                [extra.page_content],
                embedder.embed([extra.page_content]),
                [extra.metadata],
            )
            store.reset()
            self.assertEqual(store.count(), 0)
            self.assertTrue(store.check_signature(embedder.signature))
            store.upsert(
                [row.id for row in rows],
                [row.page_content for row in rows],
                embedder.embed([row.page_content for row in rows]),
                [row.metadata for row in rows],
            )
            self.assertEqual(set(store.get_all()["ids"]), {"D1_0000", "D1_0001"})


if __name__ == "__main__":
    unittest.main()
