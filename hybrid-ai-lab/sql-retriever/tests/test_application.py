"""인프라를 가짜 구현으로 바꾼 응용 계층 시험."""

import unittest

from app.application.customer_service import CustomerService
from app.application.lab_service import LabService
from app.application.models import LabRequest


class FakeRepository:
    def member(self, member_id):
        return {"member_id": member_id, "join_date": "2025-01-01"}

    def rows(self, _sql, _parameters):
        return []

    def schema(self):
        return [{"table": "member", "rows": 1, "columns": []}]


class FailingLLM:
    def ask(self, _system, _user, max_tokens=1800):
        del max_tokens
        raise AssertionError("offline 요청에서 LLM을 호출하면 안 됨")


def products(_repository, _member_id, _base_date):
    return []


def usage(_repository, _member_id, _base_date):
    return [{"month": "2026-08", "total_amount": 10}]


def delinquency(_repository, _member_id, _base_date):
    return None


def context(member_id, _products, _usage, _delinquency, base_date):
    return f"{member_id}:{base_date}"


class ApplicationTest(unittest.TestCase):
    def setUp(self) -> None:
        repository = FakeRepository()
        customers = CustomerService(repository, products, usage, delinquency, context)
        self.service = LabService(repository, FailingLLM(), customers, "system prompt")
        self.request = LabRequest("M-1", "2026-08-31", "질문", offline=True)

    def test_offline_answer_builds_context_without_llm(self) -> None:
        result = self.service.execute("ask", self.request)

        self.assertEqual(0, result.exit_code)
        self.assertEqual("system prompt", result.payload["system"])
        self.assertIn("<context>M-1:2026-08-31</context>", result.payload["user"])

    def test_schema_uses_repository_port(self) -> None:
        result = self.service.execute("schema", self.request)

        self.assertEqual("member", result.payload[0]["table"])


if __name__ == "__main__":
    unittest.main()
