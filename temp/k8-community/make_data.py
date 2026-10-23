"""K8 장표용 실측값(data.json)을 v0 활성 세대에서 뽑음. 읽기만 함.

- full: build_report.json의 K8 결과(엔티티, 관계, 묶음 수, 큰 묶음 크기, LLM 토큰)와 문서 종류가 섞인 묶음 수
- example: 보고서 예로 쓸 묶음(제목이 EXAMPLE_PREFIX로 시작)의 제목, 요약, 핵심 사실 3개
- prompt_entities, prompt_relations: 같은 묶음의 실제 LLM 입력 글(community._report_prompt) 앞부분
- macro: verify/k8-community/full/macro_eval.json의 질문별 결과
실행: (hybrid-ai-lab/indexer/graphrag/v0/.venv)/python make_data.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
LAB = HERE.parents[1] / "hybrid-ai-lab"
V0 = LAB / "indexer" / "graphrag" / "v0"
sys.path.insert(0, str(V0))

import neo4j  # noqa: E402

import community  # noqa: E402
import config  # noqa: E402
from common import load_json  # noqa: E402
from orchestrator import neo4j_password  # noqa: E402

EXAMPLE_PREFIX = "연회비 대비 가치"
CUT = 58  # 장표 코드 상자 한 줄에 들어가는 글자 수

LABELS = {"Q23": "고객군별 불만 주제", "Q24": "받아들여진 제안의 공통점", "Q25": "불만별 약관 조항과 혜택"}


def short(text: str, cut: int = CUT) -> str:
    return text if len(text) <= cut else text[:cut - 1] + "…"


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    active = load_json(config.ACTIVE_FILE)
    g = active["generation"]
    k8 = load_json(config.GENERATIONS / g / "build_report.json")["kg"]["k8"]
    macro = load_json(LAB / "verify" / "k8-community" / "full" / "macro_eval.json")
    drv = neo4j.GraphDatabase.driver(config.NEO4J_URI, auth=(config.NEO4J_USER, neo4j_password()),
                                     notifications_min_severity="OFF")
    with drv:
        ex = drv.execute_query(
            "MATCH (c:Community {generation: $g}) WHERE c.title STARTS WITH $p "
            "MATCH (e)-[:IN_COMMUNITY]->(c) RETURN c.title AS title, c.summary AS summary, c.findings AS findings, "
            "c.size AS size, collect(elementId(e)) AS members", g=g, p=EXAMPLE_PREFIX).records[0]
        entities, relations = community.read_entity_graph(drv, g)
        index = {e["id"]: i for i, e in enumerate(entities)}
        prompt, _ = community._report_prompt(entities, sorted(index[m] for m in ex["members"]), relations)
    body = prompt.split("엔티티:\n", 1)[1]
    ent_part, rel_part = body.split("\n\n관계:\n", 1)
    data = {
        "generation": g,
        "full": {"entities": k8["entities"], "relations": k8["relations"], "groups": k8["groups"],
                 "summarized": k8["summarized"], "size_top": k8["group_sizes"][:3],
                 "tokens": k8.get("llm_usage", {}).get("total_tokens"), "mixed": macro["mixed_doc_type_communities"]},
        "example": {"title": ex["title"], "summary": ex["summary"], "size": ex["size"],
                    # 근거 목록이 길어 장표에는 근거 엔티티를 앞 두 개만 보임
                    "findings": [f.split(" [근거: ")[0] + " [근거: " + ", ".join(
                        f.split(" [근거: ")[1].rstrip("]").split(", ")[:2]) + " …]" if " [근거: " in f else f
                                 for f in ex["findings"][:3]]},
        "prompt_entities": [short(x) for x in ent_part.splitlines()[:2]],
        "prompt_relations": [short(x) for x in rel_part.splitlines()[:1]],
        "macro": {q: {"label": LABELS[q], "question": r["question"], "top": r["top"], "score": r["score"], "of": r["of"]}
                  for q, r in macro["questions"].items()},
    }
    out = HERE / "data.json"
    old = json.loads(out.read_text(encoding="utf-8")) if out.exists() else {}
    data["finding"] = old.get("finding", "")  # 결과 해석 문장은 사람이 읽고 씀(덮어쓰지 않음)
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: data[k] for k in ("full", "prompt_entities", "prompt_relations")}, ensure_ascii=False, indent=1))
    print(json.dumps(data["example"], ensure_ascii=False, indent=1)[:1500])


if __name__ == "__main__":
    main()
