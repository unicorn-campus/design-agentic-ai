"""3라운드 설명 고침(다6, 다7). 2라운드 명세는 {doc}/schema_spec.r2.json으로 남김.

- 다6 Product: 상담에서 이름이 나온 카드는 마무리 발화(기록에 남긴다는 말)에 나와도 해당
- 다7 Complaint: 2라운드에서 틀린 예를 비해당에 그대로 넣고, 사용자 결정(정답표 따름)대로 '번거롭다'만 있는 말도 비해당
실행: python tools/make_specs_r3.py → build_schema.py {doc}, check_shared.py
"""

from __future__ import annotations

import shutil

from common import BASE, load_json, save_json

PRODUCT = ("해당: 한빛 카드 상품 하나. 정형 스키마의 Product를 가리키는 참조 노드. 상담에서는 상담사나 고객이 '한빛 ○○ 카드'처럼 이름을 "
           "말한 카드가 모두 해당하며, 상담을 마무리하며 '한빛 ○○ 카드 상담으로 기록하겠습니다'처럼 기록에 남긴다고 말한 카드도 해당함"
           "(이때 Consultation -MENTIONS_PRODUCT-> Product로 이음). 비해당: 실제 카드사 상품, 개별 혜택, 연회비와 가족카드 규칙"
           "(정형 데이터에 있음), '이 카드', '타사 카드'처럼 이름이 없는 말")
COMPLAINT = ("해당: 고객이 이미 겪은 일에 대해 불편하다, 불만이다, 답답하다, 부담이다, 지쳤다처럼 감정을 드러내며 직접 말한 원인. "
             "고객 말에 이런 감정 표현이 있을 때만 해당. 비해당: 감정 표현 없는 사정 설명(예: 종이 영수증은 이미 버렸어요, "
             "통화 가능한 시간을 정하기 어려워요), 할 수 없다거나 안 하겠다는 말(예: 영수증은 못 맞춰요), '번거롭다'는 말만 있고 불만이라고 "
             "하지 않은 경우(예: 종이 영수증은 이미 버려서 설명하기 번거로워요), 앞으로의 걱정(예: 옛집으로 간 우편이 먼저 걱정돼서요, "
             "불편한 고객으로 보일까 봐), 확인 요청이나 단순 질문, 사실을 말한 것(예: 취소한 결제도 보이네요), 무엇을 해 달라거나 하지 말아 "
             "달라는 부탁, 선호 표현, 상담사의 추측, 고객이 만족한다고 한 점")


def main() -> None:
    for doc in ("regulation", "benefit_guide", "consult_log"):
        src, bak = BASE / doc / "schema_spec.json", BASE / doc / "schema_spec.r2.json"
        if not bak.exists():
            shutil.copy(src, bak)
        s = load_json(f"{doc}/schema_spec.r2.json")
        for n in s["node_types"]:
            if n["label"] == "Product":
                n["description"] = PRODUCT
            elif n["label"] == "Complaint":
                n["description"] = COMPLAINT
        s["recommend"].append({"kind": "3라운드 고침", "item": "다6 Product, 다7 Complaint(8단계 2라운드 결과)", "cq": ["X2", "C1"]})
        save_json(f"{doc}/schema_spec.json", s)
    print("3라운드 명세 저장")


if __name__ == "__main__":
    main()
