"""바깥 모델 없이 도는 대역 생성기.

`HELP_DESK_LLM_PROVIDER=local`일 때 R-L1 담당자가 쓰는 구현임.
상용 LLM API(C-A1)를 부르지 않고, 단계별 성공 기준에 맞는 구조화 결과를
규칙으로 만들어 돌려줌. 로컬 실행과 시험에서만 쓰는 대역이며 운영 답변 품질을
보장하지 않음. 운영에서는 `ModelAdapterInvoker`를 사용함.

이 모듈은 `<workflow_input>` 안의 값만 읽고, 그 밖의 문장은 지시로 해석하지 않음.
"""

from __future__ import annotations

import json
import re
from typing import Any

JsonObject = dict[str, Any]

INPUT_PATTERN = re.compile(
    r"<workflow_input>(?P<payload>.*?)</workflow_input>", re.DOTALL
)

#: 상담사 인계로 보낼 신호. ③ 경로 판정 기준의 handoff 조건을 옮긴 값임.
HANDOFF_SIGNALS = ("상담사", "사람", "직접 통화", "연결해", "분실", "도난")
#: 정형 조회만으로 답할 수 있는 신호.
STRUCTURED_SIGNALS = ("내역", "건수", "금액", "승인 거절", "결제 실패", "통계")

S_R3_STATEMENT = (
    "SELECT masked_customer_id, transaction_date, transaction_status, "
    "decline_reason_code FROM masked_transaction_analysis_v"
)
S_B3_STATEMENT = (
    "SELECT consultation_ref, topic_code, resolution_code "
    "FROM masked_consultation_analysis_v"
)


def parse_workflow_input(user_prompt: str) -> JsonObject:
    """프롬프트에 담긴 `<workflow_input>` 값을 되읽음."""
    match = INPUT_PATTERN.search(user_prompt)
    if match is None:
        return {}
    try:
        parsed = json.loads(match.group("payload"))
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


class LocalStubModelInvoker:
    """단계 ID별로 규칙 기반 구조화 결과를 만드는 대역 호출자."""

    STAGES = frozenset(
        {"S-R2", "S-R3", "S-R5", "S-R8", "S-B3", "S-B5", "S-B8", "S-E3"}
    )

    async def __call__(
        self,
        stage_id: str,
        system_prompt: str,
        user_prompt: str,
    ) -> JsonObject:
        del system_prompt
        if stage_id not in self.STAGES:
            raise ValueError(f"대역 생성기 미배정 단계: {stage_id}")
        inputs = parse_workflow_input(user_prompt)
        builder = getattr(self, f"_{stage_id.lower().replace('-', '_')}")
        return builder(inputs)

    @staticmethod
    def _s_r2(inputs: JsonObject) -> JsonObject:
        text = str(inputs.get("safe_inquiry_text", ""))
        if any(signal in text for signal in HANDOFF_SIGNALS):
            return {"route_decision": "handoff"}
        if any(signal in text for signal in STRUCTURED_SIGNALS):
            return {"route_decision": "structured"}
        return {"route_decision": "composite"}

    @staticmethod
    def _s_r3(inputs: JsonObject) -> JsonObject:
        del inputs
        return {"sql_candidate": S_R3_STATEMENT}

    @staticmethod
    def _s_r5(inputs: JsonObject) -> JsonObject:
        rows = list((inputs.get("query_result") or {}).get("rows", []))
        refs = [f"table:masked_transaction_analysis_v#{index}" for index in range(len(rows))]
        refs.append("doc:card-service-guide")
        return {"evidence_refs": refs}

    @staticmethod
    def _s_r8(inputs: JsonObject) -> JsonObject:
        refs = list(inputs.get("evidence_refs", []) or [])
        external = list((inputs.get("external_evidence") or {}).get("results", []))
        risk = (inputs.get("risk_result") or {}).get("level", "unknown")
        sources = ", ".join(str(item.get("title", "")) for item in external if item)
        answer = (
            f"문의하신 내용은 확보한 근거 {len(refs)}건을 바탕으로 안내드립니다."
            f" 위험도는 {risk}으로 판정되었습니다."
        )
        if sources:
            answer = f"{answer} 참고한 공식 자료: {sources}."
        return {
            "answer_draft": {
                "answer": answer,
                "evidence_refs": refs,
                "next_action": "추가 문의가 있으면 같은 창구로 다시 문의",
            }
        }

    @staticmethod
    def _s_b3(inputs: JsonObject) -> JsonObject:
        del inputs
        return {"sql_candidate": S_B3_STATEMENT}

    @staticmethod
    def _s_b5(inputs: JsonObject) -> JsonObject:
        refs = list(inputs.get("masked_consultation_refs", []) or [])
        return {
            "topic_evidence": [
                {"topic": "결제 승인 거절", "evidence_refs": refs[:3]},
            ]
        }

    @staticmethod
    def _s_b8(inputs: JsonObject) -> JsonObject:
        topics = list(inputs.get("topic_evidence", []) or [])
        return {
            "faq_candidates": [
                {
                    "candidate_id": f"faq-{index + 1}",
                    "question": f"{topic.get('topic', '주제')} 관련 안내",
                    "evidence_refs": list(topic.get("evidence_refs", []) or []),
                }
                for index, topic in enumerate(topics)
            ]
        }

    @staticmethod
    def _s_e3(inputs: JsonObject) -> JsonObject:
        del inputs
        return {
            "summary_draft": {
                "reason": "상담 사유 요약",
                "checked": "확인한 내용 요약",
                "guidance": "안내한 내용 요약",
                "next_action": "후속 조치 없음",
            }
        }
