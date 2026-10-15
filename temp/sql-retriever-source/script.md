# SQL 검색기 프로그램 소스 설명서 — PPT 스크립트

- 산출물: `~/Documents/강의/신한카드/sql-retriever_소스설명.pptx`
- 대상 소스: `~/workspace/crc/sql-retriever`(W-1 SQL 검색기, 커밋 3bc94db)
- 설계 근거: `~/Documents/강의/신한카드/sql_retriever_워크플로우설계서.pptx`(35장, 2026-10-15)
- 참고 형식: `vector_bm25_소스설명.pptx`, `품질평가_소스설명.pptx`. 장마다 소스 발췌(파일:행) + 해설 도형
- 스타일: `references/pptx-guide.md`(`내용_단쪽`, 경로 표시 없음, Pretendard, 가운뎃점 대신 뜻을 씀).  
  코드 발췌 최소 13pt, 표지 장표 넣음(사용자 결정 2026-10-15)
- 소스 일치: 코드 발췌는 `extract.py`가 소스 파일 행 범위를 그대로 잘라 `snippets.json`으로 만들고 빌드는 그것만 씀.  
  해설 속 값(오류 코드, 키워드, 하이퍼파라미터 등)은 소스 상수에서 옮기고 `verify_deck.py`가 소스와 대조함

## 슬라이드

| # | 제목 | 발췌 | 해설(도형) |
|---|---|---|---|
| 1 | 표지 | — | SQL 검색기 주요 소스 해설 |
| 2 | SQL 검색기 한눈에 보기 | — | S-R1 ~ S-R6 흐름(되돌림 L-1, 답할 수 없음 합류) + 숫자 타일 4개 |
| 3 | 목차 | — | 4장 카드 |
| 4 | Ⅰ-1 디렉토리 구조 | 폴더 트리(README 4장, 실제 파일 목록) | 계층별 책임 표 |
| 5 | Ⅰ-2 Layered Architecture | — | 계층 상자 + 파일 이름 + 안쪽으로만 가는 화살표 |
| 6 | Ⅰ-3 DIP ① 포트 6개 | ports(PlannerPort, SqlValidatorPort) | 포트 ↔ 구현체 ↔ 시험용 가짜 표 |
| 7 | Ⅰ-4 DIP ② 조립 지점 | bootstrap(create_planner, create_service) | 조립 순서 번호 카드 |
| 8 | Ⅱ-1 진입 CLI와 API | cli.main, api.search | 진입 2종 비교 카드 |
| 9 | Ⅱ-2 서비스와 오류 응답 | services.search | 오류 코드 8종 표(HTTP, 다시 시도) |
| 10 | Ⅱ-3 LangGraph 흐름 조립 | graph.LangGraphRunner | 노드 6개와 조건 간선 2개 그림 |
| 11 | Ⅱ-4 상태 WorkflowState | models.WorkflowState(트리거, S-R1, 내부 표시) | 단계별 출력 필드 표 |
| 12 | Ⅱ-5 남은 시간 예산 | time_budget(상수, deduction_for, check_budget) | 계산식 + 단계별 착지 표 |
| 13 | Ⅱ-6 설정 읽기 | settings.load_settings | `.env` 이름 표 |
| 14 | Ⅲ-1 S-R1 ① 형식 검사와 식별자 가림 | steps.step_r1, masking._PATTERNS | 처리 순서 카드 3개 |
| 15 | Ⅲ-2 S-R1 ② 회원 확인과 세션 변수 | postgres_repository(SQL 상수, load_member_context) | 판정 3갈래 |
| 16 | Ⅲ-3 S-R2 ① LLM 계획과 대체 경로 | steps.step_r2 | 갈래 그림(LLM, 키워드 규칙, 거절) |
| 17 | Ⅲ-4 S-R2 ② C-01 커넥터 | groq_planner(하이퍼파라미터, ChatOpenAI 생성) | 설계서 24장 값 표 |
| 18 | Ⅲ-5 S-R2 ③ 프롬프트와 응답 구조 | PLAN_JSON_SCHEMA, c01_user_prompt.md | 지키는 점 카드 |
| 19 | Ⅲ-6 S-R2 ④ 실패 분류와 키워드 규칙 | groq_planner.plan(예외 분류) | 키워드 규칙 8개 표 |
| 20 | Ⅲ-7 S-R3 ① 계획 판정 | steps._judge | 판정 결과 3종 + 다음 단계 |
| 21 | Ⅲ-8 S-R3 ② 데이터 제공 기간 | periods.provision_window | 기준일 2026-08-31 예시 표 |
| 22 | Ⅲ-9 S-R4 ① SQL 검증 순서 | sql_validator._validate | 검사 순서와 사유 코드 표 |
| 23 | Ⅲ-10 S-R4 ② 뷰, 컬럼 검사와 LIMIT | _check_tables_and_columns, _apply_row_limit | 실패 시 갈래 카드 |
| 24 | Ⅲ-11 S-R5 ① 읽기 전용 트랜잭션 | _ReadOnlyTransaction, _translate | 실행 순서 띠 |
| 25 | Ⅲ-12 S-R5 ② 실행과 결과 | PostgresRepository.execute, steps.step_r5 | 결과 처리 카드 |
| 26 | Ⅲ-13 S-R6 응답과 감사 로그 | steps.step_r6, messages.result_message | 응답 13필드 + 감사 로그 필드 |
| 27 | Ⅳ-1 시험과 실측 | — | 시험 파일별 막대 + 실측 타일 |
| 28 | Ⅳ-2 정리 — 요청 한 건의 여정 | — | 단계 → 소스 파일 흐름 |

## 근거(슬라이드에는 넣지 않음)
- 시험: `work/test_report.md`(2026-10-15) 단위 261, 통합 26. 단위 261건은 2026-10-15 이 작업 중 `pytest -q`로 다시 돌려 확인
- 실측: `work/test_report.md` 5절(LLM 453 ~ 972ms, 회원 확인 5ms, 정형쿼리 1 ~ 7ms, FQ-08 302ms)
- 설계 대조: 설계서 8 ~ 19장(단계), 20 ~ 26장(커넥터), 27 ~ 28장(시간 예산), 29 ~ 33장(부록)
