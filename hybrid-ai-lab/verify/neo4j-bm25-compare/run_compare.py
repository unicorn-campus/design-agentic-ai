"""기존 BM25(Kiwi + 별칭 사전)를 Neo4j 전문 검색 인덱스로 재현할 수 있는지 순위로 견주는 스크립트임.

기준: `tools/export_baseline.py`가 뽑은 사용 중 세대의 BM25 원점수(bm25s lucene · k1=1.5 · b=0.75).
후보: 같은 청크 218건을 전용 라벨 BmChunk로 넣고 전문 검색 인덱스 3가지로 찾음.
  A. 기준과 같은 Kiwi 토큰을 공백으로 이어 붙인 속성 + whitespace 분석기(질문도 같은 Kiwi 토큰으로 검색)
  B. 색인용 본문 그대로 + cjk 분석기
  C. 색인용 본문 그대로 + standard 분석기
  A+재채점. A의 상위 50건만 받아 앱이 기준 BM25 점수로 다시 줄 세움(보정안)

전용 라벨 BmChunk와 bm25cmp_ 로 시작하는 인덱스만 만들고 지움 — 기존 Chunk·Document·Card 노드는 건드리지 않음.

실행(검증 전용 가상환경):
    verify/neo4j-vector-search/.venv/Scripts/python verify/neo4j-bm25-compare/run_compare.py
출력: results.json
"""

from __future__ import annotations

import json
import math
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Mapping, Sequence

ROOT = Path(__file__).resolve().parent
BASELINE = ROOT / "fixtures" / "baseline.json"
OUT = ROOT / "results.json"
# 접속값은 벡터 검증과 같은 시험 전용 컨테이너 설정에서 읽음. 값은 출력하지 않음.
ENV_SOURCE = ROOT.parent / "neo4j-vector-search" / ".env.example"

LABEL = "BmChunk"  # 비교 전용 라벨. 기존 Chunk 노드와 섞이지 않게 분리함
TOP_K = 10
TOP_N_ORDER = 5
K_CANDIDATES = 40  # 기존 검색기 하이브리드 후보 수(steps.py:549)
VECTOR_WEIGHT, KEYWORD_WEIGHT = 0.6, 0.4
RESCORE_POOL = 50  # 보정안에서 Neo4j가 넘겨 주는 후보 수

# Neo4j는 같은 라벨·같은 속성에 분석기만 다른 전문 검색 인덱스를 중복으로 보고 거부함(IndexAlreadyExists).
# 그래서 B·C는 내용이 똑같은 속성을 이름만 달리 둠 — 색인 대상 글자는 동일해 비교는 공정함.
CANDIDATES = (
    # (키, 인덱스 이름, 색인 속성, 분석기, 질문을 Kiwi 토큰으로 바꿀지)
    ("A", "bm25cmp_tokens_ws", "tokens_text", "whitespace", True),
    ("B", "bm25cmp_body_cjk", "body_cjk", "cjk", False),
    ("C", "bm25cmp_body_std", "body_std", "standard", False),
)

_LUCENE_SPECIAL = re.compile(r'([+\-!(){}\[\]^"~*?:\\/]|&&|\|\|)')


def escape_lucene(value: str) -> str:
    """Lucene 질의 문법 문자를 글자 그대로 찾도록 역슬래시를 붙임.

    왜 필요한가: 토큰에 섞인 '-'는 질의에서 NOT으로, '/'는 정규식 구분자로 읽혀 질문이 통째로 깨짐.
    반환값: 이스케이프한 문자열.
    """

    return _LUCENE_SPECIAL.sub(r"\\\1", value)


def load_env() -> None:
    """시험 전용 접속값을 환경변수로 올림. 이미 있는 값은 두고 감(값은 어디에도 출력하지 않음)."""

    if not ENV_SOURCE.exists():
        raise SystemExit(f"접속 설정 파일이 없음: {ENV_SOURCE}")
    for line in ENV_SOURCE.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())


# ---------------------------------------------------------------- 점수 합치기(기존 검색기와 같은 규칙)

def min_max_normalize(scores: Mapping[str, float]) -> dict[str, float]:
    """기존 검색기 fusion.min_max_normalize와 같은 규칙으로 0 ~ 1로 폄."""

    if not scores:
        return {}
    low, high = min(scores.values()), max(scores.values())
    if high == low:
        return {key: 1.0 for key in scores}
    span = high - low
    return {key: (float(value) - low) / span for key, value in scores.items()}


