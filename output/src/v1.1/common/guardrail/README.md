# 미검증 설계 — 검사·가리기·기록 계층 (런치픽 v1.1)

**미검증 설계임.** 실제 부하·실물 호출·실제 차단 측정을 하지 않았음. 확인한 것은 **대역(Mock)으로
돌린 단위 시험**과 **실제 관측 SDK가 붙어 스팬을 내보내는 것까지**임(아래 9절에 무엇을 못 했는지 적음).

사고가 나기 전에 막고 무슨 일이 있었는지 남기기 위해 만든 것임 —
**입력측 · 도구 호출측 · 출력측 3지점 검사 1벌 · 가리기 매핑 1벌 · 관측 계측 · 승인 문 ·
비용 카운터 · 감사 기록.**

> 여기서 정하지 않은 것 — 어느 노드에 승인 문을 둘지(`06-workflow.md`) · 시간 상한·재시도 값(③) ·
> 커넥터 어댑터와 도구 정의(`04-connector.md`) · 지표 실측과 골든셋 평가(`09-eval.md`).

---

## 1. 무엇을 어디서 막고 무엇을 남기나

| 지점 | 무엇을 막나 | 어느 모듈 |
|------|-----------|----------|
| 입력측 | 바깥에서 온 글이 지시로 둔갑함 | `guardrail/input_guard.py` |
| 도구 호출측 | 권한 밖 실행 · 승인 없는 되돌림 불가 쓰기 · 과금 폭주 | `guardrail/tool_guard.py` · `observability/cost_counter.py` |
| 출력측 | 민감정보·위반 문장·거짓 수치가 밖으로 나감 | `guardrail/output_guard.py` |

| 남기는 것 | 어느 모듈 | 가리기 경로 |
|----------|----------|-----------|
| 단계별 관측 기록 | `observability/record.py` | `observability` |
| 오류 메시지 · 예외 스택 | `observability/record.py` (`record_error`) | `error_stack` |
| 감사 기록(되돌릴 수 없는 일) | `observability/audit.py` | `audit` |
| 개인정보 접근 기록 | `observability/record.py` (`record_access`) | `access_log` |
| 내보내기(제품 이름 없음) | `observability/exporter.py` | — |

**쉬운 말 옆풀이**

| 낱말 | 한 줄 뜻 |
|------|---------|
| 가리기(마스킹) | 민감한 값을 별표나 뒤 4자리만 남기는 식으로 바꿔 남기는 일임 |
| 거름망 | 조건 하나라도 걸리면 못 지나가게 하는 방식임. 점수를 더해 넘기는 방식이 아님 |
| 기본 거부 | 허용을 적어 두지 않은 것은 일단 못 하게 막는 원칙임 |
| 중복 방지 키(멱등성 키) | 같은 요청이 두 번 와도 한 번만 처리하게 하는 표식임 |
| 스팬 | 한 구간이 언제 시작해 언제 끝났는지 재는 기록 한 토막임 |
| 승인 표시(승인 증거) | 누가 · 언제 · 무엇을 승인했는지를 담은 값임. 참·거짓 한 값이 아님 |
| 되돌릴 수 없음(비가역) | 해시로 바꿔 남기고 되돌릴 표를 두지 않아 원문을 되살릴 수단이 없음 |

---

## 2. 검사 규칙 원본은 1벌뿐임

| 무엇 | 어디 |
|------|------|
| 검사 규칙 원본(**1벌**) | `output/src/v1.1/common/guardrail_rules.toml` |
| 자리를 갈아 끼울 환경변수 | `LUNCHPICK_GUARDRAIL_RULES_FILE` |
| 읽는 유일한 자리 | `common.guardrail.rules.load_rulebook()` |

- 코드 안에 조건을 흩어 놓지 않음. 정규식·라벨 목록·임계·보존 기간이 전부 이 파일에 있음
- 파일을 못 읽거나 ⑥과 행 수가 어긋나면 **프로그램이 뜨는 시점에** 실패함(`RuleBookInvalid`).
  검사 없이 도는 상태를 만들지 않음
- `python -m common.guardrail.rules`로 값 확인만 할 수 있음

**행 수 대조 — ⑥과 1:1**

| ⑥의 절 | ⑥ 행 수 | 설정 배열 | 실제 행 수 |
|--------|:------:|----------|:---------:|
| 6절 차단 규칙 | 32 | `block_rule` | 32 |
| 5절 출력측 검사 | 11 | `output_check` | 11 |
| 4절 입력측 검사 | 14 | `input_check` | 14 |
| 9절 마스킹 | 24 | `mask_rule` | 24 |
| 3-1 · 3-2절 승인 지점 | 15 | `approval_tool` | 15 |
| 10절 관측 기록 지점 | 15 | `record_point` | 15 |
| ③ 4절 단계(인용) | 90 | `pattern.steps` | 90 |
| ② 판정 2-2 경계 미통과 | 7 | `boundary_forbidden_design_rows` | 7 |

---

