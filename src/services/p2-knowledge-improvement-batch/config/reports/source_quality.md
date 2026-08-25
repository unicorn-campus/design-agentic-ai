# 원천 품질 리포트

> 설계서의 오류율 인용값이 아닌 합성 고정 응답 실측 결과임.  
> 실제 원천 전환 시 같은 측정기를 다시 실행해야 함.

| 경로 | 행 수 | 빈 값 비율 | 중복 비율 | 형식 어긋남 | 실측 오류율 | 측정 방법 | 측정일 | 갱신 지연 | 품질 문턱 |
|---|---:|---|---:|---:|---:|---|---|---|---|
| `S-R4` | 100 | amount_bucket=0.00%, decline_reason_code=0.00%, masked_customer_id=0.00%, merchant_category_code=0.00%, transaction_date=0.00%, transaction_status=0.00% | 0.00% | 0건 | 0.00% | 합성 고정 응답 전건 스캔 | 2026-08-25 | 해당 없음 | 문턱 없음: 관찰값 |
| `S-B2` | 10000 | consultation_ref=0.00%, ended_at=0.00%, masked_summary=0.00%, reopen_count=0.00%, resolution_code=0.00%, topic_code=0.00% | 0.00% | 0건 | 0.00% | 합성 고정 응답 전건 스캔 | 2026-08-25 | 해당 없음 | 문턱 없음: 관찰값 |
| `S-B4` | 100 | consultation_ref=0.00%, ended_at=0.00%, masked_summary=0.00%, reopen_count=0.00%, resolution_code=0.00%, topic_code=0.00% | 0.00% | 0건 | 0.00% | 합성 고정 응답 전건 스캔 | 2026-08-25 | 해당 없음 | 문턱 없음: 관찰값 |

## 기준선 전달

`09-eval.md`는 위 실측값을 합성 데이터 기준선으로 사용함.  
실제 원천 결과가 확보되면 합성값과 섞지 않고 새 측정일의 행으로 교체함.
