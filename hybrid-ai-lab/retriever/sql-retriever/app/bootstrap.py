"""계층의 구체 구현을 한곳에서 연결하는 조립 진입점."""

from .application.customer_service import CustomerService
from .application.lab_service import LabService
from .domain.context import build_context
from .infrastructure.claude_gateway import ClaudeGateway
from .infrastructure.postgres_repository import PostgresRepository
from .infrastructure.queries import query_delinquency, query_products, query_usage
from .infrastructure.settings import ROOT, load_settings


def build_application() -> LabService:
    settings = load_settings()
    repository = PostgresRepository(settings.db_dsn, settings.db_password)
    customers = CustomerService(
        repository=repository,
        products_query=query_products,
        usage_query=query_usage,
        delinquency_query=query_delinquency,
        context_builder=build_context,
    )
    prompt = (ROOT / "app/prompts/answer_with_context.md").read_text(encoding="utf-8")
    return LabService(repository, ClaudeGateway(settings), customers, prompt)
