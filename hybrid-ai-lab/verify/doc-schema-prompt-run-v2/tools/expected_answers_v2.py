"""7단계(v2): 시험용 표본마다 역량 질문별 기대 답 초안 → {doc}/expected_answers.json.

- 문서 하나 범위: 기존 정답표가 있으면 그 칸을 쓰고(상담 C1 ~ C5), 없으면 LLM이 원문 문장을 그대로 옮겨 초안을 씀
- 여러 문서 종류 범위와 전체 모음 범위(X1, X2, A1, A2): 단위 하나로 답이 나오지 않으므로, 그 단위가 이어져야 할
  공통 노드의 대표 이름을 기대 답으로 씀. 약관 조항의 주제는 5단계에서 승인한 주제 목록 표로 정하고(LLM 안 씀),
  나머지는 LLM이 목록에서 고르거나 원문 이름을 옮김
- 5단계 결정으로 엔티티 추출에서 빼는 청크(혜택 안내의 설계 참고 출처)는 시험용에서 뺌
실행: python tools/expected_answers_v2.py [문서종류 ...]
"""

from __future__ import annotations

import asyncio
import json
import sys

from common import decisions, load_json, load_units, make_llm, save_json
from expected_answers import from_answer_table

CROSS_HINT = {
    ("regulation", "X1"): None,  # 주제 목록 표로 정함
    ("benefit_guide", "X1"): "이 혜택이 적용되는 업종이나 결제 대상 이름(예: 장보기, 편의점, 간편결제)과 혜택 받는 방식"
                             "(자동 적용, 신청 필요, 알 수 없음 중 하나). 꼴: '업종: 이름1, 이름2 / 방식: 자동 적용'",
    ("benefit_guide", "X2"): "이 청크가 설명하는 카드 상품의 이름(머리줄 card_name 또는 본문의 카드 이름)",
    ("consult_log", "X1"): "고객이 말한 불만의 주제(주제 목록에서 1 ~ 2개)와, 불만이나 제안에서 말한 업종이나 결제 대상 이름. "
                           "꼴: '주제: 이름1 / 업종: 이름1'. 불만이 없으면 '없음'",
    ("consult_log", "X2"): "상담에서 이름이 나온 한빛 카드 상품 이름(예: 한빛 모아생활). 없으면 '없음'",
    ("consult_log", "A1"): "고객이 말한 불만의 주제(주제 목록에서 1 ~ 2개). 불만이 없으면 '없음'",
    ("consult_log", "A2"): "상담사 제안마다 고객 결정(수용, 거절, 보류)과 제안 성격(제안 성격 목록에서 1 ~ 3개). "
                           "꼴: '수용: 성격1, 성격2 / 거절: 성격1'. 제안이 없으면 '없음'",
}


def excluded(unit: dict) -> bool:
    md = unit["metadata"] if isinstance(unit["metadata"], dict) else {}
    return "참고 카드:" in (md.get("section_label") or "")


async def draft(llm, doc: str, text: str, qs: list[dict], shared: dict) -> dict:
    topics = ", ".join(t["name"] for t in shared["shared_node_types"]["Topic"]["vocabulary"])
    traits = ", ".join(shared["proposal_traits"])
    lines = []
    for q in qs:
        hint = CROSS_HINT.get((doc, q["id"]))
        lines.append(f"{q['id']}: {q['question']}" + (f"\n  → 이 질문은 이 청크에서 다음만 답함: {hint}" if hint else ""))
    prompt = ("아래 문서 청크만 보고 질문마다 기대 답을 쓰세요. 규칙: 문서 하나 범위 질문의 답은 청크의 원문 문장이나 표 칸을 "
              "그대로 옮김(요약하거나 바꿔 쓰지 않음). 답이 여럿이면 대표적인 것 1 ~ 3개를 ' / '로 이음. '→' 안내가 붙은 질문은 "
              "그 안내대로만 답함. 주제는 주제 목록, 제안 성격은 제안 성격 목록의 글자만 씀. 청크에 답이 없으면 \"없음\". "
              "location에는 원문 위치를 씀. JSON으로만 답함: {\"<질문 id>\": {\"answer\": \"...\", \"location\": \"...\"}}\n\n"
              f"<topics>\n{topics}\n</topics>\n<proposal_traits>\n{traits}\n</proposal_traits>\n\n<questions>\n"
              + "\n".join(lines) + f"\n</questions>\n\n<chunk>\n{text}\n</chunk>")
    res = await llm.ainvoke(prompt)
    d = json.loads(res.content)
    return {q["id"]: {**d.get(q["id"], {"answer": "없음", "location": ""}), "source": "LLM 초안"} for q in qs}


