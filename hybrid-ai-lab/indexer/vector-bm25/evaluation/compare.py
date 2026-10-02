"""기존 Retriever의 검색 유스케이스로 두 저장 인덱스를 비교함.

Retriever 가상환경에서 실행하며 질문 변환·답변 생성은 호출하지 않음.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import time
from typing import Any

from metrics import aggregate, score

HERE = Path(__file__).resolve().parent
LAB = HERE.parents[2]
RETRIEVER = LAB / "retriever" / "vector-retriever"
sys.path.insert(0, str(RETRIEVER))

from app.application.ports import EmbedderPort
from app.application.state import RetrieverRequest
from app.bootstrap import create_service
from app.domain.search_filter import MetadataFilter
from app.domain.vector_search import DEFAULT_VECTOR_SEARCH_OPTIONS
from app.infrastructure.bm25_index import BM25Index
from app.infrastructure.chroma_store import ChromaVectorStore
from app.infrastructure.corpus_store import VersionedCorpusStore
from app.infrastructure.korean_tokenizer import KoreanTokenizer
from app.infrastructure.settings import load_settings

MODEL = "nlpai-lab/KURE-v2"
REVISION = "3431f86d399d666083890dbb882aced6708873bc"
SIGNATURE = f"sentence-transformers:{MODEL}:prompt-policy-v2"


def read_json(path: Path) -> Any:
    """UTF-8 BOM 유무와 관계없이 JSON 파일을 읽어 반환함."""
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, value: Any) -> None:
    """결과 경로의 상위 디렉터리를 만든 뒤 사람이 읽기 쉬운 JSON을 저장함."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def hashes(root: Path) -> dict[str, str]:
    """디렉터리 안 모든 파일의 상대 경로별 SHA-256 지문을 반환함."""
    return {str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(root.rglob("*")) if path.is_file()}


def snapshot_baseline(backup: Path) -> tuple[Path, dict[str, str]]:
    """기존 인덱스를 지문별 평가 경로로 복사하고 원본 지문을 반환함.

    목적: Chroma가 읽기 중 파일을 바꿀 가능성에서 원본 기준 인덱스를 보호함.
    인자: backup은 기존 인덱서 루트이며 data 아래에 Chroma와 BM25가 있어야 함.
    반환값: 평가용 복사본 경로와 원본 파일별 SHA-256 지문의 tuple임.
    예외: 기존 복사본의 기록 지문이 현재 원본과 다르면 RuntimeError를 발생시킴.
    부수효과: 최초 지문인 경우 evaluation/baseline 아래에 평가용 복사본을 생성함.
    """
    original = backup / "data"
    before = {f"{folder}/{name}": value for folder in ("chroma", "search_indexes")
              for name, value in hashes(original / folder).items()}
    fingerprint = hashlib.sha256(json.dumps(before, sort_keys=True).encode()).hexdigest()[:16]
    target = HERE / "baseline" / fingerprint
    if not target.exists():
        for folder in ("chroma", "search_indexes"):
            shutil.copytree(original / folder, target / folder)
        write_json(target / "original_hashes.json", before)
    elif read_json(target / "original_hashes.json") != before:
        raise RuntimeError("기준 인덱스 복사본의 지문이 일치하지 않습니다.")
    return target, before


class QueryEmbedder(EmbedderPort):
    """두 인덱스에 같은 질문 벡터를 공급하는 평가 전용 임베더임.

    고정 모델 revision을 오프라인으로 읽어 모든 질문을 한 번만 임베딩함.
    문서 임베딩이나 답변 생성은 수행하지 않음.
    """

    signature = SIGNATURE
    dimension = 768

    def __init__(self, questions: list[dict[str, Any]]):
        """평가 질문의 공통 벡터와 모델 처리 시간을 미리 계산함.

        인자: questions의 각 항목은 question 문자열을 포함해야 하며 255토큰 이하여야 함.
        예외: 질문이 기존 입력 상한을 넘으면 ValueError를 발생시킴.
        부수효과: 로컬 모델을 메모리에 적재하고 질문별 임베딩을 수행함.
        """
        # 같은 질문 벡터를 양쪽 인덱스에 사용해야 문서 인덱싱 차이만 비교 가능함.
        from sentence_transformers import SentenceTransformer
        self.model = SentenceTransformer(MODEL, revision=REVISION, device="cpu", local_files_only=True)
        self.model.max_seq_length = 255
        self.cache: dict[str, list[float]] = {}
        self.timings: dict[str, float] = {}
        for question in questions:
            text = question["question"]
            count = len(self.model.tokenizer.encode(text, add_special_tokens=True, truncation=False))
            if count > 255:
                raise ValueError("기존 입력 상한을 넘는 평가 질문은 별도 비교 설계가 필요합니다.")
            started = time.perf_counter()
            self.cache[text] = self.model.encode([text], normalize_embeddings=True, show_progress_bar=False)[0].tolist()
            self.timings[text] = (time.perf_counter() - started) * 1000

    def embed_query(self, text: str) -> list[float]:
        """미리 계산한 질문 벡터를 반환함.

        인자: text는 생성 시 전달한 평가 질문과 같아야 함.
        반환값: 정규화된 768차원 질문 벡터임.
        예외: 미등록 질문이면 KeyError를 발생시킴.
        부수효과: 없음.
        """
        return self.cache[text]


