"""DB 없이 실행 가능한 도메인 규칙 시험."""

import unittest

from app.domain.context import build_context, require_context
from app.domain.customer import fill_months, validate_customer


class CustomerDomainTest(unittest.TestCase):
    def test_fill_months_completes_recent_six_months(self) -> None:
        rows = [
            {"month": "2026-03", "total_amount": 100},
            {"month": "2026-08", "total_amount": 50},
        ]

        result = fill_months(rows, "2026-08-31")

        self.assertEqual(6, len(result))
        self.assertEqual({"month": "2026-04", "total_amount": 0}, result[1])
        self.assertEqual({"month": "2026-08", "total_amount": 50}, result[-1])

    def test_validate_customer_rejects_date_before_join(self) -> None:
        with self.assertRaisesRegex(ValueError, "가입 전"):
            validate_customer("2026-03-01", {"join_date": "2026-04-01"})


class ContextDomainTest(unittest.TestCase):
    def test_context_contains_sources_and_safe_missing_value(self) -> None:
        context = build_context(
            "M-1",
            [{"product_name": "샘플 카드", "annual_fee": 12000, "issue_date": "2025-01-01", "status": "ACTIVE"}],
            [
                {"month": "2026-05", "total_amount": 100},
                {"month": "2026-06", "total_amount": 90},
                {"month": "2026-07", "total_amount": 80},
                {"month": "2026-08", "total_amount": 50},
            ],
            None,
            "2026-08-31",
        )

        self.assertIn("출처: card·product·product_annual_fee", context)
        self.assertIn("-50.0%", context)
        self.assertIn("확인 필요(기준월 이하 자료 없음)", context)
        self.assertEqual(context, require_context(context))


if __name__ == "__main__":
    unittest.main()
