"""apoc.model.jdbc 결과(테이블, 열, PK, FK 표시)와 pg_constraint FK 제약을 합쳐 원본 RDB 구조를 Mermaid와 PlantUML로 그림.

왜 두 형식인가: 사용자가 비교를 요청함(2026-10-14). 변환 규칙을 적용하기 전 'RDB 구조 그대로'이며, 그래프 스키마 그림은 다음 단계에서 만듦.
입력: output/apoc_model.json, output/fk_constraints.json
출력: output/raw_structure.mmd(Mermaid erDiagram), output/raw_structure.puml(PlantUML), output/structure_input.json(다음 단계 입력)
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "output"


def load_tables() -> dict[str, list[dict]]:
    """테이블 이름 → 열 목록(이름, 형, PK, FK 표시). apoc.model.jdbc의 IN_TABLE 관계로 열을 테이블에 붙임."""

    model = json.loads((OUT / "apoc_model.json").read_text(encoding="utf-8"))
    nodes = {n["id"]: n for n in model["nodes"]}
    tables: dict[str, list[dict]] = {n["properties"]["name"]: [] for n in model["nodes"] if "Table" in n["labels"]}
    for rel in model["relationships"]:
        if rel["type"] != "IN_TABLE":
            continue
        col, table = nodes[rel["start"]], nodes[rel["end"]]
        tables[table["properties"]["name"]].append({
            "name": col["properties"]["name"], "type": col["properties"].get("type", ""),
            "pk": "PrimaryKey" in col["labels"], "fk": "ForeignKey" in col["labels"],
        })
    for cols in tables.values():
        cols.sort(key=lambda c: (not c["pk"], not c["fk"], c["name"]))
    return dict(sorted(tables.items()))


def load_fks() -> list[dict]:
    return json.loads((OUT / "fk_constraints.json").read_text(encoding="utf-8"))["foreign_keys"]


def mermaid(tables: dict[str, list[dict]], fks: list[dict]) -> str:
    """Mermaid erDiagram. 관계 표시 }o--|| = '여러 행이 한 행을 가리킴'(FK 쪽이 많음)."""

    lines = ["erDiagram"]
    for table, cols in tables.items():
        lines.append(f"    {table} {{")
        for c in cols:
            keys = ",".join(k for k, on in (("PK", c["pk"]), ("FK", c["fk"])) if on)
            lines.append(f"        {c['type'].replace(' ', '_') or 'text'} {c['name']}{(' ' + keys) if keys else ''}")
        lines.append("    }")
    for fk in fks:
        cols = ", ".join(c["column"] for c in fk["columns"])
        lines.append(f'    {fk["table_name"]} }}o--|| {fk["ref_table"]} : "{cols}"')
    return "\n".join(lines) + "\n"


def plantuml(tables: dict[str, list[dict]], fks: list[dict]) -> str:
    """PlantUML 엔터티 도식. 같은 관계 표기(}o--||)를 써서 Mermaid와 나란히 비교할 수 있게 함."""

    lines = ["@startuml raw_structure", "hide circle", "skinparam linetype ortho", ""]
    for table, cols in tables.items():
        lines.append(f"entity {table} {{")
        for c in [c for c in cols if c["pk"]]:
            lines.append(f"  * {c['name']} : {c['type']} <<PK{',FK' if c['fk'] else ''}>>")
        lines.append("  --")
        for c in [c for c in cols if not c["pk"]]:
            lines.append(f"  {c['name']} : {c['type']}{' <<FK>>' if c['fk'] else ''}")
        lines.append("}")
        lines.append("")
    for fk in fks:
        cols = ", ".join(c["column"] for c in fk["columns"])
        lines.append(f'{fk["table_name"]} }}o--|| {fk["ref_table"]} : "{cols}"')
    lines.append("@enduml")
    return "\n".join(lines) + "\n"


def main() -> None:
    tables, fks = load_tables(), load_fks()
    (OUT / "raw_structure.mmd").write_text(mermaid(tables, fks), encoding="utf-8")
    (OUT / "raw_structure.puml").write_text(plantuml(tables, fks), encoding="utf-8")
    # 다음 단계(프롬프트) 입력: 테이블마다 열과 FK '제약' 목록을 함께 담아 규칙의 FK 개수를 제약 수로 셀 수 있게 함
    structure = {"tables": {t: {"columns": cols, "foreign_keys": [fk for fk in fks if fk["table_name"] == t]}
                            for t, cols in tables.items()}}
    (OUT / "structure_input.json").write_text(json.dumps(structure, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"테이블 {len(tables)}개, FK 제약 {len(fks)}개")
    for t, v in structure["tables"].items():
        print(f"  {t}: 열 {len(v['columns'])}개, FK 제약 {len(v['foreign_keys'])}개")
    print("저장: raw_structure.mmd, raw_structure.puml, structure_input.json")


if __name__ == "__main__":
    main()