def weighted_hybrid(vector: Mapping[str, float], keyword: Mapping[str, float]) -> dict[str, float]:
    """기존 검색기 fusion.weighted_hybrid와 같은 가중합(벡터 0.6 : BM25 0.4)."""

    vector_norm, keyword_norm = min_max_normalize(vector), min_max_normalize(keyword)
    keys = set(vector_norm) | set(keyword_norm)
    return {
        key: VECTOR_WEIGHT * vector_norm.get(key, 0.0) + KEYWORD_WEIGHT * keyword_norm.get(key, 0.0)
        for key in keys
    }


def rank_keys(scores: Mapping[str, float], tie_breakers: Sequence[Mapping[str, float]] = ()) -> list[str]:
    """기존 검색기 fusion.rank_keys와 같은 정렬(점수 → 보조 점수 → 조각ID)."""

    def sort_key(key: str) -> tuple:
        extras = tuple(-float(extra.get(key, 0.0)) for extra in tie_breakers)
        return (-float(scores[key]), *extras, key)

    return sorted(scores, key=sort_key)


def top_ids(scores: Mapping[str, float], k: int) -> list[str]:
    """BM25 단독 순위 — 기존 keyword_search와 같이 점수 내림차순, 같으면 조각ID 오름차순."""

    return sorted(scores, key=lambda key: (-float(scores[key]), key))[:k]


# ---------------------------------------------------------------- 지표

def overlap(baseline: Sequence[str], candidate: Sequence[str], k: int) -> float:
    """상위 k 교집합 비율. 분모는 기준 쪽 상위 k 실제 건수임(결과가 k보다 적은 질문 대비)."""

    left, right = list(baseline)[:k], set(list(candidate)[:k])
    if not left:
        return 1.0 if not right else 0.0
    return len(set(left) & right) / len(left)


def same_position_ratio(baseline: Sequence[str], candidate: Sequence[str], k: int) -> float:
    """상위 k에서 같은 자리에 같은 조각이 있는 비율.

    왜 켄달 타우가 아닌가: 후보 결과에 기준 상위 조각이 아예 없을 수 있어 켄달 타우는 값이 정의되지 않거나
    빠진 항목을 임의로 메꿔야 함. 같은 자리 비율은 빠짐을 그대로 0점으로 세어 해석이 흔들리지 않음.
    """

    left = list(baseline)[:k]
    right = list(candidate)[:k]
    if not left:
        return 1.0
    hit = sum(1 for i, value in enumerate(left) if i < len(right) and right[i] == value)
    return hit / len(left)


def spearman(left: Sequence[float], right: Sequence[float]) -> float:
    """두 값 묶음의 순위 상관(스피어만). 동점은 평균 순위로 처리함."""

    def ranks(values: Sequence[float]) -> list[float]:
        order = sorted(range(len(values)), key=lambda i: values[i])
        result = [0.0] * len(values)
        i = 0
        while i < len(order):
            j = i
            while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
                j += 1
            average = (i + j) / 2 + 1
            for position in range(i, j + 1):
                result[order[position]] = average
            i = j + 1
        return result

    if len(left) < 2:
        return float("nan")
    a, b = ranks(left), ranks(right)
    mean_a, mean_b = sum(a) / len(a), sum(b) / len(b)
    numerator = sum((x - mean_a) * (y - mean_b) for x, y in zip(a, b))
    denominator = math.sqrt(sum((x - mean_a) ** 2 for x in a) * sum((y - mean_b) ** 2 for y in b))
    return numerator / denominator if denominator else float("nan")


# ---------------------------------------------------------------- Neo4j 적재·검색

