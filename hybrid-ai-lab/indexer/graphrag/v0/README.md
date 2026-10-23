# GraphRAG 인덱싱 v0 (교육용)

「인덱싱 워크플로우 구성안」 장표를 그대로 옮긴 교육용 코드.  
계층 구조(Layered Architecture) 없이 파일 하나가 워크플로우 하나를 맡는 단순한 파이썬 함수로 작성함.

- 오케스트레이터 워크플로우: `orchestrator.py` (① 세대 ID 발급 → ② 공통 단계 → ③ 인덱스 구축 → ④ 검증 → ⑤ 게시)
- KG 구축 서브 워크플로우: `kg_build.py` (준비 K1 ~ K3, 반영 K4 ~ K6, 정리 K7), `community.py` (K8 커뮤니티 요약, 선택)
- 검색엔진 인덱싱 서브 워크플로우: `search_index.py` (준비 S1 ~ S2, 반영 S3)

## 파일 구성

| 파일 | 하는 일 |
|------|--------|
| `config.py` | 경로, 접속 주소, 모델 이름, BM25 조절값 |
| `common.py` | JSON 읽고 쓰기, 해시, 문서 키, KURE-v2 임베딩, Groq LLM |
| `orchestrator.py` | ① ~ ⑤, 전체 재색인(full)과 증분 색인(incremental) |
| `kg_build.py` | `prepare()` K1 ~ K3, `apply()` K4 ~ K6, `cleanup()` K7 |
| `search_index.py` | `prepare()` S1 ~ S2, `apply()` S3 |
| `community.py` | `k8_summarize()` K8 커뮤니티 요약(GDS Leiden 묶기, LLM 보고서, 임베딩, 적재), `verify()` ④ 추가 검사 |
| `tests/test_community.py` | K8 단위 시험(묶음 결정성은 실제 GDS로, 보고서 재사용, 옵션을 껐을 때 무변화) |
| `tools/make_sample.py` | 시험용 표본 청킹 결과 두 개(전체용, 증분용) |
| `tools/inspect_generation.py` | 활성 세대의 그래프와 인덱스 요약(읽기만 함) |
| `tools/reset.py` | v0가 만든 세대(Neo4j 노드, 검색엔진 인덱스, data 폴더)만 지움 |

## 단계와 코드

| 단계 | 함수 | 하는 일 |
|------|------|--------|
| ① 세대 ID 발급 | `step1_issue_generation` | `gen-{실행 이름}-{해시 8자리}`. 입력 파일 지문과 설정 지문이 활성 세대와 같으면 할 일 없음(사전 검사) |
| ② 공통 단계 | `step2_common` | 1-a 인덱서가 만든 청킹 결과 파일(prepared-chunks.json)을 세대 폴더에 고정 |
| ③ 인덱스 구축 | `step3_build_full` | 전체 재색인: KG 구축과 검색엔진 인덱싱을 처음부터 끝까지 병렬 |
| K1 추출 단위 나누기 | `kg_build.k1_split_units` | 약관은 조항 제목 줄로 나눔(승인 기록의 규칙), 나머지는 청크 그대로.  
추출 단위는 LLM 입력에만 쓰고 그래프 노드가 되지 않음 |
| K2 추출, K3 가지치기 | `kg_build._k2_k3_one` | 머리줄 + 단위 본문을 LLM에 넣고, 스키마 밖 노드와 관계는 지움 |
| K4 적재 | `kg_build.apply` | 청크 노드(라벨 Chunk, 검색엔진 청크와 1대1, `chunk_id` 같음)와 엔티티를 Neo4j에 씀.  
엔티티는 자기 추출 단위가 나온 청크마다 FROM_CHUNK로 이음(겹친 조항은 두 청크). 모든 노드에 generation |
| K5 병합 | `kg_build.k5_merge` | 스키마 고유 속성(UNIQUENESS) 값이 같은 노드를 합침. 이번에 들어온 값만.  
합친 뒤 같은 엔티티와 청크 사이 FROM_CHUNK 중복을 하나로 줄임(`dedup_from_chunk`) |
| K6 노드 설명 임베딩 | `kg_build.k6_embed_descriptions` | 「라벨: 속성=값」을 KURE-v2로 임베딩, 벡터 인덱스 `kg_entity_embedding` |
| K7 청크 정리 | `kg_build.cleanup` | 바뀐 문서의 옛 청크 노드와 고아 엔티티를 지움(증분 색인에서만) |
| K8 커뮤니티 요약(선택) | `community.k8_summarize` | `--communities`로 켬. 엔티티 그래프만(청크 노드, FROM_CHUNK 제외) GDS Leiden으로 묶고,  
엔티티 3개 이상 묶음마다 LLM 보고서(title, summary, findings와 근거 엔티티) → KURE-v2 임베딩 →  
`(:Community)`와 `(엔티티)-[:IN_COMMUNITY]->(:Community)` 적재, 벡터 인덱스 `kg_community_embedding`.  
전체 재색인은 K6 뒤, 증분 색인은 K7 뒤. 구성원 지문(member_hash)이 같은 보고서는 다시 씀 |
| S1 임베딩 | `search_index.prepare` | 본문 해시가 앞 세대에 있으면 벡터 재사용, 바뀐 청크만 임베딩 |
| S2 키워드 분석 | `search_index.prepare` | 1-a와 같은 Kiwi 토크나이저 + 카드명 사전과 별칭 |
| S3 적재 | `search_index.apply` | 문서(doc_id)마다 지우고 넣기. 인덱스 이름 `card_chunks-{세대 ID}`, BM25 k1 1.5 |
| ④ 검증 | `step4_verify` | 검색엔진 chunk_id 집합 = 전체 청크 = KG 청크 노드 chunk_id 집합, 청크 하나에 노드 하나인지 비교.  
K8을 켰을 때만 「모든 Community에 summary와 embedding, 빈 묶음 없음, 구성원이 모두 현재 세대 엔티티」도 봄 |
| ⑤ 게시 | `step5_publish` | `data/active_generation.json` 하나만 교체 |

