"""고정 SQL의 읽기 전용 계약과 결과 변환 시험."""

import unittest

from app.infrastructure.queries import (
    DELINQUENCY_SQL,
    PRODUCTS_SQL,
    USAGE_SQL,
    query_usage,
)


class RecordingRepository:
    def __init__(self) -> None:
        self.calls = []

    def rows(self, sql, parameters):
        self.calls.append((sql, parameters))
        return [{"month": "2026-08", "total_amount": 50}]


class QueryTest(unittest.TestCase):
    def test_all_queries_are_bounded_selects(self) -> None:
        for sql in (PRODUCTS_SQL, USAGE_SQL, DELINQUENCY_SQL):
            normalized = " ".join(sql.upper().split())
            with self.subTest(sql=normalized[:30]):
                self.assertTrue(normalized.startswith("SELECT "))
                self.assertIn(" LIMIT ", normalized)
                for keyword in (" INSERT ", " UPDATE ", " DELETE ", " DROP ", " ALTER "):
                    self.assertNotIn(keyword, f" {normalized} ")

    def test_usage_query_binds_parameters_and_fills_missing_months(self) -> None:
        repository = RecordingRepository()

        result = query_usage(repository, "M-1", "2026-08-31")

        self.assertEqual({"member_id": "M-1", "base_date": "2026-08-31"}, repository.calls[0][1])
        self.assertEqual(6, len(result))
        self.assertEqual({"month": "2026-07", "total_amount": 0}, result[-2])


if __name__ == "__main__":
    unittest.main()
