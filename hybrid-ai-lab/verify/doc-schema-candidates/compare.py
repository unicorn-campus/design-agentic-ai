"""1건씩 따로 뽑기(output/)와 examples로 이어 뽑기(output-examples/)를 같은 표본, 같은 건수로 비교함.

공정하게 맞추는 방법: 두 실행은 같은 시드라 층마다 보는 순서가 같음. 층마다 두 실행 중 적게 본 건수까지만 비교함.
멈춤 규칙 두 가지를 나중에 같은 호출 기록 위에서 계산함
  - 규칙 A(이름 그대로): 처음 보는 이름이 나오면 '새 타입'
  - 규칙 B(2건 이상): 어떤 이름이 두 번째 건에서 나올 때 '새 타입'(한 번만 나온 잡음 이름은 세지 않음)
  둘 다 층 시작 수를 본 뒤 새 타입 0개가 연속 3건이면 멈춘 것으로 봄
실행: ../neo4j-vector-search/.venv/Scripts/python compare.py → output-examples/compare.md
"""

import json
import re
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
key = lambda s: re.sub(r"[^0-9a-z가-힣]", "", s.lower())
RUN = 3


def load(folder: str):
    calls = [json.loads(l) for l in (ROOT / folder / "calls.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    layers = json.loads((ROOT / folder / "layers.json").read_text(encoding="utf-8"))
    return calls, layers


def names(c):
    return {("n", key(x)) for x in c.get("nodes", [])} | {("r", key(x)) for x in c.get("relationships", [])}


def stop_point(rows, start, rule):
    """멈춘 건수(멈추지 않으면 None). 실패 건은 새 타입 0개로 세지 않고 연속도 끊지 않음."""

    seen, count, zero = set(), Counter(), 0
    for i, c in enumerate(rows, 1):
        if "error" in c:
            continue
        ns = names(c)
        if rule == "A":
            new = ns - seen
        else:
            new = {x for x in ns if count[x] == 1}
        seen |= ns
        for x in ns:
            count[x] += 1
        zero = zero + 1 if not new else 0
        if i >= start and zero >= RUN:
            return i
    return None


def stats(rows):
    ok = [c for c in rows if "error" not in c]
    cnt, first = Counter(), {}
    for i, c in enumerate(ok, 1):
        for x in names(c):
            cnt[x] += 1
            first.setdefault(x, i)
    n = len(ok)
    th = max(2, round(n * 0.2))
    core = {x for x, v in cnt.items() if v >= th}
    nodes = [x for x in cnt if x[0] == "n"]
    rels = [x for x in cnt if x[0] == "r"]
    return {"ok": n, "fail": len(rows) - n, "nodes": len(nodes), "rels": len(rels),
            "once_nodes": sum(1 for x in nodes if cnt[x] == 1), "once_rels": sum(1 for x in rels if cnt[x] == 1),
            "core": core, "core_last": max([first[x] for x in core] or [0]), "cnt": cnt}


a_calls, a_layers = load("output")
b_calls, b_layers = load("output-examples")
lines = ["# 1건씩 따로 뽑기(A) vs examples로 이어 뽑기(B)", "",
         "- 같은 시드, 같은 순서. 층마다 두 실행 중 적게 본 건수까지만 비교",
         "- 핵심 타입: 성공 호출의 20% 이상에서 나온 이름. 멈춤 규칙 A는 이름 그대로, B는 두 번째 건에서 나온 이름만 셈", ""]
for doc in ("regulation", "consult_log", "benefit_guide"):
    if doc not in b_layers:
        continue
    a_rows_all, b_rows_all, stop_rows = [], [], []
    for la, lb in zip(a_layers[doc], b_layers[doc]):
        k = min(la["used"], lb["used"])
        ra = [c for c in a_calls if c["doc_type"] == doc and c["layer"] == la["layer"]][:k]
        rb = [c for c in b_calls if c["doc_type"] == doc and c["layer"] == lb["layer"]][:k]
        a_rows_all += ra
        b_rows_all += rb
        stop_rows.append((la["layer"], la["population"], la["start"], k,
                          [stop_point(rows, la["start"], rule) for rows in (ra, rb) for rule in ("A", "B")]))
    sa, sb = stats(a_rows_all), stats(b_rows_all)
    pct = lambda x, y: f"{round(100 * x / y)}%" if y else "-"
    jac = len(sa["core"] & sb["core"]) / max(1, len(sa["core"] | sb["core"]))
    lines += [f"## {doc} (비교 건수 {len(a_rows_all)})", "",
              "| 지표 | A 따로 | B examples |", "|---|---:|---:|",
              f"| 성공 / 실패 | {sa['ok']} / {sa['fail']} | {sb['ok']} / {sb['fail']} |",
              f"| 노드 타입 이름 수 | {sa['nodes']} | {sb['nodes']} |",
              f"| 그중 1건에서만 나온 것 | {sa['once_nodes']} ({pct(sa['once_nodes'], sa['nodes'])}) | "
              f"{sb['once_nodes']} ({pct(sb['once_nodes'], sb['nodes'])}) |",
              f"| 관계 이름 수 | {sa['rels']} | {sb['rels']} |",
              f"| 그중 1건에서만 나온 것 | {sa['once_rels']} ({pct(sa['once_rels'], sa['rels'])}) | "
              f"{sb['once_rels']} ({pct(sb['once_rels'], sb['rels'])}) |",
              f"| 핵심 타입 수(노드 + 관계) | {len(sa['core'])} | {len(sb['core'])} |",
              f"| 핵심 타입이 모두 나온 시점 | {sa['core_last']}번째 | {sb['core_last']}번째 |", "",
              f"- 두 실행의 핵심 타입 겹침(자카드): {jac:.2f}",
              "- A에만 있는 핵심: " + ", ".join(sorted(x[1] for x in sa["core"] - sb["core"])),
              "- B에만 있는 핵심: " + ", ".join(sorted(x[1] for x in sb["core"] - sa["core"])),
              "- B 핵심 상위(나온 건수): " + ", ".join(f"{x[1]}({v})" for x, v in sb["cnt"].most_common() if x in sb["core"]),
              "", "| 층 | 전체 | 시작 | 비교 건수 | A에서 규칙 A | A에서 규칙 B | B에서 규칙 A | B에서 규칙 B |",
              "|---|---:|---:|---:|---:|---:|---:|---:|"]
    lines += [f"| {l} | {p} | {s} | {k} | " + " | ".join(str(x) if x else "안 멈춤" for x in pts) + " |"
              for l, p, s, k, pts in stop_rows]
    lines.append("")
(ROOT / "output-examples" / "compare.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
print("\n".join(lines))
