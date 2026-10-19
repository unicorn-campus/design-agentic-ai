# 검색 갈래 4단계 예제 (1-b 분리형, OpenSearch)

1-b 분리형 인덱싱 파이프라인에서 **검색 갈래 4단계**를 Python으로 구현한 교육용 예제.  
기존 1-a 구현(`indexer/vector-bm25`)의 Kiwi 토큰화와 KURE-v2 임베딩을 그대로 가져다 쓰고,  
저장소만 Chroma와 파일 BM25에서 OpenSearch로 바꿈.

## 파일

| 파일 | 내용 |
|------|------|
| `search_branch.py` | 4단계 함수와 검색 함수 (예제 본체) |
| `run_test.py` | 로컬 OpenSearch에 4단계를 실제로 돌려 확인하는 시험 (12개 장면, 41개 항목) |
| `run.log` | 마지막 시험 실행 로그 (2026-10-19, 41개 통과, 실패 0건) |
| `requirements.txt` | 이 폴더에서 새로 까는 패키지 (`opensearch-py`) |

## 4단계와 함수

| 단계 | 함수 | 하는 일 |
|------|------|---------|
| ① 청크 임베딩(바뀐 것만) | `step1_embed_changed_chunks` | 사전 검사 뒤 1번, 2번, 3번 판단을 거쳐 바뀐 청크만 임베딩 (아래 「①단계 판단 순서」) |
| ② 키워드 분석 | `step2_analyze_keywords` | 카드명 사전과 별칭을 넣은 Kiwi로 잘라 공백으로 이은 `text_tokens`를 만듦. 엔진은 `whitespace` 분석기와 k1 1.5 BM25 (아래 「②단계 키워드 분석」) |
| ③ 검색 엔진에 쓰기 | `step3_write_documents` | 문서(doc_id)마다 `delete_by_query`로 옛 청크를 지우고 `helpers.bulk`로 새 청크를 넣음 |
| ④ 별칭 전환 | `step4_switch_alias` | 건수 확인 뒤 `update_aliases` 한 번의 요청에 remove와 add를 함께 넣어 별칭을 옮김 |

- 세대 인덱스 이름: `card_chunks-gen-{세대}`. 검색은 늘 별칭 `card_chunks`에만 질의함
- 세대를 만든 실행 기록(`RunContract`: 원천 지문, 처리 정책, 문서 프로필, 임베딩 서명과 설정,  
  토크나이저 서명과 사전)은  
  그 세대 인덱스의 `_meta`에 남음. 다음 실행의 사전 검사와 1번 판단이 이 기록과 비교함
- ③에서 `_id`를 `chunk_id`로 고정해 같은 입력을 두 번 넣어도 건수가 늘지 않음
- ④에서 옛 세대 인덱스는 지우지 않음. 같은 함수에 옛 인덱스 이름을 넘기면 되돌리기가 됨
- nori 방식은 `NORI_MAPPING_EXAMPLE` 상수로 매핑만 보여 줌 (기본 이미지에 플러그인이 없어 실행하지 않음)

## ①단계 판단 순서

장표 「모델과 설정이 같고 본문도 같으면, 저장된 벡터를 재사용해 중복 계산을 줄임」과 1:1로 맞춘 함수임.  
1-a 인덱서(`indexing_service.py`의 `_is_no_op`, 임베딩 계획 단계)와 같은 판단 규칙임.

| 장표 단계 | 함수 | 조건 | 아니요일 때 |
|-----------|------|------|------------|
| 사전 검사 | `precheck_skip_run` | 원천 문서, 문서 처리 정책, 문서 프로필, 임베딩 설정이 모두 같고 전체 재색인이 아님 | 청크별 판단으로 넘어감 (예이면 실행 전체 생략) |
| 1. 재사용 가능한 실행인가요? | `check1_reusable_run` | 활성 세대 있음, 임베딩 서명과 `embedding_contract` 같음, `full_reindex` 아님 | 대상 전부 새로 임베딩 |
| 2. 같은 정제 본문이 있나요? | `check2_find_same_text` | 활성 세대에 같은 `text_hash`가 있음 (같은 ID를 먼저 보고, ID가 달라도 됨) | 그 청크 새로 임베딩 |
| 3. 선택한 기존 벡터가 있나요? | `check3_get_vectors` | 2번에서 고른 기존 청크의 벡터가 `mget` 조회 결과에 있음 | 그 청크 새로 임베딩 |

- `text_hash`는 색인용 본문(머리말 포함)의 SHA-256임. 1-a가 만든 `text_hash`와 값이 같음을 시험 a-4에서 확인함
- 1번은 서명 문자열만 보지 않고 `embedding_contract`(모델, revision, 입력 상한, 차원, 정규화, 풀링)까지 비교함.  
  모델 이름은 그대로 두고 입력 상한만 바꿔도 같은 본문에서 다른 벡터가 나오기 때문임
