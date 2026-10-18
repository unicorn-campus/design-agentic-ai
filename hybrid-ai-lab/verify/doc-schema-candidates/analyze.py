"""calls.jsonl로 포화 모양을 봄: 건별 새 타입 수, 자주 나온 핵심 타입이 몇 번째 건에서 처음 나왔는지.

핵심 타입 = 성공한 호출의 20% 이상에서 제안된 노드 타입 또는 관계(드문 이름은 사람이 합치거나 버릴 후보).
실행: ../neo4j-vector-search/.venv/Scripts/python analyze.py → output/saturation.md
"""

import json
import re
from collections import Counter
from pathlib import Path

OUT = Path(__file__).resolve().parent / "output"
key = lambda s: re.sub(r"[^0-9a-z가-힣]", "", s.lower())

calls = [json.loads(l) for l in (OUT / "calls.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
lines = ["# 포화 모양(자동 추출 결과)", ""]
for doc in ("regulation", "consult_log", "benefit_guide"):
    rows = [c for c in calls if c["doc_type"] == doc and "error" not in c]
    n = len(rows)
    node_cnt, rel_cnt, first = Counter(), Counter(), {}
    for i, c in enumerate(rows, 1):
        for t in {key(x) for x in c["nodes"]}:
            node_cnt[t] += 1
            first.setdefault(("n", t), i)
        for t in {key(x) for x in c["relationships"]}:
            rel_cnt[t] += 1
            first.setdefault(("r", t), i)
    th = max(2, round(n * 0.2))
    core_n = [t for t, v in node_cnt.items() if v >= th]
    core_r = [t for t, v in rel_cnt.items() if v >= th]
    once_n = sum(1 for v in node_cnt.values() if v == 1)
    once_r = sum(1 for v in rel_cnt.values() if v == 1)
    last_core = max([first[("n", t)] for t in core_n] + [first[("r", t)] for t in core_r] or [0])
    curve = [len(c.get("new_nodes", [])) + len(c.get("new_relationships", [])) for c in rows]
    lines += [f"## {doc} (성공 {n}건)", "",
              f"- 노드 타입 {len(node_cnt)}개 중 1건에서만 나온 것 {once_n}개, 관계 {len(rel_cnt)}개 중 1건에서만 나온 것 {once_r}개",
              f"- 핵심 타입(성공 호출의 20% 이상 = {th}건 이상): 노드 타입 {len(core_n)}개, 관계 {len(core_r)}개",
              f"- 핵심 타입이 모두 처음 나온 시점: {last_core}번째 건",
              "- 핵심 노드 타입(처음 나온 건): " + ", ".join(f"{t}({first[('n', t)]})" for t in sorted(core_n, key=lambda t: first[('n', t)])),
              "- 핵심 관계(처음 나온 건): " + ", ".join(f"{t}({first[('r', t)]})" for t in sorted(core_r, key=lambda t: first[('r', t)])),
              "- 건별 새 이름 수(노드 + 관계): " + " ".join(map(str, curve)), ""]
(OUT / "saturation.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
print("\n".join(lines))
