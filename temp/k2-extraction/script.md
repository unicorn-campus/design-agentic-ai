# KG 구축 K2 엔티티와 관계 추출 — PPT 스크립트

- 산출물: `temp/k2-extraction/K2추출.pptx` (2장: 입력과 결과, 코드 예제)
- 작성: 클로니, 2026-10-19
- 위치: K1 추출 단위 나누기 다음. KG 구축 준비 구간 K2 상세
- 스타일: `references/pptx-guide.md` — `내용_단쪽`, Pretendard, 14pt 이상, 편집 가능 도형, 출처 줄 없음(근거는 이 파일에만)
- 용어: "청크"는 검색용 청크만, LLM에 넣는 조각은 "추출 단위"로 씀(상담 기록은 추출 단위가 곧 검색용 청크)

## 근거(스크립트에만 기록)

| 내용 | 근거 |
|------|------|
| 추출기: neo4j-graphrag `LLMEntityRelationExtractor(llm, create_lexical_graph=False, on_error=OnError.RAISE)`, 스키마는 `GraphSchema` | `hybrid-ai-lab/verify/doc-schema-prompt-run/tools/fill_test.py` 171 ~ 176행 |
| 단위마다 `TextChunk(uid=단위 ID)` 하나로 호출, 형식 오류는 같은 입력으로 2번까지 다시, 한 건 실패는 기록하고 계속, 동시 4건 | `fill_test.py` `extract_one`, `CONCURRENCY = 4` |
| 머리줄: 메타데이터 칸을 `칸: 값 | …` 한 줄로 단위 앞에 붙여 키 속성을 채움. 상담 기록은 record_id, consult_date, channel, topic, member_pseudo_id | `fill_test.py` `head_line`, `consult_log/schema_spec.json` `metadata_header` |
| 기본 추출 지시(라이브러리 기본 프롬프트): JSON(nodes, relationships)으로만 답함, 주어진 노드와 관계 타입만 씀, 관계의 출발과 도착 타입과 방향을 지킴, 노드마다 고유 ID를 주고 관계에서 다시 씀 | neo4j-graphrag 1.22.0 `generation/prompts.py` `ERExtractionTemplate`(요약만 장표에 씀) |
| 응답 다듬기: 정해진 칸 밖 키 제거, id는 글자로, 빈 속성 제거 | `tools/common.py` `GraphSafeLLM._clean` |
| 노드 ID 앞에 단위 ID가 붙음(예: `D3_C-20260501-003_3415157c2811bedd_0000:3`) | `consult_log/output/fill_calls.jsonl` 실제 기록 |
| 모델: Groq `openai/gpt-oss-120b` | `decisions.json` `input.llm_model` |
| 상담 기록 스키마: 노드 Consultation, Complaint, Proposal, ReconsiderCondition / 관계 HAS_COMPLAINT, HAS_PROPOSAL, RECONSIDER_WHEN, FOLLOWS / 패턴 4개. 설명에 해당과 비해당을 함께 적음 | `consult_log/graph_schema.json` |
| 상담 기록 시험(라운드 5): 18건, 실패 0, 재시도 0, 건당 평균 4.8초, 역량 질문 C1 ~ C5 모두 통과 | `consult_log/output/fill_metrics.json`, `fill_calls.jsonl` |
| 예시 상담 C-20260501-003(698자)의 실제 추출: Consultation 2, Proposal 2, ReconsiderCondition 1 / HAS_PROPOSAL 2, RECONSIDER_WHEN 1, FOLLOWS 1. 접수 연락처는 원문에서 이미 [삭제] | `fill_calls.jsonl`, `prepared-chunks.json` |
| 약관은 조항 단위로도 합격 기준(R2 ~ R5) 미달 | `RESULT.md` 191행 |

- 코드는 스키마 설계의 채우기 시험(8단계) 코드임. 인덱싱 K2는 같은 추출기에 승인된 `graph_schema.json`과 승인된 추출 단위를 씀(프롬프트 182행 "후보 추출, 시험, 인덱싱은 같은 추출 단위")
- 시험 코드는 추출 직후 가지치기(K3)까지 한 함수에서 함. 장표 2 발췌는 K2 부분만 남기고 `return graph`로 끝냄

---

## 장표 1. K2 엔티티와 관계 추출: 무엇을 넣고 무엇을 받나

- 제목: KG 구축 K2 엔티티와 관계 추출
- 리드문: 추출 단위 하나와 승인된 그래프 스키마를 LLM에 넣어, 스키마 모양대로 노드와 관계를 JSON으로 받음