- 증분 색인(`run_incremental`): 바뀐 문서만 골라 준비(K1 ~ K3, S1 ~ S2)는 병렬로 하고,  
  반영은 K4 ~ K6 → S3 → K7 → 기록 갱신 순서로 함. 그래프는 먼저 넣고 나중에 지워서 바뀌는 동안에도 검색이 찾은 chunk_id가 그래프에 있음
- 준비 결과는 `data/generations/{세대}/kg_prepared.json`에 보관함. 본문 해시와 스키마가 같은 단위는 LLM을 다시 부르지 않음.  
  추출 단위와 그 단위가 나온 청크 ID 목록(`chunk_ids`)은 이 파일에만 있고 그래프에는 없음
- 서브 워크플로우는 활성 세대 파일을 바꾸지 않음. 게시는 오케스트레이터만 함
- 되돌리기와 옛 세대 정리는 이 흐름 밖에서 함(v0에는 없음)

## 준비

필요한 것: 실행 중인 Neo4j(APOC 포함, K8을 쓰면 GDS도), OpenSearch, `secrets/.env`의 `GROQ_API_KEY`,  
1-a 인덱서 가상환경(`indexer/vector-bm25/.venv`).

```bash
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.txt
echo C:/Users/hiond/class/design-agentic-ai/hybrid-ai-lab/indexer/vector-bm25/.venv/Lib/site-packages > .venv/Lib/site-packages/_reuse_vector_bm25.pth
```

- 1-a 가상환경의 torch, sentence-transformers, kiwipiepy와 1-a 코드(토크나이저, 임베더, 별칭 규칙)를 빌려 씀.  
  torch와 KURE-v2 모델을 다시 받지 않으려는 것임

Neo4j와 OpenSearch는 hybrid-ai-lab의 compose 파일로 띄움(hybrid-ai-lab 폴더에서 실행).

```bash
docker compose -f neo4j/compose.yml up -d
```

```bash
docker compose -f opensearch/compose.yml up -d
```

- Neo4j: 컨테이너 `neo4j`, `bolt://localhost:7687`, Neo4j 2026.09.0 Community + APOC 2026.09.0 + GDS 2026.09.0.  
  비밀번호는 코드에 두지 않음. 환경변수 `NEO4J_PASSWORD`가 있으면 그것을, 없으면 `hybrid-ai-lab/neo4j/.env`의 값을 읽음
- OpenSearch: 컨테이너 `opensearch`, `http://localhost:9200`(보안 플러그인 꺼짐, 2.19.1)
- `config.py`의 기본 접속 주소는 이 두 컨테이너임. 다른 곳에 띄웠으면 환경변수 `NEO4J_URI`, `OPENSEARCH_URL`로 넘김

## 실행

```bash
.venv/Scripts/python.exe tools/make_sample.py
```

