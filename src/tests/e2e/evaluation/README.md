# Help Desk 품질 평가

## 개요

설계서 ① 「성공기준 3개」와 「품질속성 3개」의 목표를 실제 API 진입점에서  
측정하는 평가 묶음임.  
외부 커넥터는 설계서 ②의 `Yes(Mock)` 판정을 따르고 생성 모델만 Groq 실모델을 호출함.  
채점은 골든셋 정답·경로·도구·근거를 비교하는 결정론적 방식임.  
모델 채점자를 사용하지 않음.

## 가상환경과 실행

### Windows GitBash

```bash
cd src/services/p2-knowledge-improvement-batch
uv sync --group dev
export PYTHONPATH="../../common:../../tools:../p1-sync-inquiry:.:../p3-conversation-closed-event:../../tests/e2e"
uv run python ../../tests/e2e/evaluation/runner.py
```

### Windows PowerShell

```powershell
Set-Location src/services/p2-knowledge-improvement-batch
uv sync --group dev
$env:PYTHONPATH="../../common;../../tools;../p1-sync-inquiry;.;../p3-conversation-closed-event;../../tests/e2e"
uv run python ../../tests/e2e/evaluation/runner.py
```

### Linux 또는 Mac

```bash
cd src/services/p2-knowledge-improvement-batch
uv sync --group dev
PYTHONPATH="../../common:../../tools:../p1-sync-inquiry:.:../p3-conversation-closed-event:../../tests/e2e" \
  uv run python ../../tests/e2e/evaluation/runner.py
```

루트 `.env`의 `GROQ_API_KEY`가 현재 셸 환경에 주입되어 있어야 함.  
실제 키 값은 프롬프트·로그·원본 결과·리포트에 기록하지 않음.

## 측정 시점

- 최초 측정: 위 실행 명령으로 골든셋 24문항을 2회 실행함  
- 수정 후 재측정: 담당 프롬프트의 수정이 끝난 뒤 같은 명령과  
  같은 골든셋으로 다시 실행함  
- 단위 시험: `uv run pytest ../../tests/e2e/test_evaluation.py -q` 실행  
- 실호출 시험: `uv run pytest ../../tests/e2e/test_evaluation_live.py -m live_call -q` 실행

## 지표

| 지표 ID·이름 | 목표값 | 출처 | 채점 수단 |
|---|---|---|---|
| `G-1` 고객 문의 종료 | 5초 이내(p95) | ① 「성공기준 3개」 | 부하시험·추적 로그 |
| `G-2` FAQ 개선 후보 등록 | 매일 06:00 이전 100% | ① 「성공기준 3개」 | 배치·대기열 로그 |
| `G-3` 상담 종료 이벤트 처리 | 60초 이내(p95) | ① 「성공기준 3개」 | 이벤트·CRM 로그 |
| `Q-1` 응답시간 | W-01 5초, W-02 06:00, W-03 60초 | ① 「품질속성 3개」 | 부하시험과 분산 추적 |
| `Q-2` 설명가능성 | 근거 커버리지 100% | ① 「품질속성 3개」 | Grounding·감사 로그 |
| `Q-3` 안전성 | 노출 0건, 무승인 변경 0건 | ① 「품질속성 3개」 | 민감정보·승인 로그 |

목표값과 문턱은 `src/common/config/evaluation_metrics.json`에서만 읽음.

## 골든셋 열

`golden_set.jsonl`은 한 문항 1행 JSONL 형식임.  
필수 열은 `id`, `question`, `type`, `workflow`, `expected_answer`, `evidence`, `expected_path`,  
`expected_tool_calls`, `scoring_method`임.  
문항 추가 시 기존 ID를 다시 매기지 않고 새 ID를 발급함.  
정답 또는 근거가 비어 있는 문항은 실행기가 거부함.

## 사용자 확정값

| 값 | 확정 내용 | 정한 사람 |
|---|---|---|
| 문항 수·배분 | 24문항, W-1·W-2·W-3 각 8문항 | 사용자 |
| 파일 형식·위치 | 시험 코드 아래 `evaluation/golden_set.jsonl`, 한 문항 1행 | 사용자 |
| 측정 시점 | 최초 측정과 수정 후 재측정 | 사용자 |
| 개선 전 기준선 | 원천 품질 리포트 참고, 직접 대응하지 않는 지표는 미측정 | 사용자 |
| 채점자 | 결정론적 채점, 모델 채점자 미사용 | 사용자 |
| 재현성 | 같은 순서와 씨앗으로 2회 | 사용자 |
| 실물·대역 | API 진입점·생성 모델 실호출, 외부 커넥터 Mock | 사용자·설계서 ② |
| 동시 실행 | 1건씩 순서대로 실행 | 사용자 |

100% 비율 목표의 `1 ÷ (1 − 목표비율)`은 유한 표본 수를 산출할 수 없음.  
목표를 낮추지 않고 24문항 전건 성공 여부를 측정하며 유한 표본의 한계를 리포트에 남김.

## 확인필요

| # | 항목 | 영향 |
|---:|---|---|
| 1 | `[확인필요: 승인 문서 원천 건수]` | 실원천 기준 Grounding 모집단 확정 불가 |
| 2 | `[확인필요: 승인 문서 기준일]` | 최신성 기준 확정 불가 |
| 3 | `[확인필요: G-2 전체 배치 완료 시각]` | 승인 API 대역으로 06:00 완료율 측정 불가 |
| 4 | `[확인필요: G-3 이벤트 수신부터 CRM 완료 시각]` | 승인 API 대역으로 전체 p95 측정 불가 |
| 5 | `[확인필요: Q-1 전체 경로 p95]` | 조립된 전체 실행 진입점 부재 |

①에 되돌려 물은 목표값·측정 방법·채점 수단은 0건임.

## 이 묶음이 하지 않는 것

미달 원인을 측정하고 담당 프롬프트를 지정함.  
검색기·워크플로우·API·가드레일 코드를 고치지 않음.
