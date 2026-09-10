"""
함수 만들기 예제
"""

def build_customer_line(member_id, base_date):
    return f"고객 {member_id}님의 조회 기준일은 {base_date}입니다."

message = build_customer_line("M-1042", "2026-08-31")
print(message)