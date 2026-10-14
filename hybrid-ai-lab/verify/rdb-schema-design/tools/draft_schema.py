"""RDB 구조(structure_input.json)와 사람의 결정(decisions.json)으로 그래프 스키마 초안을 만들고 Mermaid, PlantUML로 그림.

규칙(설계 가이드 450 ~ 472행, 장표 「정형 테이블 → 노드 타입과 관계」):
  다른 표가 가리키는 표는 노드(관계는 FK 대상이 될 수 없음) · FK 0개 또는 1개는 노드 · FK 2개이고 업무 열 없음은 관계로 흡수 ·
  FK 2개 + 업무 열은 사람이 ①(노드) 또는 ③(관계 + 속성)을 정함 · FK 3개 이상은 중간 노드. FK 개수는 제약 수로 셈.
FK 열은 관계로 바꾼 뒤 노드 속성에서 지움. 단 키(PK)에 들어가는 열은 노드를 알아보는 데 필요해 남김.
초안은 neo4j-graphrag GraphSchema로 검증하고, 같은 라벨이 두 번 나오는지는 따로 검사함(GraphSchema가 못 거름).

실행(검증 가상환경): ../neo4j-vector-search/.venv/Scripts/python tools/draft_schema.py
출력: output/schema_draft.json(GraphSchema 입력 dict), output/schema.mmd, output/schema.puml, output/schema_preview.html
"""

from __future__ import annotations

import copy
import html
import json
from collections import Counter
from pathlib import Path

from neo4j_graphrag.components.schema import GraphSchema

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "output"
TYPE_MAP = {"text": "STRING", "varchar": "STRING", "bpchar": "STRING", "int2": "INTEGER", "int4": "INTEGER",
            "int8": "INTEGER", "numeric": "FLOAT", "float8": "FLOAT", "bool": "BOOLEAN", "date": "DATE"}


def build() -> dict:
    tables = json.loads((OUT / "structure_input.json").read_text(encoding="utf-8"))["tables"]
    dec = json.loads((ROOT / "decisions.json").read_text(encoding="utf-8"))
    tables = {t: v for t, v in tables.items() if t not in dec["exclude_tables"]}
    referenced = {fk["ref_table"] for v in tables.values() for fk in v["foreign_keys"]}

    kinds, undecided = {}, []
    for t, v in tables.items():
        fks = v["foreign_keys"]
        fk_cols = {c["column"] for fk in fks for c in fk["columns"]}
        business = [c for c in v["columns"] if not c["pk"] and c["name"] not in fk_cols]
        if t in referenced or len(fks) <= 1 or len(fks) >= 3:
            kinds[t] = "node"
        elif not business:
            kinds[t] = "relationship"  # 규칙 ②
        else:
            kinds[t] = dec["rule1"].get(t)  # 규칙 ① 또는 ③ — 사람이 정함
            if kinds[t] is None:
                undecided.append(t)
    if undecided:
        raise SystemExit(f"decisions.json rule1에 판정이 없는 표: {undecided}")

    nodes, constraints, rels, patterns = [], [], [], []
    for t, v in tables.items():
        if kinds[t] != "node":
            continue
        fk_cols = {c["column"] for fk in v["foreign_keys"] for c in fk["columns"]}
        keep = [c for c in v["columns"] if c["pk"] or c["name"] not in fk_cols]
        label = dec["node_names"][t]
        nodes.append({"label": label, "description": f"RDB 표 {t}",
                      "properties": [{"name": c["name"], "type": TYPE_MAP.get(c["type"], "STRING")} for c in keep]})
        constraints.append({"type": "UNIQUENESS", "node_type": label,
                            "property_names": [c["name"] for c in v["columns"] if c["pk"]]})
        for fk in v["foreign_keys"]:
            r = dec["relationships"][fk["constraint_name"]]
            rels.append(r["name"])
            patterns.append((dec["node_names"][r["from"]], r["name"], dec["node_names"][r["to"]]))
    for t, v in tables.items():  # 규칙 ②③: 표가 관계가 되는 경우(이번 데이터에는 없음)
        if kinds[t] in ("relationship", "rel_props"):
            a, b = (dec["node_names"][fk["ref_table"]] for fk in v["foreign_keys"])
            name = dec["relationships"][t]["name"]
            rels.append(name)
            patterns.append((a, name, b))

    schema = {"node_types": nodes, "relationship_types": [{"label": r} for r in dict.fromkeys(rels)],
              "patterns": patterns, "constraints": constraints,
              "additional_node_types": False, "additional_relationship_types": False, "additional_patterns": False}
    dup = [k for k, n in Counter(n["label"] for n in nodes).items() if n > 1]
    if dup:
        raise SystemExit(f"같은 라벨이 두 번 나옴: {dup}")
    # 패턴의 정의 안 된 타입, 정의 안 된 속성을 가리키는 제약을 거부함.
    # 사본을 넘기는 이유: model_validate가 받은 dict의 patterns를 Pattern 객체로 바꿔 놓아 JSON 저장이 깨짐(1.22.0 실측)
    GraphSchema.model_validate(copy.deepcopy(schema))
    return {"schema": schema, "kinds": kinds, "keys": {n["label"]: c["property_names"] for n, c in zip(nodes, constraints)},
            "candidates": {r["name"] for r in dec["relationships"].values() if r.get("_후보")}}


