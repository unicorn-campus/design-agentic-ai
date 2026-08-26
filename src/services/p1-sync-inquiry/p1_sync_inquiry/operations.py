"""W-1 결정론 담당자(R-D1)의 실제 처리 함수 모음.

`06-workflow.md`의 S-R1·S-R4·S-R6·S-R7·S-R10 성공 기준을 그대로 구현함.
바깥 호출은 전부 `ExternalTools`를 거치며 커넥터 기본값은 Mock임.
결정론 단계이므로 모델 어댑터를 사용하지 않고 같은 입력에는 같은 결과를 냄.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from help_desk_guardrails import InputGuard, SensitiveDataMasker
from help_desk_tools import ExternalTools, InvocationPolicy
from help_desk_tools.schemas import AnalyticsRequest, SearchRequest
from sqlglot import exp, parse

JsonObject = dict[str, Any]

#: S-R4가 조회할 수 있는 유일한 뷰와 열. 출처는 ⑤ 정형 접근 경로 1행임.
#: `help_desk_dataset.source.PATH_SPECS["S-R4"]`와 같은 값이며, 그 모듈은
#: P-2 패키지에만 있어 P-1에서 가져다 쓸 수 없어 같은 기준을 여기 다시 둠.
S_R4_TABLE = "masked_transaction_analysis_v"
S_R4_ALLOWED_COLUMNS = frozenset(
    {
        "masked_customer_id",
        "transaction_date",
        "transaction_status",
        "decline_reason_code",
        "amount_bucket",
        "merchant_category_code",
    }
)

#: 근거가 이만큼 모이면 위험도를 낮음으로 봄. ③ 위험 분기 기준을 옮긴 값임.
EVIDENCE_ENOUGH = 2

HANDOFF_DECISIONS = frozenset({"반려", "중단", "reject", "cancel"})


def derive_customer_ref(auth_session_ref: str, salt: str) -> str:
    """인증 세션 참조를 고객 참조로 바꿈. 원본 식별자를 그대로 두지 않음."""
    return hashlib.sha256(f"{auth_session_ref}{salt}".encode()).hexdigest()


def validate_read_statement(statement: str, limit: int) -> str:
    """S-R4 후보 SQL이 읽기 전용이며 허용 뷰·열만 쓰는지 검사함."""
    statements = parse(statement, read="postgres")
    if len(statements) != 1 or not isinstance(statements[0], exp.Select):
        raise ValueError("단일 SELECT 문만 허용됨")
    query = statements[0]
    if query.find(exp.DML) is not None or query.find(exp.DDL) is not None:
        raise ValueError("읽기 외 구문은 허용되지 않음")
    tables = {table.name for table in query.find_all(exp.Table)}
    if tables != {S_R4_TABLE}:
        raise ValueError(f"허용 테이블은 {S_R4_TABLE} 하나임")
    columns = {column.name for column in query.find_all(exp.Column)}
    if query.find(exp.Star) is not None or not columns.issubset(S_R4_ALLOWED_COLUMNS):
        raise ValueError("허용 열만 조회 가능함")
    return query.limit(limit, copy=True).sql(dialect="postgres")


@dataclass(frozen=True)
class InquiryOperations:
    """W-1 결정론 단계 5개를 담은 조립 단위."""

    tools: ExternalTools
    input_guard: InputGuard
    masker: SensitiveDataMasker
    masking_salt: str
    policies: Mapping[str, InvocationPolicy]
    max_rows: int

    def as_mapping(self) -> dict[str, Any]:
        return {
            "S-R1": self.input_gate,
            "S-R4": self.query_transactions,
            "S-R6": self.search_official,
            "S-R7": self.route_risk,
            "S-R10": self.deliver_answer,
        }

    async def input_gate(self, inputs: JsonObject) -> JsonObject:
        """S-R1 입력 게이트. 사람 입력을 검사하고 식별자를 가림."""
        inquiry_text = str(inputs.get("inquiry_text", ""))
        decision = self.input_guard.inspect(
            "IN-W1-R1", inquiry_text, "프롬프트 조립 직전"
        )
        if not decision.accepted:
            raise ValueError(f"IN-W1-R1 위반: {', '.join(decision.violations)}")
        auth_session_ref = str(inputs["auth_session_ref"])
        safe_text = self.masker.sanitize({"text": inquiry_text}, "access")["text"]
        return {
            "request_id": str(inputs["request_id"]),
            "auth_session_ref": auth_session_ref,
            "customer_ref": derive_customer_ref(auth_session_ref, self.masking_salt),
            "safe_inquiry_text": safe_text,
        }

    async def query_transactions(self, inputs: JsonObject) -> JsonObject:
        """S-R4 정형 조회. 검사를 통과한 SQL만 C-A2로 넘김."""
        statement = validate_read_statement(
            str(inputs["sql_candidate"]), self.max_rows
        )
        response = await self.tools.query_analytics(
            AnalyticsRequest(
                statement=statement, parameters={}, max_rows=self.max_rows
            ),
            stage_id="S-R4",
            policy=self.policies["C-A2"],
        )
        return {"rows": response.rows, "row_count": response.row_count}

    async def search_official(self, inputs: JsonObject) -> JsonObject:
        """S-R6 외부 근거 확인. 비식별 검색어만 C-A3로 넘김."""
        response = await self.tools.search_official(
            SearchRequest(
                query=str(inputs.get("safe_inquiry_text", "")),
                source_type="web",
                period_days=365,
                sort="relevance",
                max_results=3,
                include_content=True,
            ),
            stage_id="S-R6",
            policy=self.policies["C-A3"],
        )
        return {"results": [item.model_dump(mode="json") for item in response.results]}

    async def route_risk(self, inputs: JsonObject) -> JsonObject:
        """S-R7 위험 분기. 확보한 근거 수만으로 판정하는 결정론 규칙임."""
        evidence = list(inputs.get("evidence_refs", []) or [])
        level = "low" if len(evidence) >= EVIDENCE_ENOUGH else "high"
        score = round(max(0.0, 1.0 - len(evidence) / EVIDENCE_ENOUGH), 2)
        return {
            "risk_result": {
                "level": level,
                "score": score,
                "reason": f"근거 {len(evidence)}건",
            }
        }

    async def deliver_answer(self, inputs: JsonObject) -> JsonObject:
        """S-R10 답변 전달.

        반려·중단 결정이면 처리 실패로 상담사에게 넘김.
        경로 판정이 처음부터 인계였던 경우에는 초안이 없으므로
        인계 접수 완료로 알림.
        """
        request_id = str(inputs["request_id"])
        approval = inputs.get("approval_result") or {}
        if str(approval.get("decision", "")) in HANDOFF_DECISIONS:
            return {
                "result_type": "handoff",
                "handoff_ref": request_id,
                "request_status": "failed",
            }
        draft = dict(inputs.get("answer_draft") or {})
        revised = approval.get("revised_answer")
        if isinstance(revised, dict) and revised:
            draft = revised
        if not draft:
            return {
                "result_type": "handoff",
                "handoff_ref": request_id,
                "request_status": "completed",
            }
        return {
            "result_type": "answer",
            "answer": draft,
            "request_status": "completed",
        }
