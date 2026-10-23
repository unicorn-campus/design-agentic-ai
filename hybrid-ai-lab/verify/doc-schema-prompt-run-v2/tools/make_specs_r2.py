"""2라운드 스키마 고침(8단계 1라운드 결과, 사용자 승인한 고칠 안 다1 ~ 다5, 라1 ~ 라3).

1라운드 명세는 {doc}/schema_spec.r1.json, shared_concepts.r1.json으로 남기고 그 위에 고침.
- 다1 Deadline: 미리 알리는 시점 예를 원문 꼴로 더하고, 시점 없는 '알립니다'는 비해당으로 둠
- 다2 Complaint: 감정 표현이 있을 때만 해당. 사정 설명, 할 수 없다는 말, 확인 요청은 비해당
- 다3 Topic: 불만의 원인 대상으로 고르고 상담 장면으로 고르지 않음. 주제마다 한 줄 뜻
- 다4 ProposalTrait: 성격마다 뜻과 예
- 다5 Benefit.apply_method: 신청, 등록, 응모 문구가 없으면 자동 적용
- 라1 MerchantCategory: 대표 이름 목록 18개에서만 고름
- 라2 FOLLOWS: 코드가 메타데이터(같은 가명 회원, 상담일 순)로 채움. LLM 추출에서 뺌
- 라3 혜택 안내의 표지와 카드 목록(절 제목 없음) 청크도 엔티티 추출에서 뺌
실행: python tools/make_specs_r2.py → 이어서 build_schema.py {doc}, check_shared.py
"""

from __future__ import annotations

import json
import shutil

from common import BASE, load_json, save_json

TOPIC_MEANING = {
    "연회비": "연회비를 매기고 면제하거나 돌려주는 일",
    "부가서비스와 포인트": "할인, 적립, 캐시백 같은 부가서비스와 포인트를 받는 조건, 신청, 적용 대상",
    "본인 인증과 보안": "본인 확인, 인증 절차, 비밀번호, 카드와 인증수단 보관",
    "통지와 광고": "카드사가 회원에게 알리는 방법과 광고, 판촉 알림",
    "민원과 이의 처리": "민원, 이의신청, 다툼의 접수와 처리 경과 설명",
    "명세서와 결제": "이용대금 명세서, 결제일과 출금, 납부, 취소와 환불의 반영",
    "할부": "할부 거래와 그 철회, 항변",
    "분실과 부정 사용": "분실, 도난, 의심 문자, 본인이 하지 않은 거래",
    "이용정지와 휴면": "카드 이용정지와 해제, 오래 쓰지 않은 카드",
    "해지": "회원이나 카드사의 계약 해지, 다른 카드사로 옮기기",
    "발급과 카드 관리": "카드 발급, 가족카드, 전달, 갱신, 여러 장 보유 정리",
    "개인정보와 회원 정보": "개인정보 처리, 주소나 연락처 같은 회원 정보 변경",
    "해외 이용": "해외 결제와 해외 이용 수수료, 원화결제",
    "카드대출과 금리": "카드대출, 연체, 금리",
    "이용한도와 승인": "이용한도, 승인과 취소의 원칙",
}

CATEGORIES = [
    ("일반 가맹점", "업종을 가리지 않는 국내 일반 가맹점 전체"),
    ("해외 결제", "해외 가맹점 결제와 해외 원화 환산 매입"),
    ("장보기와 마트", "마트, 장보기, 식료품과 생활용품 구매(매장이든 앱 주문이든)"),
    ("편의점", "편의점"),
    ("커피와 제과", "커피점, 제과점"),
    ("음식점과 배달", "음식점, 배달앱 식사 주문"),
    ("온라인쇼핑", "쇼핑몰, 생활소품몰, 반려생활몰 같은 온라인 구매"),
    ("간편결제", "간편결제 서비스와 결제 앱을 거친 결제"),
    ("대중교통과 택시", "버스, 도시철도, 택시, 철도 승차권"),
    ("주유와 충전", "주유, 전기차 충전, 수소 충전"),
    ("자동차 관리와 주차", "정비, 세차, 주차요금"),
    ("통신", "이동통신, 통신요금"),
    ("정기결제와 구독", "영상, 음악 같은 구독과 생활요금, 관리비, 렌탈, 멤버십의 월 정기결제"),
    ("문화와 여가", "영화, 공연, 놀이공원, 운동시설, 취미 수강권"),
    ("여행과 숙박", "공항 라운지, 숙박, 리조트 예약"),
    ("교육", "학원, 온라인 강의 수강료"),
    ("의료와 돌봄", "병원, 약국, 동물병원, 돌봄 서비스"),
    ("사업경비", "사무용품, 택배 같은 사업 운영 경비"),
]

