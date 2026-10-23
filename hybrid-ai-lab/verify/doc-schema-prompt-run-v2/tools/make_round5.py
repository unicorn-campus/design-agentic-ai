"""5라운드 준비(마지막 반복, 8단계 4라운드 결과).

기대 답(나5)
- 약관 제30조 R2: "정지 원인이 해소되고 ~ 끝나면 재개할 수 있습니다"는 4라운드 설명(다8)대로 상황별 처리(R4)이지 충족 조건이 아님 → "없음"
- 상담 C-20260507-035 X1, A1: 불만 "주문 앱만 할인에서 빠지는 게 불만"의 원인 대상은 부가서비스뿐이라 "민원과 이의 처리"를 뺌
설명
- 다11 상담 ABOUT과 Complaint: 불만 노드마다 빠짐없이 주제 1 ~ 2개를 ABOUT으로 이음
- 다12 ReconsiderCondition과 RECONSIDER_WHEN: 관계 설명이 "보류된 제안"에만 붙는다고 해 노드 설명(거절한 제안에도 붙임)과 어긋났음.
  결정(수용, 거절, 보류)과 상관없이 '다시 ~할게요', '그때 ~할게요'를 뽑게 하고 놓친 예를 넣음
4라운드 명세와 기대 답은 *.r4.json으로 남김.
"""

from __future__ import annotations

import shutil

from common import BASE, load_json, load_units, save_json

RECONSIDER = ("해당: 고객이 나중에 다시 생각하거나 행동하겠다며 말한 조건. 제안의 결정(수용, 거절, 보류)과 상관없이, 고객이 '~하면 다시 생각할게요', "
              "'~면 그때 ~할게요', '~나오면 다시 볼게요', '그래도 ~하면 다음에 문의할게요'처럼 말하면 모두 해당(예: 다음 명세서를 보고 다시 "
              "판단할게요, 그래도 안 맞으면 다음 명세서 나올 때 다시 문의할게요, 연결된 결제 확인이 끝나면 그때 신청할게요). 그 말이 붙은 제안에 "
              "RECONSIDER_WHEN으로 붙임. 비해당: 수용하거나 거절한 이유 자체(reason에 씀), 상담사의 안내나 질문")


def main() -> None:
    for doc in ("regulation", "benefit_guide", "consult_log"):
        for name in ("schema_spec.json", "expected_answers.json"):
            src, bak = BASE / doc / name, BASE / doc / name.replace(".json", ".r4.json")
            if not bak.exists():
                shutil.copy(src, bak)
    units = {u["id"]: u for u in load_units()}
    changes = []
    e = load_json("regulation/expected_answers.r4.json")
    for cid, a in e["answers"].items():
        if cid.endswith(":제30조"):
            changes.append({"doc": "regulation", "chunk_id": cid, "q": "R2", "before": a["R2"]["answer"], "after": "없음"})
            a["R2"] = {"answer": "없음", "location": "", "source": "5라운드 고침(다8 기준으로 상황별 처리)"}
    save_json("regulation/expected_answers.json", e)
    e = load_json("consult_log/expected_answers.r4.json")
    for cid, a in e["answers"].items():
        if units[cid]["metadata"]["record_id"] == "C-20260507-035":
            for q, new in (("X1", "주제: 부가서비스와 포인트 / 업종: 간편결제"), ("A1", "부가서비스와 포인트")):
                changes.append({"doc": "consult_log", "chunk_id": cid, "q": q, "before": a[q]["answer"], "after": new})
                a[q] = {"answer": new, "location": "정답표 complaint_cause", "source": "5라운드 고침(불만 원인 대상만)"}
    save_json("consult_log/expected_answers.json", e)
    save_json("benefit_guide/expected_answers.json", load_json("benefit_guide/expected_answers.r4.json"))
    for doc in ("regulation", "benefit_guide", "consult_log"):
        s = load_json(f"{doc}/schema_spec.r4.json")
        if doc == "consult_log":
            for n in s["node_types"]:
                if n["label"] == "ReconsiderCondition":
                    n["description"] = RECONSIDER
                elif n["label"] == "Complaint":
                    n["description"] += ". 불만 노드마다 빠짐없이 그 원인이 된 주제 1 ~ 2개를 ABOUT으로 이음"
            for r in s["relationship_types"]:
                if r["label"] == "RECONSIDER_WHEN":
                    r["description"] = "제안(수용, 거절, 보류 모두)에 고객이 덧붙인 다시 생각하거나 나중에 행동할 조건"
                elif r["label"] == "ABOUT":
                    r["description"] = "불만이 다루는 주제. 불만 노드마다 빠짐없이 주제 1 ~ 2개를 이음"
        s["recommend"].append({"kind": "5라운드 고침", "item": "다11 Complaint와 ABOUT, 다12 ReconsiderCondition과 RECONSIDER_WHEN", "cq": ["C4", "X1", "A1"]})
        save_json(f"{doc}/schema_spec.json", s)
    save_json("output/round5_changes.json", {"expected_changes": changes})
    print("기대 답 고침", len(changes), "| 5라운드 명세 저장")


if __name__ == "__main__":
    main()
