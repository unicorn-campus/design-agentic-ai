# 검색 갈래 ③ 검색 엔진에 쓰기 — PPT 스크립트

- 산출물: `temp/search-engine-write/검색엔진쓰기.pptx` (3장)
- 작성: 클로니, 2026-10-19
- 위치: 「2. 인덱싱: 1-b 분리형(검색 엔진)의 인덱싱 파이프라인」 검색 갈래 ③ 「검색 엔진에 쓰기(문서 단위로 넣고 지움)」 설명.
  키워드 분석 장표(`temp/keyword-analysis/키워드분석.pptx`) 다음에 둠
- 스타일: `references/pptx-guide.md` — `내용_단쪽`, Pretendard, 14pt 이상, 편집 가능 도형, 출처 줄 없음(근거는 이 파일에만)

## 근거(스크립트에만 기록)

| 내용 | 근거 |
|------|------|
| `step3_write_documents`, `to_engine_document`, `document_id_of` 코드 | `hybrid-ai-lab/verify/search-branch-example/search_branch.py` |
| 엔진 문서 필드(`chunk_id`, `doc_id`, `text_hash`, `text`, `text_tokens`, `embedding`, 메타데이터 키워드 필드) | 같은 파일 `build_index_mapping`, `to_engine_document` |
| chunk_id 꼴 `{문서키}_{본문해시16}_{순번4}`, 예 `D1_27223010abe31291_112f1e4abea05436_0000` | `document_id_of` docstring, `prepared-chunks.json` |
| 시험 b: 약관 문서 10개 중 첫 청크 본문을 고쳐 ID가 바뀌고 마지막 청크를 뺌 → 9개 | `run_test.py` b 장면, `run.log` |
| 시험 f: 활성 세대에 그 문서를 다시 쓸 때 지움 9, 넣음 10, 고아 없음 | `run.log` f-2, f-3 |
| `delete_by_query`의 `refresh=True`는 요청이 끝난 뒤 반영, `conflicts="proceed"`는 버전 충돌이 나도 멈추지 않고 셈 | OpenSearch Delete by query API 문서 |
| `helpers.bulk`는 일부 실패 시 `BulkIndexError` | opensearch-py `helpers` (context7 `/opensearch-project/opensearch-py`) |

- 장표 1의 「낱개로 덮어쓰기」 결과(11개, 고아 2개)는 `_id` 덮어쓰기 규칙으로 따진 결과임(실행한 시험 아님).
  `_id`가 같은 8개는 덮어써지고, 새 ID 1개는 추가되고, 옛 첫 청크와 뺀 청크 2개는 지울 주체가 없어 남음
- 장표 2의 코드는 실제 소스에서 타입 표기, docstring, `str()` 변환, 빈 입력 처리를 줄이고 단계 주석을 붙인 발췌임.
  처리 순서와 호출 인자는 소스와 같음

---

## 장표 1. 문서 단위로 지우고 넣어야 고아 청크가 안 남음

- 제목: 검색 갈래 ③ 검색 엔진에 쓰기
- 리드문: 문서 하나를 통째로 지우고 다시 넣어, 고친 문서의 옛 청크가 남지 않게 함

**도형 구성**

1. 맨 위 줄(y 1.9 ~ 2.75): 「고친 문서」 다크 배지 + 청크 칸 흐름
   - 고치기 전: 약관 문서 청크 칸 10개(1 ~ 10)
   - 화살표 라벨: 1번 본문 수정(ID 바뀜), 10번 삭제
   - 고친 뒤: 칸 9개(1′ 블루, 2 ~ 9 흰색)
2. 가운데 두 칸(y 2.95 ~ 5.25)
   - 왼쪽 「청크 단위로 교체하는 방식 (chunk_id 기준)」 회색 헤더: 인덱스 결과 칸 11개(옛 1과 10은 점선 회색 칸에 "고아" 표시)
     → 판정 다크 카드: 11개 남음. 옛 1번과 빠진 10번이 검색에 섞여 나옴
   - 오른쪽 「문서 단위로 교체하는 방식 (doc_id 기준)」 블루 헤더: [doc_id가 같은 청크 10개 지움] → [새 청크 9개 넣음] → 결과 칸 9개
     → 판정 블루 카드: 9개만 남음. 고아 없음
