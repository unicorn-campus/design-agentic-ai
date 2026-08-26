from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from help_desk_dataset.source import AnalyticsSource, PATH_SPECS, validate_read_statement
from help_desk_runtime.model import ModelClientAdapter
from sqlglot import exp, parse_one


BLOCKED_COLUMNS = frozenset(
    {
        "masked_transaction_analysis_v.original_customer_id",
        "masked_transaction_analysis_v.full_card_number",
        "masked_transaction_analysis_v.cvc",
        "masked_transaction_analysis_v.password",
        "masked_transaction_analysis_v.resident_registration_number",
        "masked_transaction_analysis_v.auth_token",
        "masked_consultation_analysis_v.original_customer_id",
        "masked_consultation_analysis_v.raw_transcript",
        "masked_consultation_analysis_v.full_card_number",
        "masked_consultation_analysis_v.cvc",
        "masked_consultation_analysis_v.resident_registration_number",
        "masked_consultation_analysis_v.auth_token",
        "consultation_event_inbox.raw_transcript",
        "langgraph_checkpoints.state_ciphertext",
    }
)


@dataclass(frozen=True)
class GeneratedQuery:
    statement: str
    parameters: Mapping[str, object]


def validate_knowledge_statement(statement: str, stage_id: str, row_limit: int) -> str:
    if "--" in statement or "/*" in statement or "*/" in statement:
        raise ValueError("SQL 주석은 허용되지 않음")
    query = parse_one(statement, read="postgres")
    safe_functions = (exp.Count, exp.Sum, exp.Avg, exp.Min, exp.Max)
    if any(not isinstance(function, safe_functions) for function in query.find_all(exp.Func)):
        raise ValueError("허용되지 않은 함수 호출")
    return validate_read_statement(statement, PATH_SPECS[stage_id], row_limit)


class NL2SQLGenerator:
    def __init__(self, adapter: ModelClientAdapter) -> None:
        self._adapter = adapter

    def generate(self, stage_id: str, question: str, row_limit: int) -> GeneratedQuery:
        if stage_id not in {"S-R4", "S-B4"}:
            raise ValueError("제한형 NL2SQL 단계가 아님")
        spec = PATH_SPECS[stage_id]
        schema = ", ".join(sorted(spec.allowed_columns))
        prompt = (
            "단일 PostgreSQL SELECT만 반환함. 주석과 다중 문장을 쓰지 않음. "
            f"허용 테이블: {spec.table}. 허용 열: {schema}. "
            f"행 상한: {row_limit}. 질문: {question}"
        )
        response = self._adapter.create().invoke(prompt)
        statement = str(getattr(response, "content", response)).strip()
        safe = validate_knowledge_statement(statement, stage_id, row_limit)
        return GeneratedQuery(statement=safe, parameters={})


class KnowledgeQueryService:
    def __init__(self, source: AnalyticsSource, generator: NL2SQLGenerator | None = None) -> None:
        self._source = source
        self._generator = generator

    def query_s_r4(
        self,
        statement: str,
        parameters: Mapping[str, object] | None,
        row_limit: int,
    ) -> list[dict[str, object]]:
        safe = validate_knowledge_statement(statement, "S-R4", row_limit)
        return self._source.read_s_r4(safe, parameters, row_limit)

    def query_s_b2(
        self,
        start_at: Any,
        end_at: Any,
        row_limit: int,
    ) -> list[dict[str, object]]:
        statement = (
            "SELECT consultation_ref, ended_at, topic_code, resolution_code, "
            "reopen_count, masked_summary FROM masked_consultation_analysis_v "
            "WHERE ended_at >= %(start_at)s AND ended_at < %(end_at)s ORDER BY ended_at"
        )
        safe = validate_knowledge_statement(statement, "S-B2", row_limit)
        return self._source.read_s_b2(
            safe,
            {"start_at": start_at, "end_at": end_at},
            row_limit,
        )

    def query_s_b4(
        self,
        statement: str,
        parameters: Mapping[str, object] | None,
        row_limit: int,
    ) -> list[dict[str, object]]:
        safe = validate_knowledge_statement(statement, "S-B4", row_limit)
        return self._source.read_s_b4(safe, parameters, row_limit)

    def generate_and_query(
        self,
        stage_id: str,
        question: str,
        row_limit: int,
    ) -> list[dict[str, object]]:
        if self._generator is None:
            raise RuntimeError("NL2SQL 생성기가 설정되지 않음")
        generated = self._generator.generate(stage_id, question, row_limit)
        if stage_id == "S-R4":
            return self.query_s_r4(generated.statement, generated.parameters, row_limit)
        return self.query_s_b4(generated.statement, generated.parameters, row_limit)