TRAITS = [
    ("소비 증가 필요", "제안대로 하려면 고객이 돈을 더 쓰거나 실적을 채워야 함(예: 면제 조건을 맞추려 사용액을 늘림)"),
    ("고객 할 일 증가", "고객이 새로 신청, 방문, 서류 준비, 설정 같은 일을 해야 함"),
    ("고객 할 일 없음", "고객이 따로 할 일 없이 자동으로 적용되거나 상담사가 대신 처리함"),
    ("글로 남는 안내", "이메일, 문자, 서면, 앱 화면 정리처럼 나중에 다시 볼 수 있게 글로 보냄"),
    ("말로만 안내", "전화나 대화로만 설명하고 글로 남기지 않음"),
    ("고객이 요청한 방식", "고객이 원한다고 말한 채널이나 방식(예: 앱에서 직접, 오전 전화, 집에서)에 맞춤"),
]


def topic_desc() -> str:
    vocab = "; ".join(f"{k}: {v}" for k, v in TOPIC_MEANING.items())
    return ("해당: 조항이나 불만이 다루는 업무 주제 하나. 이름은 아래 대표 이름 목록에서만 고름(각 이름 뒤는 뜻). "
            "불만에 붙일 때는 불만의 원인이 된 대상으로 고르고, 상담이 일어난 장면(명세서를 보며 통화, 앱 화면 확인 등)으로 고르지 않음"
            "(예: 혜택 조건이 불만이면 명세서를 보며 말했어도 '부가서비스와 포인트'). 목록: " + vocab
            + ". 비해당: 목록에 없는 이름, 카드 이름, 혜택 이름, 업종 이름")


def category_desc() -> str:
    vocab = "; ".join(f"{k}: {v}" for k, v in CATEGORIES)
    return ("해당: 혜택이 적용되거나 고객이 말한 결제 대상 업종 하나. 이름은 아래 대표 이름 목록에서만 고름(각 이름 뒤는 뜻). "
            "가맹점 한 곳의 이름(예: 가상 편의점 하루상점)은 그 가맹점이 속한 업종 이름으로 바꿔 씀. 목록: " + vocab
            + ". 비해당: 목록에 없는 이름, 가맹점 이름 그대로, 매장이나 우편처럼 결제 대상이 아닌 장소나 수단")


def trait_desc() -> str:
    vocab = "; ".join(f"{k}: {v}" for k, v in TRAITS)
    return ("해당: 제안이 고객에게 요구하거나 주는 성격 하나. 이름은 아래 목록에서만 고름(각 이름 뒤는 뜻). 제안 하나에 맞는 것을 "
            "1 ~ 3개 고름. 목록: " + vocab + ". 비해당: 제안 내용 문장, 고객의 결정(수용, 거절, 보류)")