3. 아래(y 5.45 ~ 7.95): 「검색 엔진에 넣는 한 건 = 청크 하나」 헤더 바
   - 필드 칩 7개(이름 + 하는 일): `_id = chunk_id`(같은 청크는 덮어씀), `doc_id`(지울 때 쓰는 원천 문서 키),
     `text_hash`(벡터 재사용 판단), `text`(보여 주기용, 색인 안 함), `text_tokens`(토큰화된 낱말),
     `embedding`(색인용 본문을 벡터화), `메타데이터`(카드명, 회원 키 등 필터)
   - doc_id 만드는 법 줄: `D1_27223010abe31291` | `_112f1e4abea05436` | `_0000`을 세 칸으로 나눠 그림
     (문서 키 / 본문 해시 / 청크 순번) → "chunk_id의 앞 칸만 남기면 doc_id. 본문이 바뀌어도 문서 키는 그대로"

**사람 검토 반영(2026-10-19)**

- 사용자가 PowerPoint에서 고친 글을 그대로 `build.js`에 옮김: 두 칸 헤더(청크 단위로 교체하는 방식, 문서 단위로
  교체하는 방식), 아래 헤더(검색 엔진에 넣는 한 건 = 청크 하나), 필드 칩 설명 4개, 순번 칸, doc_id 설명 문장
- 헤더 앞의 공백 한 칸만 뺌. 고치기 전 덱은 `검색엔진쓰기.before-review.pptx`
- 검토 의견 3곳은 사용자 승인 뒤 고침:
  - `embedding` 칩 "text_tokens를 벡터화" → "색인용 본문을 벡터화"(임베딩 입력은 `index_text or text`, 낱말 목록이 아님)
  - doc_id 문장 "청크 순번의 앞 칸" → "chunk_id의 앞 칸"(순번은 맨 뒤 칸이고, 문서 키는 chunk_id의 앞부분임)
  - `text_hash` "청크 재사용 판단 용도" → "벡터 재사용 판단"(청크는 새 세대에 다시 쓰고, 재사용하는 것은 벡터임)

**발표자 노트**

검색 엔진에 쓸 때는 청크 하나를 엔진 문서 하나로 넣습니다. 문제는 문서를 고쳤을 때입니다. 청크 ID에는 본문 해시가 들어 있어서
본문이 바뀌면 ID도 바뀝니다. 그래서 청크 ID로 덮어쓰기만 하면 옛 ID의 청크와 빠진 청크가 지울 주인 없이 남습니다.
이렇게 남은 고아 청크는 이미 고친 옛 내용을 검색 결과에 섞어 냅니다. 그래서 문서 키로 그 문서의 청크를 먼저 모두 지우고
새 청크를 넣습니다. 문서 키는 청크 ID의 앞 칸이라 본문이 바뀌어도 변하지 않습니다.

---

## 장표 2. 코드 예제

- 제목: ③ 검색 엔진에 쓰기 코드
- 리드문: 문서별로 묶고, 옛 청크를 지우고, 새 청크를 한꺼번에 넣은 뒤 바로 보이게 함

**도형 구성**

1. 왼쪽(x 0.557, w 7.9, y 1.9 ~ 7.95): 코드 상자 「search_branch.py 발췌」, 14pt
   ```python
   def step3_write_documents(client, index, documents):
       # ① 문서(doc_id)별로 묶음
       grouped = {}
       for document in documents:
           grouped.setdefault(document["doc_id"], []).append(document)
       # ② 문서마다 옛 청크를 통째로 지움
       deleted = 0
       for doc_id in grouped:
           response = client.delete_by_query(
               index=index,
               body={"query": {"term": {"doc_id": doc_id}}},
               refresh=True, conflicts="proceed")
           deleted += response.get("deleted", 0)
       # ③ 새 청크를 한꺼번에 넣음 (_id = chunk_id)
       actions = [{"_index": index, "_id": d["chunk_id"], "_source": d}
                  for docs in grouped.values() for d in docs]
       helpers.bulk(client, actions, max_retries=3)
       # ④ 바로 검색되게 반영
       client.indices.refresh(index=index)
       return WriteReport(deleted, len(actions), tuple(grouped))
   ```