## 3. 규칙 대응표 — ⑥의 어느 행이 어느 설정 항목인가

### 3-1. 차단 규칙 32행

`설정 항목 이름`은 `block_rule[].id`이며 조건 이름은 `signal`, 행동 이름은 `action`임.

| ⑥의 행 | 설정 항목 이름(`signal`) | 검사 지점 | 걸렸을 때 행동(`action`) |
|--------|----------------------|----------|--------------------|
| B-1 | `excluded_ingredient_overlap` | 도구 | `halt_before_model` — 모델을 부르지 않고 멈춤 |
| B-2 | `hard_filter_uncertain` | 입력 | `exclude_candidate` — 해당 식당 전체 제외 |
| B-3 | `confidence_below_threshold` | 출력 | `force_safety_net` — 안전망 추천으로 강제 대체 |
| B-4 | `diet_violation_label_hit` | 출력 | `discard_sentence` — 문장 폐기 |
| B-5 | `sensitive_pattern_hit` | 출력 | `discard_sentence_and_audit` — 폐기 + 감사 기록 |
| B-6 | `learning_message_mismatch` | 출력 | `hide_message` — 메시지 비노출 |
| B-7 | `batch_quality_below_threshold` | 도구 | `forbid_commit` — 커밋 금지 |
| B-8 | `undo_window_not_elapsed` | 도구 | `hold_transfer` — 전달 보류 |
| B-9 | `consent_absent_or_unknown` | 도구 | `deny_tool_call` — 기본 거부 |
| B-10 | `daily_cost_or_call_limit_reached` | 비용 | `downgrade_to_rule_based` |
| B-11 | `per_request_call_cap_exceeded` | 비용 | `land_fallback` — 착지로 감 |
| B-12 | `approval_flag_absent` | 도구 | `deny_tool_call` |
| B-13 | `confirm_flag_absent_or_empty` | 도구 | `deny_and_reconfirm` |
| B-14 | `send_guard_absent` | 도구 | `deny_tool_call` |
| B-15 | `push_body_check_failed` | 출력 | `block_send` — 발송 차단 |
| B-16 | `business_status_closed` | 입력 | `exclude_candidate` |
| B-17 | `instruction_pattern_hit` | 입력 | `demote_to_data` — 데이터로 강등 |
| B-18 | `location_format_invalid` | 입력 | `halt_with_notice` |
| B-19 | `label_out_of_list` | 입력 | `reject_request` |
| B-20 | `card_pattern_in_pipeline` | 전 구간 | `discard_now_and_audit` — 즉시 폐기 + 감사 기록 |
| B-21 | `disclosure_item_missing` | 출력 | `safe_exit` — 승인 화면을 띄우지 않음 |
| B-22 | `approval_session_expired` | 도구 | `deny_and_reconfirm` |
| B-23 | `cancel_precondition_unmet` | 도구 | `deny_and_retry_queue` — 예약 롤백 금지 |
| B-24 | `insight_aggregate_mismatch` | 출력 | `hide_mismatched_items` |
| B-25 | `improvement_formula_absent` | 출력 | `leave_field_empty` — 칸을 비움 |
| B-26 | `transition_precondition_unknown` | 도구 | `skip_commit_notify_human` |
| B-27 | `transition_commit_failed` | 도구 | `keep_previous_state` — 이전 상태 유지 |
| B-28 | `already_premium_or_plan_unknown` | 도구 | `reject_request` |
| B-29 | `subscription_state_unreadable` | 입력 | `halt_with_notice` |
| B-30 | `idempotency_key_absent` | 도구 | `deny_tool_call` |
| B-31 | `pg_response_out_of_enum` | 입력 | `mark_pending` — `확인 중`으로 두고 닫음 |
| B-32 | `pg_auto_retry_attempted` | 도구 | `deny_tool_call` |

**차단은 거름망임** — `ToolGuard.sieve()`가 설정 순서대로 훑어 **첫 규칙**에서 멈춤.
점수를 합산하지 않으므로 실적 좋은 항목 하나로 위반을 상쇄할 수 없음.

**알릴 대상** — `notify` 칸의 `ops_unconfirmed`는
`[확인필요: 가드레일 경보·차단 알림 수신 주체]`(⑥ 소유)임. 값이 오면 이 이름만 바꿈.

### 3-2. 입력측 검사 14행

