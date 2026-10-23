"""2라운드 기대 답 고침(사용자 승인한 고칠 안 가1 일부, 나1, 나2, 라1, 라3). 1라운드 기대 답은 {doc}/expected_answers.r1.json으로 남김.

- R1: 질문이 "조항 번호와 제목"이므로 기대 답을 단위 첫 줄의 '제N조(제목)'으로 통일(LLM 초안이 본문 문장을 적은 곳이 있었음).
  제2조처럼 본문이 있는 조항의 "없음"도 고침
- R3: 시점 없는 '알립니다' 문장만 있던 칸은 "없음"으로, 섞인 칸은 시점 있는 문장만 남김(사람 판단, 아래 R3_FIX)
- R4: 1라운드에서 "잘못 뽑음"이던 Handling 중 실제 상황별 처리 문장을 원문에서 찾아 기대 답에 넣음(사람 판단, 아래 R4_ADD)
- 혜택 X2: 카드 청크인데 "없음"이던 2건을 머리줄 card_name으로 고침
- 업종: X1 기대 답의 업종 이름을 2라운드 대표 이름 목록으로 바꿈(키워드 표). 목록에 맞지 않는 이름(매장, 가전, 우편, 타사)은 뺌
- 라3: 혜택 안내의 절 제목 없는 청크(표지, 카드 목록)를 시험용에서 뺌
실행: python tools/revise_expected_r2.py → output/expected_r2_changes.json
"""

from __future__ import annotations

import json
import re
import shutil

from common import BASE, load_json, load_units, save_json

R3_FIX = {  # 조항 → 고친 기대 답("없음"이면 시점 있는 문장이 없음)
    "제6조의2": "카드사는 연회비, 발급 가능 수, 결제 책임과 이용 범위를 사전에 안내합니다",
    "제16조의3": "없음",
    "제30조": "없음",
    "제38조의2": "없음",
}
R4_ADD = {  # 조항 → 원문에서 찾을 상황 구절(1라운드 잘못 뽑음 중 실제 상황별 처리)
    "제16조": ["일부 회차를 먼저 납부하면"],
    "제16조의3": ["계약을 이행하지 않거나 계약이 취소된 경우"],
    "제19조의2": ["해외 가맹점이 원화결제를 제안하면"],
    "제24조": ["반환 계좌를 확인할 수 없으면"],
    "제25조": ["결제일 전에 접수되면", "결제일 이후 접수되면"],
    "제25조의2": ["여러 채무를 함께 납부하면"],
    "제27조": ["고의 공유나 카드 양도가 확인된 경우"],
    "제28조": ["사용하지 않은 거래를 신고하면"],
    "제30조": ["정지 원인이 해소되고 본인 확인이 끝나면"],
    "제38조": ["약관을 변경할 때에는"],
    "제39조": ["의견 차이가 생기면"],
}
CAT_RULES = [  # (키워드들, 대표 이름). 앞에서부터 맞춰 봄(구독 서비스 이름이 '극장'을 품어 구독을 먼저 봄)
    (["구독", "정기결제", "월납", "관리비", "렌탈", "멤버십", "화면극장", "생활고지", "맑은집", "소리서재", "생각도우미"], "정기결제와 구독"),
    (["해외"], "해외 결제"),
    (["간편결제", "별빛페이", "주문 앱", "주문앱", "결제계정", "결제 계정"], "간편결제"),
    (["마트", "장보기", "살림곳"], "장보기와 마트"),
    (["편의점", "하루상점"], "편의점"),
    (["커피", "나무잔", "제과", "밀꽃"], "커피와 제과"),
    (["음식점", "배달", "한끼"], "음식점과 배달"),
    (["쇼핑몰", "달빛상점", "온라인쇼핑", "소품몰", "집꽃", "꼬리마을", "반려생활", "패션몰", "옷나래"], "온라인쇼핑"),
    (["버스", "도시철도", "지하철", "택시", "철도", "교통"], "대중교통과 택시"),
    (["주유", "충전", "수소", "새길오일", "초록전기"], "주유와 충전"),
    (["정비", "세차", "주차"], "자동차 관리와 주차"),
    (["통신", "모바일"], "통신"),
    (["영화", "극장", "공연", "놀이공원", "운동", "건강뜰", "취미", "문화"], "문화와 여가"),  # '공방'은 정비망 이름(바퀴공방)과 겹쳐 뺌
    (["라운지", "숙박", "리조트", "고요숲", "여행"], "여행과 숙박"),
    (["학원", "강의", "교육", "배움뜰", "지식마루", "수강"], "교육"),
    (["병원", "약국", "돌봄"], "의료와 돌봄"),
    (["사업경비", "사무용품", "택배", "일터문구"], "사업경비"),
    (["일반 가맹점", "일반가맹점", "일반 음식점"], "일반 가맹점"),
]
NOT_CATEGORY = {"매장", "가전", "우편", "타사", "단말기"}
EXTRA_FIX = {  # 1라운드를 다시 채점하다 찾은 기대 답 빠짐(원문 표의 '혜택 제외', '대상·채널' 줄)
    ("benefit_guide", "D2_5a3c0df949be0524_a3653494ff5f3081_0000"): {
        "B4": "상품권·선불 충전·현금서비스·취소 거래에는 혜택을 제공하지 않음. / 해외송금·현금인출 모의 거래에는 적용하지 않음.",
        "X1": "업종: 일반 가맹점 / 방식: 자동 적용",
    },
}