- 2번과 3번은 벡터 없이 지문만 먼저 읽고(`load_active_snapshot`), 재사용하기로 고른 청크의 벡터만 `mget`으로 가져옴
- 청크마다 판단 결과(`EmbedReport.reasons`)를 남김: `reuse_same_id`, `reuse_same_text`,  
  `new_not_reusable_run`, `new_no_same_text`, `new_vector_missing`
- 벡터를 재사용해도 메타데이터는 이번 입력의 최신 값으로 새 세대에 다시 씀

## ②단계 키워드 분석

1-a(벡터DB 인덱싱의 BM25 색인)와 같은 토큰화 규칙, 카드명 사전, 별칭, 조절값을 씀.

| 항목 | 함수 또는 설정 | 내용 |
|------|---------------|------|
| 카드명 사전과 별칭 | `build_keyword_dictionary` | 색인할 혜택 안내서(D2) 청크의 카드명을 고유명사로 등록하고, 접두어 "한빛"과 접미어 "카드"를 떼어 별칭을 만듦. 일반 명사와 같은 별칭(예: 장보기)은 자동으로 뺌 |
| 별칭 규칙 파일 | `load_alias_policy` | 1-a의 `config/card_alias_rules.json`, `config/card_alias_overrides.json`을 그대로 읽음 |
| 사전 보관 | `RunContract.keyword_dictionary` | 세대 인덱스 `_meta`에 카드명 사전, 별칭, 자동 제외 목록과 토크나이저 서명을 함께 남김 |
| 검색 쪽 토크나이저 | `load_query_tokenizer` | 활성 세대 `_meta`의 사전으로 토크나이저를 다시 만들고 서명이 기록과 같은지 대조함 |
| BM25 조절값 | 인덱스 `similarity.bm25_lab` | k1 1.5, b 0.75. OpenSearch 기본값(k1 1.2)이 아닌 1-a와 같은 값을 `text_tokens` 필드에 검 |

- 카드명 사전과 별칭은 한 쌍임. 사전만 넣으면 문서에는 `한빛가족돌봄` 한 낱말만 남는데,
  "가족돌봄"이라고만 묻는 질문은 `가족`, `돌봄`으로 잘려 카드명 낱말과 겹치지 않음
- 사전이나 별칭이 바뀌면 토크나이저 서명이 바뀌어 사전 검사가 생략하지 않음(새 세대로 다시 색인).
  임베딩 설정은 그대로라 벡터는 1번 판단에서 재사용됨
- 카드명 사전 추출(`_card_dictionary_words`)과 별칭 정책 정규화(`_normalized_alias_policy`)는
  1-a의 내부 함수를 그대로 import함. 규칙을 다시 적으면 1-a와 1-b의 사전이 조용히 달라질 수 있기 때문임

## 실행 방법

이 예제는 `indexer/vector-bm25`의 코드와 가상환경(Kiwi, sentence-transformers, KURE-v2)을 빌려 씀.  
torch와 모델을 다시 받지 않도록 `.pth` 파일로 그 가상환경의 패키지 폴더를 이어 붙임.

```bash
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.txt
echo C:/Users/hiond/class/design-agentic-ai/hybrid-ai-lab/indexer/vector-bm25/.venv/Lib/site-packages > .venv/Lib/site-packages/_reuse_lab_venv.pth
```

```bash
docker run -d --name verify-opensearch -p 19200:9200 -e discovery.type=single-node -e DISABLE_SECURITY_PLUGIN=true -e DISABLE_INSTALL_DEMO_CONFIG=true -e "OPENSEARCH_JAVA_OPTS=-Xms1g -Xmx1g" opensearchproject/opensearch:2.19.1
```

```bash
OPENSEARCH_URL=http://localhost:19200 .venv/Scripts/python.exe run_test.py
```

```bash
docker rm -f verify-opensearch
```

- `run_test.py`는 시작할 때 `card_chunks-gen-*` 인덱스를 지우고 시작함. 시험 전용 컨테이너에서만 돌릴 것
- 보안 플러그인을 끈 설정은 로컬 실습 전용임. 운영에서는 인증을 켜고 접속 정보는 환경변수로 넣음
- `vector-bm25` 폴더 위치가 다르면 `LAB_ROOT` 환경변수로 지정함

## 시험 내용 (run_test.py)

입력: `prepared-chunks.json`에서 고른 청크 23개, 문서 5개 (약관 10, 혜택 10, 상담 3).  
혜택 10개는 앞 6개와 한빛 가족돌봄 카드 청크 4개임. 이 표본에서 카드명 사전 6개, 별칭 17개, 자동 제외 1개(장보기)가 나옴.

