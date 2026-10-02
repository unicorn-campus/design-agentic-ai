# Agentic RAG 적용 방안 — PPT 스크립트 (1장)

대상: 「문서 검색 아키텍처 패턴」 3장 교재를 들은 교육생  
전달 목표: Agentic RAG가 "다른 패턴을 도구로 활용"한다는 말이 우리 카드 상품 문서 검색 서비스에서  
어떤 흐름이 되는지 한 장으로 보여 줌  
공통 화면 사양: 16:9(1152 × 648pt), 흰 배경, Pretendard, 본문 최소 14pt, `references/pptx-guide.md` 팔레트

---

## 슬라이드 1. Agentic RAG 적용 방안

### breadcrumb

`Ⅲ. 문서 검색 아키텍처 › 4. Agentic RAG 적용`

### 제목

`Agentic RAG 적용 방안`

### 리드문

기존 부품(검색 · 질문 변환 · 근거 검증)을 도구로 감싸고 에이전트가 골라 쓰게 함.  
Self-RAG · Adaptive · CRAG는 에이전트의 판단과 도구 안으로 들어감

### 레이아웃 패턴

**패턴 A 변형 (2단 헤더 바)** — 좌측(약 8.6″): 단색 네이비 헤더 바 `에이전트 흐름` + 틴트 박스 안 도식.  
우측(약 6.0″): 그라디언트(블루) 헤더 바 `도구와 가드레일` + 다크 배지 2개(도구 표 · 가드레일 리스트).

### 본문 — 좌측 도식 (PPT 도형으로 작도)

```
[질문 + 역할(agent/auditor)]
   ↓
[계획 — 질문 분석] ── 옆 메모 ── Self-RAG: 검색 불필요(인사·잡담) → 바로 답변
   ↓                            Adaptive: 복합 질문 → 미리 분해, 원 질문 검색도 함께
┌──────── 반복 (상한 있음) ────────┐
│ [행동 — search_docs 호출]         │
│    ↓                             │
│ [관찰 — grade_results 채점] ── 옆 박스(CRAG) ── 정확 → 근거로 쌓음
│    ↓                             │              애매 → transform_query(rewrite) 후 재검색
│ [평가 — 근거를 다 모았나?]        │              부정확 → web_search(선택) / 근거 부족 표시
│    └─ 아니오 → 앞 결과로 다음 질문 ↺ (Multi-hop) │
└──────────────────────────────────┘
   ↓ 예
[답변 생성]
   ↓
[근거 검증 — verify_evidence] ── 통과 ──→ [최종 답변]
   ↺ 실패 시 답변 재작성(최대 2회) · 끝내 부족하면 「확인 필요」로 종료
```

- 실선 노드 = 에이전트 단계, 점선 테두리 = 반복 구간
- 패턴명은 작은 태그(필 라벨)로 해당 단계 옆에 붙임

### 본문 — 우측 ① 도구 표 (다크 배지 `도구 — 기존 부품을 감쌈`)

| 도구 | 하는 일 | 담당 패턴 | 상태 |
|---|---|---|---|
| `search_docs` | Vector · Hybrid · Rerank | 검색 부품 | 기존 |
| `transform_query` | 재작성 · 분해 등 5종 | CRAG · Adaptive | 기존 |
| `grade_results` | 정확 · 애매 · 부정확 채점 | CRAG | **추가** |
| `verify_evidence` | 인용문 원문 대조 | Self-RAG | 기존 |
| `web_search` | 문서 밖 정보 보충 | CRAG | **선택** |

- 권한 필터는 `search_docs` 안에서 강제함(가드레일 2번)
- 화면 폭 때문에 셀 문구를 줄였고, 상태는 별도 열로 분리함

### 본문 — 우측 ② 가드레일 (다크 배지 `적용 시 반드시 붙일 가드레일`)

1. **LLM 호출 상한 재설정** — 현재 요청당 2회 상한으로는 루프가 돌지 못함
2. **권한은 도구 안에서 강제** — LLM이 판단하지 않고 서버(인증값)가 권한 주입
3. **결정적 관문 유지** — 점수 기준 · 인용문 대조는 LLM 판단이 아닌 규칙으로
4. **근거 부족 시 「확인 필요」로 종료** — 답을 지어내지 않음

### 출처 (하단 작게)

- 교재 「10. RAG」 5.4 · 5.5절 — https://github.com/cna-bootcamp/aistudy/blob/main/agentic-ai/textbook/10.RAG.md
- ReAct, Yao et al.(2022) — https://arxiv.org/abs/2210.03629
- Adaptive-RAG, Jeong et al.(2024) — https://arxiv.org/abs/2403.14403
- LangGraph Agentic RAG — https://docs.langchain.com/oss/python/langgraph/agentic-rag
- Anthropic, Building effective agents — https://www.anthropic.com/engineering/building-effective-agents

### 발표자 노트

- 세 패턴을 미리 그려 둔 분기로 붙이면 워크플로우이고, 다음 행동을 LLM이 실행 중에 고르면 Agentic임.  
  기준은 "몇 개 합쳤나"가 아니라 "흐름의 운전대를 누가 잡았나"임.
- 예시 「올해 비용 면제와 포인트 적립 조건을 함께 알려주세요」: 계획에서 하위 질문 2개로 분해 →  
  ① 연회비 면제 검색, 채점 정확 → ② 포인트 적립 검색, 채점 애매 → rewrite 후 재검색, 채점 정확 →  
  근거 모두 확보 → 답변 생성 → 근거 검증 통과.
- 지금 워크플로우는 질문을 미리 쪼개 한 번에 검색하지만, Agentic은 ②의 결과를 보고 나서 재검색을 고른다는 점이 다름.
- 분해(decomposition)는 질문 문장만 보고 판단 가능하므로 계획 단계에서 미리 수행.  
  rewrite · HyDE · step-back은 결과가 나쁠 때만 의미가 있으므로 관찰 단계 이후에 사용.
- 가드레일 1번이 가장 먼저 부딪히는 제약임. 도입 전 평가셋으로 정답 수와 LLM 호출 수를 함께 비교해야 함.