def in_scope(record: dict[str, Any], scopes: list[dict[str, Any]]) -> bool:
    """평가 청크가 질문에 합의한 고객·카드 범위 중 하나에 속하는지 판정함.

    인자: scopes의 각 항목은 AND 조건이며 여러 항목은 OR 조건으로 적용됨.
    반환값: 범위가 없거나 하나 이상의 범위를 만족하면 True임.
    부수효과: 없음.
    """
    if not scopes:
        return True
    metadata = record.get("metadata", {})
    for scope in scopes:
        matches = True
        for key, expected in scope.items():
            if key == "card_id":
                actual = str(metadata.get("card_id", "")) + " " + str(metadata.get("card_id_all", ""))
                # 기존 코퍼스에는 안정 카드 코드 필드가 없어 benefit_id와 본문까지 함께 확인함.
                actual += " " + str(metadata.get("benefit_id", "")) + " " + record.get("text", "")
                matches = matches and str(expected) in actual
            else:
                matches = matches and str(metadata.get(key, "")) == str(expected)
        if matches:
            return True
    return False


class ScopedBM25(BM25Index):
    """검색 점수 계산 전에 질문별 허용 청크 범위를 적용하는 평가용 BM25임.

    기존 BM25 점수와 오탈자 처리 방식은 바꾸지 않으며 평가 범위만 마스크에 추가함.
    """

    allowed_ids: set[str] | None = None

    def _retrieve(self, retriever, records, terms, mask, k):
        """접근 등급 마스크에 질문별 허용 ID 마스크를 결합해 검색함."""
        import numpy as np
        if self.allowed_ids is not None:
            mask = mask * np.asarray([str(row["chunk_id"]) in self.allowed_ids for row in records], dtype=np.float32)
        return BM25Index._retrieve(retriever, records, terms, mask, min(k, int(np.count_nonzero(mask))))


class ScopedVector(ChromaVectorStore):
    """벡터 순위 계산 전에 질문별 허용 청크 ID를 메타데이터로 제한함."""

    allowed_ids: set[str] | None = None

    def search(self, query_embedding, k, metadata_filter, options=DEFAULT_VECTOR_SEARCH_OPTIONS):
        """기존 필터에 허용 청크 ID를 더한 뒤 벡터 검색을 수행함.

        반환값: 질문 범위 안에서 점수가 높은 검색 결과임. 허용 ID가 비어 있으면 빈 목록임.
        부수효과: Chroma 조회를 수행하며 클라이언트 초기화 시 로컬 관리 파일이 갱신될 수 있음.
        """
        if self.allowed_ids is not None:
            if not self.allowed_ids:
                return []
            # 두 인덱스 모두 chunk_id를 메타데이터에 저장하므로 순위 계산 전에 같은 범위를 적용 가능함.
            metadata_filter = MetadataFilter(
                metadata_filter.allowed_values + (("chunk_id", tuple(sorted(self.allowed_ids))),),
                metadata_filter.equalities,
            )
        return super().search(query_embedding, k, metadata_filter, options)


