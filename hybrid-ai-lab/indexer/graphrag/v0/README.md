# GraphRAG 인덱싱 v0 (교육용)

「인덱싱 워크플로우 구성안」 장표를 그대로 옮긴 교육용 코드.  
계층 구조(Layered Architecture) 없이 파일 하나가 워크플로우 하나를 맡는 단순한 파이썬 함수로 작성함.

- 오케스트레이터 워크플로우: `orchestrator.py` (① 세대 ID 발급 → ② 공통 단계 → ③ 인덱스 구축 → ④ 검증 → ⑤ 게시)
- KG 구축 서브 워크플로우: `kg_build.py` (준비 K1 ~ K3, 반영 K4 ~ K6, 정리 K7)
- 검색엔진 인덱싱 서브 워크플로우: `search_index.py` (준비 S1 ~ S2, 반영 S3)

## 파일 구성

| 파일 | 하는 일 |
|------|--------|
| `config.py` | 경로, 접속 주소, 모델 이름, BM25 조절값 |
| `common.py` | JSON 읽고 쓰기, 해시, 문서 키, KURE-v2 임베딩, Groq LLM |
| `orchestrator.py` | ① ~ ⑤, 전체 재색인(full)과 증분 색인(incremental) |
| `kg_build.py` | `prepare()` K1 ~ K3, `apply()` K4 ~ K6, `cleanup()` K7 |
| `search_index.py` | `prepare()` S1 ~ S2, `apply()` S3 |
| `tools/make_sample.py` | 시험용 표본 청킹 결과 두 개(전체용, 증분용) |
| `tools/inspect_generation.py` | 활성 세대의 그래프와 인덱스 요약(읽기만 함) |
| `tools/reset.py` | v0가 만든 세대(Neo4j 노드, 검색엔진 인덱스, data 폴더)만 지움 |

## 단계와 코드

| 단계 | 함수 | 하는 일 |
|------|------|--------|
| ① 세대 ID 발급 | `step1_issue_generation` | `gen-{실행 이름}-{해시 8자리}`. 입력 파일 지문과 설정 지문이 활성 세대와 같으면 할 일 없음(사전 검사) |
| ② 공통 단계 | `step2_common` | 1-a 인덱서가 만든 청킹 결과 파일(prepared-chunks.json)을 세대 폴더에 고정 |
| ③ 인덱스 구축 | `step3_build_full` | 전체 재색인: KG 구축과 검색엔진 인덱싱을 처음부터 끝까지 병렬 |
| K1 추출 단위 나누기 | `kg_build.k1_split_units` | 약관은 조항 제목 줄로 나눔(승인 기록의 규칙), 나머지는 청크 그대로 |
| K2 추출, K3 가지치기 | `kg_build._k2_k3_one` | 머리줄 + 단위 본문을 LLM에 넣고, 스키마 밖 노드와 관계는 지움 |
| K4 적재 | `kg_build.apply` | 추출 단위 노드(라벨 Chunk, parent_chunk_ids)와 엔티티를 Neo4j에 씀. 모든 노드에 generation |
| K5 병합 | `kg_build.k5_merge` | 스키마 고유 속성(UNIQUENESS) 값이 같은 노드를 합침. 이번에 들어온 값만 |
| K6 노드 설명 임베딩 | `kg_build.k6_embed_descriptions` | 「라벨: 속성=값」을 KURE-v2로 임베딩, 벡터 인덱스 `kg_entity_embedding` |
| K7 청크 정리 | `kg_build.cleanup` | 바뀐 문서의 옛 추출 단위 노드와 고아 엔티티를 지움 |
| S1 임베딩 | `search_index.prepare` | 본문 해시가 앞 세대에 있으면 벡터 재사용, 바뀐 청크만 임베딩 |
| S2 키워드 분석 | `search_index.prepare` | 1-a와 같은 Kiwi 토크나이저 + 카드명 사전과 별칭 |
| S3 적재 | `search_index.apply` | 문서(doc_id)마다 지우고 넣기. 인덱스 이름 `card_chunks-{세대 ID}`, BM25 k1 1.5 |
| ④ 검증 | `step4_verify` | 검색엔진 chunk_id = 전체 청크, KG의 parent_chunk_ids가 전체 청크를 덮는지 비교 |
| ⑤ 게시 | `step5_publish` | `data/active_generation.json` 하나만 교체 |

- 증분 색인(`run_incremental`): 바뀐 문서만 골라 준비(K1 ~ K3, S1 ~ S2)는 병렬로 하고,  
  반영은 K4 ~ K6 → S3 → K7 → 기록 갱신 순서로 함. 그래프는 먼저 넣고 나중에 지워서 바뀌는 동안에도 검색이 찾은 chunk_id가 그래프에 있음
- 준비 결과는 `data/generations/{세대}/kg_prepared.json`에 보관함. 본문 해시와 스키마가 같은 단위는 LLM을 다시 부르지 않음
- 서브 워크플로우는 활성 세대 파일을 바꾸지 않음. 게시는 오케스트레이터만 함
- 되돌리기와 옛 세대 정리는 이 흐름 밖에서 함(v0에는 없음)

## 준비

필요한 것: 실행 중인 Neo4j(APOC 포함), OpenSearch, `secrets/.env`의 `GROQ_API_KEY`, 1-a 인덱서 가상환경(`indexer/vector-bm25/.venv`).

