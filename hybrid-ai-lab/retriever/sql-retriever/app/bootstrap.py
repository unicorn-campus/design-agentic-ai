"""계층별 어댑터를 조립하는 유일한 구성 지점."""
from app.application.search_service import SearchService
from app.infrastructure.groq_gateway import GroqGateway
from app.infrastructure.postgres_repository import PostgresRepository
from app.infrastructure.settings import load_settings
from app.infrastructure.sql_guard import LOGICAL_SCHEMA, validate_sql


def create_service() -> SearchService:
    settings = load_settings()
    repository = PostgresRepository(settings.db_dsn, settings.db_password,
                                    statement_timeout_ms=settings.statement_timeout_ms)
    return SearchService(repository, GroqGateway(settings), validate_sql, LOGICAL_SCHEMA)
