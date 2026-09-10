"""
None과 0을 구분하여 연체율 계산 예제
"""

delinquency = {
    "base_month": "2026-08",
    "overdue_count_12m": 0,
    "overdue_days": 0,
    "overdue_amount": 0,
}

if delinquency is None:
    print("연체지표: 확인 필요(기준월 이하 자료 없음)")
else:
    print(
        f"{delinquency['base_month']} 기준 연체지표:\n"
        f"12개월 연체건수: {delinquency['overdue_count_12m']:,}건,\n"
        f"연체일수: {delinquency['overdue_days']:,}일,\n"
        f"연체금액: {delinquency['overdue_amount']:,}원"
    )