"""E2E 시험이 저장소를 직접 읽을 때 쓰는 도우미.

**운영자 계정**으로 읽음 — 관측 기록은 쓰기 전용 계정으로 적재되고 읽기는
운영자 계정으로만 가능함(⑦ 4-2 K-12). 시험은 그 운영자 자리에 섬.
"""

from __future__ import annotations

import os
import subprocess

import pytest


class DbProbe:
    """`docker exec psql`로 조회함 — 시험 실행 환경에 드라이버를 요구하지 않음."""

    def __init__(self, container: str, db: str, user: str) -> None:
        self.container = container
        self.db = db
        self.user = user

    def execute(self, sql: str, params: tuple = ()) -> list[tuple]:
        rendered = sql
        for value in params:
            rendered = rendered.replace("%s", _literal(value), 1)
        proc = subprocess.run(
            [
                "docker", "exec", self.container,
                "psql", "-U", self.user, "-d", self.db,
                "-At", "-F", "\x1f", "-c", rendered,
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        if proc.returncode != 0:
            raise RuntimeError(f"psql 실패: {proc.stderr.strip()}\nSQL: {rendered}")
        rows = []
        for line in proc.stdout.splitlines():
            if not line:
                continue
            rows.append(tuple(_coerce(v) for v in line.split("\x1f")))
        return rows


def _literal(value) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, (int, float)):
        return str(value)
    escaped = str(value).replace("'", "''")
    return f"'{escaped}'"


def _coerce(raw: str):
    if raw == "":
        return None
    if raw.startswith("{") and raw.endswith("}") and not raw.startswith('{"'):
        inner = raw[1:-1]
        return [x.strip('"') for x in inner.split(",")] if inner else []
    if raw.isdigit():
        return int(raw)
    return raw


@pytest.fixture(scope="session")
def db() -> DbProbe:
    return DbProbe(
        container=os.environ.get("LP_PG_CONTAINER", "lp-postgres"),
        db=os.environ.get("LP_DB_NAME", "lunchpick"),
        user=os.environ.get("LP_PG_SUPERUSER", "postgres"),
    )


@pytest.fixture(scope="session", autouse=True)
def reseed() -> None:
    """E2E 실행 전 합성 데이터를 다시 깖 — 실행 간 오염을 끊음.

    왜 필요한가: ⑥ B-4는 최근 3일 내 추천된 동일 식당을 후보에서 뺌.
    시험이 추천을 만들 때마다 그 식당들이 3일간 막히므로, 재실행을 거듭하면
    후보 풀이 말라 `B-7 후보 0건` 착지로 떨어짐. **이것은 설계대로 도는
    것이며 버그가 아님** — 다만 시험이 매번 같은 상태에서 시작하도록
    데이터를 되돌림.

    관측 기록(obs_span·obs_access_log)은 건드리지 않음 — S-6 `변조 방지`.
    """
    src_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    proc = subprocess.run(
        ["docker", "compose", "--env-file", ".env", "--profile", "seed",
         "run", "--rm", "lp-synth"],
        cwd=src_dir, capture_output=True, text=True, encoding="utf-8",
    )
    if proc.returncode != 0:
        pytest.skip(f"합성 데이터 재시드 실패 — 스택이 떠 있는지 확인 필요:\n{proc.stderr[-500:]}")
