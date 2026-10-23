"""4라운드 준비(8단계 3라운드 결과, 사용자 결정: 모두 통과하거나 5라운드까지 계속).

기대 답(나4): 3라운드에서 찾은 기대 답 오류 4건을 원문으로 고침
- 혜택 X1 3건: 원문에 대상 업종이 있는데 "없음"이던 청크(D2-C043 대상 영역, D2-C030 통신요금 할인, D2-C007-B03 생활 업종 할인)
- 상담 A2 1건: C-20260501-003은 종이 영수증 제안을 거절한 상담이라 답이 있음
설명(다8 ~ 다10)
- 다8 Requirement: 상황과 처리를 정한 문장(Handling)과 일반 의무는 비해당임을 예와 함께 적음
- 다9 Deadline: 속성에는 시점이 든 문장 전체를 씀(시점 낱말 조각만 쓰지 않음). 시점 낱말이 든 문장은 모두 뽑음
- 다10 MerchantCategory, APPLIES_TO: 청크에 대상, 대상·채널, 대상 영역이 적힌 혜택에만 이음. 한도나 이용 기준만 있는 청크는 잇지 않음
설계(라4): 목록에서만 고르는 노드(Topic, MerchantCategory, ProposalTrait)의 이름이 목록에 없으면 코드가 그 노드와 관계를 지움
(fill_test_v2.py의 vocab_filter. 인덱싱도 같은 규칙을 써야 함)
3라운드 명세와 기대 답은 *.r3.json으로 남김.
"""

from __future__ import annotations

import re
import shutil

from common import BASE, load_json, load_units, save_json
from revise_expected_r2 import apply_method_by_rule

X1_FIX = {
    "3628fa639d6036c8": "업종: 장보기와 마트, 커피와 제과, 대중교통과 택시, 음식점과 배달, 교육, 온라인쇼핑",
    "4ec1975240ee01b1": "업종: 통신",
    "89396f4c91417ef8": "업종: 편의점, 장보기와 마트, 커피와 제과",
}
A2_FIX = {"C-20260501-003": "거절: 고객 할 일 증가"}

REQUIREMENT = ("해당: 무엇을 받거나 할 수 있는지가 갈리는 기준. 보통 숫자(금액, 일수, 횟수, 비율)나 '~이상', '~인 경우에만', "
               "'~을 모두 충족할 때 제공', '~하면 받을 수 있음' 꼴임(예: 직전 12개월 이용금액이 300만 원 이상이면 면제, 전월 이용금액과 "
               "월 한도를 모두 충족할 때 제공). 비해당: 상황을 먼저 말하고 그때의 처리를 정한 문장(Handling에 씀, 예: 계약이 취소된 경우 "
               "지급 보류를 요청할 수 있습니다, 인증 실패가 감지되면 정지할 수 있습니다), 누가 무엇을 한다는 일반 의무나 절차(예: 본인 확인 후 "
               "전달합니다, 회원이 직접 입력합니다, 명세서에 표시합니다, 함께 기록합니다, 절차를 적용합니다), 기한만 정한 문장")
DEADLINE_PROP = ("기한이나 시점이 든 문장 전체(원문 그대로). 시점 낱말 조각만 쓰지 않음(예: '청구 전에'가 아니라 '장기간 이용하지 않은 카드의 "
                 "차기 연회비는 청구 전에 회원에게 안내합니다.')")
DEADLINE_ADD = (" 조항에서 '전에, 이내, 부터, 즉시, 다음 영업일, 후에는, 결제일에, 사전에' 같은 시점 낱말이 든 문장은 하나도 빠뜨리지 말고 "
                "모두 Deadline으로 뽑음")
CATEGORY_ADD = (" 혜택에 잇는 것은 청크에 '대상', '대상·채널', '대상 영역'처럼 적용 대상이 적혀 있을 때만임. 한도, 이용 기준, 통합 한도만 "
                "적힌 청크에서는 업종을 만들지 않음")


def main() -> None:
    docs = ("regulation", "benefit_guide", "consult_log")
    for doc in docs:
        for name in ("schema_spec.json", "expected_answers.json"):
            src, bak = BASE / doc / name, BASE / doc / name.replace(".json", ".r3.json")
            if not bak.exists():
                shutil.copy(src, bak)
    units = {u["id"]: u for u in load_units()}
    changes = []
    # 기대 답
    e = load_json("benefit_guide/expected_answers.r3.json")
    for cid, a in e["answers"].items():
        key = next((k for k in X1_FIX if k in cid), None)
        if key:
            new = X1_FIX[key] + " / 방식: " + apply_method_by_rule(units[cid]["text"])
            changes.append({"doc": "benefit_guide", "chunk_id": cid, "q": "X1", "before": a["X1"]["answer"], "after": new})
            a["X1"] = {"answer": new, "location": "원문 표의 대상 줄", "source": "4라운드 고침(기대 답 오류)"}
    save_json("benefit_guide/expected_answers.json", e)
    e = load_json("consult_log/expected_answers.r3.json")
    for cid, a in e["answers"].items():
        rid = units[cid]["metadata"]["record_id"]
        if rid in A2_FIX:
            changes.append({"doc": "consult_log", "chunk_id": cid, "q": "A2", "before": a["A2"]["answer"], "after": A2_FIX[rid]})
            a["A2"] = {"answer": A2_FIX[rid], "location": "정답표 proposal, proposal_decision", "source": "4라운드 고침(기대 답 오류)"}
    save_json("consult_log/expected_answers.json", e)
    save_json("regulation/expected_answers.json", load_json("regulation/expected_answers.r3.json"))
    # 설명
    for doc in docs:
        s = load_json(f"{doc}/schema_spec.r3.json")
        for n in s["node_types"]:
            if n["label"] == "Requirement":
                n["description"] = REQUIREMENT
            elif n["label"] == "Deadline":
                n["description"] = n["description"].rstrip(".") + "." + DEADLINE_ADD
                for p in n["properties"]:
                    if p["name"] == "description":
                        p["description"] = DEADLINE_PROP
            elif n["label"] == "MerchantCategory":
                n["description"] = re.sub(r"\. 비해당:", "." + CATEGORY_ADD + ". 비해당:", n["description"], count=1)
        for r in s["relationship_types"]:
            if r["label"] == "APPLIES_TO":
                r["description"] = "혜택이 적용되는 업종. 청크에 적용 대상(대상, 대상·채널, 대상 영역)이 적혀 있을 때만 이음. 혜택 하나에 0 ~ 6개"
        s["recommend"].append({"kind": "4라운드 고침", "item": "다8 Requirement, 다9 Deadline, 다10 MerchantCategory와 APPLIES_TO, 라4 목록 밖 이름 지우기",
                               "cq": ["R2", "R3", "X1"]})
        save_json(f"{doc}/schema_spec.json", s)
    sc = load_json("shared_concepts.json")
    sc["vocabulary_enforcement"] = {"labels": ["Topic", "MerchantCategory", "ProposalTrait"],
                                    "rule": "이름(띄어쓰기를 뺀 꼴)이 대표 이름 목록에 없으면 그 노드와 관계를 지움(4라운드 라4)"}
    save_json("shared_concepts.json", sc)
    save_json("output/round4_changes.json", {"expected_changes": changes})
    print("기대 답 고침", len(changes), "| 4라운드 명세 저장")


if __name__ == "__main__":
    main()