```bash
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.txt
echo C:/Users/hiond/class/design-agentic-ai/hybrid-ai-lab/indexer/vector-bm25/.venv/Lib/site-packages > .venv/Lib/site-packages/_reuse_vector_bm25.pth
```

- 1-a 가상환경의 torch, sentence-transformers, kiwipiepy와 1-a 코드(토크나이저, 임베더, 별칭 규칙)를 빌려 씀.  
  torch와 KURE-v2 모델을 다시 받지 않으려는 것임

```bash
docker run -d --name verify-opensearch -p 19200:9200 -e discovery.type=single-node -e DISABLE_SECURITY_PLUGIN=true -e DISABLE_INSTALL_DEMO_CONFIG=true -e "OPENSEARCH_JAVA_OPTS=-Xms1g -Xmx1g" opensearchproject/opensearch:2.19.1
```

- Neo4j는 `verify/neo4j-vector-search`의 시험 컨테이너(`verify-neo4j`, 포트 17687)를 씀. 비밀번호는 코드에 두지 않고  
  환경변수 `NEO4J_PASSWORD`로 넘김(시험 컨테이너 값은 그 폴더의 README에 있음)

## 실행

```bash
.venv/Scripts/python.exe tools/make_sample.py
```

```bash
NEO4J_PASSWORD=비밀번호 .venv/Scripts/python.exe orchestrator.py full --run sample-001 --chunks data/sample-chunks.json
```

```bash
NEO4J_PASSWORD=비밀번호 .venv/Scripts/python.exe orchestrator.py incremental --run sample-002 --chunks data/sample-chunks-v2.json
```

```bash
NEO4J_PASSWORD=비밀번호 .venv/Scripts/python.exe tools/inspect_generation.py
```

- `--chunks`를 빼면 1-a 활성 청킹 결과 전체(218개)를 씀. LLM 호출이 약 260번 생김
- 같은 입력으로 `full`을 다시 돌리면 사전 검사가 「할 일 없음」으로 끝남. 그래도 새로 만들려면 `--full-reindex`

## 표본 실행 결과 (2026-10-19)

표본: 약관 청크 2개(조항이 겹치는 이웃 청크), 혜택 안내 청크 4개(한빛 가족돌봄), 상담 기록 청크 4개.  
모델 Groq `openai/gpt-oss-120b`, Neo4j 2026.09.0 Community, OpenSearch 2.19.1.

| 실행 | 결과 |
|------|------|
| 전체 재색인 `sample-001` | K1 단위 24개(겹친 조항 2개는 부모 청크 2개), K2 LLM 24번(토큰 76,401), K4 노드 134개, K5 병합 3묶음, K6 임베딩 91개, S1 10개, S2 카드명 사전 1개와 별칭 3개, S3 10건, ④ 통과, ⑤ 게시 |
| 같은 입력으로 다시 `full` | ① 사전 검사에서 「할 일 없음」으로 끝남 |
| 증분 색인 `sample-002` (상담 1건 본문 수정, 혜택 청크 1개 뺌) | 바뀐 문서 2개. K2 LLM 1번(3개는 재사용), S1 임베딩 1개(3개 재사용), 반영 순서 K4 ~ K6 → S3(옛 청크 5건 지우고 4건 넣음) → K7(옛 추출 단위 노드 5개, 고아 엔티티 33개 지움), ④ 통과 |
| 같은 입력으로 다시 증분 | 바뀐 문서가 없어 「할 일 없음」 |

- K5 병합 예: 조항 16개에서 각각 뽑힌 약관 문서 노드(TermsDocument)가 1개로, 앞 상담을 가리키며 생긴 상담 노드가  
  실제 상담 노드와 1개로 합쳐짐(FOLLOWS 관계 1개 유지)

## 한계 (v0)

- 약관 그래프 스키마는 채움 시험 합격 기준 미달 상태로 확정된 것임(`schema/doc/regulation/approval.json`의 `below_criteria`)
- 혜택 안내와 상담 기록 스키마는 자동 승인 상태임. 인덱싱 운영 전에 사람 승인이 필요함
- ② 공통 단계는 1-a 인덱서의 청킹 결과 파일을 받기만 함(로드, 정제와 가명처리, 청킹은 1-a가 함)
- 증분 색인의 카드명 사전은 활성 세대 것을 그대로 씀. 새 카드명이 생기면 전체 재색인이 필요함
- K5 병합은 `apoc.refactor.mergeNodes`의 `properties: 'discard'`라 값이 다르면 먼저 있던 노드의 값을 남김
- S1의 벡터 재사용은 앞 세대 인덱스를 통째로 읽음. 청크가 많으면 바뀐 청크만 골라 읽도록 바꿔야 함
- 증분 색인의 반영은 두 저장소에 걸쳐 한 번에 일어나지 않음(KG 먼저, 검색엔진 나중으로 어긋남을 줄임)
- 검색기(질의)는 없음. 검색기는 활성 세대 파일을 요청마다 한 번 읽고 `card_chunks-{세대}`와 Neo4j `generation`으로 조회해야 함
- 실행 중 `LLMInterface is deprecated` 경고가 나옴(neo4j-graphrag 1.22.0). 동작에는 영향 없음