| 시험 | 확인 내용 | 결과 |
|------|----------|------|
| a. 1세대 전체 색인 | 활성 세대가 없어 23개 모두 1번 아니요로 임베딩, `_meta`에 실행 기록, text_hash가 1-a와 같음 | `new_not_reusable_run=23` |
| p. 사전 검사 | 같은 입력과 설정으로 다시 실행하면 새 세대를 만들지 않음. `full_reindex`면 생략하지 않음 | `skipped=True` |
| b. 2세대 | 약관 청크 하나를 고치고 하나를 뺌. 고친 청크만 2번 아니요, 나머지는 같은 ID로 재사용 | `new_no_same_text=1, reuse_same_id=21` |
| c. 전환 뒤 검색 | 별칭으로 BM25, kNN, 하이브리드, 회원 필터 질의가 결과를 돌려줌. 1세대 인덱스는 남아 있음 | 통과 |
| q. 키워드 분석 | 사전에 한빛 가족돌봄, 별칭 가족돌봄 → 한빛가족돌봄. 장보기 자동 제외. 검색 쪽 토크나이저 서명 일치. "가족돌봄 카드 할인 조건이 뭐예요?"의 BM25 1등이 가족돌봄 카드 청크. explain에 k1 1.5. 별칭이 바뀌면 사전 검사 생략 안 함, 벡터는 재사용 | 9개 통과 |
| f. 증분 색인 | 활성 2세대에 그 문서를 원래 10건으로 되돌려 씀. 옛 청크 9건 삭제, 10건 넣음, 고아 없음 | `new_no_same_text=2, reuse_same_id=8` |
| g. 2번(ID만 바뀜) | 순번이 바뀐 청크가 같은 본문의 벡터를 재사용 | `reuse_same_text=1` |
| h. 메타데이터만 바뀜 | `access_level`만 바꿈. 벡터는 재사용하고 새 메타데이터로 다시 적재 | `reuse_same_id=10` |
| i. 1번(설정 변경) | 서명은 그대로 두고 `max_seq_length`만 800에서 400으로 바꿈 | `new_not_reusable_run=10` |
| j. 1번(full_reindex) | 설정이 같아도 강제 재색인이면 전부 새로 임베딩 | `new_not_reusable_run=10` |
| k. 3번(벡터 없음) | 지문을 읽은 뒤 그 청크가 지워짐. 2번은 예였지만 조회에 없어 새로 임베딩 | `new_vector_missing=1` |
| d. 되돌리기 | 별칭을 1세대로 되돌림, 건수 23, 검색 동작 | 통과 |

## 한계

- 하이브리드 점수는 BM25 점수와 kNN 점수를 그냥 더한 값이라 BM25가 순위를 좌우함.  
  운영에서는 OpenSearch `hybrid` 질의와 `normalization-processor` 검색 파이프라인으로 점수를 맞춰 합쳐야 함
- ③을 운영 중인 인덱스에 바로 쓰면(증분 색인) 지우기와 넣기 사이에 그 문서가 잠깐 검색되지 않음.  
  새 세대 인덱스에 쓰고 ④로 전환하면 이 틈이 생기지 않음
- 카드명 사전은 이번에 색인하는 청크에서 만듦(1-a와 같음). 시험 표본은 혜택 청크 10개라 사전 6개, 별칭 17개뿐임.  
  전체 말뭉치에서는 사전 64개, 별칭 189개, 자동 제외 3개(대중교통, 장보기, 출퇴근)
- `load_active_snapshot`은 활성 세대의 지문(chunk_id, text_hash)을 통째로 읽음. 벡터는 읽지 않아 가볍지만  
  청크가 아주 많으면 바뀐 문서의 지문만 골라 읽도록 바꿔야 함
- 증분 색인(시험 f, h)은 활성 세대에 바로 쓰므로 `_meta`의 원천 지문이 갱신되지 않음.  
  운영에서는 증분 색인 뒤 `_meta`도 함께 고쳐야 다음 사전 검사가 맞게 판단함
- 원천 문서 지문은 원천 파일 대신 청크 본문으로 계산함(예제 입력이 청킹 결과이기 때문). 1-a는 원천 파일의 해시를 씀
- 검증 규모는 청크 19개임. 전체 218개나 운영 규모의 속도와 메모리는 재지 않음
- 별칭 전환 순간에 질의를 동시에 보내는 시험은 하지 않음. 원자성은 OpenSearch 문서의 보장에 기댐
- 장표의 「검색 엔진 별칭과 Neo4j 세대를 같은 순간에 바꿈」 중 검색 엔진 쪽만 구현함
