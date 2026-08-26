from __future__ import annotations

from datetime import UTC, datetime
from argparse import ArgumentParser
from pathlib import Path

import psycopg
from pgvector.psycopg import register_vector

from help_desk_knowledge.indexing import OpenAIEmbeddingClient, build_chunks
from help_desk_knowledge.rag import build_index_statements
from help_desk_knowledge.specs import RagSpec, required, safe_identifier
from help_desk_runtime.settings import RuntimeSettings


def main() -> None:
    parser = ArgumentParser()
    parser.add_argument("source_dir", type=Path)
    args = parser.parse_args()
    settings = RuntimeSettings()
    spec = RagSpec.from_settings(settings)
    paths = tuple(
        path
        for path in sorted(args.source_dir.rglob("*"))
        if path.is_file() and path.suffix.lower() in {".pdf", ".html", ".htm"}
    )
    if spec.source_count != len(paths):
        raise ValueError("확정한 승인 문서 원천 건수와 실제 파일 수가 다름")
    embedding_client = OpenAIEmbeddingClient(str(required(settings, "llm_api_key")))
    chunks = build_chunks(paths, spec, embedding_client)
    suffix = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
    target_table = safe_identifier(f"{spec.table}_{suffix}")
    statements = build_index_statements(spec, target_table, len(chunks))
    with psycopg.connect(spec.dsn) as connection:
        register_vector(connection)
        for statement in statements[:3]:
            connection.execute(statement)
        connection.executemany(
            f"INSERT INTO {target_table} "
            "(chunk_id, document_id, content, source_uri, source_location, baseline_date, embedding) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s)",
            [
                (
                    item.chunk_id,
                    item.document_id,
                    item.content,
                    item.source_uri,
                    item.source_location,
                    spec.baseline_date,
                    list(item.embedding),
                )
                for item in chunks
            ],
        )
        for statement in statements[3:]:
            connection.execute(statement)
    print(f"새 색인 테이블 생성 완료: {target_table}")
    print("검색 별칭 교체는 검수 완료 후 운영자가 트랜잭션으로 수행해야 함")


if __name__ == "__main__":
    main()