| ⑥의 행 | 방식 | 걸린 단계 | 걸렸을 때 행동 | 가동 |
|--------|------|----------|--------------|:----:|
| I-1 | 필드 지정 | S-R7 → S-R10 | 목록 밖 필드 버림 | O |
| I-2 | 필드 지정 | S-R6 → S-R10 | 목록 밖 필드 버림 | O |
| I-3 | 라벨 목록 | S-R8 | 필터 미적용 사유로 기록(B-16) | O |
| I-4 | 라벨 목록 + 패턴 | S-R3 · S-R9 | 해당 식당 전체 제외(B-2) | **X — `[확인필요]`** |
| I-5 | 패턴 | 걸 단계 없음(③) | 데이터 강등(B-17) | **X — `[확인필요]`** |
| I-6 | 필드 지정 | S-R10 · S-E7 | 칸 자체를 만들지 않음 | O |
| I-7 | 라벨 목록 + 패턴 | S-R2 · S-R3 | 추천 중단 안내(B-18) | O(라벨 절반만) |
| I-8 | 라벨 목록 | S-R2 · S-E1 | 요청 거부(B-19) | **X — `[확인필요]`** |
| I-9 | 패턴 | 전 구간 | 즉시 폐기 + 감사 기록(B-20) | O |
| I-10 | 필드 지정 | S-R16 | 출력측 검사를 다시 지남 | O |
| I-11 | 라벨 목록 | S-C6 | 사유 없이 예약 진행 | **X — `[확인필요]`** |
| I-12 | 라벨 목록 | S-S5 → S-S8 | 결제 요청 거부(B-28) | O(마스터에서 읽음) |
| I-13 | 필드 지정 | S-S9 · S-C10 · S-S13 | `확인 중`으로 둠(B-31) | O |
| I-14 | 필드 지정 | S-I2 · S-I6 → S-I3 | 중단(B-29) | O |

**방식 순서를 못 박음 — 패턴 → 라벨 목록 → 필드 지정.**
화이트리스트로 칸을 버리는 것이 먼저 돌면 카드번호 적중을 감사 기록에 남기지 못함
(`B-20`은 폐기 **+ 감사 기록**을 함께 요구함). 시험
`test_card_pattern_is_detected_before_whitelist_drops_the_field`가 이 순서를 지킴.

**바깥 글을 프롬프트에 넣는 방법은 1개뿐임**

```python
from common.guardrail import wrap_external_text

prompt_part = wrap_external_text("kakao_map", 지도_응답_문자열)
```

- 태그로 감싸고 **지시 실행 금지 문구를 병기**함. 태그 이름과 문구는 설정이 가짐
- 태그 흉내를 내는 꺾쇠는 먼저 무력화해 경계가 깨지지 않음(글자 수는 그대로 둠)
- `guardrail/input_guard.py`에 `wrap`으로 시작하는 함수가 **1개뿐**임(시험이 셈)

### 3-3. 출력측 검사 11행

| ⑥의 행 | 방식(그 행이 고른 1종) | 나가는 지점 | 걸렸을 때 행동 | 가동 |
|--------|-------------------|-----------|--------------|:----:|
| O-C1 | 라벨 목록 | S-R13 | 문장 폐기 · 기본 이유로 대체 | O(라벨은 상태에서 받음) |
| O-C2 | 라벨 목록 | S-R13 | 문장 폐기 | **X — `[확인필요]`** |
| O-C3 | 패턴 | S-R13 · S-B8 · C-10 | 폐기 + 감사 기록 | O |
| O-C4 | 필드 지정 | S-B8 | 메시지 비노출 | O |
| O-C5 | 필드 지정 | S-I10 → S-I11 | 불일치 항목만 비노출 | O |
| O-C6 | 라벨 목록 + 패턴(재적용) | C-10 | 발송 차단 | O |
| O-C7 | 필드 지정 | S-R8 → S-R9 | 후보 제외 | O(원천 Mock) |
| O-C8 | 라벨 목록 | S-S6 → S-S7 | 안전 종료 — 승인 화면 안 띄움 | O |
| O-C9 | 필드 지정 | S-C5 | 안전 종료 — 모달 안 띄움 | O |
| O-C10 | 필드 지정 | S-N4 · S-I12 | 칸 비우기 | **X — `[확인필요]`** |
| O-C11 | 패턴 | S-S12 · S-C9 | 뒤 4자리만 · 카드번호는 폐기 | O |

**방식이 3종인 이유** — ⑥ 5절은 방식을 문서 단위로 1개 고른 것이 아니라 **행마다 1개씩** 골랐고
11행에 3종이 모두 나타남(⑥ 5절 「검사 방식 3종 확인」 — `패턴` 3행 · 나머지는 `필드 지정`·`라벨 목록`).
그래서 판정기 3종을 두되 **한 행에는 그 행이 고른 방식만** 돌림. ⑥이 안 고른 방식은 어느 행에도
붙지 않음. 3종 중 1종만 만들면 11행 중 8행이 덮이지 않음.

**밖으로 나가는 모든 경로가 이 검사를 지남** — 부분 전송(스트리밍)도 예외가 아님.
조각마다 같은 `OutputGuard.redact()`를 부름(시험 `test_streaming_path_uses_the_same_check`).

**미가동 2행은 통과로 세지 않음** — `checks_disabled`에 담기고 `failed_checks()`에도 들어감.
목록이 오기 전에는 통과 판정을 낼 수 없음.

---

## 4. 가리기 표 — 필드 ↔ 방법 ↔ 변환 자리 ↔ 4경로

