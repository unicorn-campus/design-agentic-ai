"""저장된 추출 원본(fill_calls_roundN.jsonl)을 지금 채점과 지금 기대 답으로 다시 셈(LLM 호출 없음).
실행: python tools/rescore.py N → output/rescore_roundN_now.json"""
import json, sys
from pathlib import Path
from fill_test_v2 import score_v2
from common import load_json
n = sys.argv[1]
crit = load_json("pass_criteria.json"); out = {}
for doc in ["regulation", "benefit_guide", "consult_log"]:
    res = [json.loads(l) for l in Path(f"../{doc}/output/fill_calls_round{n}.jsonl").read_text(encoding="utf-8").splitlines()]
    exp = load_json(f"{doc}/expected_answers.json")["answers"]
    sc = score_v2(doc, [r for r in res if r["chunk_id"] in exp], exp, load_json(f"{doc}/schema_spec.json")["cq_map"], crit)
    out[doc] = sc["metrics"]
passed = sum(m["pass"] for d in out.values() for m in d.values())
Path(f"../output/rescore_round{n}_now.json").write_text(json.dumps({"passed": passed, "metrics": out}, ensure_ascii=False, indent=1), encoding="utf-8")
print("round", n, "지금 기준 통과", passed, "/ 21", {d: [q for q, m in v.items() if not m["pass"]] for d, v in out.items()})
