# 품질평가 프로그램 소스 설명서 — PPT 스크립트

- 산출물: `~/Documents/강의/신한카드/품질평가_소스설명.pptx`
- 대상 소스: `hybrid-ai-lab/ragas`(품질평가 프로그램) + `hybrid-ai-lab/retriever/vector-retriever/evaluate_retriever.py`(추가 인자)
- 참고 형식: `vector-retriever_소스설명.pptx` · `vector_bm25_소스설명.pptx` — 개요 → Ⅰ 구조 → Ⅱ 공통 뼈대 → 처리 흐름 → 설정·결과 → 정리,
  장마다 소스 발췌(파일:행) + 해설 카드
- 스타일: `references/pptx-guide.md`(`내용_단쪽`, 표지 · 경로 표시 없음, Pretendard). 최소 글자 13pt(사용자 허용 2026-10-04)
- 소스 일치: 코드 발췌는 `extract.py`가 소스 파일에서 행 범위 그대로 잘라 `snippets.json`으로 만들고 빌드가 그것만 씀.
  docstring은 빼고, 이어지지 않는 구간 사이에 `# …(생략)`을 넣음. 머리에 `파일:행`을 적음

## 슬라이드

| # | 제목 | 발췌 | 해설(도형) |
|---|---|---|---|
| 1 | 품질평가 프로그램 한눈에 보기 | — | 평가셋 준비 → 실행기 F0 ~ F7 → 비교표 흐름 + 숫자 타일 4개 |
| 2 | 목차 | — | 6장 카드 |
| 3 | Ⅰ-1 디렉토리 구조 | 폴더 트리(실제 파일 목록) | 폴더별 책임 표 |
| 4 | Ⅰ-2 Layered Architecture | — | 계층 상자 + 파일 이름 + 안쪽으로만 가는 화살표 |
| 5 | Ⅰ-3 DIP ① 포트 | ports(IndexerPort · PointerPort.write) | 포트 9개 ↔ 어댑터 표 |
| 6 | Ⅰ-3 DIP ② 조립 지점 | bootstrap(create_services) | 조립 순서 번호 카드 |
| 7 | Ⅰ-3 DIP ③ 가짜 포트로 시험 | fakes.FakeIndexer · test_runner 첫 시험 | 2단 발췌 |
| 8 | Ⅱ-1 진입 — CLI 하위 명령 | cli.main | 실행 스크립트 → 하위 명령 표, 종료 코드 칩 |
| 9 | Ⅱ-2 설정 읽기 | settings.load_settings | 우선순위 화살표 · 주요 키 표 |
| 10 | Ⅱ-3 파일 어댑터 | files(_atomic_write · ActivePointer.write) | 어댑터 4종 카드 |
| 11 | Ⅲ-1 평가셋 md → json | eval_set.parse_eval_set_markdown | md 줄 → json 칸 대응 도형 |
| 12 | Ⅲ-2 평가셋 검증 | verification.check_against_index | 검사 5종 카드 + 실측 20/20 |
| 13 | Ⅳ-1 계획 파일 검사 | plan.check_plan | 거부 · 미지원 갈래 |
| 14 | Ⅳ-2 실행 흐름 run | runner.run | F0 ~ F7 세로 흐름 |
| 15 | Ⅳ-3 F1 설정 적용 | runner._apply | 적용기 3종 카드 |
| 16 | Ⅳ-4 F2 색인 · F4 되돌리기 | runner._run_version | 포인터 상태 띠 |
| 17 | Ⅳ-5 하위 프로세스 호출 | processes._run | 실패 분류 표 |
| 18 | Ⅳ-6 되돌리기 · 이어 하기 | runner._restore · _done | 상태 6종 표 |
| 19 | Ⅴ-1 코드 채점 @k · @5 | evaluate_retriever.score_hits | k 칸 그림 + 추가 인자 표 |
| 20 | Ⅴ-2 RAGAS 입력 · 제외 | scoring.METRIC_FIELDS · split_rows | 4지표 읽는 칸 점 격자 · 제외 사유 |
| 21 | Ⅴ-3 RAGAS 채점 루프 | ragas_service.score_rows | 행 × 지표 × 반복 그림 |
| 22 | Ⅴ-4 평가자 연결 | ragas_judge.build_llm | 평가자 3종 표 |
| 23 | Ⅴ-5 Claude 어댑터 | anthropic_llm.agenerate | 왜 따로 만들었나 카드 |
| 24 | Ⅴ-6 사람 검토표 일치도 | scoring.Agreement.kappa · agreement | 2×2 표 + 교재 예시 값 |
| 25 | Ⅴ-7 비교표 판정 | compare_service.build · comparison.judge_ragas | 판정 규칙 표 |
| 26 | Ⅵ-1 계획 파일 · 설정 | plans/top_k.yaml | .env 키 표 |
| 27 | Ⅵ-2 설계서와 달라진 점 | — | README 8장 표 |
| 28 | Ⅵ-3 실측과 시험 | — | 시험 파일별 막대 + 실험 숫자 타일 |
| 29 | 정리 — 단계별 산출물 | — | 단계 → 파일 흐름 |

## 근거(슬라이드에는 넣지 않음)
- 실측: README 7장(2026-10-04) — 평가셋 20/20 통과, 청크 계획 40분 43초 · Top-k 계획 36분 49초, 포인터 실행 전후 같음
- 시험: `pytest --collect-only` — test_domain 20 · test_runner 11 · test_adapters 10 · test_services 7 = 48(live 2 포함), 리트리버 192
