"""운영 어댑터가 응용 계층 포트를 명시적으로 구현하는지 검증함."""

import inspect
import unittest
from unittest.mock import patch

import psycopg

from app.application.ports import CustomerRepositoryPort, LLMPort
from app.infrastructure.claude_gateway import ClaudeGateway
from app.infrastructure.postgres_repository import PostgresRepository


class PortContractTest(unittest.TestCase):
    def test_operational_adapters_complete_ports(self) -> None:
        for implementation, port in (
            (PostgresRepository, CustomerRepositoryPort),
            (ClaudeGateway, LLMPort),
        ):
            with self.subTest(implementation=implementation.__name__):
                self.assertIn(port, implementation.__mro__)
                self.assertFalse(inspect.isabstract(implementation))

    def test_postgres_error_is_translated_to_runtime_error(self) -> None:
        repository = PostgresRepository("host=invalid")
        with (
            patch(
                "app.infrastructure.postgres_repository.psycopg.connect",
                side_effect=psycopg.OperationalError("connection failed"),
            ),
            self.assertRaisesRegex(RuntimeError, "PostgreSQL 읽기 전용 조회 실패"),
        ):
            repository.schema()


if __name__ == "__main__":
    unittest.main()
