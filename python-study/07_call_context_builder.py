from context_builder import build_context

products = [
    {"product_name": "생활 카드", "annual_fee": 12000},
    {"product_name": "여행 카드", "annual_fee": 80000}
]

monthly_usage = [
    {"month": "2026-07", "total_amount": 600000},
    {"month": "2026-08", "total_amount": 510000}
]

delinquency = {
    "base_month": "2026-08",
    "overdue_count_12m": 0
}

context = build_context(
    member_id="1234567890",
    base_date="2026-08-31",
    products=products,
    monthly_usage=monthly_usage,
    delinquency=delinquency  
)

print(context)