```bash
.venv/Scripts/python.exe orchestrator.py full --run sample-001 --chunks data/sample-chunks.json
```

```bash
.venv/Scripts/python.exe orchestrator.py incremental --run sample-002 --chunks data/sample-chunks-v2.json
```

```bash
.venv/Scripts/python.exe tools/inspect_generation.py
```

K8 커뮤니티 요약을 켜려면 `--communities`를 붙임(전체 재색인과 증분 색인 모두).

```bash
.venv/Scripts/python.exe orchestrator.py full --run sample-015 --chunks data/sample-chunks.json --full-reindex --communities
```

```bash
.venv/Scripts/python.exe -m pytest tests/test_community.py -q
```

- `--chunks`를 빼면 1-a 활성 청킹 결과 전체(218개)를 씀. LLM 호출이 약 260번 생김
- 같은 입력으로 `full`을 다시 돌리면 사전 검사가 「할 일 없음」으로 끝남. 그래도 새로 만들려면 `--full-reindex`

## 표본 실행 결과 (2026-10-23, 청크 노드 1대1 구조)

표본: 약관 청크 2개(조항이 겹치는 이웃 청크), 혜택 안내 청크 4개(한빛 가족돌봄), 상담 기록 청크 4개.  
모델 Groq `openai/gpt-oss-120b`, Neo4j 2026.09.0 Community, OpenSearch 2.19.1.  
앞 세대(sample-001) 준비 결과를 재사용해 LLM은 바뀐 단위만 부름.

| 실행 | 결과 |
|------|------|
| 전체 재색인 `sample-003` (`--full-reindex`) | K1 단위 24개(겹친 조항 2개는 청크 2개에서 나옴), K2 LLM 2번(22개 재사용, 토큰 9,088), K4 노드 122개(청크 노드 10개 포함), 관계 216개, K5 병합 3묶음, FROM_CHUNK 중복 0개, K6 임베딩 93개, S3 10건, ④ 통과(검색엔진 10/10, 청크 노드 10개 = 고유 10/10), ⑤ 게시 |
| 같은 입력으로 다시 `full` | ① 사전 검사에서 「할 일 없음」으로 끝남 |
| 증분 색인 `sample-004` (상담 1건 본문 수정, 혜택 청크 1개 뺌) | 바뀐 문서 2개. K2 LLM 1번(3개는 재사용), S1 임베딩 1개(3개 재사용), 반영 순서 K4 ~ K6 → S3(옛 청크 5건 지우고 4건 넣음) → K7(옛 청크 노드 5개, 고아 엔티티 35개 지움), ④ 통과(검색엔진 9/9, 청크 노드 9개 = 고유 9/9) |
| 같은 입력으로 다시 증분 | 바뀐 문서가 없어 「할 일 없음」 |
| 전체 재색인 `sample-005` (필드 이름 `chunk_ids`로 바꾼 뒤) | K1 단위 24개, K2 LLM 2번(22개 재사용, 토큰 8,886), K3 엔티티 110개, K4 노드 120개(청크 노드 10개 포함), 관계 212개(FROM_CHUNK 120, 추출 관계 92), K5 병합 3묶음(엔티티 110 → 91), K6 임베딩 91개, ④ 통과(10/10) |
| 증분 색인 `sample-006` | K4 노드 35개(청크 노드 4개 포함), 관계 64개, K5 병합 3묶음(새 엔티티 31개 중 5개가 기존 노드와 합쳐짐), K7 옛 청크 노드 5개와 고아 엔티티 33개 지움, ④ 통과(9/9) |

- 두 청크에 걸친 조항 제16조와 제16조의2는 엔티티가 두 청크 노드에 모두 이어짐(`tools/inspect_generation.py`로 확인)
- K5 병합 예: 조항 16개에서 각각 뽑힌 약관 문서 노드(TermsDocument)가 1개로 합쳐지고 두 약관 청크에 하나씩 이어짐.  
  앞 상담을 가리키며 생긴 상담 노드가 실제 상담 노드와 1개로 합쳐짐(FOLLOWS 관계 1개 유지)
- 그래프의 청크 노드에는 옛 구조의 `parent_chunk_ids` 속성이 없음(0개 확인). 추출 단위 기록은 `kg_prepared.json`에만 있음

## K8 커뮤니티 요약 결과 (2026-10-23, 새 compose 컨테이너)

GDS Leiden(randomSeed 42, concurrency 1, 한 단계), 엔티티 3개 이상 묶음만 요약, 보고서 판 v2.  
기록: `hybrid-ai-lab/verify/k8-community/`(실행 로그 run-a ~ run-d, `result.json`, `README.md`).

