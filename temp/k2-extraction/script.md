# KG 구축 K2 엔티티와 관계 추출 — PPT 스크립트

- 산출물: `temp/k2-extraction/K2추출.pptx` (2장: 입력과 결과, 코드 예제)
- 작성: 클로니, 2026-10-19 (v0 소스 기준으로 재작성)
- 위치: K1 추출 단위 나누기 다음. KG 구축 준비 구간(K1 ~ K3)의 K2 상세
- 스타일: `references/pptx-guide.md` — `내용_단쪽`, Pretendard, 14pt 이상, 편집 가능 도형, 출처 줄 없음(근거는 이 파일에만)
- 용어: "청크"는 검색용 청크만, LLM에 넣는 조각은 "추출 단위"로 씀(상담 기록은 추출 단위가 곧 검색용 청크)

## 근거(스크립트에만 기록)

모든 코드와 수치는 `hybrid-ai-lab/indexer/graphrag/v0`(이하 v0) 기준임.

| 내용 | 근거 |
|------|------|
| 스키마: 문서 유형마다 승인 기록이 있는 `graph_schema.json`을 `GraphSchema.from_file`로 읽음 | v0 `kg_build.py` `load_schemas` |
| 머리줄 칸: `schema_spec.json`의 `metadata_header`. 상담 기록은 record_id, consult_date, channel, topic, member_pseudo_id | `load_schemas`, `_head_line`, `schema/doc/consult_log/schema_spec.json` |
| 추출기: `LLMEntityRelationExtractor(llm=llm, create_lexical_graph=False, on_error=OnError.RAISE)`, 가지치기 `GraphPruning()`, 동시 `asyncio.Semaphore(config.LLM_CONCURRENCY)` = 4 | `kg_build.py` `prepare` 안 `run_all`, `config.py` |
| 단위마다 `TextChunk(text=머리줄+본문, index=0, uid=단위 ID)` 하나로 호출. 형식 오류는 `config.LLM_RETRIES`(2)번까지 다시, 끝내 실패하면 `{"error": …}`를 돌려주고 `failed_units`에 남김 | `kg_build.py` `_k2_k3_one`, `prepare` |
| K3 가지치기를 같은 함수에서 바로 함. 결과는 `graph.model_dump()`로 돌려주고 오케스트레이터가 `kg_prepared.json`에 보관. Neo4j에는 K4에서 씀 | `_k2_k3_one`, `orchestrator.py` `step3_build_full` |
| 재사용: (문서 유형, 본문 해시, 스키마 지문)이 앞 세대 결과와 같으면 LLM을 부르지 않음 | `kg_build.py` `prepare`의 `cache` |
| 추출 지시는 라이브러리 기본 프롬프트(v0는 `prompt_template`을 주지 않음): JSON(nodes, relationships)으로만, 주어진 타입만, 관계 방향 지킴 | neo4j-graphrag 1.22.0 `ERExtractionTemplate`(요약만 장표에 씀) |
| 응답 다듬기: 정해진 칸 밖 키 제거, id는 글자로, 빈 속성 제거 | `common.py` `GroqLLM._clean` |
| 모델: Groq `openai/gpt-oss-120b`, JSON 모드, temperature 0 | `config.py` `LLM_MODEL`, `common.py` `GroqLLM.invoke` |
| 노드 ID 앞 단위 ID: 라이브러리가 `uid`를 노드 ID 앞에 붙임(예: `D3_C-20260501-003_c7974732fbb9ceb3_0000:p1`). K4에서 `Neo4jWriter`가 임시 ID로 관계 양 끝을 찾은 뒤 지움. 검색용 청크와 잇는 것은 추출 단위 노드(라벨 Chunk)의 `parent_chunk_ids`와 FROM_CHUNK 관계 | `kg_build.py` `_k2_k3_one` 주석, `apply` K4 주석 |
| 예시 그래프: v0 세대 `gen-sample-001-bd2b148b`의 `kg_prepared.json`에 보관된 상담 C-20260501-003 결과. 노드 5(Consultation 2, Proposal 2, ReconsiderCondition 1), 관계 4(HAS_PROPOSAL 2, RECONSIDER_WHEN 1, FOLLOWS 1), 가지치기로 지운 노드 0 | 증분 색인 `sample-002` 실행. 표본 v2라 본문 끝에 시험용 상담사 한 줄이 붙은 740자 본문임(장표에 나온 4줄은 그 줄과 무관) |
| 같은 원문(698자)을 2026-10-19 v0 코드로 한 번 더 추출: 노드 4개. 재검토 조건이 따로 노드가 되지 않고 Proposal의 reason 속성에 들어감 | scratchpad `k2_one.py` 실행(토큰 4,076). 발표자 노트에서 "부를 때마다 결과가 조금씩 다름"의 근거로만 씀 |
| 표본 수치: 전체 재색인 `sample-001` 추출 단위 24개, LLM 24번, 실패 0, 토큰 76,401 / 증분 색인 `sample-002` LLM 1번, 재사용 3개 | `build_report.json`, 실행 로그, v0 `README.md` |
| 약관 스키마는 합격 기준 미달 상태로 확정되어 사용 중 | `schema/doc/regulation/approval.json` `below_criteria` |

- 장표 2 코드는 `kg_build.py` 원문 발췌임. 줄 나눔만 장표 폭에 맞게 바꾸고, 생략은 `…`로 표시, 주석 일부는 장표용으로 붙임

---

## 장표 1. K2 엔티티와 관계 추출: 무엇을 넣고 무엇을 받나

