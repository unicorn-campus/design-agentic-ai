# 골든셋 품질 평가 묶음 — 런치픽 v1.1

설계서 ①의 목표를 바꾸지 않고 ⑤의 골든셋 34문항을 실제 진입점 포트로 실행하는 묶음임.  
현재 실물 API 계약이 통합되지 않아 고정 대역으로 실행기 계약만 검증함. 제품 품질 실측은 `미측정`임.

## 1. 적용 판정

| 항목 | 판정 | 근거 |
|------|------|------|
| 골든셋 | 34문항 — 목록 8 · 집계 7 · 단건 5 · 의미 근접 3 · 코드 고정 8 · 해석 3 | ⑤ 9절 |
| Q-1 응답시간 | 3,000ms(p95), 최소 20표본 · 실물 전용 | ① Q-1 · ⑥ 11절 |
| Q-2 설명가능성 | GS-12 ~ GS-15 4문항 · 100% | ⑥ 11절 |
| Q-3 안전성 | 11문항 중 측정 가능 3 · 보류 8 · 노출 0건 | ⑥ 11절 |
| 실행 방식 | 한 번에 1건 · 같은 문항 순서로 2회 | `09-eval.md` 기본값 |
| 제품 실측 | 미측정 — 실제 API 진입점 미확정 | `07-api-ui` 통합 대기 |

진단값으로 경로 정확도 · 필수 요소 포함률 · 근거 추적률 · 도구 순서 정확도를 함께 냄.  
이 네 값은 ①·⑥이 정한 배포 목표가 아니므로 목표 없이 관찰값으로만 표시함.

## 2. 파일

| 파일 | 설명 |
|------|------|
| `golden_set.jsonl` | 한 문항 1행인 정답지. 정답·근거·기대 경로·도구 순서 포함 |
| `metrics.json` | ①·⑥이 소유한 목표와 실행 옵션. 목표 숫자를 코드에서 분리함 |
| `models.py` | 문항·응답·문항 결과 계약과 파일 검증 |
| `runner.py` | 진입점 호출, 실패 보존, 2회 실행, 원본·요약 리포트 생성 |
| `metrics.py` | 지표 계산과 회차 간 차이 계산 |
| `fixtures/replay_responses.jsonl` | 외부 호출 없는 고정 대역 응답. 제품 품질 근거로 사용 금지 |
| `test_runner.py` | 실행기 단위 시험 |
| `test_live_call.py` | 실물 API 전건 실행. 기본 시험에서 제외됨 |
| `reports/` | 실행 원본 JSONL과 마크다운 리포트 |

## 3. 실행

추가 의존성은 없음. `common` 가상환경의 Python 3.12와 pytest를 같이 사용함.

### Windows PowerShell

```powershell
cd output\src\v1.1
uv sync --project common --extra dev
uv run --project common pytest tests\eval -q -m "not live_call"
uv run --project common python -m tests.eval.runner
```

### Windows GitBash

```bash
cd output/src/v1.1
uv sync --project common --extra dev
uv run --project common pytest tests/eval -q -m "not live_call"
uv run --project common python -m tests.eval.runner
```

### Linux / macOS

```bash
cd output/src/v1.1
uv sync --project common --extra dev
uv run --project common pytest tests/eval -q -m "not live_call"
uv run --project common python -m tests.eval.runner
```

실물 API는 `LUNCHPICK_EVAL_API_URL`에 문항 실행 URL을 넣고 아래처럼 분리 실행함.

```powershell
$env:LUNCHPICK_EVAL_API_URL = "https://example.invalid/eval"
uv run --project common pytest tests\eval\test_live_call.py -q -m live_call
uv run --project common python -m tests.eval.runner --live-url $env:LUNCHPICK_EVAL_API_URL
```

## 4. 골든셋 열

| 열 | 뜻 |
|----|----|
| `case_id` | ⑤가 정한 GS-01 ~ GS-34 번호. 재부여하지 않음 |
| `input` | 사용자가 묻는 문장 또는 검증 질문 |
| `case_type` | ⑤의 유형 6종 중 하나 |
| `expected_route` | 기대 정형·벡터·필터·검사 경로 |
| `expected_answer` | 기계가 대조 가능한 정답 구조 |
| `must_include` | 응답에 반드시 있어야 할 값 또는 문구 |
| `evidence` | 설계·기획의 근거 위치. 비어 있으면 적재 거부 |
| `expected_tool_calls` | 순서까지 맞춰야 할 외부 도구 목록. 내부 지식 문항은 빈 목록임 |
| `metric_ids` | 문항이 계산에 들어갈 ⑥ 지표 |
| `scorable` | 지금 자동 채점 가능한지 여부 |
| `unscorable_reason` | 측정 보류일 때 필수인 사유 |

문항 추가는 ⑤ 「골든셋 문항」을 먼저 고친 뒤 JSONL에 같은 번호·유형·정답·근거를 추가함.  
문항 수를 이 평가 묶음에서 임의로 늘리거나 줄이지 않음.

## 5. 리포트 읽는 법

- `raw-*.jsonl`은 오류 문항을 포함한 실행 원본임. 오류를 표본에서 빼지 않음
- `eval-*.md`는 목표값 · 실측값 · 표본 수 · 판정 · 회차 간 차이를 함께 표시함
- 대역 모드의 Q-1은 항상 `미측정`임. 빠른 대역 응답을 제품 지연으로 보고하지 않음
- GS-19 ~ GS-26은 알레르겐 판정 원천이 없어 측정 보류임. 통과로 계산하지 않음
- GS-11·GS-34는 추천 정확도 향상률 산출식이 없어 측정 보류임

## 6. 되묻기 기본값

| 항목 | 적용값 | 설계서에 되돌릴 곳 |
|------|-------|------------------|
| 파일 형식 | 시험 폴더 아래 JSONL · 한 문항 1행 | ⑤ 9절 |
| 재현성 실행 | 같은 순서로 2회 | ① 측정 시점 |
| 실물·대역 | 실제 API 전에는 고정 대역 · `live_call` 분리 | ② 외부 서비스 구분 |
| 동시 실행 | 1건씩 순서대로 | ①·⑤ 평가 절차 |
| 모델 채점자 | 사용하지 않음 — 전건 결정론 정답지 판정 | ① 채점 수단 |

## 7. `[확인필요]` 목록 — 7건

| # | 항목 | 영향 |
|:-:|------|------|
| 1 | 실물 API 진입점 URL·응답 스키마 | 전건 제품 품질 실측과 원본 응답 수집이 막힘 |
| 2 | 알레르겐 판정 데이터 원천 | GS-19 ~ GS-26과 Q-3의 식이제한 부분 채점이 막힘 |
| 3 | 추천 정확도 향상률 산출식·원천 | GS-11·GS-34 채점이 막힘 |
| 4 | 골든셋 정답 검수자 2명 | 정답 독립 검수 완료를 보고할 수 없음 |
| 5 | 실물 API 개선 전 기준선 | 목표 대비 개선 폭을 비교할 수 없음 |
| 6 | 피크 시간대 트래픽 집중 비율과 부하시험 시나리오 | Q-1의 동시 1,000명 실측 조건이 닫히지 않음 |
| 7 | G-2 취향 반영 비율 목표값 | G-2의 통과 문턱을 정할 수 없음 |

## 8. 하지 않는 것

평가 결과가 미달이어도 검색·워크플로우·API 코드를 이 묶음에서 고치지 않음.  
문서 RAG·GraphRAG·NL2SQL은 설계 미채택이므로 평가 경로에도 추가하지 않음.
