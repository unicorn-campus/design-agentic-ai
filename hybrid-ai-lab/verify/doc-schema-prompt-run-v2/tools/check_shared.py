"""6단계 추가 검사: 공통 노드 타입과 참조 노드가 쓰이는 모든 문서 종류 초안에서 라벨, description, 키 속성이 같은지 봄.

실행: python tools/check_shared.py → output/check_shared.log
"""

from __future__ import annotations

import json

from common import BASE, load_json

DOCS = ["regulation", "benefit_guide", "consult_log"]


def main() -> None:
    shared = load_json("shared_concepts.json")
    targets = {**{k: v["docs"] for k, v in shared["shared_node_types"].items()},
               **{k: v["docs"] for k, v in shared["reference_nodes"].items()}}
    drafts = {d: json.loads((BASE / d / "output" / "schema_draft.json").read_text(encoding="utf-8")) for d in DOCS}
    log, ok = [], True
    for label, docs in targets.items():
        found = {}
        for d in docs:
            n = next((x for x in drafts[d]["node_types"] if x["label"] == label), None)
            if n is None:
                log.append(f"{label}: {d} 초안에 없음")
                ok = False
                continue
            keys = sorted(c["property_name"] for c in drafts[d]["constraints"] if c["node_type"] == label)
            found[d] = (n["description"], json.dumps(n["properties"], ensure_ascii=False, sort_keys=True), tuple(keys))
        same = len({v for v in found.values()}) == 1
        ok &= same
        log.append(f"{label}: 쓰는 문서 종류 {list(found)} → 라벨, description, 속성, 키 {'같음' if same else '다름'}")
    log.append("결과: " + ("통과" if ok else "실패"))
    (BASE / "output" / "check_shared.log").write_text("\n".join(log) + "\n", encoding="utf-8")
    print("\n".join(log))


if __name__ == "__main__":
    main()