2. 오른쪽(x 8.757 ~ 15.457): 넘버 배지 카드 4개
   - ① 문서별로 묶음: 여러 문서가 한꺼번에 들어와도 문서마다 따로 지움
   - ② 옛 청크 지우기: `term doc_id`로 그 문서 청크를 모두 지움. `refresh=True`라 지운 결과가 바로 반영됨.
     `conflicts="proceed"`는 지우는 중 충돌이 나도 멈추지 않음
   - ③ 한꺼번에 넣기: `_id`를 chunk_id로 고정해 같은 입력을 두 번 넣어도 건수가 그대로임. 일부가 실패하면 `BulkIndexError`
   - ④ 반영: 넣은 청크가 다음 검색부터 보임
3. 오른쪽 아래: 시험 결과 칩 「지움 9 → 넣음 10, 고아 0」 + 주의 콜아웃 + 세대 전환 이름표 비교 카드 2개
   - 콜아웃: 운영 중인 인덱스에 바로 쓰면 ②와 ③ 사이에 그 문서가 잠깐 안 보임.
     그래서 전체 재색인은 새 세대에 쓰고 검색이 보는 이름표만 바꿈
   - 카드 「벡터DB 인덱싱의 활성 세대 파일」(사용자 수정 제목): active_generation.json 교체 / 리트리버가 새 세대를 다시 읽어 올림
   - 카드 「검색엔진 별칭」(사용자 수정 제목): card_chunks를 새 인덱스로 옮김 / 엔진 안 이름표라 모든 검색에 바로 적용
   - 근거: 1-a 포인터 교체 `indexer/vector-bm25/app/infrastructure/index_repository.py` 64행(`os.replace`),
     리트리버가 요청마다 포인터를 읽고 세대가 바뀌면 새 세대를 올림 `retriever/vector-retriever/app/infrastructure/index_store.py`
     416 ~ 449행(`acquire`, 백그라운드 재적재 중에는 옛 세대로 응답)

**발표자 노트**

코드는 네 덩어리입니다. 먼저 들어온 청크를 문서 키로 묶습니다. 다음으로 문서마다 delete_by_query로 그 문서의 옛 청크를 모두
지웁니다. refresh를 켜 두어야 지운 결과가 바로 반영됩니다. 그다음 bulk로 새 청크를 한꺼번에 넣는데, 이때 _id를 청크 ID로
고정해 두면 같은 입력을 두 번 넣어도 건수가 늘지 않습니다. 마지막으로 refresh를 불러 다음 검색부터 보이게 합니다.
시험에서는 고친 문서를 다시 쓸 때 옛 청크 9개를 지우고 10개를 넣었고, 남은 고아 청크는 없었습니다.
지금 쓰는 인덱스에 바로 쓰면 지우기와 넣기 사이에 그 문서가 잠깐 보이지 않으므로, 전체 재색인은 새 세대에 쓰고 별칭을 바꿉니다.
별칭은 1-a의 활성 세대 파일(active_generation.json)과 같은 역할입니다. 둘 다 검색이 보는 이름표이고, 새 세대를 다 만든 뒤
이름표만 바꿉니다. 차이는 반영 방식입니다. 1-a는 리트리버가 파일을 읽고 새 세대를 메모리에 다시 올려야 하고,
1-b는 이름표가 검색 엔진 안에 있어 바꾸는 즉시 모든 검색에 적용됩니다.

---