def to_categories(name: str) -> list[str]:
    """한 이름에 업종이 여럿 들 수 있어(예: 패션몰과 일반 음식점 업종) 맞는 것을 모두 돌려줌.
    '일반 가맹점'은 다른 업종이 하나도 없을 때만 씀(일반 음식점이 일반 가맹점으로 잡히지 않게)."""

    if name.strip() in NOT_CATEGORY:
        return []
    hits = [cat for words, cat in CAT_RULES if any(w in name for w in words)]
    return [c for c in hits if c != "일반 가맹점"] or hits


def apply_method_by_rule(text: str) -> str:
    return "신청 필요" if re.search(r"신청|등록|응모|지정|선택", text) else "자동 적용"


def remap_x1(answer: str, unmapped: list) -> str:
    if answer == "없음":
        return answer
    parts = []
    for part in answer.split("/"):
        k, sep, v = part.partition(":")
        if sep and k.strip() == "업종":
            cats = []
            for n in re.split(r"[,，]", v):
                n = n.strip()
                if not n or n == "없음":
                    continue
                found = to_categories(n)
                if not found:
                    unmapped.append(n)
                cats += [c for c in found if c not in cats]
            parts.append("업종: " + (", ".join(cats) if cats else "없음"))
        else:
            parts.append(part.strip())
    out = " / ".join(parts)
    return "없음" if all(p.split(":", 1)[-1].strip() == "없음" for p in parts) else out


def sentence_with(text: str, phrase: str) -> str | None:
    for s in re.split(r"(?<=[.다])\s+|\n", text):
        if phrase in s:
            return re.sub(r"^[①-⑳]\s*", "", s.strip())
    return None


