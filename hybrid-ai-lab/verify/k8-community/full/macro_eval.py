"""K8 커뮤니티 요약의 거시 질문(Q23 ~ Q25) 품질을 잼. v0 활성 세대를 읽기만 함.

1) 찾기: 질문 임베딩으로 kg_community_embedding 상위 5개 보고서를 찾고, 정답 요점이 그 보고서들에 있는지 셈
   (같은 요점이 커뮤니티 전체 어딘가에는 있는지도 함께 세어, 찾기 실패와 요약 누락을 가름)
2) 답하기: 상위 5개 보고서만 근거로 LLM(v0와 같은 Groq 모델)이 답을 쓰게 하고(Global Search 방식), 답에 요점이 있는지 셈
요점 판정은 요점마다 정한 낱말이 모두 들어 있는지로 함(자동 판정이라 사람이 답 글을 함께 읽어 확인함).
실행: ../../../indexer/graphrag/v0/.venv/Scripts/python.exe macro_eval.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
V0 = HERE.parents[2] / "indexer" / "graphrag" / "v0"
sys.path.insert(0, str(V0))

import neo4j  # noqa: E402

import config  # noqa: E402
from common import embed, load_json, make_llm  # noqa: E402
from orchestrator import neo4j_password  # noqa: E402

TOP_K = 5

# 정답 요점: (이름, 모두 들어 있어야 하는 낱말 묶음들 중 하나라도 맞으면 있음)
POINTS = {
    "Q23": [
        ("장기보유: 연회비 대비 혜택 부족", [["연회비", "혜택"]]),
        ("연회비부담: 장보기 할인 제외", [["장보기"]]),
        ("신규가입: 앱 인증 반복", [["인증"]]),
        ("VIP: 혜택 신청 반복", [["신청", "반복"], ["신청", "매달"]]),
        ("장기보유: 민원 경과 설명 없음", [["민원"]]),
        ("휴면직전: 광고 알림 중복", [["광고"]]),
        # 「신규」, 「장기」만으로는 「신규 승인」, 「장기 미사용」에도 맞아, 고객군 이름 그대로 찾음
        ("고객군 구분이 드러남", [["신규가입"], ["신규 가입"], ["장기보유"], ["장기 보유"], ["VIP"], ["휴면직전"],
                               ["휴면 직전"], ["다중카드"], ["다중 카드"], ["연회비부담"], ["연회비 부담 고객"]]),
    ],
    "Q24": [
        ("할 일이나 소비가 늘지 않는 제안", [["자동"], ["할 일"], ["번거"]]),
        ("글로 남는 안내", [["이메일"], ["서면"], ["글로"], ["문서"]]),
        ("고객이 원한 방식(앱, 집에서)", [["앱"], ["집에서"]]),
        ("소비를 늘리는 제안은 거절", [["소비"], ["거절"]]),
    ],
    "Q25": [
        ("연회비 불만 → 제9조 또는 제10조", [["제9조"], ["제10조"]]),
        ("혜택 조건 불만 → 제17조", [["제17조"]]),
        ("민원 경과 → 제34조", [["제34조"]]),
        ("알림 중복 → 제5조", [["제5조"]]),
        ("인증 반복 → 제29조", [["제29조"]]),
        ("혜택: 자동맞춤", [["자동맞춤"]]),
        ("혜택: 장보기 직접 결제 또는 간편생활", [["간편생활"], ["직접 결제"]]),
    ],
}

ANSWER_SYSTEM = ("너는 카드사 상담 지원 도우미다. 아래 커뮤니티 보고서만 근거로 질문에 한국어로 답한다. "
                 "보고서에 없는 내용은 지어내지 말고 '보고서에 없음'이라고 쓴다. "
                 'JSON {"answer": "..."} 하나로만 답한다.')


def has_point(text: str, alternatives: list[list[str]]) -> bool:
    return any(all(w in text for w in words) for words in alternatives)


def report_text(c: dict) -> str:
    findings = c.get("findings") or []
    if isinstance(findings, str):
        try:
            findings = json.loads(findings)
        except json.JSONDecodeError:
            findings = [findings]
    parts = [c.get("title") or "", c.get("summary") or ""]
    parts += [f if isinstance(f, str) else json.dumps(f, ensure_ascii=False) for f in findings]
    return "\n".join(parts)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    g = load_json(config.ACTIVE_FILE)["generation"]
    evalset = {q["id"]: q for q in load_json(HERE.parents[2] / "ragas" / "eval-set.json")["questions"]}
    drv = neo4j.GraphDatabase.driver(config.NEO4J_URI, auth=(config.NEO4J_USER, neo4j_password()),
                                     notifications_min_severity="OFF")
    llm = make_llm()
    out = {"generation": g, "top_k": TOP_K, "questions": {}}
    with drv:
        rec, _, _ = drv.execute_query(
            "MATCH (c:Community {generation: $g})<-[:IN_COMMUNITY]-(e) "
            "OPTIONAL MATCH (e)-[:FROM_CHUNK]->(k:Chunk) "
            "WITH c, count(DISTINCT e) AS n, collect(DISTINCT k.doc_type) AS types "
            "RETURN c.community_id AS id, c.title AS title, c.summary AS summary, c.findings AS findings, n, types",
            g=g)
        comms = {r["id"]: dict(r) for r in rec}
        out["communities"] = len(comms)
        out["mixed_doc_type_communities"] = sum(1 for c in comms.values() if len(c["types"]) > 1)
        all_text = "\n".join(report_text(c) for c in comms.values())
        vecs = embed([evalset[q]["question"] for q in POINTS])
        for (q, points), v in zip(POINTS.items(), vecs):
            rec, _, _ = drv.execute_query(
                "CALL db.index.vector.queryNodes('kg_community_embedding', 50, $v) YIELD node, score "
                "WHERE node.generation = $g RETURN node.community_id AS id, score ORDER BY score DESC LIMIT $k",
                v=v, g=g, k=TOP_K)
            top = [(r["id"], round(r["score"], 3)) for r in rec]
            top_text = "\n".join(report_text(comms[i]) for i, _ in top)
            context = "\n\n".join(f"[보고서 {n + 1}] {report_text(comms[i])}" for n, (i, _) in enumerate(top))
            raw = llm.chat_json(f"질문: {evalset[q]['question']}\n\n{context}", system_instruction=ANSWER_SYSTEM)
            try:
                answer = json.loads(raw).get("answer", raw)
            except json.JSONDecodeError:
                answer = raw
            rows = [{"point": name, "in_any_report": has_point(all_text, alts),
                     "in_top_reports": has_point(top_text, alts), "in_answer": has_point(str(answer), alts)}
                    for name, alts in points]
            out["questions"][q] = {
                "question": evalset[q]["question"],
                "top": [{"id": i, "score": s, "title": comms[i]["title"], "doc_types": comms[i]["types"],
                         "members": comms[i]["n"]} for i, s in top],
                "points": rows, "answer": answer,
                "score": {k: sum(r[k] for r in rows) for k in ("in_any_report", "in_top_reports", "in_answer")},
                "of": len(rows)}
    out["llm_usage"] = dict(llm.usage)
    (HERE / "macro_eval.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print("세대", g, "| 커뮤니티", out["communities"], "| 문서 종류가 섞인 묶음", out["mixed_doc_type_communities"])
    for q, r in out["questions"].items():
        print(f"\n== {q} {r['question']}")
        print("  상위:", " / ".join(f"{t['title']}({'+'.join(t['doc_types'])}, {t['score']})" for t in r["top"]))
        print("  요점 (보고서 전체 / 상위 5 / 답):", r["score"], "of", r["of"])
        for p in r["points"]:
            print(f"   - {p['point']}: {int(p['in_any_report'])} {int(p['in_top_reports'])} {int(p['in_answer'])}")
        print("  답:", str(r["answer"])[:600])


if __name__ == "__main__":
    main()