필드 ID(`F-n`)의 주인은 ⑤이고 변환 자리(`SL-n`)의 주인은 ②임. **새 번호를 붙이지 않았음.**
`가리기 방법 이름`은 이 산출물이 소유하는 값임(`MASK_METHODS`의 열쇠).

| `M-n` | 필드 ID(⑤) | 가리는 방법 | 변환 자리(②) | 관측 | 오류 스택 | 감사 | 접근 기록 |
|-------|-----------|-----------|-----------|:----:|:--------:|:----:|:--------:|
| M-1 | F-1 | `all_stars` | SL-1 | O | O | O | O |
| M-2 | F-2 | `token_id_only` | SL-1 | O | O | O | O |
| M-3 | F-3 | `email_local2_or_hash12` | SL-1 | O | O | O | O |
| M-4 | F-4 | `region_label_only` | SL-3 | O | O | O | O |
| M-5 | F-5 | `count_only` | SL-2 | O | O | O | O |
| M-6 | F-6 | `bool_only` | SL-2 | O | O | O | O |
| M-7 | F-7 | `drop_field` | SL-4 | O | O | O | O |
| M-8 | F-8 | `last4` | SL-4 | O | O | O | O |
| M-9 | F-9 | `count_and_category` | SL-5 | O | O | O | O |
| M-10 | F-10 | `dim_and_time` | SL-5 | O | O | O | O |
| M-11 | F-11 | `separate_store` | SL-5 | O | O | O | O |
| M-12 | F-12 | `first_char_stars` | SL-8 | O | O | O | O |
| M-13 | F-13 | `allow_value`(감사만) · `not_recorded`(그 밖) | 대응 없음 | O | O | **값 허용** | O |
| M-14 | F-14 | `last4` | SL-7 | O | O | O | O |
| M-15 | F-15 | `not_recorded` | 대응 없음 | O | O | O | O |
| M-16 | F-16 | `sentence_or_discard` · 경로별 갈림 | SL-6 | **원문 허용** | O | O | O |
| M-17 | F-17 | `hash_only` | 대응 없음 | O | O | O | O |
| M-18 | F-18 | `count_only` | 대응 없음 | O | O | O | O |
| M-19 | 기록 계열 | `field_whitelist` | — | O | O | O | O |
| M-20 | 기록 계열 | `summary_only` | SL-6 | O | O | O | O |
| M-21 | 기록 계열 | `substitute` | — | O | O | O | O |
| M-22 | 기록 계열 | `len_hash_count` | — | O | O | O | O |
| M-23 | 기록 계열 | `field_and_hash_diff` | — | O | O | O | O |
| M-24 | 기록 계열 | `hash_and_purpose` | — | O | O | O | O |

- **미적용 경로 0건임.** 24행 전건이 4경로를 다 덮는 것을 시험이 셈
  (`test_every_masking_row_has_all_four_record_paths`)
- **출력 직전 1회만 가리는 구조가 아님.** 기록 경로마다 같은 매핑 1벌을 지남
- **같은 값이 두 경계를 넘으면 두 번 가림**(⑥ 9절 두 번 넘는 데이터 4건)
- **되돌릴 수 없게 함**(3단계 되묻기 기본값). `Masker`에 `unmask`가 없고 되돌릴 표를 두지 않음
- `M-19` ~ `M-24`의 `field_id`는 `기록 계열(⑤ F-n 아님)`이라고 적었음 — ⑥ 기록 계열 6행이
  특정 필드가 아니라 기록 묶음 전체를 대상으로 하는 규칙이라 ⑤ 번호를 새로 만들지 않았음

**⑥보다 엄격하게 둔 자리 1건** — `M-8`(결제 식별자)은 ⑥이 `내부 로그는 허용`이라 적었으나,
같은 ⑥의 `M-19`가 **PG 왕복은 뒤 4자리만**을 못 박았음. 두 규칙이 갈리므로
⑥ 3-1절이 쓴 것과 같은 원칙(**엄격한 쪽을 따름**)으로 4경로 전부에 뒤 4자리를 적용했음.

**⑥이 값 기록을 명시로 허용한 자리 2건(숨기지 않고 적음)**

| `M-n` | 경로 | ⑥의 근거 |
|-------|------|---------|
| M-13 | 감사 · 응답 | 동의·구독 상태는 **감사 필수 항목**이라 값 기록 허용(⑥ 9절) |
| M-16 | 관측 · 응답 | 모델 생성문은 원문 기록 허용. 폐기는 출력측 검사가 판정(⑥ 9절) |

기록 전수 검색 시험은 이 2건을 대상에서 빼고 돌리며, 뺀 사실과 건수를 시험 안에 적어 둠.

---

## 5. 기록 항목 표 — 단계 / 항목 이름 / ③의 어느 단계에서 왔나

