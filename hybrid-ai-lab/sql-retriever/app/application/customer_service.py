"""고객 데이터를 조회하고 Context로 조립하는 응용 서비스."""

from ..domain.context import require_context
from ..domain.customer import validate_customer
from .ports import ContextBuilderPort, CustomerRepositoryPort, QueryPort


class CustomerService:
    def __init__(
        self,
        repository: CustomerRepositoryPort,
        products_query: QueryPort,
        usage_query: QueryPort,
        delinquency_query: QueryPort,
        context_builder: ContextBuilderPort,
    ) -> None:
        self.repository = repository
        self.products_query = products_query
        self.usage_query = usage_query
        self.delinquency_query = delinquency_query
        self.build_context = context_builder

    def validate(self, member_id, base_date):
        member = self.repository.member(member_id)
        return validate_customer(base_date, member)

    def products(self, member_id, base_date):
        self.validate(member_id, base_date)
        return self.products_query(self.repository, member_id, base_date)

    def monthly_usage(self, member_id, base_date):
        self.validate(member_id, base_date)
        return self.usage_query(self.repository, member_id, base_date)

    def delinquency(self, member_id, base_date):
        self.validate(member_id, base_date)
        return self.delinquency_query(self.repository, member_id, base_date)

    def snapshot(self, member_id, base_date):
        self.validate(member_id, base_date)
        return {
            'products': self.products_query(self.repository, member_id, base_date),
            'monthly_usage': self.usage_query(self.repository, member_id, base_date),
            'delinquency': self.delinquency_query(self.repository, member_id, base_date),
        }

    def context(self, member_id, base_date):
        data = self.snapshot(member_id, base_date)
        result = self.build_context(member_id, data['products'], data['monthly_usage'],
                                    data['delinquency'], base_date)
        return require_context(result)
