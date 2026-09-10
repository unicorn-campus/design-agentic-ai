def build_context(member_id, base_date, products, monthly_usage, delinquency):
    lines = [
        f"[고객 기본] 고객 ID: {member_id}, 기준일: {base_date}"
    ]
    
    lines.append("[분류 상품]")
    for product in products:
        name = product["product_name"]
        fee = product["annual_fee"]
        lines.append(f" - {name}: 연회비 {fee:,}원")
    
    lines.append("[최근 사용액]")
    for usage in monthly_usage:
        month = usage["month"]
        amount = usage["total_amount"]
        lines.append(f" - {month}: 사용액 {amount:,}원")
        
    lines.append("[연체 지표]")
    if delinquency is None:
        lines.append(" - 연체지표: 확인 필요(기준월 이하 자료 없음)")
    else:
        lines.append(
            f" - {delinquency['base_month']} 기준 연체지표:\n"
            f"   12개월 연체건수: {delinquency['overdue_count_12m']:,}건"
        )
    return "\n".join(lines)

if __name__ == "__main__":
    print("context_builder.py 모듈이 직접 실행되었습니다.")
    
    demo_context = build_context("M-1004", "2026-08-31", [], [], None)
    print(demo_context)