| `O-n` | 걸린 단계(③) | 남길 항목 이름(⑥ 그대로) |
|-------|------------|--------------------|
| O-1 | S-R2 · S-B1 · S-E1 · S-E5 | `request_id` · `trigger_kind` · `deadline_at` · 접수 시각 |
| O-2 | S-R6 · S-R7 · S-R8 | 도구명 · 소요시간 · `error.type` · 응답 필드 수 · 재시도 횟수 |
| O-3 | S-R11 · S-B5 | 프롬프트 버전 · `gen_ai.usage.input_tokens` · `gen_ai.usage.output_tokens` · 건당 환산 금액 · 일일 누적 콜 수 |
| O-4 | S-R12 | 확신 스코어 · 임계 통과 여부 · 안전망 대체 여부 |
| O-5 | S-R13 | 출력측 검사 결과 3종 · 3필드 완전성 · `fallback_reason` |
| O-6 | S-R16 · S-B10 · S-E8 | `fallback_reason` · 캐시 나이(초) · 착지 사유 |
| O-7 | S-B9 | 갱신 사용자 수 · 평균 변화량 · 임계 미달 사용자 수 · 배치 상태 · 만족 비율 |
| O-8 | 쓰기 도구 26단계 | 호출자 · 도구명 · 입력 요약 · 결과 · 소요시간 · 동의 시각·버전 · 멱등성 키 해시 |
| O-9 | 단계 아님 — 재시도 **5계층** | 단계 재시도 · 사용자 재요청 · 전달 재시도 · PG 자동 재시도 · 결제 사용자 재시도 |
| O-10 | S-R11 · S-B5 진입 직전 | 일일 콜 수 · 일일 환산 금액 · 임계 도달 여부 |
| O-11 | S-S2 · S-C2 · S-I2 · S-I6 · S-N1 · S-X1 | `request_id` · `trigger_kind` · `deadline_at` · 접수 시각 · 구획 식별자 |
| O-12 | S-S7 · S-C5 승인 게이트 | 승인 ID 해시 · 표시한 고지·안내 항목 목록 · 승인 시각 · 만료 여부 · 미승인 종료 사유 |
| O-13 | S-S9 · S-C10 PG 호출 | 도구명 · 멱등성 키 해시 · 결과 열거값 · `pg_cancel_status`<br>`error.type` · 소요시간 · 재시도 횟수 · 예약 커밋 성공 |
| O-14 | S-I10 | 대조한 항목 수 · 불일치 항목 수와 이름 · 비노출 처리 건수 · 향상률 칸을 비운 사유 · `fallback_reason` |
| O-15 | S-X2 ~ S-X7 | 전환 대상 건수 · 판정 불가로 건너뛴 건수 · 커밋 성공·실패 건수 · 열람 제한 재적용 실패 건수 · 배치 상태 · 실행 창 초과 여부 |

- **항목 이름을 빼거나 더하지 않음.** ⑥에 없는 이름을 넣으면 `UnknownRecordItem`으로 실패함
- **③이 나눈 단계를 합치지 않음.** 90단계 전건에 기록 1개씩 남음
- 재시도 5계층도 한 항목으로 합치지 않음. 어느 계층에서 터졌는지 갈라 볼 수 있음
- 실패 사유 값은 `04-connector.md`의 오류 분류 이름 4종을 그대로 씀 —
  `인증 오류` · `입력 오류` · `일시 장애` · `권한 부족`(`guardrail.errors.ToolErrorClass`).
  **`04-connector.md`는 이 열거형을 가져다 써야 함.** 같은 이름을 두 곳에 정의하면 어느 쪽이
  진짜인지 모르게 됨

### 5-1. 숫자로 보이는 대조 — ⑥ 기록 지점 15개 vs ③ 단계 90개

**두 숫자가 다름.** 합치지 않고 숫자 그대로 적음.

| 값 | 숫자 |
|----|:----:|
| ③이 나눈 단계 수 | **90** |
| ⑥ 「관측 기록 지점」 묶음 수(`O-1` ~ `O-15`) | **15** |
| 그 15묶음이 항목을 적어 준 단계 수 | **47** |
| ⑥에 기록 항목이 안 적힌 단계 수 | **43** |
| 코드가 실제로 기록을 남기는 단계 수 | **90** (= ③ 단계 수) |

- ⑥의 `O-n`은 **여러 단계를 한 묶음으로 묶은 것**이라 묶음 수(15)와 단계 수(90)가 애초에 같아질
  수 없음. `O-9`는 단계에 걸리지 않고 재시도 계층에 걸림
- **여기서 합치거나 쪼개지 않았음.** 코드는 90단계 전건에 기록 1개씩 남기고, ⑥이 항목을
  안 적어 준 43단계는 `note`에 `[확인필요: ⑥ 관측 기록 지점 미지정 단계]`를 붙여 드러냄
- **⑥에 되물을 것** — 이 43단계에 남길 항목 이름을 ⑥ 10절에 적어 주기 바람.
  7절 `[확인필요]` 목록 11번 행임

---

## 6. 승인 문 — 기본은 거부임