def evaluate(label: str, chroma: Path, search_root: Path, questions, embedder,
             run_tag: str) -> tuple[list[dict], dict]:
    """한 인덱스에서 Vector·Hybrid Top-5 검색을 실행하고 문항별 근거 지표를 계산함.

    목적: 답변 생성 영향을 제외하고 인덱싱 변경에 따른 검색 순위만 비교함.
    인자: label은 결과 구분명이며 chroma와 search_root는 같은 세대의 저장 경로여야 함.
    반환값: 문항별 검색 결과·지표 목록과 벡터 인덱스 설명 정보의 tuple임.
    예외: 검색이 LLM을 호출하거나 답변을 만들면 AssertionError를 발생시킴.
    부수효과: 평가용 변환 캐시를 만들 수 있으며 진행 상황을 표준 출력함.
    """
    bm25 = ScopedBM25(VersionedCorpusStore(search_root), KoreanTokenizer(num_workers=1))
    bm25.warm()
    vector = ScopedVector(chroma, "card_docs", SIGNATURE)
    records = [{"chunk_id": hit.chunk_id, "text": hit.text, "metadata": hit.metadata}
               for hit in bm25.chunks().values()]
    settings = load_settings({"CHROMA_PATH": chroma, "SEARCH_INDEX_ROOT": search_root,
                              "VECTOR_SEARCH_STRATEGY": "similarity", "CANDIDATE_MULTIPLIER": 4,
                              "HYBRID_WEIGHT_BM25": 0.4, "HYBRID_WEIGHT_VECTOR": 0.6,
                              "TRANSFORM_MODE": "off", "KOREAN_TOKENIZER_WORKERS": 1,
                              "TRANSFORM_CACHE_PATH": HERE / "cache" / f"{label}.sqlite"})
    service = create_service(settings=settings, embedder=embedder, vector_store=vector, bm25=bm25)
    rows = []
    for mode in ("vector", "hybrid"):
        for question in questions:
            eligible = {record["chunk_id"] for record in records if in_scope(record, question.get("filters", []))}
            bm25.allowed_ids = vector.allowed_ids = eligible
            # 검색기는 같은 thread_id의 체크포인트가 있으면 저장된 결과를 그대로 돌려줌.
            # 실행마다 다른 run_tag를 넣어 이전 평가의 결과가 재사용되지 않게 함.
            request = RetrieverRequest(query=question["question"], mode=mode, transform="off", top_k=5,
                                       role="auditor",
                                       thread_id=f"eval-{run_tag}-{label}-{mode}-{question['id']}")
            started = time.perf_counter()
            result = service.search(request)
            elapsed = (time.perf_counter() - started) * 1000
            if result.llm_calls or result.answer is not None:
                raise AssertionError("검색 전용 평가에서 답변 생성이 호출되었습니다.")
            hits = [hit.model_dump() for hit in result.hits]
            row = {"index": label, "mode": mode, "id": question["id"], "question": question["question"],
                   "eligible_count": len(eligible), "search_ms": elapsed,
                   "query_embedding_ms": embedder.timings[question["question"]],
                   "status": result.status, "metrics": score(question, hits), "hits": hits}
            rows.append(row)
            print(f"{label} {mode} {question['id']} hit={row['metrics']['hit_at_5']} ms={elapsed:.1f}", flush=True)
    return rows, vector.describe()


def main() -> int:
    """기존·신규 인덱스를 같은 조건으로 평가하고 비교 JSON을 저장함.

    반환값: 정상 완료 시 프로세스 종료 코드 0임.
    예외: 질문 수가 20개가 아니거나 원본 인덱스 지문이 바뀌면 예외를 발생시킴.
    부수효과: 기준 인덱스 복사본·질문 벡터 캐시·비교 결과 JSON을 생성하고 요약을 표준 출력함.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("--backup", type=Path, default=HERE.parent.parent / "vector-bm25-v1-backup")
    parser.add_argument("--new-data", type=Path, default=HERE.parent / "data")
    parser.add_argument("--questions", type=Path, default=HERE / "group2_questions.json")
    parser.add_argument("--output", type=Path, default=HERE / "results" / "comparison.json")
    args = parser.parse_args()
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TOKENIZERS_PARALLELISM"] = "false"
    fixture = read_json(args.questions)
    questions = fixture["questions"] if isinstance(fixture, dict) else fixture
    if len(questions) != 20:
        raise ValueError("2조 평가 질문은 정확히 20개여야 합니다.")
    baseline, original_hashes = snapshot_baseline(args.backup)
    active = read_json(args.new_data / "active_generation.json")
    publication = active.get("publication", active)
    def resolve(value):
        """상대 게시 경로를 신규 데이터 루트 기준으로 해석함."""
        path = Path(value)
        return path if path.is_absolute() else args.new_data / path
    embedder = QueryEmbedder(questions)
    run_tag = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    old_rows, old_info = evaluate("old", baseline / "chroma", baseline / "search_indexes", questions, embedder,
                                  run_tag)
    new_rows, new_info = evaluate("new", resolve(publication["chroma_path"]),
                                  resolve(publication["search_index_root"]), questions, embedder, run_tag)
    after = {f"{folder}/{name}": value for folder in ("chroma", "search_indexes")
             for name, value in hashes(args.backup / "data" / folder).items()}
    if after != original_hashes:
        raise RuntimeError("원본 기준 인덱스가 평가 중 변경되었습니다.")
    rows = old_rows + new_rows
    report = {"created_at": datetime.now(timezone.utc).isoformat(),
              "configuration": {"model": MODEL, "revision": REVISION, "dimension": 768,
                                "old_document_input_limit": 255, "new_document_input_limit": 800,
                                "query_input_limit": 255, "transform": "off", "top_k": 5,
                                "scope": "metadata OR filter before ranking", "query_embedding_cached": True,
                                "vector_strategy": "similarity", "candidate_multiplier": 4,
                                "hybrid_weights": {"vector": 0.6, "bm25": 0.4}},
              "original_indexes_unchanged": True, "original_hashes": original_hashes,
              "index_info": {"old": old_info, "new": new_info},
              "fixture_sha256": hashlib.sha256(args.questions.read_bytes()).hexdigest(),
              "summary": {f"{label}_{mode}": aggregate([row for row in rows if row["index"] == label and row["mode"] == mode])
                          for label in ("old", "new") for mode in ("vector", "hybrid")}, "results": rows}
    write_json(args.output, report)
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