def setup(session, chunks: list[dict]) -> None:
    """비교 전용 라벨로 청크 218건을 넣고 전문 검색 인덱스 3개를 만듦(기존 노드는 건드리지 않음)."""

    teardown(session)
    rows = [
        {
            "chunk_id": row["chunk_id"],
            "tokens_text": " ".join(row["tokens"]),
            "body_cjk": row["index_text"],
            "body_std": row["index_text"],
        }
        for row in chunks
    ]
    session.run(
        f"UNWIND $rows AS row CREATE (n:{LABEL}) SET n = row", rows=rows
    ).consume()
    for _key, name, prop, analyzer, _kiwi in CANDIDATES:
        session.run(
            f"CREATE FULLTEXT INDEX {name} FOR (n:{LABEL}) ON EACH [n.{prop}] "
            "OPTIONS {indexConfig: {`fulltext.analyzer`: $analyzer}}",
            analyzer=analyzer,
        ).consume()
    deadline = time.time() + 120
    while time.time() < deadline:
        states = session.run(
            "SHOW INDEXES YIELD name, state WHERE name STARTS WITH 'bm25cmp_' RETURN name, state"
        ).values()
        if len(states) == len(CANDIDATES) and all(state == "ONLINE" for _n, state in states):
            return
        time.sleep(1.0)
    raise SystemExit("전문 검색 인덱스가 ONLINE이 되지 않음")


def teardown(session) -> None:
    """비교 전용 인덱스와 라벨만 지움."""

    for row in session.run(
        "SHOW INDEXES YIELD name WHERE name STARTS WITH 'bm25cmp_' RETURN name"
    ).values():
        session.run(f"DROP INDEX {row[0]} IF EXISTS").consume()
    session.run(f"MATCH (n:{LABEL}) DETACH DELETE n").consume()


def search(session, index_name: str, query: str, limit: int) -> dict[str, float]:
    """전문 검색 인덱스에서 조각ID → Lucene 점수를 얻음. 질의가 비면 빈 결과임."""

    if not query.strip():
        return {}
    rows = session.run(
        "CALL db.index.fulltext.queryNodes($name, $q, {limit: $limit}) "
        "YIELD node, score RETURN node.chunk_id AS chunk_id, score",
        name=index_name, q=query, limit=limit,
    ).values()
    return {str(chunk_id): float(score) for chunk_id, score in rows}