| 판정 | 도구 수 | 도구 |
|------|:------:|------|
| 사람 승인·확인 필수 | **3** | `C-9` 결제 등록 · `C-12` PG 중지 · `R-9` 해지 예약 |
| 제한 장치로 대체 | **10** | `C-10` · `R-2` · `R-4` · `R-5` · `R-6` · `R-7` · `R-11` · `R-13` · `R-15` · `R-16` |
| 규제가 요구해 문을 두지 않음 | **2** | `S-6-write` 감사 로그 적재 · `S-6-audit` 감사 기록·잠금 |
| 합 | **15** | 맨몸 실행 0건 |

- **표에 없는 도구 식별자는 무조건 거부함**(`mode="unknown"`). 허용을 적어 두지 않은 것은 못 함
- 승인 표시는 `누가(가려진 참조) · 언제 · 무엇을 · 보여 준 고지 항목 · 만료 시각`을 담음.
  참·거짓 한 값이 아님
- **고지 없는 승인은 승인으로 세지 않음** — `shown_items`가 비면 거부(`B-21` · `B-13`)
- **같은 승인 표시를 두 번 쓸 수 없음** — `ApprovalLedger`가 중복 방지 키와 짝지어 한 번만 통과시킴.
  `04-connector.md`의 중복 방지 키와 여기서 만나게 되어 있음
- 호출 상한 — ⑥이 값을 준 곳만 셈(`C-10` 1일 1회 · 요청당 모델 호출 2콜).
  값이 없는 상한을 지어내지 않음
- **어느 노드에 승인 문을 둘지는 여기서 정하지 않음.** `06-workflow.md`가
  `ToolGuard.evaluate()`를 부를 자리를 정함

```python
from common.guardrail import ApprovalEvidence, ToolGuard

guard = ToolGuard()
decision = guard.evaluate(
    "C-9", request_id=req, now_ms=now, evidence=evidence,
    guards_met={"pg_auto_retry_zero": True}, idempotency_key=key,
)
if not decision.allowed:
    ...  # decision.decision.user_reason_code 만 사용자에게 보임
```

---

## 7. `[확인필요]` 목록 — **23건**

이 표의 행 수(23)는 `guardrail_rules.toml`의 `[[unconfirmed]]` 행 수와 같음
(시험 `test_readme_unconfirmed_table_matches_config`가 셈).

| # | `[확인필요]` 항목 | 주인 | 누구에게 되묻나 | 값이 없어 막히는 것 |
|:-:|-----------------|------|---------------|-----------------|
| 1 | 금지 표현 라벨 목록 — 의료·영양 단정·광고성 문구 | ⑥ | 기획 · 법무 | `O-C2` 미가동 · `B-4` 절반이 빔 |
| 2 | 지시문 패턴 차단 목록 | ⑥ | 기획 · 보안 | `I-5` · `B-17` 미가동 |
| 3 | 가드레일 경보 · 차단 알림 수신 주체 | ⑥ | 운영 · 기획 | 차단 규칙 32건의 알릴 대상이 `ops_unconfirmed`로 남음 |
| 4 | 확신 스코어 노출 임계값 | ⑥(④가 지목) | 기획 | `B-3` 판정을 못 닫음 |
| 5 | 배치 품질 자가 검증 임계값 | ⑥(④가 지목) | 기획 | `B-7`이 통과·미통과를 못 가름 |
| 6 | 비식별 조치의 법령 근거 | ⑥ | 개인정보 보호책임자 · 법무 | 코드 자리 없음 — 점검 칸으로 둘 수 없음 |
| 7 | 알레르기 자유 입력의 식재료 코드 매핑 표와 허용 패턴 | ⑥(이번 판 신규) | 기획 · 지식니 | `I-4` 미가동 |
| 8 | 지역명 화이트리스트 값 목록 | ⑥(이번 판 신규) | 기획 | `I-7`의 라벨 목록 절반이 빔 |
| 9 | 거절 사유 · 피드백 키워드 고정 라벨 목록 | ⑥(이번 판 신규) | 기획 | `I-8` 미가동 |
| 10 | 해지 사유 고정 라벨 4종의 값 | ⑥(이번 판 신규) | 기획 | `I-11` 미가동(흐름은 막히지 않음) |
| 11 | ⑥ 관측 기록 지점이 안 적힌 43단계의 기록 항목 | ⑥(이번 판 신규) | 커넥니 · 플로니 | 43단계에 항목 이름이 없음 |
| 12 | 좌표 로그 정밀도 규칙 | ⑤ | 지식니 | `M-4`가 지역 라벨 자리를 비운 채 남김 |
| 13 | job_cluster 원천 | ⑤ · `V-04` | 지식니 · 기획 | `M-15` 미가동(경로 불가) |
| 14 | 추천 캐시 TTL · 갱신 지연 | ⑤ | 지식니 | `R-2` 보존 기간 칸이 빔 |
| 15 | 배치 1회 대상 사용자 수 상한과 병렬도 | ③ | 플로니 | `R-4` 제한 장치 ⓓ가 안 닫힘 |
| 16 | 해지 예약 만료 전환 배치 1회 대상 건수 상한과 병렬도 | ③ | 플로니 | `R-11` 제한 장치 ⓓ가 안 닫힘 |
| 17 | 결제 · 해지 사람 승인 대기의 유효 시간(승인 세션 만료) | ③ | 플로니 | `B-22` 기준선 없음 — `expires_at_ms`가 비면 만료로 안 셈 |
| 18 | 추천 정확도 향상률 산출식 · 원천 | ③ · ⑤ | 플로니 · 지식니 | `O-C10` 미가동 · `B-25`의 칸 비우기로만 동작 |
| 19 | 건당 단가 정본 | ① | 기획 | 금액으로 못 재고 콜 수 상한으로만 막음 |
| 20 | 배치 LLM 호출이 월 30만 건 건수 전제에 포함되는지 | ③ | 플로니 | 일일 금액 임계의 전제가 안 닫힘(콜 수 임계는 영향 없음) |
| 21 | 해지 예약 · 해지 사유 · 전환 실행 기록의 보존 기간 | ⑤ | 지식니 · 개인정보 보호책임자 | `08-deploy.md`에 넘길 기간 값이 없음 |
| 22 | S-1 · S-4 · S-5 보관분의 보존 기간 | ② · ⑤ | 지식니 · 클로니 | 같음 |
| 23 | 관측 백엔드 제품 | `D-11` · `V-07` | 사용자 | 제품 연결 보류 — 표준출력 JSON으로만 남김 |

