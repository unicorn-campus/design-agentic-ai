"""CLI와 API가 공유하는 요청·응답 및 검색 계획 계약."""
from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

QueryMode = Literal["auto", "fixed", "nl2sql"]
QueryId = Literal["customer_snapshot", "cards", "monthly_usage", "delinquency"]


class SearchError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 400):
        super().__init__(message)
        self.code, self.message, self.status_code = code, message, status_code


class SearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    query_mode: QueryMode = "auto"
    member_id: str = Field(pattern=r"^M-[0-9]{1,20}$", max_length=22)
    base_date: date
    question: str | None = Field(default=None, min_length=1, max_length=2000)
    query_id: QueryId | None = None
    explain: bool = False

    @field_validator("base_date", mode="before")
    @classmethod
    def iso_date_only(cls, value):
        if isinstance(value, str):
            if len(value) != 10:
                raise ValueError("기준일은 YYYY-MM-DD 형식이어야 합니다.")
            try:
                return date.fromisoformat(value)
            except ValueError as error:
                raise ValueError("유효한 YYYY-MM-DD 날짜가 필요합니다.") from error
        if type(value) is not date:
            raise ValueError("기준일은 날짜여야 합니다.")
        return value

    @model_validator(mode="after")
    def consistent_mode(self):
        if self.query_mode != "fixed" and not self.question:
            raise ValueError("auto와 nl2sql 모드에는 question이 필요합니다.")
        if self.query_mode != "fixed" and self.query_id is not None:
            raise ValueError("query_id는 fixed 모드에서만 지정합니다.")
        return self


class QueryPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")
    query_mode: Literal["fixed", "nl2sql", "unsupported"]
    query_id: QueryId | None
    sql: str | None = Field(max_length=10000)
    reason: str = Field(min_length=1, max_length=1000)

    @model_validator(mode="after")
    def valid_plan(self):
        if self.query_mode == "fixed" and (self.query_id is None or self.sql is not None):
            raise ValueError("고정 계획에는 query_id만 있어야 합니다.")
        if self.query_mode == "nl2sql" and (not self.sql or self.query_id is not None):
            raise ValueError("NL2SQL 계획에는 sql만 있어야 합니다.")
        if self.query_mode == "unsupported" and (self.sql is not None or self.query_id is not None):
            raise ValueError("미지원 계획에는 실행할 조회가 없어야 합니다.")
        return self


class SearchResponse(BaseModel):
    query_mode: Literal["fixed", "nl2sql"]
    requested_query_mode: QueryMode = "auto"
    query_id: QueryId | None = None
    routing_reason: str = ""
    member_id: str
    base_date: date
    data: dict
    explanation: str | None = None
    explanation_status: Literal["not_requested", "completed", "failed"] = "not_requested"
    warnings: list[str] = Field(default_factory=list)