def main() -> None:
    if not BASELINE.exists():
        raise SystemExit(f"기준 자료가 없음. 먼저 tools/export_baseline.py를 실행함: {BASELINE}")
    data = json.loads(BASELINE.read_text(encoding="utf-8"))
    chunks = data["chunks"]
    questions = data["questions"]
    source_by_id = {row["chunk_id"]: row["source"] for row in chunks}

    load_env()
    from neo4j import GraphDatabase

    driver = GraphDatabase.driver(
        os.environ["NEO4J_URI"], auth=(os.environ["NEO4J_USER"], os.environ["NEO4J_PASSWORD"])
    )
    per_question: list[dict] = []
    try:
        with driver.session() as session:
            setup(session, chunks)
            stored = session.run(f"MATCH (n:{LABEL}) RETURN count(n)").single()[0]
            if int(stored) != len(chunks):
                raise SystemExit(f"적재 건수가 다름: {stored} != {len(chunks)}")

            for item in questions:
                base_scores = {k: float(v) for k, v in item["keyword_scores"].items()}
                base_top = top_ids(base_scores, TOP_K)
                vector_scores = {k: float(v) for k, v in item["vector_scores"].items()}
                base_keyword_pool = {k: base_scores[k] for k in top_ids(base_scores, K_CANDIDATES)}
                base_hybrid = weighted_hybrid(vector_scores, base_keyword_pool)
                base_hybrid_top = rank_keys(base_hybrid, (vector_scores, base_keyword_pool))[:TOP_K]

                kiwi_query = " ".join(escape_lucene(t) for t in item["tokens"] if t.strip())
                plain_query = escape_lucene(item["question"])

                row: dict[str, Any] = {
                    "id": item["id"], "group": item["group"], "answerable": item["answerable"],
                    "expected_sources": item["expected_sources"],
                    "baseline": {
                        "top": base_top,
                        "top_scores": [round(base_scores[c], 6) for c in base_top],
                        "hybrid_top": base_hybrid_top,
                        "match_count": len(base_scores),
                    },
                    "candidates": {},
                }

                pools: dict[str, dict[str, float]] = {}
                for key, name, _prop, _analyzer, use_kiwi in CANDIDATES:
                    query = kiwi_query if use_kiwi else plain_query
                    scores = search(session, name, query, 300)
                    pools[key] = scores
                    cand_top = top_ids(scores, TOP_K)
                    cand_pool = {k: scores[k] for k in top_ids(scores, K_CANDIDATES)}
                    cand_hybrid = weighted_hybrid(vector_scores, cand_pool)
                    cand_hybrid_top = rank_keys(cand_hybrid, (vector_scores, cand_pool))[:TOP_K]
                    row["candidates"][key] = {
                        "top": cand_top,
                        "top_scores": [round(scores[c], 6) for c in cand_top],
                        "hybrid_top": cand_hybrid_top,
                        "match_count": len(scores),
                        "overlap10": overlap(base_top, cand_top, TOP_K),
                        "top1": 1.0 if cand_top[:1] == base_top[:1] else 0.0,
                        "order5": same_position_ratio(base_top, cand_top, TOP_N_ORDER),
                        "overlap5": overlap(base_top, cand_top, TOP_N_ORDER),
                        "hybrid_same10": 1.0 if cand_hybrid_top == base_hybrid_top else 0.0,
                        "hybrid_overlap10": overlap(base_hybrid_top, cand_hybrid_top, TOP_K),
                        "hybrid_same5": 1.0 if cand_hybrid_top[:5] == base_hybrid_top[:5] else 0.0,
                        "hybrid_overlap5": overlap(base_hybrid_top, cand_hybrid_top, 5),
                        "hybrid_order5": same_position_ratio(base_hybrid_top, cand_hybrid_top, 5),
                    }

                # 보정안: A가 넘겨 준 상위 50건만 앱이 기준 BM25 점수로 다시 줄 세움
                pool_ids = top_ids(pools["A"], RESCORE_POOL)
                rescored = {c: base_scores.get(c, 0.0) for c in pool_ids if base_scores.get(c, 0.0) > 0.0}
                res_top = top_ids(rescored, TOP_K)
                res_pool = {c: rescored[c] for c in top_ids(rescored, K_CANDIDATES)}
                res_hybrid = weighted_hybrid(vector_scores, res_pool)
                res_hybrid_top = rank_keys(res_hybrid, (vector_scores, res_pool))[:TOP_K]
                row["candidates"]["A_rescore"] = {
                    "top": res_top,
                    "top_scores": [round(rescored[c], 6) for c in res_top],
                    "hybrid_top": res_hybrid_top,
                    "match_count": len(rescored),
                    "overlap10": overlap(base_top, res_top, TOP_K),
                    "top1": 1.0 if res_top[:1] == base_top[:1] else 0.0,
                    "order5": same_position_ratio(base_top, res_top, TOP_N_ORDER),
                    "overlap5": overlap(base_top, res_top, TOP_N_ORDER),
                    "hybrid_same10": 1.0 if res_hybrid_top == base_hybrid_top else 0.0,
                    "hybrid_overlap10": overlap(base_hybrid_top, res_hybrid_top, TOP_K),
                    "hybrid_same5": 1.0 if res_hybrid_top[:5] == base_hybrid_top[:5] else 0.0,
                    "hybrid_overlap5": overlap(base_hybrid_top, res_hybrid_top, 5),
                    "hybrid_order5": same_position_ratio(base_hybrid_top, res_hybrid_top, 5),
                }
                per_question.append(row)
            teardown(session)
    finally:
        driver.close()

    # ------------------------------------------------------------ 요약
    keys = [key for key, *_ in CANDIDATES] + ["A_rescore"]
    summary: dict[str, Any] = {}
    graded = [row for row in per_question if row["expected_sources"]]
    answerable = [row for row in per_question if row["answerable"]]
    unanswerable = [row for row in per_question if not row["answerable"]]

    def hit_rate(rows: list[dict], getter, k: int) -> float:
        """기대 출처 문서가 상위 k 안에 하나라도 있는 질문의 비율."""

        if not rows:
            return float("nan")
        hits = 0
        for row in rows:
            wanted = set(row["expected_sources"])
            if any(source_by_id.get(c) in wanted for c in getter(row)[:k]):
                hits += 1
        return hits / len(rows)

    def margin(rows: list[dict], getter) -> float:
        """상위 1점 대비 상위 5점의 떨어짐 폭 평균((s1 - s5) / s1) — 점수 크기에 안 휘둘리는 분포 지표임."""

        values = []
        for row in rows:
            scores = getter(row)
            if len(scores) >= 5 and scores[0] > 0:
                values.append((scores[0] - scores[4]) / scores[0])
        return sum(values) / len(values) if values else float("nan")

    summary["baseline"] = {
        "hit5_graded": hit_rate(graded, lambda r: r["baseline"]["top"], 5),
        "hit10_graded": hit_rate(graded, lambda r: r["baseline"]["top"], TOP_K),
        "margin_answerable": margin(answerable, lambda r: r["baseline"]["top_scores"]),
        "margin_unanswerable": margin(unanswerable, lambda r: r["baseline"]["top_scores"]),
        "mean_match_count": sum(r["baseline"]["match_count"] for r in per_question) / len(per_question),
    }
    for key in keys:
        rows = [row["candidates"][key] for row in per_question]
        base_top1 = [row["baseline"]["top_scores"][0] if row["baseline"]["top_scores"] else 0.0
                     for row in per_question]
        cand_top1 = [row["candidates"][key]["top_scores"][0] if row["candidates"][key]["top_scores"] else 0.0
                     for row in per_question]
        summary[key] = {
            "overlap10": sum(r["overlap10"] for r in rows) / len(rows),
            "overlap5": sum(r["overlap5"] for r in rows) / len(rows),
            "top1_match": sum(r["top1"] for r in rows) / len(rows),
            "top1_match_count": int(sum(r["top1"] for r in rows)),
            "order5": sum(r["order5"] for r in rows) / len(rows),
            "hybrid_same10": sum(r["hybrid_same10"] for r in rows) / len(rows),
            "hybrid_same10_count": int(sum(r["hybrid_same10"] for r in rows)),
            "hybrid_overlap10": sum(r["hybrid_overlap10"] for r in rows) / len(rows),
            "hybrid_same5": sum(r["hybrid_same5"] for r in rows) / len(rows),
            "hybrid_same5_count": int(sum(r["hybrid_same5"] for r in rows)),
            "hybrid_overlap5": sum(r["hybrid_overlap5"] for r in rows) / len(rows),
            "hybrid_order5": sum(r["hybrid_order5"] for r in rows) / len(rows),
            "hit5_graded": hit_rate(graded, lambda r, k=key: r["candidates"][k]["top"], 5),
            "hit10_graded": hit_rate(graded, lambda r, k=key: r["candidates"][k]["top"], TOP_K),
            "margin_answerable": margin(answerable, lambda r, k=key: r["candidates"][k]["top_scores"]),
            "margin_unanswerable": margin(unanswerable, lambda r, k=key: r["candidates"][k]["top_scores"]),
            "mean_match_count": sum(r["match_count"] for r in rows) / len(rows),
            "spearman_top1_score": spearman(base_top1, cand_top1),
        }

    payload = {
        "generation": data["generation"],
        "chunk_count": data["chunk_count"],
        "baseline_bm25": data["bm25"],
        "question_count": len(per_question),
        "graded_question_count": len(graded),
        "unanswerable_question_count": len(unanswerable),
        "top_k": TOP_K,
        "k_candidates": K_CANDIDATES,
        "rescore_pool": RESCORE_POOL,
        "neo4j_image": "neo4j:2026.09.0-community",
        "candidates": {
            key: {"index": name, "property": prop, "analyzer": analyzer, "query": "kiwi" if kiwi else "raw"}
            for key, name, prop, analyzer, kiwi in CANDIDATES
        },
        "summary": summary,
        "questions": per_question,
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"저장: {OUT}")
    print(f"{'후보':<12}{'겹침10':>8}{'상위1':>8}{'순서5':>8}{'하이브5구성':>12}"
          f"{'하이브5순서':>12}{'적중5':>8}")
    for key in ["baseline"] + keys:
        if key == "baseline":
            print(f"{'기준':<12}{1.0:>8.3f}{1.0:>8.3f}{1.0:>8.3f}{1.0:>12.3f}{1.0:>12.3f}"
                  f"{summary['baseline']['hit5_graded']:>8.3f}")
            continue
        value = summary[key]
        print(f"{key:<12}{value['overlap10']:>8.3f}{value['top1_match']:>8.3f}{value['order5']:>8.3f}"
              f"{value['hybrid_overlap5']:>12.3f}{value['hybrid_same5']:>12.3f}"
              f"{value['hit5_graded']:>8.3f}")


if __name__ == "__main__":
    main()
