"""
조건문 사용 예제  
"""
monthly_usage = [
    { "month": "2026-05", "total_amount": 820000 },
    { "month": "2026-06", "total_amount": 700000 },
    { "month": "2026-07", "total_amount": 950000 },
    { "month": "2026-08", "total_amount": 600000 }
]

for usage in monthly_usage:
    month = usage["month"]
    amount = usage["total_amount"]

    print(f"{month}: {amount:,}원") 

old = monthly_usage[-4]
latest = monthly_usage[-1]

before = old["total_amount"]
after = latest["total_amount"]

if before is not None and before != 0 and after is not None:
    rate = (after/before - 1) * 100
    print(f"{old['month']} 대비 {latest['month']} 변화율: {rate:+.2f}%")
else:
    print("변화율: 확인필요")