- 제목: KG 구축 K2 엔티티와 관계 추출
- 리드문: 추출 단위 하나와 그 문서 유형의 그래프 스키마를 LLM에 넣어, 스키마 모양대로 노드와 관계를 JSON으로 받음

**도형 구성**

1. 왼쪽 「LLM에 넣는 것」 카드 4개(위에서 아래로):
   - ① 문서 유형별 graph_schema.json: 상담 기록은 노드 4, 관계 4와 해당, 비해당 설명
   - ② 머리줄 (메타데이터 5칸): record_id, 상담일, 채널, 주제, 가명 회원 키
   - ③ 추출 단위 본문 (K1 결과): 상담은 검색용 청크 1개가 곧 단위 1개
   - ④ 추출 지시 (라이브러리 기본): JSON으로, 주어진 타입만, 관계 방향 지킴
2. 가운데 LLM 상자(네이비): gpt-oss-120b (Groq), 단위 하나에 1번, 동시 4건
3. 오른쪽 「나온 그래프 (v0 표본 실행, 상담 C-20260501-003)」: 세 칸 줄 4개(노드 → 관계 → 노드)
   - Consultation(C-20260501-003, 콜센터) → HAS_PROPOSAL → Proposal(종이 영수증 대조, 거절)
   - Consultation → HAS_PROPOSAL → Proposal(주문 내역 화면 대조, 수용)
   - Proposal(주문 내역 화면 대조) → RECONSIDER_WHEN → ReconsiderCondition(다음 명세서 나올 때 다시 문의)
   - Consultation → FOLLOWS → Consultation(C-20260302-002, 앞 상담)
4. 아래 규칙 카드 4개:
   - 같은 본문은 다시 묻지 않음: 본문 해시와 스키마 지문이 같으면 앞 결과를 씀
   - 형식 오류는 다시: 같은 입력으로 2번까지 다시 물음
   - 실패는 기록하고 계속: failed_units에 남기고 나머지 단위는 진행
   - 노드 ID 앞 단위 ID는 임시: 단위끼리 ID가 겹치지 않게 함. K4 적재 중에만 씀
5. 맨 아래 결과 띠(네이비):
   - v0 표본: 전체 재색인 단위 24개, LLM 24번, 실패 0, 토큰 76,401 / 증분 색인 LLM 1번, 3개 재사용
   - 결과는 K3까지 마친 뒤 kg_prepared.json에 보관만 함. Neo4j에는 K4 반영 때 씀

**발표자 노트**

K2는 추출 단위 하나를 LLM에 넣어 노드와 관계를 받는 단계입니다. LLM에는 네 가지가 들어갑니다. 그 문서 유형의 graph_schema.json,
메타데이터 머리줄, 추출 단위 본문, 그리고 라이브러리의 기본 추출 지시입니다. 머리줄은 상담 번호나 날짜처럼 본문에 잘 드러나지
않는 키 속성을 채우려고 붙입니다.
예시 상담에서 LLM은 상담사가 권한 두 방법을 제안 노드로, 고객이 말한 다시 문의할 조건을 재검토 조건 노드로 뽑고, 본문에 적힌
앞 상담 번호로 이전 상담과 이었습니다. 다만 같은 원문을 한 번 더 넣었더니 재검토 조건이 제안의 이유 속성으로 들어갔습니다.
LLM은 부를 때마다 결과가 조금씩 다릅니다. 그래서 본문과 스키마가 그대로인 단위는 다시 묻지 않고 앞 결과를 씁니다.
노드 ID 앞에 붙는 단위 ID는 단위끼리 ID가 겹치지 않게 하는 임시 표시입니다. 검색용 청크와 잇는 일은 K4에서 추출 단위 노드와
FROM_CHUNK 관계가 맡습니다.

---

## 장표 2. K2 추출 코드

- 제목: K2 추출 코드 (kg_build.py)
- 리드문: 추출기는 한 번 만들고, 단위마다 머리줄을 붙여 부르며, K3 가지치기까지 마친 결과를 파일로 보관함
- 왼쪽 코드 상자 「추출기 만들기와 _k2_k3_one (kg_build.py 발췌)」
- 오른쪽 위 코드 상자 「kg_prepared.json에 보관한 결과 (일부)」: unit_id, text_hash, schema_signature, graph의 Proposal 노드 1개와
  RECONSIDER_WHEN 관계 1개. 노드 ID 앞에 단위 ID가 붙은 모습
- 오른쪽 가운데 코드 상자 「앞 세대 결과 재사용 (prepare 발췌)」: cache.get → reused 또는 todo
- 오른쪽 아래 카드: 응답 다듬기 (GroqLLM._clean): 정해진 칸 밖 키 제거, id는 글자로, 빈 속성 제거

**발표자 노트**

추출기는 한 번만 만듭니다. 검색용 청크 노드는 만들지 않고, 오류가 나면 예외로 올리게 설정합니다. 단위마다 머리줄을 붙인 글을
TextChunk 하나로 감싸 넣는데, uid에 단위 ID를 줍니다. 그래서 돌려받은 노드 ID 앞에 단위 ID가 붙습니다.
형식 오류는 같은 입력으로 두 번까지 다시 묻고, 그래도 안 되면 오류를 돌려줘 실패 목록에 남깁니다. 받은 그래프는 같은 함수에서
바로 가지치기를 하고, 결과를 kg_prepared.json에 보관합니다. 다음 실행에서는 본문 해시와 스키마 지문이 같으면 이 보관 결과를
그대로 씁니다.
