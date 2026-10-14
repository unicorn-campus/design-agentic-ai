# AGENTS.md 구성 한눈에 보기 — PPT 스크립트

- 산출물: `temp/agents-overview/AGENTS구성.pptx` (1장)
- 작성: 클로니(직접 수행 — 슬라이드 정리는 팀원 담당 영역 밖)
- 근거: 저장소 루트 `AGENTS.md` 전체 절(팀명 · 목표 · 행동원칙 · 멤버 · 위임 규칙 · 멀티 도구 호환 ·  
  대화 가이드 · 최적안 도출 · Git · URL · 마크다운 · 정직한 보고 · PPT · 엑셀 · 프롬프트 · 파이썬 ·  
  Lessons Learned · Advisor · 플러그인 슬래시 명령)
- 스타일: `references/pptx-guide.md` — `내용_단쪽` 레이아웃, Pretendard, 14pt 이상, 출처 줄 없음
- 표현: 표 · 불릿 나열 대신 편집 가능한 도형(층 라벨 · 카드 · 화살표)으로 구조를 그림

## 슬라이드 1 — AGENTS.md 구성 한눈에 보기

- 리드문: 목표 · 원칙(WHY) 아래 8명 팀(WHO)이 협업 · 작업 규칙(HOW)으로 움직이고, 품질 장치(CHECK)가 결과를 지킴
- 도형 구성: 왼쪽 세로 라벨 4개(WHY · WHO · HOW · CHECK) + 오른쪽 층별 카드

| 층 | 도형 | 내용 |
|----|------|------|
| WHY 목표·M사상 | 목표 카드 1 + 원칙 카드 3 | Agentic AI 아키텍처 설계(멀티모달 · LangGraph · RAG/GraphRAG · NL2SQL · 온톨로지 · MCP/A2A · MAS) / Value-Oriented(WHY First) · Interactive(Yes And) · Iterative(Fast fail · Pivot) |
| WHO 팀 8명 | 네이비 상자(클로니) → 화살표 → 팀원 카드 7 + 점선 카드 1 | 플로니 · 지식니 · 커넥니 · 모달니 · 스택니 · 옵스니 · 에듀니 + 라우팅 규칙(키워드로 담당자 선정, 해당 없으면 클로니 직접) |
| HOW 협업·작업 규칙 | 패턴 카드 2×2 + 규칙 카드 3×2 | 계층형(기본값) · 파이프라인형 · 토론형 · 협업형 / 대화 가이드 · Git 연동 · 문서·프롬프트 · 파이썬 개발 · 멀티 도구 호환 · 도구 사용 |
| CHECK 품질 장치 | 카드 3 | 정직한 보고 · Lessons Learned · Advisor 자문 |

- 발표자 노트: 위에서 아래로 "왜 → 누가 → 어떻게 → 어떻게 지키나" 순서로 읽음.  
  팀원 위임은 `.agents/agents/` 원본 정의를 Agent 도구로 실제 호출하는 방식임을 덧붙임