| 실행 | 결과 |
|------|------|
| a. 전체 재색인 `sample-014` (옵션 없음) | K4 노드 123개, 관계 218개, K5 3묶음, K6 94개, ④ 통과(10/10). 보고서와 검증 결과에 K8 칸 없음 |
| b. 전체 재색인 `sample-015` (`--communities`) | a와 K4 ~ K6이 같음. K8 묶음 16개(엔티티 94개, 관계 95개) 중 15개 요약, LLM 15번, ④ 통과(커뮤니티 15개) |
| c. 같은 입력으로 `sample-016` | 묶음과 지문 15개가 b와 같음, LLM 0번(15개 재사용) |
| d. 증분 색인 `sample-017` (`--communities`) | K7 뒤 K8: 묶음 14개 중 13개 요약, LLM 4번, 재사용 9개, ④ 통과(커뮤니티 13개, 9/9) |
| 단위 시험 | 8개 통과(GDS 실제 실행으로 묶음 결정성 확인 포함) |

- a와 b의 준비 결과와 K4 ~ K6 결과가 같아, 옵션을 켜고 끄는 것은 K8 말고 바꾸지 않음
- 묶음은 모두 한 문서 종류 안에서만 생김(약관 8, 혜택 안내 3, 상담 2, 섞인 묶음 0). 엔티티 사이 관계가 문서 안에서만 있어서임
- 처음에는 igraph와 leidenalg로 묶었으나 GDS Leiden으로 바꿈. 그래프가 이미 Neo4j에 있고 Neo4j GraphRAG에서 더 일반적이기 때문임.  
  그래서 두 라이브러리는 requirements에 넣지 않았고 가상환경에서도 지움

## 한계 (v0)

- 약관 그래프 스키마는 채움 시험 합격 기준 미달 상태로 확정된 것임(`schema/doc/regulation/approval.json`의 `below_criteria`)
- 혜택 안내와 상담 기록 스키마는 자동 승인 상태임. 인덱싱 운영 전에 사람 승인이 필요함
- ② 공통 단계는 1-a 인덱서의 청킹 결과 파일을 받기만 함(로드, 정제와 가명처리, 청킹은 1-a가 함)
- 증분 색인의 카드명 사전은 활성 세대 것을 그대로 씀. 새 카드명이 생기면 전체 재색인이 필요함
- K5 병합은 `apoc.refactor.mergeNodes`의 `properties: 'discard'`라 값이 다르면 목록 첫 노드의 값을 남김.  
  목록 순서를 정하지 않아(`collect`에 정렬 없음) 증분 색인에서 옛 노드와 새 노드가 합쳐질 때 어느 값이 남을지 정해져 있지 않음
- K6은 임베딩이 없는 엔티티만 임베딩함. 증분 색인에서 새 노드가 K5로 기존 노드와 합쳐지면 기존 임베딩이 남아,  
  합치며 바뀐 속성이 설명 임베딩에 반영되지 않음(표본 증분: 새 엔티티 29개 중 합쳐진 5개는 다시 임베딩하지 않음)
- S1의 벡터 재사용은 앞 세대 인덱스를 통째로 읽음. 청크가 많으면 바뀐 청크만 골라 읽도록 바꿔야 함
- 증분 색인의 반영은 두 저장소에 걸쳐 한 번에 일어나지 않음(KG 먼저, 검색엔진 나중으로 어긋남을 줄임)
- 검색기(질의)는 없음. 검색기는 활성 세대 파일을 요청마다 한 번 읽고 `card_chunks-{세대}`와 Neo4j `generation`으로 조회해야 함
- 실행 중 `LLMInterface is deprecated` 경고가 나옴(neo4j-graphrag 1.22.0). 동작에는 영향 없음
- K8은 문서를 건너는 관계가 없어 상담과 약관을 한 묶음으로 엮지 못함. 거시 질문 중 문서 건너기(Q25)는 커뮤니티 보고서만으로 답할 수 없음
- K8은 매 실행 세대의 Community를 모두 다시 씀. 묶음 경계가 조금만 바뀌어도 그 묶음 보고서는 LLM으로 다시 만듦
- K8 보고서 판(`community.REPORT_VERSION`)을 올리면 모든 보고서를 다시 만듦. 프롬프트를 바꿀 때 올려야 옛 보고서가 섞이지 않음