---

## 8. 되묻기로 정한 값 — 설계서·기입란에 되돌려 적을 것

이번 판은 사용자 승인으로 **기본값으로 진행**했음.

| # | 무엇을 | 무엇으로 정했나 | 어디에 되돌려 적나 |
|:-:|-------|---------------|-----------------|
| 1 | 차단됐을 때 사용자에게 보이는 것 | **사유 구분 값만**(`B-31:mark_pending` 꼴) · 원문 미노출 | ⑥ 6절 「차단 규칙」에 노출 규격 1행 |
| 2 | 가린 값을 되돌릴 수 있게 할지 | **되돌릴 수 없게 함** — 해시 한 방향 · 되돌릴 표 없음 | ⑥ 9절 「마스킹」 머리 1행 |
| 3 | 비용 상한을 넘겼을 때 행동 | **그 요청만 중단하고 알림**(`abort_request_and_notify`) | ⑥ 7-3절 「걸렸을 때」 칸 |
| 4 | 감사 기록 보관 기간 | **6개월** — ⑤ 「보존·삭제」 · ⑥ 11절 값을 그대로 씀(개발이 정하지 않음) | 이미 그 값임 · 확정 표시만 필요 |
| 5 | 출력측 검사 방식 | **3종을 다 만듦** — ⑥이 행마다 1종씩 골라 11행에 3종이 모두 나타남 | ⑥ 5절에 `방식은 행 단위 선택임`을 1줄 명기 |
| 6 | `M-8` 결제 식별자 로그 | **4경로 전부 뒤 4자리**(⑥ 「내부 로그 허용」보다 엄격) | ⑥ 9절 `M-8` 행 — `M-19`와 갈리는 자리 조정 |

**⑥에 변경요청 1행** — ⑥ 10절 기록 지점 15묶음이 ③ 90단계 중 47단계만 덮음.
남은 43단계의 기록 항목 이름을 ⑥이 적어 주기 바람. **여기서 합치거나 지어내지 않았음.**

**③에 변경요청 0행** — 시간 상한을 여기서 만지지 않았음. 이 계층에 시간 값이 0건임
(`common.config`의 `LUNCHPICK_STEP_TIMEOUT_MS`만 인용). ⑥ 12절이 이미 남긴 2건 외에 새로 낼 것 없음.

---

## 9. 가상환경 만들기와 실행

의존성은 `../pyproject.toml`에 `==`로 고정돼 있음(확인일 2026-08-08).
`05-guardrail` 추가분은 `opentelemetry-api` · `opentelemetry-sdk` ·
`opentelemetry-exporter-otlp-proto-http` **1.44.0** 3건임.

### Windows PowerShell

```powershell
cd output\src\v1.1\common
uv venv --python 3.12
.venv\Scripts\Activate.ps1
uv sync --extra dev
python -m pytest
python -m common.guardrail.rules
```

### Windows GitBash

```bash
cd output/src/v1.1/common
uv venv --python 3.12
source .venv/Scripts/activate
uv sync --extra dev
python -m pytest
python -m common.guardrail.rules
```

### Linux / macOS

```bash
cd output/src/v1.1/common
uv venv --python 3.12
source .venv/bin/activate
uv sync --extra dev
python -m pytest
python -m common.guardrail.rules
```

바깥을 실제로 부르는 시험은 기본 실행에서 빠져 있음. 돌리려면 `python -m pytest -m live_call`.

