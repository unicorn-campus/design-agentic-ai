"""약관과 혜택: 역량 질문 없이(output/) vs 역량 질문만(output-cqonly-docs/) 비교. 층마다 두 실행 중 적게 본 건수까지만 셈.

실행: ../neo4j-vector-search/.venv/Scripts/python compare_docs.py → output-cqonly-docs/compare.md
"""
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent
key = lambda s: re.sub(r"[^0-9a-z]", "", s.lower())


def load(folder, doc):
    calls = [json.loads(l) for l in (ROOT / folder / "calls.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    return [c for c in calls if c["doc_type"] == doc]


lines = ["# 약관과 혜택: 역량 질문 없이(A) vs 역량 질문만(CQ)", ""]
for doc in ("regulation", "benefit_guide"):
    a_all, c_all = load("output", doc), load("output-cqonly-docs", doc)
    a, c = [], []
    for layer in dict.fromkeys(x["layer"] for x in a_all):
        la = [x for x in a_all if x["layer"] == layer]
        lc = [x for x in c_all if x["layer"] == layer]
        k = min(len(la), len(lc))
        a += la[:k]
        c += lc[:k]
    lines += [f"## {doc} (비교 건수 {len(a)})", "", "| 지표 | A | CQ |", "|---|---:|---:|"]
    res = {}
    for name, rows in (("A", a), ("CQ", c)):
        ok = [x for x in rows if "error" not in x]
        cnt, names = Counter(), {}
        for x in ok:
            for kind, xs in (("n", x["nodes"]), ("r", x["relationships"])):
                for kk, v in {key(y): y for y in xs}.items():
                    cnt[(kind, kk)] += 1
                    names.setdefault((kind, kk), v)
        th = max(2, round(len(ok) * 0.2))
        res[name] = {"ok": len(ok), "fail": len(rows) - len(ok), "cnt": cnt, "names": names,
                     "core": [k for k, v in cnt.most_common() if v >= th]}
    for label, f in (("성공 / 실패", lambda r: f"{r['ok']} / {r['fail']}"),
                     ("노드 타입 이름 수", lambda r: sum(1 for k in r["cnt"] if k[0] == "n")),
                     ("관계 이름 수", lambda r: sum(1 for k in r["cnt"] if k[0] == "r")),
                     ("1건에서만 나온 이름 비율", lambda r: f"{round(100 * sum(1 for v in r['cnt'].values() if v == 1) / max(1, len(r['cnt'])))}%"),
                     ("핵심 이름 수(20% 이상)", lambda r: len(r["core"]))):
        lines.append(f"| {label} | {f(res['A'])} | {f(res['CQ'])} |")
    for name in ("A", "CQ"):
        r = res[name]
        lines += ["", f"- {name} 핵심 노드 타입: " + ", ".join(f"{r['names'][k]}({r['cnt'][k]})" for k in r["core"] if k[0] == "n"),
                  f"- {name} 핵심 관계: " + ", ".join(f"{r['names'][k]}({r['cnt'][k]})" for k in r["core"] if k[0] == "r")]
    only = [k for k in res["CQ"]["cnt"] if k not in res["A"]["cnt"] and res["CQ"]["cnt"][k] >= 2]
    lines += ["", "- CQ에만 나온 이름(2건 이상): " + ", ".join(
        f"{res['CQ']['names'][k]}({res['CQ']['cnt'][k]})" for k in sorted(only, key=lambda k: -res['CQ']['cnt'][k])), ""]
(ROOT / "output-cqonly-docs" / "compare.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
print("\n".join(lines))
