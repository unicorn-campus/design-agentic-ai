"""후보 A와 기준 BM25의 순위가 갈리는 원인을 점수 공식으로 되짚는 스크립트임.

하는 일 1 — 공식 되짚기: 기준(bm25s lucene)과 똑같은 식을 파이썬으로 다시 적고 설정을 하나씩 Lucene 쪽으로 바꿔 가며
  어느 설정이 Neo4j 실제 점수와 맞아떨어지는지 확인함.
    V1. k1=1.5, 문서 길이 그대로        → 기준과 같아야 함(구현 검증)
    V2. k1=1.2, 문서 길이 그대로        → k1 차이만 반영
    V3. k1=1.2, 문서 길이 Lucene 양자화 → Neo4j 실제 값과 같아야 함
하는 일 2 — 분석기 낱말 쪼개기 확인: 짧은 글을 넣은 탐침 노드로 Kiwi·cjk·standard가 같은 질문을 잡는지 봄.

실행(검증 전용 가상환경):
    verify/neo4j-vector-search/.venv/Scripts/python verify/neo4j-bm25-compare/tools/diagnose.py
출력: diagnosis.json
"""

from __future__ import annotations

import json
import math
import os
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))

from run_compare import LABEL, escape_lucene, load_env, overlap, top_ids  # noqa: E402

BASELINE = ROOT / "fixtures" / "baseline.json"
RESULTS = ROOT / "results.json"
OUT = ROOT / "diagnosis.json"
PROBE_LABEL = "BmProbe"
TOP_K = 10


def int_to_byte4(value: int) -> int:
    """Lucene SmallFloat.intToByte4 — 문서 길이를 1바이트로 줄여 담는 규칙임."""

    if value < 8:
        return value
    shift = value.bit_length() - 4
    return ((shift + 1) << 3) | ((value >> shift) - 8)


def byte4_to_int(encoded: int) -> int:
    """Lucene SmallFloat.byte4ToInt — 1바이트로 줄인 문서 길이를 되돌림(값이 뭉개짐)."""

    bits = encoded & 0xFF
    shift = (bits >> 3) - 1
    if shift == -1:
        return bits & 0x07
    return (8 | (bits & 0x07)) << shift


def quantize(length: int) -> int:
    """Lucene이 실제로 점수 계산에 쓰는 뭉갠 문서 길이."""

    return byte4_to_int(int_to_byte4(length))


def score_all(token_lists: list[list[str]], query_tokens: list[str], *, k1: float, b: float,
              lucene_norm: bool) -> list[float]:
    """기준(bm25s lucene)과 같은 식으로 모든 문서 점수를 계산함.

    식: idf = ln(1 + (N - df + 0.5) / (df + 0.5)), tfc = tf / (k1 * ((1 - b) + b * dl / avgdl) + tf).
    인자: lucene_norm이 참이면 dl을 Lucene처럼 1바이트로 뭉개 씀.
    반환값: 문서 순서대로의 점수 목록.
    """

    counts = [Counter(tokens) for tokens in token_lists]
    lengths = [len(tokens) for tokens in token_lists]
    total = len(token_lists)
    average = sum(lengths) / total
    document_frequency: Counter[str] = Counter()
    for bag in counts:
        document_frequency.update(bag.keys())

    scores = [0.0] * total
    for token in query_tokens:  # 질문에 같은 낱말이 두 번 나오면 기준과 같이 두 번 더함
        df = document_frequency.get(token, 0)
        if df == 0:
            continue
        idf = math.log(1 + (total - df + 0.5) / (df + 0.5))
        for row, bag in enumerate(counts):
            tf = bag.get(token, 0)
            if not tf:
                continue
            dl = quantize(lengths[row]) if lucene_norm else lengths[row]
            scores[row] += idf * (tf / (k1 * ((1 - b) + b * dl / average) + tf))
    return scores


def probe(session, cases: list[dict]) -> list[dict]:
    """탐침 노드 몇 건을 넣고 분석기별로 같은 질문이 잡히는지 확인함."""

    session.run(f"MATCH (n:{PROBE_LABEL}) DETACH DELETE n").consume()
    for row in session.run(
        "SHOW INDEXES YIELD name WHERE name STARTS WITH 'bm25probe_' RETURN name"
    ).values():
        session.run(f"DROP INDEX {row[0]} IF EXISTS").consume()

    session.run(
        f"UNWIND $rows AS row CREATE (n:{PROBE_LABEL}) SET n = row",
        rows=[{"name": c["name"], "body_cjk": c["text"], "body_std": c["text"]} for c in cases],
    ).consume()
    for analyzer, prop in (("cjk", "body_cjk"), ("standard", "body_std")):
        session.run(
            f"CREATE FULLTEXT INDEX bm25probe_{analyzer} FOR (n:{PROBE_LABEL}) ON EACH [n.{prop}] "
            "OPTIONS {indexConfig: {`fulltext.analyzer`: $analyzer}}",
            analyzer=analyzer,
        ).consume()
    import time
    time.sleep(3.0)

    found = []
    for case in cases:
        row = {"name": case["name"], "text": case["text"], "query": case["query"],
               "kiwi_tokens": case.get("kiwi_tokens", [])}
        for analyzer in ("cjk", "standard"):
            hits = session.run(
                "CALL db.index.fulltext.queryNodes($name, $q, {limit: 20}) YIELD node, score "
                "RETURN node.name AS name ORDER BY score DESC",
                name=f"bm25probe_{analyzer}", q=escape_lucene(case["query"]),
            ).values()
            row[analyzer] = [h[0] for h in hits]
        found.append(row)

    session.run(f"MATCH (n:{PROBE_LABEL}) DETACH DELETE n").consume()
    for analyzer in ("cjk", "standard"):
        session.run(f"DROP INDEX bm25probe_{analyzer} IF EXISTS").consume()
    return found


