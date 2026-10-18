"""상담 이력 v2 원문(output-examples/)과 v3 원문(output-examples-v3/)의 examples 방식 결과 비교.

같은 시드라도 청크 ID가 바뀌므로 상담ID(record_id) 순서가 같은지 먼저 확인함.
업무 핵심 타입(불만 원인, 제안, 수용과 거절, 보류 조건)에 해당하는 이름이 나왔는지 낱말로 찾음.
실행: ../neo4j-vector-search/.venv/Scripts/python compare_v3.py [폴더 ...] → 마지막 폴더/compare.md
  (폴더를 안 주면 output-examples와 output-examples-v3)
"""

import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent
key = lambda s: re.sub(r"[^0-9a-z]", "", s.lower())
rid = lambda c: re.search(r"C-\d{8}-\d{3}", c["chunk_id"]).group(0)
# 업무 핵심 개념을 가리키는 이름 조각(영문 라벨 기준)
CONCEPTS = {"불만 원인": ["complaint", "grievance", "dissatisf", "painpoint", "issue", "cause", "problem"],
            "제안": ["proposal", "propos", "offer", "suggest", "recommend"],
            "수용과 거절": ["accept", "reject", "declin", "refus", "response", "decision"],
            "보류와 재검토": ["hold", "defer", "postpon", "reconsider", "review", "pending", "condition"]}


def load(folder):
    calls = [json.loads(l) for l in (ROOT / folder / "calls.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    return [c for c in calls if c["doc_type"] == "consult_log"]


def stats(rows):
    ok = [c for c in rows if "error" not in c]
    cnt, names = Counter(), {}
    for c in ok:
        for kind, xs in (("n", c["nodes"]), ("r", c["relationships"])):
            for x in {key(x): x for x in xs}.items():
                cnt[(kind, x[0])] += 1
                names.setdefault((kind, x[0]), x[1])
    th = max(2, round(len(ok) * 0.2))
    core = {k for k, v in cnt.items() if v >= th}
    hits = {c: sorted({f"{names[k]}({cnt[k]})" for k in cnt if any(w in k[1] for w in ws)},
                      key=lambda s: -int(s.rsplit("(", 1)[1][:-1])) for c, ws in CONCEPTS.items()}
    return ok, cnt, names, core, hits


import sys

folders = sys.argv[1:] or ["output-examples", "output-examples-v3"]  # 비교할 출력 폴더들(첫 폴더 순서가 기준)
runs = [(f, load(f)) for f in folders]
base = [rid(c) for c in runs[0][1]]
lines = ["# 상담 이력 스키마 후보 비교", "",
         "- 상담ID 순서가 첫 폴더와 같음: " + ", ".join(f"{f} {[rid(c) for c in rows] == base}" for f, rows in runs), ""]
for name, rows in runs:
    ok, cnt, names, core, hits = stats(rows)
    nodes = [k for k in cnt if k[0] == "n"]
    rels = [k for k in cnt if k[0] == "r"]
    lines += [f"## {name} (호출 {len(rows)}, 성공 {len(ok)})", "",
              f"- 노드 타입 {len(nodes)}개, 관계 {len(rels)}개",
              "- 핵심 노드 타입: " + ", ".join(f"{names[k]}({cnt[k]})" for k, _ in cnt.most_common() if k in core and k[0] == "n"),
              "- 핵심 관계: " + ", ".join(f"{names[k]}({cnt[k]})" for k, _ in cnt.most_common() if k in core and k[0] == "r"),
              "- 업무 핵심 개념에 해당하는 이름(나온 건수):"]
    lines += [f"  - {c}: " + (", ".join(h) if h else "없음") for c, h in hits.items()]
    lines.append("")
(ROOT / folders[-1] / "compare.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
print("\n".join(lines))
