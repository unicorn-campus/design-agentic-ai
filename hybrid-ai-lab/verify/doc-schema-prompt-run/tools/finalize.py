"""9단계: 8단계 통과가 승인된 문서 종류만 GraphSchema 파일과 승인 기록을 만듦.

GraphSchema.save()로 저장한 뒤 from_file()로 다시 읽어 노드 타입, 관계, 패턴, 제약 수가 초안과 같은지 비교함.
실행: python tools/finalize.py {doc} → {doc}/graph_schema.json, {doc}/approval.json
"""

from __future__ import annotations

import copy
import hashlib
import sys
import time

from neo4j_graphrag.components.schema import GraphSchema

from common import AUTO, BASE, load_json, save_json


def sha256(path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def counts(s: GraphSchema) -> dict:
    return {"node_types": len(s.node_types), "relationship_types": len(s.relationship_types),
            "patterns": len(s.patterns), "constraints": len(s.constraints)}


def main() -> None:
    doc = sys.argv[1]
    metrics = load_json(f"{doc}/output/fill_metrics.json")
    if not metrics["all_pass"]:
        raise SystemExit(f"{doc}: 8단계 합격 기준 미달이라 9단계를 진행하지 않음")
    draft = load_json(f"{doc}/output/schema_draft.json")
    schema = GraphSchema.model_validate(copy.deepcopy(draft))
    path = BASE / doc / "graph_schema.json"
    schema.save(str(path), overwrite=True)
    reread = GraphSchema.from_file(str(path))
    want = counts(schema)  # 검증을 거친 초안 기준(required 속성이 제약으로 바뀌는 판이 있어 원본 dict 수와 다를 수 있음)
    got = counts(reread)
    same = want == got
    inputs = ["competency_questions.md", "sample_plan.json", "decisions.json", f"{doc}/expected_answers.json"]
    approval = {"doc": doc, "approver": AUTO, "approved_at": time.strftime("%Y-%m-%d %H:%M"),
                "input_sha256": {f: sha256(BASE / f) for f in inputs},
                "last_metrics": metrics, "draft_counts": want, "reread_counts": got, "reread_same": same}
    save_json(f"{doc}/approval.json", approval)
    print(f"{doc}: 초안 {want} / 다시 읽음 {got} → {'같음' if same else '다름'}")


if __name__ == "__main__":
    main()
