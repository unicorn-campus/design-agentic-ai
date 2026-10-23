"""5단계 초안: 이전 확정 스키마(2026-10-18) 위에 공통 개념, 참조 노드, 메타데이터 노드를 얹어 {doc}/schema_spec.json과
shared_concepts.json을 만듦. 문서 종류별 노드 타입(조항, 혜택, 불만 등)은 이전 시험을 통과한 description을 그대로 씀.

실행: python tools/make_specs_v2.py → {doc}/schema_spec.json, shared_concepts.json
이어서: python tools/build_schema.py {doc} → 그림과 기계 검증
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

from common import BASE, save_json

OLD = BASE.parents[1] / "indexer" / "graphrag" / "schema" / "doc"

# 주제 대표 이름 목록. 약관 조항 제목 52개와 상담 메타데이터 주제 12개를 함께 보고 묶음.
# 한 주제가 거의 모든 단위에 붙지 않게(허브 방지) 조항 묶음 크기가 2 ~ 8개가 되도록 나눔
TOPICS = [
    {"name": "연회비", "clauses": ["제9조", "제10조"], "consult_topics": ["연회비 대비 가치"]},
    {"name": "부가서비스와 포인트", "clauses": ["제17조", "제18조"], "consult_topics": ["혜택 불일치", "생활비 절약"]},
    {"name": "본인 인증과 보안", "clauses": ["제8조", "제26조", "제27조", "제29조"], "consult_topics": ["앱 인증 불편 완화"]},
    {"name": "통지와 광고", "clauses": ["제5조", "제38조"], "consult_topics": ["광고 알림 누적"]},
    {"name": "민원과 이의 처리", "clauses": ["제34조", "제35조", "제39조"], "consult_topics": ["민원 처리 경과 부재"]},
    {"name": "명세서와 결제", "clauses": ["제20조", "제21조", "제22조", "제22조의2", "제24조", "제25조", "제25조의2"],
     "consult_topics": ["명세서 항목 이해"]},
    {"name": "할부", "clauses": ["제16조", "제16조의2", "제16조의3"], "consult_topics": ["가전 구매 주기"]},
    {"name": "분실과 부정 사용", "clauses": ["제12조", "제28조"], "consult_topics": ["의심 문자 확인"]},
    {"name": "이용정지와 휴면", "clauses": ["제12조의2", "제12조의3", "제29조", "제30조"], "consult_topics": []},
    {"name": "해지", "clauses": ["제36조", "제37조", "제38조의2"], "consult_topics": ["타사 관리 절차 비교"]},
    {"name": "발급과 카드 관리", "clauses": ["제6조", "제6조의2", "제7조", "제11조"], "consult_topics": ["카드 중복"]},
    {"name": "개인정보와 회원 정보", "clauses": ["제31조", "제32조", "제33조"], "consult_topics": ["우편 주소 수정"]},
    {"name": "해외 이용", "clauses": ["제19조", "제19조의2"], "consult_topics": []},
    {"name": "카드대출과 금리", "clauses": ["제22조의3", "제22조의4", "제23조", "제34조의2"], "consult_topics": []},
    {"name": "이용한도와 승인", "clauses": ["제13조", "제14조", "제15조"], "consult_topics": []},
]
# 어느 주제에도 넣지 않은 조항: 제1조(목적), 제2조(용어의 정의), 제3조, 제4조, 제40조(시행일). 약관 전체에 걸친 일반 조항이라
# 주제를 붙이면 거의 모든 질문에 끼어들어 묶는 힘이 없음
TOPIC_NAMES = [t["name"] for t in TOPICS]
TRAITS = ["소비 증가 필요", "고객 할 일 증가", "고객 할 일 없음", "글로 남는 안내", "말로만 안내", "고객이 요청한 방식"]

P = lambda name, desc, t="STRING": {"name": name, "type": t, "description": desc}

TOPIC = {"label": "Topic", "ko": "주제", "shared": True,
         "description": "해당: 조항, 불만, 상담이 다루는 업무 주제 하나. 이름은 아래 대표 이름 목록에서만 고름: "
                        + ", ".join(TOPIC_NAMES) + ". 비해당: 목록에 없는 이름, 카드 이름, 혜택 이름, 업종 이름",
         "properties": [P("name", "주제 대표 이름. 목록의 글자를 그대로 씀")]}
CATEGORY = {"label": "MerchantCategory", "ko": "업종과 결제 대상", "shared": True,
            "description": "해당: 혜택이 적용되거나 고객이 말한 결제 대상 업종이나 사용처 분야(예: 장보기, 편의점, 주유, 대중교통, "
                           "간편결제, 해외 결제). 비해당: 특정 가맹점 한 곳의 이름, 카드 이름, 혜택 크기",
            "properties": [P("name", "업종 대표 이름. 띄어쓰기를 없앤 꼴로 맞추고 동의어 표로 합침")]}
PRODUCT = {"label": "Product", "ko": "카드 상품(정형 참조)", "reference": True,
           "description": "해당: 한빛 카드 상품 하나. 정형 스키마의 Product를 가리키는 참조 노드. 비해당: 실제 카드사 상품, "
                          "개별 혜택, 연회비와 가족카드 규칙(정형 데이터에 있음)",
           "properties": [P("product_id", "상품 ID(예: D2-C001). 혜택 안내는 머리줄 값, 상담은 상품 이름으로 정형 데이터에서 찾음"),
                          P("product_name", "상품 이름(예: 한빛 모아생활). 정형 Product.product_name과 같은 글자")]}


def load_old(doc: str) -> dict:
    return json.loads((OLD / doc / "schema_spec.json").read_text(encoding="utf-8"))


def regulation() -> dict:
    s = load_old("regulation")
    s["node_types"].append(copy.deepcopy(TOPIC))
    s["relationship_types"].append({"label": "ABOUT", "ko": "주제를 다룸",
                                    "description": "조항이 다루는 주제. 조항 하나에 주제 0 ~ 2개(일반 조항은 잇지 않음)"})
    for r in s["relationship_types"]:
        if r["label"] == "HAS_CLAUSE":
            r["structural"] = True  # 문서 하나가 모든 조항에 이어지는 구조용 관계. 커뮤니티 묶기에서 뺄 수 있게 표시
    s["patterns"].append(["Clause", "ABOUT", "Topic"])
    s["constraints"].append({"type": "UNIQUENESS", "node_type": "Topic", "property_name": "name"})
    s["cq_map"]["X1"] = [{"rel": "ABOUT"}]
    s["recommend"] += [
        {"kind": "공통", "item": "Topic(주제) 추가, Clause -ABOUT-> Topic", "cq": ["X1"]},
        {"kind": "구조용 표시", "item": "HAS_CLAUSE는 약관 문서 하나가 모든 조항에 이어지는 관계라 구조용으로 표시", "cq": []},
    ]
    return s


def benefit_guide() -> dict:
    s = load_old("benefit_guide")
    s["node_types"] = [n for n in s["node_types"] if n["label"] != "ProductGuide"]
    s["node_types"].insert(0, copy.deepcopy(PRODUCT))
    for n in s["node_types"]:
        if n["label"] == "Benefit":
            n["properties"].append(P("apply_method", "혜택을 받는 방식. '자동 적용', '신청 필요', '알 수 없음' 중 하나"))
    s["node_types"].append(copy.deepcopy(CATEGORY))
    s["relationship_types"].append({"label": "APPLIES_TO", "ko": "업종에 적용됨",
                                    "description": "혜택이 적용되는 업종이나 결제 대상. 혜택 하나에 0 ~ 3개"})
    s["patterns"] = [["Product" if x == "ProductGuide" else x for x in p] for p in s["patterns"]]
    s["patterns"].append(["Benefit", "APPLIES_TO", "MerchantCategory"])
    s["constraints"] = [{"type": "UNIQUENESS", "node_type": "Product", "property_name": "product_id"},
                        {"type": "UNIQUENESS", "node_type": "MerchantCategory", "property_name": "name"}]
    s["cq_map"]["X1"] = [{"rel": "APPLIES_TO"}, {"label": "Benefit", "property": "apply_method"}]
    s["cq_map"]["X2"] = [{"rel": "OFFERS_BENEFIT"}]
    s["recommend"] += [
        {"kind": "참조", "item": "ProductGuide → Product(정형 참조, product_id와 product_name). 정형 스키마에 있는 개념이라 "
                                 "같은 라벨과 키로 가리킴", "cq": ["X2", "B1"]},
        {"kind": "공통", "item": "MerchantCategory(업종과 결제 대상) 추가, Benefit -APPLIES_TO-> MerchantCategory", "cq": ["X1"]},
        {"kind": "추가", "item": "Benefit.apply_method(자동 적용, 신청 필요). 혜택 신청 반복 불만과 자동 적용 혜택을 잇는 데 씀",
         "cq": ["X1"]},
    ]
    return s


def consult_log() -> dict:
    s = load_old("consult_log")
    for n in s["node_types"]:
        if n["label"] == "Consultation":
            n["properties"] = [p for p in n["properties"] if p["name"] not in ("topic", "member_pseudo_id")]
    s["node_types"] += [
        copy.deepcopy(TOPIC), copy.deepcopy(CATEGORY), copy.deepcopy(PRODUCT),
        {"label": "CustomerSegment", "ko": "고객군", "metadata_node": True,
         "description": "해당: 상담 기록이 속한 고객군 하나(메타데이터 원천 파일 이름에서 채움). 비해당: 나이대, 상담 채널",
         "properties": [P("name", "고객군 이름(예: 신규가입, 장기보유)")]},
        {"label": "PseudoMember", "ko": "가명 회원", "metadata_node": True,
         "description": "해당: 가명 처리된 회원 하나(메타데이터 member_pseudo_id). 비해당: 실명, 연락처, 정형 Member(키가 다름)",
         "properties": [P("member_pseudo_id", "가명 회원 ID")]},
        {"label": "ProposalTrait", "ko": "제안 성격",
         "description": "해당: 제안이 고객에게 요구하거나 주는 성격 하나. 이름은 목록에서만 고름: " + ", ".join(TRAITS)
                        + ". 비해당: 제안 내용 자체, 고객의 결정",
         "properties": [P("name", "제안 성격 대표 이름. 목록의 글자를 그대로 씀")]},
    ]
    s["relationship_types"] += [
        {"label": "ABOUT", "ko": "주제를 다룸", "description": "불만이 다루는 주제. 불만 하나에 주제 1 ~ 2개"},
        {"label": "HAS_TOPIC", "ko": "상담 주제", "description": "상담 기록의 주제(메타데이터 topic을 대표 이름으로 바꿔 채움)"},
        {"label": "MENTIONS_CATEGORY", "ko": "업종을 말함", "description": "불만이나 제안에서 고객이나 상담사가 말한 업종이나 결제 대상"},
        {"label": "MENTIONS_PRODUCT", "ko": "카드를 말함", "description": "상담에서 이름이 나온 한빛 카드 상품"},
        {"label": "IN_SEGMENT", "ko": "고객군에 속함", "description": "상담 기록이 속한 고객군(메타데이터로 채움)"},
        {"label": "OF_MEMBER", "ko": "회원의 상담", "description": "상담 기록의 가명 회원(메타데이터로 채움)"},
        {"label": "HAS_TRAIT", "ko": "제안 성격을 가짐", "description": "제안의 성격. 제안 하나에 1 ~ 3개"},
    ]
    s["patterns"] += [["Complaint", "ABOUT", "Topic"], ["Consultation", "HAS_TOPIC", "Topic"],
                      ["Complaint", "MENTIONS_CATEGORY", "MerchantCategory"],
                      ["Proposal", "MENTIONS_CATEGORY", "MerchantCategory"],
                      ["Consultation", "MENTIONS_PRODUCT", "Product"], ["Consultation", "IN_SEGMENT", "CustomerSegment"],
                      ["Consultation", "OF_MEMBER", "PseudoMember"], ["Proposal", "HAS_TRAIT", "ProposalTrait"]]
    s["constraints"] += [{"type": "UNIQUENESS", "node_type": t, "property_name": k} for t, k in
                         [("Topic", "name"), ("MerchantCategory", "name"), ("Product", "product_id"),
                          ("CustomerSegment", "name"), ("PseudoMember", "member_pseudo_id"), ("ProposalTrait", "name")]]
    s["metadata_header"] = ["record_id", "consult_date", "channel"]
    s["cq_map"].update({"X1": [{"rel": "ABOUT"}, {"rel": "MENTIONS_CATEGORY"}], "X2": [{"rel": "MENTIONS_PRODUCT"}],
                        "A1": [{"rel": "IN_SEGMENT"}, {"rel": "ABOUT"}], "A2": [{"rel": "HAS_TRAIT"}]})
    s["recommend"] += [
        {"kind": "공통", "item": "Topic: Complaint -ABOUT-> Topic, Consultation -HAS_TOPIC-> Topic", "cq": ["X1", "A1"]},
        {"kind": "공통", "item": "MerchantCategory: Complaint, Proposal -MENTIONS_CATEGORY-> MerchantCategory", "cq": ["X1"]},
        {"kind": "참조", "item": "Product(정형 참조): Consultation -MENTIONS_PRODUCT-> Product", "cq": ["X2"]},
        {"kind": "추가", "item": "CustomerSegment(메타데이터 source), PseudoMember(메타데이터 member_pseudo_id). "
                               "Consultation의 topic, member_pseudo_id 속성은 노드로 옮겨 뺌", "cq": ["A1", "C5"]},
        {"kind": "추가", "item": "ProposalTrait(제안 성격): Proposal -HAS_TRAIT-> ProposalTrait", "cq": ["A2"]},
    ]
    return s


def main() -> None:
    specs = {"regulation": regulation(), "benefit_guide": benefit_guide(), "consult_log": consult_log()}
    for doc, s in specs.items():
        save_json(f"{doc}/schema_spec.json", s)
    shared = {
        "shared_node_types": {
            "Topic": {"docs": ["regulation", "consult_log"], "key": "name", "name_rule": "대표 이름 목록에서만 고름",
                      "vocabulary": TOPICS,
                      "unassigned_clauses": ["제1조", "제2조", "제3조", "제4조", "제40조"]},
            "MerchantCategory": {"docs": ["benefit_guide", "consult_log"], "key": "name",
                                 "name_rule": "띄어쓰기를 없앤 꼴로 맞추고, 8단계 시험에서 나온 이름으로 동의어 표를 만들어 합침"},
        },
        "reference_nodes": {"Product": {"docs": ["benefit_guide", "consult_log"], "structured_label": "Product",
                                        "key": "product_id",
                                        "fill": {"benefit_guide": "머리줄 product_id", "consult_log": "상품 이름으로 정형 Product에서 찾음"}}},
        "metadata_nodes": {
            "CustomerSegment": {"doc": "consult_log", "field": "source", "rule": r"^D3_S\d+_([^_]+)_", "rel": "IN_SEGMENT"},
            "PseudoMember": {"doc": "consult_log", "field": "member_pseudo_id", "rel": "OF_MEMBER"},
            "Topic(상담 주제)": {"doc": "consult_log", "field": "topic", "rel": "HAS_TOPIC",
                               "map": {ct: t["name"] for t in TOPICS for ct in t["consult_topics"]}},
        },
        "structural_relationships": [{"doc": "regulation", "rel": "HAS_CLAUSE",
                                      "why": "문서 노드 하나가 모든 조항에 이어짐. 검색 경로로는 쓰고 커뮤니티 묶기에서는 뺄 수 있음"}],
        "paths": {
            "X1": ["(Complaint)-[ABOUT]->(Topic)<-[ABOUT]-(Clause)",
                   "(Complaint)-[MENTIONS_CATEGORY]->(MerchantCategory)<-[APPLIES_TO]-(Benefit)"],
            "X2": ["(Consultation)-[MENTIONS_PRODUCT]->(Product)-[OFFERS_BENEFIT]->(Benefit)"],
            "A1": ["(CustomerSegment)<-[IN_SEGMENT]-(Consultation)-[HAS_COMPLAINT]->(Complaint)-[ABOUT]->(Topic)"],
            "A2": ["(Proposal {decision})-[HAS_TRAIT]->(ProposalTrait)"],
        },
        "proposal_traits": TRAITS,
    }
    save_json("shared_concepts.json", shared)
    print({d: (len(s["node_types"]), len(s["relationship_types"]), len(s["patterns"])) for d, s in specs.items()})


if __name__ == "__main__":
    main()
