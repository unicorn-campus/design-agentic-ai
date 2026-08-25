from __future__ import annotations

import argparse
from pathlib import Path

import psycopg

from help_desk_dataset.glossary import load_glossary
from help_desk_runtime.settings import RuntimeSettings


def main() -> None:
    parser = argparse.ArgumentParser(description="카드업무용어를 PostgreSQL 정규화 테이블에 적재함")
    parser.add_argument("source", type=Path)
    parser.add_argument("--generation-id", required=True)
    args = parser.parse_args()
    settings = RuntimeSettings()
    if settings.glossary_postgres_dsn is None:
        raise RuntimeError("HELP_DESK_GLOSSARY_POSTGRES_DSN 설정이 필요함")
    glossary = load_glossary(args.source)
    rows = [
        (glossary.name, alias, "|".join(canonical_terms), args.generation_id, "active")
        for alias, canonical_terms in glossary.aliases.items()
    ]
    statement = (
        "INSERT INTO glossary_term "
        "(lexicon_name, alias, canonical_term, generation_id, status, updated_at) "
        "VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP) "
        "ON CONFLICT (lexicon_name, alias, generation_id) DO UPDATE SET "
        "canonical_term = EXCLUDED.canonical_term, status = EXCLUDED.status, "
        "updated_at = CURRENT_TIMESTAMP"
    )
    with psycopg.connect(settings.glossary_postgres_dsn.get_secret_value()) as connection:
        with connection.cursor() as cursor:
            cursor.executemany(statement, rows)


if __name__ == "__main__":
    main()