def clause_topics(unit: dict, shared: dict) -> str:
    no = unit["id"].split(":", 1)[1]
    names = [t["name"] for t in shared["shared_node_types"]["Topic"]["vocabulary"] if no in t["clauses"]]
    return ", ".join(names) if names else "없음"


def align_consult(out: dict) -> list[dict]:
    """상담 X1, A1의 불만 주제를 정답표의 불만(C1)에 맞춤. LLM은 불만이 없는 상담에도 주제를 적는 일이 잦았음(2회 실측).

    C1이 "없음"이면 A1은 "없음", X1의 주제 부분은 "없음"(업종이 있으면 업종은 남김). C1이 있는데 A1이 "없음"이면
    고치지 않고 목록에 남겨 사람이 정하게 함.
    """

    fixes = []
    for cid, a in out.items():
        if a["C1"]["answer"] != "없음":
            if a["A1"]["answer"] == "없음":
                fixes.append({"chunk_id": cid, "q": "A1", "before": "없음", "after": "(사람 확인 필요)"})
            continue
        if a["A1"]["answer"] != "없음":
            fixes.append({"chunk_id": cid, "q": "A1", "before": a["A1"]["answer"], "after": "없음"})
            a["A1"] = {"answer": "없음", "location": "", "source": "AI가 C1과 맞춤(불만 없음)"}
        x = a["X1"]["answer"]
        if x != "없음" and "주제:" in x:
            up = x.split("/", 1)[1].strip() if "/" in x else "업종: 없음"
            new = "없음" if up.replace(" ", "") in ("업종:없음", "") else "주제: 없음 / " + up
            if new != x:
                fixes.append({"chunk_id": cid, "q": "X1", "before": x, "after": new})
                a["X1"] = {"answer": new, "location": a["X1"].get("location", ""), "source": "AI가 C1과 맞춤(불만 없음)"}
    return fixes


async def main() -> None:
    plan = load_json("sample_plan.json")
    shared = load_json("shared_concepts.json")
    units = {c["id"]: c for c in load_units()}
    llm = make_llm()
    summary = {}
    for doc in sys.argv[1:] or decisions()["input"]["doc_types"]:
        qs = load_json("competency_questions.json")[doc]
        test_ids = [cid for g in plan["docs"][doc]["groups"].values() for cid in g["test"]]
        dropped = [cid for cid in test_ids if excluded(units[cid])]
        test_ids = [cid for cid in test_ids if cid not in dropped]
        table = from_answer_table(doc, test_ids, units)  # 정답표가 있는 질문(상담 C1 ~ C5)
        fields = load_json(f"{doc}/schema_spec.json").get("metadata_header", [])
        out = {}
        for cid in test_ids:
            u = units[cid]
            md = u["metadata"] if isinstance(u["metadata"], dict) else {}
            head = " | ".join(f"{f}: {md[f]}" for f in fields if md.get(f) not in (None, ""))
            have = table.get(cid, {})
            missing = [q for q in qs if q["id"] not in have and (doc, q["id"]) != ("regulation", "X1")]
            ans = dict(have)
            if missing:
                ans.update(await draft(llm, doc, (head + "\n" if head else "") + u["text"], missing, shared))
            if doc == "regulation":
                ans["X1"] = {"answer": clause_topics(u, shared), "location": "5단계 주제 목록 표", "source": "주제 목록 표"}
            out[cid] = {q["id"]: ans[q["id"]] for q in qs}
            print(f"[{doc}] {cid}", flush=True)
        fixes = align_consult(out) if doc == "consult_log" else []
        save_json(f"{doc}/expected_answers.json", {"doc": doc, "dropped_excluded": dropped, "answers": out,
                                                   "consistency_fixes": fixes})
        has = {q["id"]: sum(1 for a in out.values() if a[q["id"]]["answer"] != "없음") for q in qs}
        summary[doc] = {"test": len(out), "dropped_excluded": len(dropped), "has_answer": has}
        print(f"[{doc}] 시험용 {len(out)}건(뺀 것 {len(dropped)}), 질문별 답 있음 {has}", flush=True)
    save_json("output/expected_summary.json", {"summary": summary, "llm_usage": dict(llm.usage)})


if __name__ == "__main__":
    asyncio.run(main())
