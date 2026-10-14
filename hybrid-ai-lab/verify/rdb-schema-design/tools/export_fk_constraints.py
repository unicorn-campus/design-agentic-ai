"""PostgreSQL 카탈로그(pg_constraint)에서 FK 제약을 '제약 1개 = 1행'으로 뽑아 JSON으로 저장하는 스크립트임.

왜 필요한가(2026-10-14 실측): apoc.model.jdbc 결과는 FK 열에 ForeignKey 라벨만 붙이고, 그 FK가 가리키는 테이블과 열은 담지 않음.
또 복합 FK(card의 product_id, brand → product_annual_fee)는 열이 2개라도 제약은 1개라서, 변환 규칙의 'FK 개수'는 제약 수로 세야 함.
information_schema를 단순 조인하면 복합 FK의 열 짝이 엇갈려 곱해지므로 pg_constraint의 conkey와 confkey를 순서대로 짝지음.

실행: python tools/export_fk_constraints.py  (로컬 개발 DB 컨테이너 hybrid-ai-lab-rdb에 docker exec로 읽기 전용 조회)
출력: output/fk_constraints.json
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "output" / "fk_constraints.json"
CONTAINER = os.environ.get("RDB_CONTAINER", "hybrid-ai-lab-rdb")
DB = os.environ.get("RDB_NAME", "cardlab")

QUERY = """
select coalesce(json_agg(row_to_json(t) order by t.table_name, t.constraint_name), '[]'::json)
from (
  select c.conname as constraint_name,
         rel.relname as table_name,
         ref.relname as ref_table,
         json_agg(json_build_object('column', a.attname, 'ref_column', ra.attname) order by k.ord) as columns
  from pg_constraint c
  join pg_class rel on rel.oid = c.conrelid
  join pg_class ref on ref.oid = c.confrelid
  join pg_namespace n on n.oid = rel.relnamespace
  join lateral unnest(c.conkey, c.confkey) with ordinality as k(attnum, ref_attnum, ord) on true
  join pg_attribute a on a.attrelid = c.conrelid and a.attnum = k.attnum
  join pg_attribute ra on ra.attrelid = c.confrelid and ra.attnum = k.ref_attnum
  where c.contype = 'f' and n.nspname = 'public'
  group by c.conname, rel.relname, ref.relname
) t;
"""


def main() -> None:
    env = dict(os.environ, MSYS_NO_PATHCONV="1")
    result = subprocess.run(
        ["docker", "exec", CONTAINER, "psql", "-U", os.environ.get("RDB_ADMIN_USER", "cardlab"), "-d", DB,
         "-At", "-c", QUERY],
        capture_output=True, text=True, encoding="utf-8", check=True, env=env)
    rows = json.loads(result.stdout.strip())
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"source": {"container": CONTAINER, "database": DB, "catalog": "pg_constraint"},
                               "foreign_keys": rows}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"저장: {OUT} — FK 제약 {len(rows)}개")
    for r in rows:
        cols = ", ".join(f"{c['column']}→{c['ref_column']}" for c in r["columns"])
        print(f"  {r['table_name']} → {r['ref_table']} ({cols})")


if __name__ == "__main__":
    main()
