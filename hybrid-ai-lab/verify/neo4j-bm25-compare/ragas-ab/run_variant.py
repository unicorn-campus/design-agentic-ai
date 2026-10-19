"""BM25를 바꿔 끼운 채로 기존 평가 스크립트(`evaluate_retriever.py`)를 그대로 돌리는 진입 스크립트임.

기존 코드를 고치지 않는 방법: 조립 지점이 만든 색인 공급자의 `acquire`만 이 자리에서 감싸,
돌려주는 색인을 `Neo4jKeywordIndex`로 한 겹 싸서 넘김. 평가와 검색 흐름은 기존 코드를 그대로 씀.

실행(검색기 가상환경에서):
    retriever/vector-retriever/.venv/Scripts/python verify/neo4j-bm25-compare/ragas-ab/run_variant.py \
        --bm25 baseline --out <결과.json> --label base1
    ... --bm25 neo4j --out <결과.json> --label A

`--bm25 baseline`이면 기존 BM25를 그대로 쓰고(기준), `--bm25 neo4j`면 A 방식으로 바꿔 끼움.
두 경우 모두 평가셋, top_k, 답변 생성 설정은 같게 두어 BM25만 달라지게 함.
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LAB_ROOT = ROOT.parent.parent.parent
RETRIEVER_DIR = LAB_ROOT / "retriever" / "vector-retriever"
POINTER = LAB_ROOT / "indexer" / "vector-bm25" / "data" / "active_generation.json"
DEFAULT_QUESTIONS = LAB_ROOT / "ragas" / "eval-set.json"

sys.path.insert(0, str(RETRIEVER_DIR))  # 기존 검색기 패키지를 그대로 import하기 위함
sys.path.insert(0, str(ROOT))


def install_neo4j_bm25(session) -> list:
    """색인 공급자가 돌려주는 색인을 Neo4j 어댑터로 감싸도록 `acquire`를 갈아 끼움.

    왜 클래스 메서드를 바꾸나: 조립 지점(bootstrap)이 공급자를 직접 만들어 밖에서 끼워 넣을 자리가 없음.
    기존 파일을 고치지 않으려고 이 실행 안에서만 감쌈(파일은 그대로임).
    반환값: 만들어진 어댑터 목록(실행 뒤 Neo4j 호출 횟수를 확인하려고 모아 둠).
    부수효과: 이 프로세스 안에서만 `LocalIndexProvider.acquire` 동작이 바뀜.
    """

    from neo4j_keyword_index import Neo4jKeywordIndex
    from app.infrastructure.index_store import LocalIndexProvider

    made: list = []
    original = LocalIndexProvider.acquire
    wrapped: dict[int, Neo4jKeywordIndex] = {}

    def acquire(self):
        """원래 대여 결과를 받아 색인만 Neo4j 어댑터로 바꿔 돌려줌(세대와 경고는 그대로)."""

        lease = original(self)
        adapter = wrapped.get(id(lease.index))
        if adapter is None:
            adapter = Neo4jKeywordIndex(lease.index, session)
            wrapped[id(lease.index)] = adapter
            made.append(adapter)
        return dataclasses.replace(lease, index=adapter)

    LocalIndexProvider.acquire = acquire
    return made


def main(argv: list[str] | None = None) -> int:
    """평가 1회를 실행함. 반환값은 종료 코드(정상 0)."""

    parser = argparse.ArgumentParser(description="BM25를 바꿔 끼우고 기존 리트리버 평가를 1회 실행함")
    parser.add_argument("--bm25", choices=("baseline", "neo4j"), required=True, help="기존 BM25 또는 Neo4j A 방식")
    parser.add_argument("--out", type=Path, required=True, help="결과 JSON 경로")
    parser.add_argument("--label", required=True, help="결과에 남길 실행 이름(base1, base2, A)")
    parser.add_argument("--questions", type=Path, default=DEFAULT_QUESTIONS, help="평가셋 JSON")
    parser.add_argument("--top-k", type=int, default=5, help="세 실행 모두 같게 둠(기본 5)")
    args = parser.parse_args(argv)

    pointer_before = POINTER.read_text(encoding="utf-8")
    backup = ROOT / "_backup" / "active_generation.json"
    backup.parent.mkdir(parents=True, exist_ok=True)
    if not backup.exists():
        shutil.copyfile(POINTER, backup)

    session = None
    adapters: list = []
    try:
        if args.bm25 == "neo4j":
            from neo4j_keyword_index import BASELINE, Neo4jQuerySession, read_connection, setup_index, teardown_index

            fixture = json.loads(BASELINE.read_text(encoding="utf-8"))
            pointer = json.loads(pointer_before)
            if fixture["generation"] != pointer["generation"]:
                raise SystemExit(f"기준 자료의 세대가 사용 중 세대와 다름: {fixture['generation']} != {pointer['generation']}")
            url, auth = read_connection()
            session = Neo4jQuerySession(url, auth)
            setup_index(session, fixture["chunks"])
            adapters = install_neo4j_bm25(session)
            print(f"[{args.label}] Neo4j A 방식 준비 완료 — 조각 {len(fixture['chunks'])}건")
        else:
            print(f"[{args.label}] 기존 BM25 그대로 사용")

        import evaluate_retriever

        code = evaluate_retriever.main([
            "--questions", str(args.questions),
            "--generate-answer",
            "--out", str(args.out),
            "--top-k", str(args.top_k),
            "--version-label", args.label,
        ])
    finally:
        if session is not None:
            try:
                calls = sum(adapter.neo4j_calls for adapter in adapters)
                print(f"[{args.label}] Neo4j 낱말 검색 호출 {calls}회")
                teardown_index(session)
                print(f"[{args.label}] 전용 라벨과 인덱스 정리 완료")
            finally:
                session.close()

    pointer_after = POINTER.read_text(encoding="utf-8")
    same = pointer_after == pointer_before
    print(f"[{args.label}] 사용 중 세대 포인터 내용 같음: {same}")
    if not same:
        shutil.copyfile(backup, POINTER)
        raise SystemExit("포인터가 바뀌어 백업으로 되돌림 — 결과를 쓰지 말 것")
    return code


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    raise SystemExit(main())