def main() -> None:
    data = json.loads(BASELINE.read_text(encoding="utf-8"))
    results = json.loads(RESULTS.read_text(encoding="utf-8"))
    chunks = data["chunks"]
    order = [row["chunk_id"] for row in chunks]
    token_lists = [row["tokens"] for row in chunks]
    b = float(data["bm25"]["b"])

    variants = {
        "V1_k1-1.5_len-exact": {"k1": 1.5, "lucene_norm": False},
        "V2_k1-1.2_len-exact": {"k1": 1.2, "lucene_norm": False},
        "V3_k1-1.2_len-lucene": {"k1": 1.2, "lucene_norm": True},
    }
    by_id = {row["id"]: row for row in results["questions"]}
    agreement = {name: {"vs_baseline_top10": [], "vs_A_top10": [], "vs_A_top1": [],
                        "max_score_gap_vs_A": 0.0} for name in variants}

    for item in data["questions"]:
        base_top = by_id[item["id"]]["baseline"]["top"]
        a_top = by_id[item["id"]]["candidates"]["A"]["top"]
        a_scores = dict(zip(a_top, by_id[item["id"]]["candidates"]["A"]["top_scores"]))
        for name, config in variants.items():
            raw = score_all(token_lists, item["tokens"], b=b, **config)
            scores = {order[i]: raw[i] for i in range(len(order)) if raw[i] > 0.0}
            top = top_ids(scores, TOP_K)
            agreement[name]["vs_baseline_top10"].append(overlap(base_top, top, TOP_K))
            agreement[name]["vs_A_top10"].append(overlap(a_top, top, TOP_K))
            agreement[name]["vs_A_top1"].append(1.0 if top[:1] == a_top[:1] else 0.0)
            for chunk_id, value in a_scores.items():
                if chunk_id in scores:
                    gap = abs(scores[chunk_id] - value) / max(value, 1e-9)
                    agreement[name]["max_score_gap_vs_A"] = max(
                        agreement[name]["max_score_gap_vs_A"], gap)

    summary = {
        name: {
            "mean_overlap10_vs_baseline": sum(v["vs_baseline_top10"]) / len(v["vs_baseline_top10"]),
            "mean_overlap10_vs_A": sum(v["vs_A_top10"]) / len(v["vs_A_top10"]),
            "top1_match_vs_A": sum(v["vs_A_top1"]) / len(v["vs_A_top1"]),
            "max_relative_score_gap_vs_A": v["max_score_gap_vs_A"],
        }
        for name, v in agreement.items()
    }

    lengths = [len(t) for t in token_lists]
    quantized = [quantize(n) for n in lengths]
    length_effect = {
        "min_length": min(lengths), "max_length": max(lengths),
        "mean_length": sum(lengths) / len(lengths),
        "changed_by_quantization": sum(1 for a, c in zip(lengths, quantized) if a != c),
        "mean_relative_shift": sum(abs(c - a) / a for a, c in zip(lengths, quantized)) / len(lengths),
        "examples": [{"exact": a, "lucene": c} for a, c in list(zip(lengths, quantized))[:6]],
    }

    load_env()
    from neo4j import GraphDatabase

    driver = GraphDatabase.driver(
        os.environ["NEO4J_URI"], auth=(os.environ["NEO4J_USER"], os.environ["NEO4J_PASSWORD"])
    )
    cases = [
        {"name": "josa", "text": "연회비를 면제합니다.", "query": "연회비",
         "kiwi_tokens": ["연회비", "면제", "하"]},
        {"name": "compound", "text": "직전 12개월 이용금액이 3,000,000원 이상",
         "query": "이용금액", "kiwi_tokens": ["직전", "12", "개월", "이용", "금액", "3000000", "원", "이상"]},
        {"name": "number_comma", "text": "3,000,000원 이상이면 면제", "query": "3000000",
         "kiwi_tokens": ["3000000", "원", "이상", "면제"]},
        {"name": "date_form", "text": "2026-02 명세서", "query": "2026년 2월",
         "kiwi_tokens": ["2026-02", "명세서"]},
    ]
    try:
        with driver.session() as session:
            probes = probe(session, cases)
    finally:
        driver.close()

    OUT.write_text(json.dumps({
        "formula": "idf = ln(1 + (N - df + 0.5)/(df + 0.5)), tfc = tf / (k1*((1-b) + b*dl/avgdl) + tf)",
        "baseline_bm25": data["bm25"],
        "variants": {name: {**config, "b": b} for name, config in variants.items()},
        "variant_agreement": summary,
        "length_quantization": length_effect,
        "analyzer_probe": probes,
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"저장: {OUT}")
    print(f"{'변형':<24}{'기준과 겹침10':>14}{'A와 겹침10':>12}{'A와 상위1':>11}{'A와 점수차':>12}")
    for name, value in summary.items():
        print(f"{name:<24}{value['mean_overlap10_vs_baseline']:>14.3f}"
              f"{value['mean_overlap10_vs_A']:>12.3f}{value['top1_match_vs_A']:>11.3f}"
              f"{value['max_relative_score_gap_vs_A']:>12.2%}")
    print(f"\n길이 뭉갬 영향: 218건 중 {length_effect['changed_by_quantization']}건 변함, "
          f"평균 어긋남 {length_effect['mean_relative_shift']:.2%}")
    for row in probes:
        print(f"탐침 {row['name']:<14} 질문 {row['query']!r:<12} cjk={row['cjk']} standard={row['standard']}")


if __name__ == "__main__":
    main()