def mermaid(d: dict) -> str:
    """그래프 스키마를 노드(이름 + 속성)와 이름 붙은 화살표로 그림. 키 속성에는 (키)를 붙임."""

    s, keys = d["schema"], d["keys"]
    ids = {n["label"]: f"N{i}" for i, n in enumerate(s["node_types"])}
    lines = ["flowchart LR"]
    for n in s["node_types"]:
        props = "<br/>".join(f"{p['name']}{' (키)' if p['name'] in keys[n['label']] else ''}" for p in n["properties"])
        lines.append(f'    {ids[n["label"]]}["<b>:{n["label"]}</b><br/>{props}"]')
    for a, r, b in s["patterns"]:
        lines.append(f'    {ids[a]} -->|"{r}"| {ids[b]}')
    lines.append("    classDef node fill:#EEF3FA,stroke:#1E2A5C,stroke-width:2px,color:#2B3242")
    lines.append("    class " + ",".join(ids.values()) + " node")
    return "\n".join(lines) + "\n"


def plantuml(d: dict) -> str:
    """같은 스키마를 PlantUML 클래스 도식 꼴로 그림(노드 = 상자, 관계 = 이름 붙은 화살표)."""

    s, keys = d["schema"], d["keys"]
    ids = {n["label"]: f"N{i}" for i, n in enumerate(s["node_types"])}
    lines = ["@startuml graph_schema", "hide empty methods", "hide circle", "skinparam classAttributeIconSize 0",
             "skinparam class {", "  BackgroundColor #EEF3FA", "  BorderColor #1E2A5C", "}", "left to right direction", ""]
    for n in s["node_types"]:
        lines.append(f'class ":{n["label"]}" as {ids[n["label"]]} <<노드>> {{')
        for p in n["properties"]:
            lines.append(f"  {p['name']} : {p['type']}{' <<키>>' if p['name'] in keys[n['label']] else ''}")
        lines.append("}")
    lines.append("")
    for a, r, b in s["patterns"]:
        lines.append(f"{ids[a]} --> {ids[b]} : {r}")
    lines.append("@enduml")
    return "\n".join(lines) + "\n"


def main() -> None:
    d = build()
    OUT.mkdir(exist_ok=True)
    (OUT / "schema_draft.json").write_text(json.dumps(d["schema"], ensure_ascii=False, indent=2), encoding="utf-8")
    mmd = mermaid(d)
    (OUT / "schema.mmd").write_text(mmd, encoding="utf-8")
    (OUT / "schema.puml").write_text(plantuml(d), encoding="utf-8")
    page = ("<!doctype html><html><head><meta charset='utf-8'><title>graph schema</title>"
            "<script src='https://cdn.jsdelivr.net/npm/mermaid@11.4.1/dist/mermaid.min.js'></script>"
            "<style>body{background:#fff;font-family:sans-serif;margin:16px}</style></head><body>"
            f"<pre class='mermaid'>{html.escape(mmd)}</pre><div id='status'></div><script>"
            "mermaid.initialize({startOnLoad:false, flowchart:{htmlLabels:true}});"
            "mermaid.run().then(()=>{document.getElementById('status').textContent='RENDER_OK'})"
            ".catch(e=>{document.getElementById('status').textContent='RENDER_FAIL '+e});</script></body></html>")
    (OUT / "schema_preview.html").write_text(page, encoding="utf-8")
    s = d["schema"]
    print(f"노드 타입 {len(s['node_types'])}개, 관계 {len(s['relationship_types'])}개, 패턴 {len(s['patterns'])}개, "
          f"제약 {len(s['constraints'])}개 — GraphSchema 검증 통과")
    for t, k in d["kinds"].items():
        print(f"  {t}: {k}")


if __name__ == "__main__":
    main()