def main() -> None:
    units = {u["id"]: u for u in load_units()}
    changes = []
    for doc in ("regulation", "benefit_guide", "consult_log"):
        src, bak = BASE / doc / "expected_answers.json", BASE / doc / "expected_answers.r1.json"
        if not bak.exists():
            shutil.copy(src, bak)
    # 약관
    e = load_json("regulation/expected_answers.r1.json")
    for cid, a in e["answers"].items():
        u, no = units[cid], cid.split(":", 1)[1]
        head = u["text"].splitlines()[0].strip()
        if a["R1"]["answer"] != head:
            changes.append({"doc": "regulation", "chunk_id": cid, "q": "R1", "before": a["R1"]["answer"][:80], "after": head})
            a["R1"] = {"answer": head, "location": "단위 첫 줄", "source": "2라운드 고침(조항 번호와 제목으로 통일)"}
        if no in R3_FIX and a["R3"]["answer"] != R3_FIX[no]:
            changes.append({"doc": "regulation", "chunk_id": cid, "q": "R3", "before": a["R3"]["answer"][:80], "after": R3_FIX[no]})
            a["R3"] = {"answer": R3_FIX[no], "location": "", "source": "2라운드 고침(시점 없는 통지 문장 뺌)"}
        if no in R4_ADD:
            found = [s for p in R4_ADD[no] if (s := sentence_with(u["text"], p))]
            old = [] if a["R4"]["answer"] == "없음" else [a["R4"]["answer"]]
            new = " / ".join(dict.fromkeys(old + found))
            if new and new != a["R4"]["answer"]:
                changes.append({"doc": "regulation", "chunk_id": cid, "q": "R4", "before": a["R4"]["answer"][:80], "after": new[:160]})
                a["R4"] = {"answer": new, "location": "원문", "source": "2라운드 고침(실제 상황별 처리 문장 더함)"}
    save_json("regulation/expected_answers.json", e)
    # 혜택 안내
    e = load_json("benefit_guide/expected_answers.r1.json")
    unmapped: list[str] = []
    for cid in list(e["answers"]):
        md = units[cid]["metadata"]
        if not (md.get("section_label") or "").strip():
            e["answers"].pop(cid)
            e.setdefault("dropped_excluded", []).append(cid)
            changes.append({"doc": "benefit_guide", "chunk_id": cid, "q": "전체", "before": "시험용", "after": "추출 제외(라3)"})
            continue
        a = e["answers"][cid]
        if a["X2"]["answer"] == "없음" and md.get("card_name"):
            changes.append({"doc": "benefit_guide", "chunk_id": cid, "q": "X2", "before": "없음", "after": md["card_name"]})
            a["X2"] = {"answer": md["card_name"], "location": "머리줄 card_name", "source": "2라운드 고침(카드 청크)"}
        new = remap_x1(a["X1"]["answer"], unmapped)
        if "알 수 없음" in new:  # 2라운드 규칙: 알 수 없음은 혜택 설명이 없을 때만. 있으면 신청 문구로 판단
            new = new.replace("알 수 없음", apply_method_by_rule(units[cid]["text"]))
        if new != a["X1"]["answer"]:
            changes.append({"doc": "benefit_guide", "chunk_id": cid, "q": "X1", "before": a["X1"]["answer"][:100], "after": new})
            a["X1"] = {**a["X1"], "answer": new, "source": "2라운드 고침(업종 대표 이름)"}
    for (doc, cid), fix in EXTRA_FIX.items():
        for q, ans in fix.items():
            changes.append({"doc": doc, "chunk_id": cid, "q": q, "before": e["answers"][cid][q]["answer"][:80], "after": ans})
            e["answers"][cid][q] = {"answer": ans, "location": "원문 표", "source": "2라운드 고침(기대 답 빠짐)"}
    save_json("benefit_guide/expected_answers.json", e)
    # 상담 기록
    e = load_json("consult_log/expected_answers.r1.json")
    for cid, a in e["answers"].items():
        new = remap_x1(a["X1"]["answer"], unmapped)
        if new != a["X1"]["answer"]:
            changes.append({"doc": "consult_log", "chunk_id": cid, "q": "X1", "before": a["X1"]["answer"][:100], "after": new})
            a["X1"] = {**a["X1"], "answer": new, "source": "2라운드 고침(업종 대표 이름)"}
    save_json("consult_log/expected_answers.json", e)
    save_json("output/expected_r2_changes.json", {"changes": changes, "unmapped_category_names": unmapped})
    from collections import Counter
    print("고친 칸", len(changes), Counter((c["doc"], c["q"]) for c in changes))
    print("목록에 안 맞아 뺀 업종 이름", sorted(set(unmapped)))


if __name__ == "__main__":
    main()
