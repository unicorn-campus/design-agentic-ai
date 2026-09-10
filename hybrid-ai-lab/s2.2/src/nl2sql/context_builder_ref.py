try:
    from . import _bootstrap
except ImportError:
    import _bootstrap
"""도메인 계층: DB/SDK에 의존하지 않는 Context 조립 정답."""
from datetime import date


def build_context(member_id: str, products: list[dict], monthly_usage: list[dict],
                  delinquency: dict | None, base_date: str) -> str:
    date.fromisoformat(base_date)
    lines = [f'[고객 기본] 교육용 합성 가명ID: {member_id} · 기준일: {base_date}',
             f'[보유 상품] (출처: card·product·product_annual_fee 조회, 기준일 {base_date})']
    for row in products:
        fee = row.get('annual_fee')
        fee_text = '확인 필요' if fee is None else f'{fee:,}원'
        lines.append(f"- {row['product_name']}: 연회비 {fee_text}, "
                     f"발급 {row['issue_date']}, 상태 {row['status']}")
    if not products:
        lines.append('- 조회 조건에 맞는 보유 상품 없음(조회 상한 20건)')
    lines.append(f'[최근 사용 추이 · 월별 합계, 단위 원] (출처: card_txn 승인 거래 집계, 기준일 {base_date})')
    for row in monthly_usage:
        amount = row.get('total_amount')
        value = '확인 필요' if amount is None else f'{amount:,}원'
        lines.append(f"- {row['month']}: {value}")
    if not monthly_usage:
        lines.append('- 사용 추이: 확인 필요(조회 자료 없음)')
    # 가장 최근 월과 3개월 전 월 비교. 분모가 0/누락이면 비율을 만들지 않음.
    if len(monthly_usage) >= 4:
        old, latest = monthly_usage[-4], monthly_usage[-1]
        before, after = old.get('total_amount'), latest.get('total_amount')
        rate = f'{(after / before - 1) * 100:+.1f}%' if before and after is not None else '확인 필요(비교 기준값 없음 또는 0원)'
        lines.append(f"- {old['month']} 대비 {latest['month']} 변화율: {rate}")
    lines.append(f'[연체 여부] (출처: delinquency, 조회 기준일 {base_date})')
    if delinquency is None:
        lines.append('- 연체 지표: 확인 필요(기준월 이하 자료 없음)')
    else:
        month = delinquency['base_month']
        lines.append(f"- 자료 기준월: {month} · 최근 12개월 연체 {delinquency['overdue_count_12m']}건 · "
                     f"해당 기준월 연체 일수 {delinquency['overdue_days']}일")
        if month != base_date[:7]:
            lines.append('- 현재 기준월 상태: 확인 필요(과거 기준월 자료만 존재)')
    lines.append('[미확인 항목] 상담 이력·혜택 규정·이탈 예측값: 확인 필요(S2.2 미연결)')
    return '\n'.join(lines)

if __name__ == '__main__':
    from src.nl2sql.presentation import run
    raise SystemExit(run('context', reference=True))
