"""완성 제공 응용 계층: 학생 또는 정답 구현을 명시적으로 연결함."""
from datetime import date
from importlib import import_module


class CustomerService:
    def __init__(self, repository, reference=False):
        self.repository = repository
        suffix = '_ref' if reference else ''
        self.products_query = import_module('src.nl2sql.04_query_products').query
        self.usage_query = import_module('src.nl2sql.04_query_usage' + suffix).query
        self.delinquency_query = import_module('src.nl2sql.04_query_delinquency' + suffix).query
        self.build_context = import_module('src.nl2sql.context_builder' + suffix).build_context

    def validate(self, member_id, base_date):
        parsed = date.fromisoformat(base_date)
        if not date(2026, 3, 1) <= parsed <= date(2026, 8, 31):
            raise ValueError('실습 조회 기준일은 2026-03-01 ~ 2026-08-31 범위임')
        member = self.repository.member(member_id)
        if member is None:
            raise ValueError('존재하지 않는 합성 고객 ID임')
        if member['join_date'] > base_date:
            raise ValueError('가입 전 기준일로 조회할 수 없음')
        return member

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
        return {'member': self.validate(member_id, base_date),
                'products': self.products(member_id, base_date),
                'monthly_usage': self.monthly_usage(member_id, base_date),
                'delinquency': self.delinquency(member_id, base_date)}

    def context(self, member_id, base_date):
        data = self.snapshot(member_id, base_date)
        result = self.build_context(member_id, data['products'], data['monthly_usage'],
                                    data['delinquency'], base_date)
        if not isinstance(result, str) or not result.strip():
            raise ValueError('context_builder.py: 빈 값 대신 Context 문자열 반환 필요')
        return result
