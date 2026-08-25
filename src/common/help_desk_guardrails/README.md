# 미검증 설계: Help Desk 가드레일·관측

> 실제 외부 커넥터 호출과 부하 시험은 수행하지 않음. 대역 기반 단위 시험만 완료함.  
> 규칙 원본: `src/common/config/guardrail_policy.json` 1벌임.

## 개요

입력측은 외부 문자열을 `<untrusted_contents>`로 분리함.  
설계된 시점마다 결정론적 검사를 수행함.  
도구 호출측은 승인 표시, 위임·커넥터별 호출 상한, Circuit Breaker를 적용함.  
출력측은 설계서에 지정된 패턴·필드·라벨 검사와 요청별 Kill-Switch를 적용함.  
관측 계층은 실행 문맥의 공통 라벨, 단계·구간 기록, 비용, 알림, 감사 기록을 제공함.

## 가상환경과 시험 실행

### Windows GitBash

```bash
cd src/common
uv sync --all-groups
uv run pytest -q
```

### Windows PowerShell

```powershell
Set-Location src/common
uv sync --all-groups
uv run pytest -q
```

### Linux·Mac

```bash
cd src/common
uv sync --all-groups
uv run pytest -q
```

## ⑥ 14항목 대응표

| ⑥ 항목 | 어느 코드가 받았나 | 설정 항목 | 대응 건수 |
|---|---|---|---:|
| 단계별 구조화 로그 항목 | `NodeTelemetryCallback` | `stage_logs` | 27 |
| 구간별 구조화 로그 항목 | `observation_name`·내보내기 어댑터 | `segment_logs` | 5 |
| 구조화 로그 관측 이름 규칙 | `observation_name` | `observation_names` | 4 |
| 관측 적재처 | `GuardedExporter` | `observation_sinks` | 3 |
| 입력측 처리 | `InputGuard`·`wrap_untrusted` | `input_rules` | 21 |
| 승인 지점 | `ApprovalGate` | `approval_points` | 9 |
| 위임 호출 상한 | `InvocationLimiter` | `delegation_limits` | 1: 대상 0건 |
| 커넥터 호출 상한 | `InvocationLimiter`·`retry_delays` | `connector_limits` | 9 |
| 연속 실패 차단 | `CircuitBreaker` | `circuit_breakers` | 9 |
| 비용 상한 | `CostCounter` | `cost_limits` | 3 |
| 출력측 검사 | `OutputGuard` | `output_rules` | 10 |
| 차단 규칙(Kill-Switch) | `KillSwitch` | `kill_switches` | 10 |
| 알림 임계값 | `AlertMonitor`·`AlertSender` | `alert_thresholds` | 11 |
| 마스킹 | `SensitiveDataMasker`·`GuardedExporter` | `masking` | 14 |

미대응 0건임.

## 규칙 대응표

| ⑥ 표·행 | 설정 항목 | 검사 지점 | 걸렸을 때 행동 |
|---|---|---|---|
| 입력측 처리 21행 | `input_rules` | 입력측: 각 `checkpoints` 전부 | 안전 종료·값 폐기·사람 확인 중 설계값 |
| 승인 지점 9행 | `approval_points` | 도구 호출측 | 승인 6행 기본 거부·제한 장치 1행·자동 실행 2행 |
| 위임 호출 상한 1행 | `delegation_limits` | 도구 호출측 | 위임 대상 0건 유지 |
| 커넥터 호출 상한 9행 | `connector_limits` | 도구 호출측 | 동시 실행·호출 수 초과 차단 |
| 연속 실패 차단 9행 | `circuit_breakers` | 도구 호출측 | 닫힘·열림·반열림 전이와 대체 응답 |
| 출력측 검사 10행 | `output_rules` | 출력측 | 설계 행별 가림 또는 중단 |
| 차단 규칙 10행 | `kill_switches` | 출력측·도구 호출측 | 요청별 중단과 누적 상향 조치 |
| 알림 임계값 11행 | `alert_thresholds` | 전역 | 경고·즉시 발신, 흐름은 계속 |

## 가리기 표

관측 기록의 원문 차단은 이 표가 아닌 `GuardedExporter`가 전담함.

| 필드 ID | 방법 | 변환 자리 | 오류 | 감사 | 접근 | 체크포인트 |
|---|---|---|:---:|:---:|:---:|:---:|
| `F-1` | 제외 | `SL-3` | O | O | O | O: 아예 제외 |
| `F-2` | 제외 | `SL-3` | O | O | O | O: 아예 제외 |
| `F-3` | 제외 | `SL-4` | O | O | O | O: 아예 제외 |
| `F-4` | 제외 | `SL-5` | O | O | O | O: 아예 제외 |
| `F-5` | 제외 | `SL-1` | O | O | O | O: 아예 제외 |
| `F-6` | 해싱 | `SL-2` | O | O | O | O: 암호화 어댑터 |
| `F-7` | 마스킹 | `SL-6` | O | O | O | O: 아예 제외 |

## 기록 항목

| 워크플로우 | 단계 | 설정 행 | ③ 단계 대조 |
|---|---:|---:|---:|
| `W-1` | `S-R1` ~ `S-R10` | 10 | 10: 일치 |
| `W-2` | `S-B1` ~ `S-B10` | 10 | 10: 일치 |
| `W-3` | `S-E1` ~ `S-E7` | 7 | 7: 일치 |

기록 항목 이름은 `stage_logs[].fields`에서만 읽음. 노드별 이름 조립 코드 복제 없음.  
단계 안을 더 나눠 봐야 하면 함수 이름을 새로 만들지 않음.  
③에 단계 분할 변경요청 필요함.