## 장표 3. 벡터 색인과 키워드 색인은 한 번에 구축됨

- 제목: 벡터 색인과 키워드 색인을 한 번에 구축
- 리드문: 검색 엔진 인덱스 하나가 벡터 검색과 키워드 검색을 모두 맡아, 청크 한 건에 담아 한 번에 넣음
- 계기: 사용자 질문 "벡터DB와 키워드 인덱스가 이 과정에서 한꺼번에 구축되는가" → 1-b는 예, 재료(벡터, 낱말)는 그 전에 따로 만듦

**근거(장표에는 넣지 않음)**

| 내용 | 근거 |
|------|------|
| 한 인덱스 매핑에 `embedding`(knn_vector, hnsw, lucene)과 `text_tokens`(whitespace, BM25)가 함께 있음 | `search_branch.py` `build_index_mapping` |
| 벡터, text_tokens, 메타데이터를 한 건으로 합침 | `search_branch.py` `to_engine_document` |
| ①, ②는 파이썬 메모리에서 따로 만들고 ③ bulk 한 번에 넣음, refresh 뒤 검색 가능 | `search_branch.py` `build_generation`, `step3_write_documents` |
| 1-a는 새 세대에 벡터를 Chroma에 먼저 넣고 BM25 점수표 파일을 따로 만든 뒤 활성 세대 파일로 함께 게시 | `indexer/vector-bm25` `IndexRepositoryPort`(`begin`, `upsert`, `build_text_index`, `publish`), `lexical_index.py` |

**도형 구성**

1. 위쪽 흐름도(y 1.9 ~ 4.75)
   - [청크] → 위아래 두 칸 [① 임베딩 → 벡터 768차원], [② 키워드 분석 → text_tokens], 아래 캡션 "파이썬에서 따로 만듦"
   - 두 칸 → [엔진 문서 한 건: 벡터 + text_tokens + 메타데이터]
   - 화살표 라벨 「③ bulk 한 번」
   - 큰 테두리 상자 「검색 엔진 인덱스 하나 (card_chunks-gen-…)」 안에 두 칸
     - [embedding 필드 → 벡터 색인 / HNSW 그래프, kNN 검색에 씀]
     - [text_tokens 필드 → 키워드 역색인 / 낱말 → 청크 목록, BM25 점수에 씀]
     - 아래 칩 「refresh → 둘이 함께 검색 가능」
2. 아래 표(y 5.05 ~ 7.35): 항목 / 벡터DB 인덱싱 / 검색 엔진
   - 저장소: 벡터는 Chroma, 키워드는 bm25s 파일(두 군데) / 검색 엔진 인덱스 한 군데
   - 구축 순서: 벡터를 Chroma에 먼저 넣고 BM25 점수표 파일을 따로 만듦 / bulk 한 번에 둘 다
   - 어긋나지 않게: 둘 다 만든 뒤 활성 세대 파일 하나로 함께 게시 / 같은 한 건에 들어 있어 어긋날 수 없음
   - 지우기: 저장소마다 따로 처리 / delete_by_query 한 번에 둘 다
3. 맨 아래 콜아웃: 벡터DB 인덱싱은 따로 만들고 마지막에 함께 바꾸고, 검색 엔진은 처음부터 함께 넣음

**발표자 노트**

검색 엔진 방식에서는 따로 된 벡터DB가 없습니다. 검색 엔진 인덱스 하나에 벡터 필드와 키워드 필드가 함께 있어서,
청크 한 건을 넣으면 벡터 색인과 키워드 역색인이 같은 순간에 갱신됩니다. 다만 벡터를 만드는 임베딩과 낱말을 만드는 키워드 분석은
그 전에 파이썬에서 따로 합니다. 벡터DB 인덱싱은 벡터를 Chroma에, 점수표를 파일에 따로 만든 뒤 활성 세대 파일 하나로 함께
바꿉니다. 어느 쪽이든 벡터 검색과 키워드 검색은 늘 같은 세대를 봅니다.