def main() -> None:
    for doc in ("regulation", "benefit_guide", "consult_log"):
        src, bak = BASE / doc / "schema_spec.json", BASE / doc / "schema_spec.r1.json"
        if not bak.exists():
            shutil.copy(src, bak)
    if not (BASE / "shared_concepts.r1.json").exists():
        shutil.copy(BASE / "shared_concepts.json", BASE / "shared_concepts.r1.json")
    specs = {d: load_json(f"{d}/schema_spec.r1.json") for d in ("regulation", "benefit_guide", "consult_log")}
    for doc, s in specs.items():
        for n in s["node_types"]:
            if n["label"] == "Topic":
                n["description"] = topic_desc()
            elif n["label"] == "MerchantCategory":
                n["description"] = category_desc()
                n["properties"] = [{"name": "name", "type": "STRING", "description": "업종 대표 이름. 목록의 글자를 그대로 씀"}]
            elif n["label"] == "ProposalTrait":
                n["description"] = trait_desc()
            elif n["label"] == "Deadline":
                n["description"] = (
                    "해당: 무엇을 해야 하는 기한이나 시점(예: ~일 이내, 즉시, 다음 영업일, ~까지, ~한 시점부터, 1년 단위로), "
                    "미리 알리는 시점(예: 사전에 안내, 청구 전에 안내, ~일 전에 알림, 종료일 30일 전부터). 상황 조건이 붙은 문장이어도 "
                    "시점이 있으면 해당하며 같은 문장을 Handling에도 둘 수 있음. 비해당: 시점 없이 '알립니다', '안내합니다'만 있는 문장"
                    "(예: 처리 결과를 알립니다), 처리 방법, 금액 조건. 조항에 기한이나 시점이 여러 개 있으면 시점마다 Deadline 노드를 하나씩 "
                    "만들고 SETS_DEADLINE으로 조항에 이음")
            elif n["label"] == "Complaint":
                n["description"] = (
                    "해당: 고객이 이미 겪은 일에 대해 불편하다, 불만이다, 답답하다, 부담이다, 지쳤다처럼 감정을 드러내며 직접 말한 원인. "
                    "고객 말에 이런 감정 표현이 있을 때만 해당. 비해당: 감정 표현 없는 사정 설명(예: 종이 영수증은 이미 버렸어요, "
                    "시간이 없어요), 할 수 없다거나 안 하겠다는 말(예: 영수증은 못 맞춰요), 확인 요청이나 단순 질문, 사실을 말한 것"
                    "(예: 취소한 결제도 보이네요), 무엇을 해 달라거나 하지 말아 달라는 부탁, 선호 표현, 앞으로의 걱정, 상담사의 추측, "
                    "고객이 만족한다고 한 점")
            elif n["label"] == "Benefit":
                for p in n["properties"]:
                    if p["name"] == "apply_method":
                        p["description"] = ("혜택을 받는 방식. 혜택 설명에 신청, 등록, 응모, 지정, 선택처럼 고객이 따로 해야 하는 일이 "
                                            "적혀 있으면 '신청 필요', 그런 문구가 없으면 '자동 적용'. '알 수 없음'은 혜택 설명 자체가 "
                                            "없을 때만 씀")
        for r in s["relationship_types"]:
            if r["label"] == "FOLLOWS":
                r["metadata_rel"] = True
                r["description"] = ("이번 상담이 같은 가명 회원의 바로 앞 상담에 이어짐. 코드가 메타데이터(같은 member_pseudo_id, "
                                    "상담일 순)로 채움. LLM 추출에 쓰지 않음")
        s["recommend"].append({"kind": "2라운드 고침", "item": "다1 ~ 다5, 라1 ~ 라3(8단계 1라운드 결과)", "cq": []})
    specs["consult_log"]["cq_map"]["C5"] = [{"rel": "FOLLOWS", "metadata": True}]
    specs["regulation"]["cq_map"]["R1"] = [{"label": "Clause", "property": "clause_no"}, {"label": "Clause", "property": "title"}]
    for doc, s in specs.items():
        save_json(f"{doc}/schema_spec.json", s)
    sc = load_json("shared_concepts.r1.json")
    sc["shared_node_types"]["MerchantCategory"]["name_rule"] = "대표 이름 목록에서만 고름(2라운드 라1)"
    sc["shared_node_types"]["MerchantCategory"]["vocabulary"] = [{"name": k, "meaning": v} for k, v in CATEGORIES]
    sc["shared_node_types"]["Topic"]["meanings"] = TOPIC_MEANING
    sc["proposal_traits"] = [k for k, _ in TRAITS]
    sc["proposal_trait_meanings"] = dict(TRAITS)
    sc["metadata_nodes"]["FOLLOWS"] = {"doc": "consult_log", "rule": "같은 member_pseudo_id의 상담을 consult_date 순으로 이음",
                                       "rel": "FOLLOWS"}
    sc["excluded_from_extraction"] = [
        sc["excluded_from_extraction"] if isinstance(sc["excluded_from_extraction"], dict) else sc["excluded_from_extraction"][0],
        {"doc": "benefit_guide", "rule": "section_label이 비어 있는 청크(표지와 카드 찾아보기 목록)",
         "why": "혜택 내용이 없고 카드 목록에서 상품 노드가 수십 개씩 잘못 생김(8단계 1라운드, 사용자 승인 라3)"}]
    save_json("shared_concepts.json", sc)
    print("2라운드 명세 저장")


if __name__ == "__main__":
    main()