**도형 구성**

1. 왼쪽 「LLM에 넣는 것」 카드 4개(위에서 아래로): 승인된 그래프 스키마(노드 4, 관계 4, 패턴 4와 해당, 비해당 설명) /
   머리줄(record_id, 상담일, 채널, 주제, 가명 회원 키) / 추출 단위 본문(상담 1건 698자) / 추출 지시(JSON으로, 주어진 타입만, 관계 방향 지킴)
2. 가운데 LLM 상자(네이비): gpt-oss-120b(Groq), 단위 하나에 호출 한 번
3. 오른쪽 「나온 그래프 (상담 C-20260501-003 실제 결과)」: 세 칸 줄 4개(노드 → 관계 → 노드)
   - Consultation(C-20260501-003, 콜센터) → HAS_PROPOSAL → Proposal(종이 영수증 대조, 거절)
   - Consultation → HAS_PROPOSAL → Proposal(주문 내역 화면 대조, 수용)
   - Proposal(주문 내역 화면 대조) → RECONSIDER_WHEN → ReconsiderCondition(다음 명세서 나올 때 다시 문의)
   - Consultation → FOLLOWS → Consultation(C-20260302-002, 앞 상담)
4. 아래 규칙 카드 4개: 형식 오류는 같은 입력으로 2번까지 다시 / 한 건 실패는 기록하고 계속(동시 4건) /
   노드 ID에 단위 ID가 붙음(K4에서 검색용 청크와 이음) / 스키마 밖 노드와 관계는 K3에서 지움
5. 맨 아래 결과 띠: 상담 기록 시험 18건, 실패 0, 재시도 0, 건당 평균 4.8초, 역량 질문 5개 모두 통과.
   약관은 조항 단위로도 아직 미달

**발표자 노트**

K2는 추출 단위 하나를 LLM에 넣어 노드와 관계를 받는 단계입니다. LLM에는 네 가지가 들어갑니다. 승인된 그래프 스키마, 메타데이터
머리줄, 추출 단위 본문, 그리고 라이브러리의 기본 추출 지시입니다. 스키마의 설명에는 해당하는 것과 해당하지 않는 것을 함께 적어서
LLM이 경계를 판단하게 합니다. 머리줄은 상담 번호나 날짜처럼 본문에 잘 드러나지 않는 키 속성을 채우려고 붙입니다.
예시 상담에서 LLM은 상담사가 권한 두 가지 방법을 제안 노드로, 고객이 말한 다시 문의할 조건을 재검토 조건 노드로 뽑고,
본문에 적힌 앞 상담 번호로 이전 상담과 이었습니다. 응답 형식이 깨지면 같은 입력으로 두 번까지 다시 묻고, 그래도 안 되면
그 단위만 실패로 기록하고 나머지를 계속합니다. 노드 ID 앞에는 단위 ID가 붙어서 K4에서 검색용 청크와 이을 수 있습니다.

---

## 장표 2. K2 코드 예제

- 제목: K2 엔티티와 관계 추출 코드
- 리드문: 추출기 하나를 만들고, 단위마다 머리줄을 붙여 호출하며, 형식 오류는 다시 시도함
- 왼쪽 코드 상자 「추출기 만들기와 extract_one (fill_test.py 발췌)」
- 오른쪽 위 「LLM이 돌려준 JSON (다듬은 뒤, 일부)」: 상담 C-20260501-003의 Consultation, Proposal(수용), ReconsiderCondition과 관계 2개
- 오른쪽 아래 카드 두 개: 응답 다듬기(GraphSafeLLM: 정해진 칸 밖 키 제거, id는 글자로, 빈 속성 제거) /
  노드 ID 앞에 단위 ID가 붙음(`"3"` → `D3_C-20260501-003_…_0000:3`)

**발표자 노트**

추출기는 한 번만 만듭니다. LLM, 그리고 검색용 청크 노드는 만들지 않는다는 설정, 오류가 나면 예외로 올린다는 설정을 줍니다.
단위마다 머리줄을 붙인 글을 TextChunk 하나로 감싸 넣는데, 이때 uid에 단위 ID를 줍니다. 그래서 돌려받은 노드 ID 앞에 단위 ID가
붙습니다. 형식 오류는 같은 입력으로 두 번까지 다시 묻고, 받은 그래프는 다음 단계인 가지치기로 넘깁니다.