**한글이 깨지면** — Windows 콘솔이 UTF-8이 아닐 때 `PYTHONUTF8=1`을 함께 줌.

---

## 10. 관측 내보내기 갈아 끼우는 법

| 설정 값 | 무엇이 되나 |
|--------|-----------|
| `LUNCHPICK_OTLP_ENDPOINT` 비움 | 관측 SDK가 있으면 **콘솔 내보내기** · 없으면 표준출력 JSON 한 줄씩 |
| `LUNCHPICK_OTLP_ENDPOINT` = 주소 | 그 주소로 **표준 규격(OTLP/HTTP)** 으로 내보냄 |

```python
from common.config import get_settings
from common.observability import build_sink, StepRecorder

settings = get_settings()
sink = build_sink(endpoint=settings.otlp_endpoint, service_name="lunchpick-recommendation")
recorder = StepRecorder(sink)
```

- **제품 이름이 코드에 0건임.** 어느 제품인지는 주소값이 정함(시험이 제품 이름을 훑어 셈)
- 제품이 정해지면 `observability/exporter.py`의 `OtelSink._otlp_exporter` 한 자리만 봄
  (gRPC로 갈 거면 `opentelemetry-exporter-otlp-proto-grpc`로 바꿈)
- **이름 규칙은 표준 후보임 · 조회일 2026-08-05 기준**(⑥ 10절). GenAI 이름 규칙 문서 상태가
  `Development`이며 `gen_ai.*`에 `Stable`은 0건임. `error.type` · `server.address` ·
  `server.port`만 `Stable`이므로 그 셋만 규격 이름으로 쓰고 나머지는 우리 이름을 붙였음
- 관측 SDK 사양은 코드 작성 직전에 **context7 MCP**로 확인함(2026-08-08)

---

## 11. 디렉터리 구조와 파일별 설명

```
output/src/v1.1/common/
├── guardrail_rules.toml     검사 규칙 원본 1벌. 조건·임계·보존 기간이 전부 여기 있음
├── guardrail/
│   ├── README.md            이 문서
│   ├── rules.py             규칙 원본을 읽는 유일한 자리. 어긋나면 뜨는 시점에 실패
│   ├── errors.py            오류 분류 4종(04 소유 이름) · 차단 판정 · 차단 예외
│   ├── masking.py           가리기 매핑 1벌 · 방법 22종 · 되돌릴 수 없는 표식
│   ├── input_guard.py       입력측 검사 · 바깥 글 감싸개 1개 · 경계 미통과 버리기
│   ├── tool_guard.py        승인 문 · 승인 표시 1회용 장부 · 호출 상한 · 거름망
│   ├── output_guard.py      출력측 검사 3방식 · 폐기·가림·안전 종료
│   └── hooks.py             01-runtime이 비워 둔 HookSet 자리를 채움
└── observability/
    ├── record.py            단계마다 기록 1개 · 항목 이름 검사 · 오류·접근 경로
    ├── audit.py             감사 기록(붙이기만) · 보관 기간 값 넘김
    ├── cost_counter.py      비용 카운터 · 일일·월 임계 · 최악값
    └── exporter.py          내보내기 감싸개. 제품 이름 없음
```

---

## 12. 확인하지 않은 것 (정직한 보고)

- **실물 호출로 막아 본 것이 0건임.** PG·지도·날씨·식약처·발송 채널은 ②·⑤가 Mock으로 판정했고
  이 판에서 실제로 부르지 않았음. 차단·가림은 전부 **대역 값으로 만든 시험**에서 확인함
- **부하·지연·비용 실측 0건임.** 비용 카운터는 세는 코드가 도는 것까지만 확인했고
  실제 모델 호출 금액을 재지 않았음. ① `Q-1` 응답시간 목표도 재지 않았음
- **관측 백엔드 제품에 실제로 내보내지 않았음.** 확인한 것은 관측 SDK가 붙어
  `TracerProvider` → 콘솔 내보내기까지 스팬이 나가는 것임(`-m live_call` 1건 통과).
  OTLP 주소로 실제 전송한 것은 **확인하지 못했음**
- **⑥ `Q-3` 안전성의 채점이 닫힌 8문항은 여기서도 못 열었음** — 알레르겐 판정 데이터 원천이
  없어 `B-1` · `B-2`가 실제 위반을 잡아내는지 잴 수 없음(⑥ 11절과 같은 상태).
  차단 규칙은 걸어 두었으나 **효과를 통과로 적지 않음**
- **미가동 검사 4건을 통과로 세지 않았음** — `I-4` · `I-5` · `I-8` · `I-11` 입력측 4건과
  `O-C2` · `O-C10` 출력측 2건. 목록·패턴이 오기 전에는 통과 판정을 낼 수 없음
- **`04-connector.md`가 아직 없음.** 오류 분류 이름 4종을 여기 열거형에 적었고, 04가 만들어질 때
  이 열거형을 가져다 써야 함. 04가 따로 정의하면 이름이 두 벌이 됨 — 그때 통합이 필요함