## 구간 기록

| 워크플로우 | 구간 | 항목 이름 |
|---|---|---|
| `W-1` | 전체 | 요청ID·전체지연·총토큰·최종상태·종료사유 |
| `W-1` | `S-R3~S-R4` | 요청ID·R-1반복횟수·상한소진여부·착지노드 |
| `W-2` | 전체 | 요청ID·전체지연·총토큰·최종상태·종료사유 |
| `W-2` | `S-B3~S-B4` | 요청ID·R-2반복횟수·상한소진여부·착지노드 |
| `W-3` | 전체 | 요청ID·전체지연·총토큰·최종상태·종료사유 |

## 적재처

| 로그 유형 | 저장소 유형 | 외부 전송 | 원문 전송 차단 | 제품 |
|---|---|---|---|---|
| 트레이싱 로그 | 사내 저장소 | 아니오 | F-1 ~ F-7 변환 뒤 요약·해시만 적재 | D-11 관측 제품 미확정 |
| 구조화 로그 | 사내 저장소 | 아니오 | 원문 필드 제외 | D-11 관측 제품 미확정 |
| 감사 로그 | 사내 저장소 | 아니오 | 변경 전후 값 가리기 | D-11 관측 제품 미확정 |

관측 이름은 OpenTelemetry Semantic Conventions 표준 후보임. 조회일 2026-08-25 기준임.  
외부 전송 대상은 0건임.

## 상한·차단

| 대상 집합 | 구분 | 동시 실행 | 호출 수 | 위임 깊이 | 재시도 간격 | 실패 임계·차단 시간 |
|---|---|---|---|---|---|---|
| 해당 없음 | 위임 | 0건 | 0건 | 0건 | 해당 없음 | 해당 없음 |
| `W-1` `C-A1`·`C-A2`·`C-A3` | 커넥터 | 각 1 | 11·2·1 | 해당 없음 | 설정의 고정·지수 값 | 3·2·2회, 60·60·120초 |
| `W-2` `C-A1`·`C-A2`·`C-A3` | 커넥터 | 각 1 | 10·4·2 | 해당 없음 | 설정의 지수 값 | 각 3회·300초 |
| `W-3` `C-A1`·`C-A4`·`C-A5` | 커넥터 | 각 1 | 4·3·2 | 해당 없음 | 설정의 지수 값 | 3·4·3회, 120·300·300초 |

상한과 Circuit Breaker 대상 집합은 각각 9건으로 일치함.  
위임 카운터와 커넥터 카운터는 별도 인스턴스로 생성함.

## 알림

| 무엇을 보나 | 임계 | 경고·즉시 | 재발송 억제 | 알릴 대상 |
|---|---|---|---|---|
| 비용 상한 소진율 | 80% | 경고 | 30분 | Help Desk 운영자 |
| 예상 대비 실제 비용 | 150% | 경고 | 30분 | Help Desk 운영자 |
| 입력 컨텍스트 소진율 | 70% | 경고 | 30분 | Help Desk 운영자 |
| 되돌아간 횟수 | ③ 반복 상한의 50% | 경고 | 10분 | Help Desk 운영자 |
| 연속 실패 차단 발생 | 1시간에 3회 | 경고 | 10분 | Help Desk 운영자 |
| 지연 | ① 목표값 초과 | 경고 | 10분 | Help Desk 운영자 |
| Grounding 실패율 | 1% | 경고 | 30분 | Help Desk 운영자 |
| 출력측 검사 적중률 | 1% | 경고 | 30분 | Help Desk 운영자 |
| 입력측 검출 건수 | 1시간에 5건 | 경고 | 10분 | Help Desk 운영자 |
| 민감 필드 검출 | 1건 | 즉시 | 없음 | Help Desk 운영자 |
| 무승인 쓰기 시도 | 1건 | 즉시 | 없음 | Help Desk 운영자 |

## 어댑터 교체

관측 내보내기는 `Exporter.export(log_type, payload)` 계약 구현체로 교체함.  
OpenTelemetry 적용 시 `TracerProvider`와 `BatchSpanProcessor`에 제품별 exporter를 주입함.  
제품명과 접속 정보는 코드에 넣지 않고 D-11과 환경변수에서 주입함.  
알림 발신은 `AlertSender.send(alert)` 계약 구현체로 교체함. 기본 구현은 stdout JSON 1줄임.

## 되묻기로 정한 값

| 항목 | 적용값 | 되돌려 적을 곳 |
|---|---|---|
| 차단 사용자 메시지 | 사유 구분 값만 표시, 원문 비공개 | `decisions.blocked_response` |
| 가린 값 복원 | 비가역 | `decisions.masking_reversible` |
| 비용 초과 행동 | ⑥ 워크플로우별 값 유지 | `cost_limits[].action` |
| 알림 발신 | stdout 1줄 + 교체 어댑터 | D-11·`decisions.alert_transport` |
| 상한 카운터 | 요청 내 실행 문맥, 요청 간 SQLite | `decisions.counter_storage` |
| 감사 보관 | W-1 600000ms·W-2 3600000ms·W-3 60000ms | ⑤ 보존·삭제·`decisions.audit_retention` |

## 확인필요

| # | 항목 | 영향 |
|---:|---|---|
| 1 | `[확인필요: D-11 관측 제품]` | 제품별 exporter와 접속 설정 생성 보류 |

확인필요 1건임. 표의 제품 셀 3곳은 같은 미확정 항목을 인용함.
