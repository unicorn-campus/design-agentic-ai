# S3.2 임베딩·적재와 검색 실습

교재 슬라이드 1~21 범위의 실습 코드임. 조별 골격과 `_ref` 완성본을 별도로 제공함.  
슬라이드 18~21은 검색 결과를 조립하고 원문 위치·원문 발췌·출처가 있는 답을 만듦.

## 파일과 작성할 부분

| 파일 | 역할 |
|---|---|
| `src/indexing.py` | 슬라이드 8: 임베딩·upsert·재시도 TODO 3곳 작성 |
| `src/indexing_ref.py` | 임베딩·적재 완성본 |
| `src/retrieval.py` | 슬라이드 13: 조건 필터 합성·Hit 변환 TODO 2곳 작성 |
| `src/retrieval_ref.py` | 권한 필터·검색 완성본 |
| `src/models.py` | `Chunk`·`Hit` 공통 구조 |
| `src/helpers.py` | 강사 제공 모델·Chroma·메타데이터 처리 |
| `src/answering.py` | 슬라이드 18~21: 조별 프롬프트 조립 TODO 1곳 작성 |
| `src/answering_ref.py` | 프롬프트 조립 완성본 |
| `src/sources.py` | 약관 조항·혜택 항목·상담 턴 위치와 원본 문서 표시 |
| `src/evidence.py` | JSON 응답 해석·원문 발췌 검증·사람용 답변 표시 |
| `src/llm_client.py` | 저장소 `.env`의 키를 사용하는 Claude 호출 어댑터 |
| `lab_io.py` | S3.1 `chunks.jsonl` 읽기·기본 품질 수치 |
| `lab_cli.py` | 공통 실행 도구 |
| `run_lab.py` | 조별 골격 실행 |
| `run_lab_ref.py` | 완성본 실행 |
| `smoke_test.py` | 테스트 벡터와 실제 Chroma를 사용하는 기본 동작 검사 |
| `templates/query_variants.json` | 슬라이드 15~16 질문 3개·사전 정답 ID 작성 양식 |

골격의 `raise NotImplementedError(...)` 줄을 구현 코드로 교체함.  
미완성 상태의 실행은 종료 코드 3으로 작성할 위치를 안내함. 완성본을 자동으로 대신 실행하지 않음.  
각 조는 실습 저장소 사본을 사용하고, `--group 1`의 번호를 조 번호로 변경함.

## 환경 준비

아래 명령의 작업 위치는 `hybrid-ai-lab` 루트임. Python 3.10 이상 사용 필요함.  
기본 검증은 Python 3.13·ChromaDB 1.5.9 환경에서 수행함.

```powershell
python -m venv s3.2/.venv
s3.2/.venv/Scripts/python.exe -m pip install -r s3.2/requirements.txt
```

실제 뜻 검색을 준비할 때 추가 설치함.

```powershell
s3.2/.venv/Scripts/python.exe -m pip install -r s3.2/requirements-model.txt
```

`s3.2/.env.example`을 참고해 `s3.2/.env` 작성 가능함. 기존 `.env`는 덮어쓰지 않음.  
설정 우선순위는 CLI → 환경 변수 → `s3.2/.env` → 루트 `.env` → 기본값임.

- 모델 기본값: `nlpai-lab/KURE-v1`, 최초 실제 실행 시 다운로드 발생함.
- `EMBED_MODEL`: 조 전체가 동일한 모델 사용 필요함.
- `CLAUDE_API_KEY`: `answer` 실행에 필요함. 루트 또는 `s3.2/.env`에 저장하고 출력하지 않음.
- `CLAUDE_MODEL`: 선택 설정임. 미지정 시 `claude-sonnet-5` 사용함.
- `DB_PATH`: 상대 경로는 `s3.2` 기준임. `--group 2` 이상은 해당 조의 기본 DB 경로를 사용함.
- 기본 DB: `s3.2/data/chroma/group1/`. 다른 조는 `group2`~`group6`으로 분리함.
- 골격 기본 컬렉션: `card_docs`, 완성본 기본 컬렉션: `card_docs_ref`임.
- 모델을 바꿀 때 새 `--db-path` 또는 `--collection` 사용 필요함. 모델이 다른 컬렉션 재사용은 차단함.

## 슬라이드 5~14: 읽기·적재·검색

기본 입력은 `s3.1/data/chunked/chunks.jsonl`임. S3.1 결과의 승인된 청크만 읽음.  
`review.jsonl`·`exceptions.jsonl`은 검토 대상이므로 적재하지 않음.

```powershell
s3.2/.venv/Scripts/python.exe s3.2/run_lab.py check
s3.2/.venv/Scripts/python.exe s3.2/run_lab_ref.py index --group 1
s3.2/.venv/Scripts/python.exe s3.2/run_lab_ref.py inspect --group 1
s3.2/.venv/Scripts/python.exe s3.2/run_lab_ref.py search --query "연회비 반환 기준" --top-k 3
```

학생 함수 완성 후 위 명령의 `run_lab_ref.py`를 `run_lab.py`로 바꿔 실행함.  
적재 미완성 조는 검색 함수 작성 후 `--collection card_docs_ref`로 같은 조의 강사 적재본을 검색 가능함.  
강사 적재본도 해당 모델로 `run_lab_ref.py index`를 실행해야 생성됨.

직접 지정한 `--input`·`--output`·`--questions`는 현재 작업 폴더 기준임.  
`--db-path`만 `s3.2` 기준임. 실행 도움말은 `run_lab.py --help`로 확인함.

Python에서 교재의 함수 시그니처를 그대로 호출하는 예시임. 작업 위치는 `s3.2`임.

```python
from src.helpers import configure
from src.retrieval_ref import search

configure(collection="card_docs_ref")
hits = search("연회비 반환 기준", top_k=3,
              filters={"doc_type": "regulation", "version": "1.2"},
              user_role="agent")
for hit in hits:
    print(hit.score, hit.metadata["chunk_id"], hit.metadata["source"])
```

- 실제 배포 데이터의 `version`은 `check` 출력으로 확인함. 교재의 합성 예시 `v3`를 그대로 넣지 않음.
- KURE-v1은 공식 사용 예시처럼 적재와 검색 모두 원문을 그대로 임베딩함. 별도 접두어를 붙이지 않음.
- KURE-v1 벡터는 1,024차원이며 모델 입력 한도는 8,192토큰임.
- 실제 모델 입력 한도를 넘으면 자르지 않고 실패로 기록함. S3.1에서 재분할 후 재적재 필요함.
- 메타데이터 `None` 키는 제거하고, 목록·객체는 JSON 문자열로 보존함. 필터는 원래의 단순 값 키에 적용함.
- `agent`는 `public`·`internal`, `auditor`는 `restricted`까지 검색 가능함. 모르는 역할은 오류로 중단함.
- 감사 역할에 상담 조회 권한이 있어도 모든 질문의 Top-K에 상담이 포함되는 것은 아님.
  상담 접근 확인은 `filters={"doc_type": "consult_log"}`로 수행함.
- `ok + len(failed)`로 입력 건수를 대조함. `count == ok` 비교는 비어 있던 컬렉션에 처음 적재할 때 적용함.
- 배치 재시도는 1회임. 재실패 시 콘솔에 ID·오류 사유를 남기고 `failed`로 반환함.
- 종료 코드: 0 성공, 1 설정·입력 오류, 2 일부 적재 실패, 3 골격 작성 필요임.

## 지금 수행하는 기본 동작 검사

```powershell
s3.2/.venv/Scripts/python.exe -X utf8 s3.2/smoke_test.py
s3.2/.venv/Scripts/python.exe s3.2/run_lab_ref.py index --backend smoke
```

`smoke`는 모델 다운로드·외부 API 호출 없이 만든 테스트 벡터임. 의미 유사도와 검색 품질 판단에는 사용 불가함.  
ChromaDB 적재·필터·조회 자체는 실제 실행함. 테스트 DB는 `data/smoke/`와 `data/chroma_smoke/`에 별도 저장함.  
실제 모델의 DB나 조별 코드 사본에는 테스트 데이터가 섞이지 않음.

## 슬라이드 15~16: 함께 진행할 표현 변형 실습

KURE-v1 실제 모델로 아래 비교 실습을 실행했으며, 정답 `D1_0010`의 순위가 1위·2위·3위로 달라짐.

1. 양식을 조별 사본으로 복사함.
2. 원문을 확인해 정답 `chunk_id`를 먼저 `expected_chunk_ids`에 기록함.
3. 같은 뜻의 상담사 말투·고객 말투·키워드형 질문을 `questions`에 각각 기록함.
4. 아래 명령으로 Top-3와 정답 포함 순위를 저장하고 원인 가설을 조가 작성함.

```powershell
Copy-Item s3.2/templates/query_variants.json s3.2/templates/group1_queries.json
# group1_queries.json 편집 후 실행함.
s3.2/.venv/Scripts/python.exe s3.2/run_lab_ref.py variants --questions s3.2/templates/group1_queries.json
```

출력: `s3.2/data/group1/w3_query_variants.md`. `--group`으로 조 번호 변경 가능함.  
`variants`는 `--backend smoke` 사용을 거절하며 빈 질문·미지정 정답으로 실행하지 않음.

2026-09-10 검증 결과는 `data/slide15/results_kure_v12.md`에 저장함.  
재현 질문은 `templates/group1_queries_v12.json`, 후보 24건의 순위 기록은  
`data/slide15/rank_probe_kure_v12.json`에 저장함.  
기본 강사 컬렉션 `card_docs_ref`와 재현용 `card_docs_ref_kure_v12`에 KURE 벡터 485개를 적재함.  
실패 0건과 벡터 차원 1,024를 확인함.

## 슬라이드 18~21: 프롬프트 조립과 원문 발췌 검사

학생은 `src/answering.py`의 TODO 한 곳을 완성함. 강사 완성본은 `_ref`로 바로 실행 가능함.  
Windows 명령줄에서 JSON 따옴표 문제를 피하도록 `--doc-type`과 `--version` 필터를 제공함.

```powershell
s3.2/.venv/Scripts/python.exe s3.2/run_lab_ref.py prompt `
  --query "연회비 면제 조건은?" --top-k 3 `
  --doc-type regulation --version 1.2 --collection card_docs_ref

s3.2/.venv/Scripts/python.exe s3.2/run_lab_ref.py answer `
  --query "연회비 면제 조건은?" --top-k 3 `
  --doc-type regulation --version 1.2 --collection card_docs_ref `
  --output s3.2/data/slide21/answer_test_kure_v12.json
```

`prompt`는 API 없이 검색결과 번호·원본 문서·`chunk_id`·본문·질문 위치·빈 검색 결과를 검사함.  
`answer`는 Claude를 한 번 호출하고 다음 구조를 기록함.

- `answer.conclusion`: 질문에 직접 답하는 결론임.
- `answer.evidence`: 사람이 읽는 원문 위치·연속 원문 발췌·내부 `chunk_id` 목록임.
- LLM의 `ref(현재 검색결과의 임시 순번)`는 `hits[ref - 1]` 연결에만 사용하며 화면에는 표시하지 않음.
- `answer.sources`: 사용한 원본 파일명과 버전·시행일 목록임.
- `answer.verification`: JSON 구조·검색결과 참조 범위·발췌문 원문 일치 검사 결과임.
- `rendered_answer`: 사용자 화면에 표시할 결론·근거·출처·주의사항임.

원문 위치는 약관 `문서명 제N조 제M항`, 혜택 `카드명 > 항목`, 상담이력  
`상담 기록번호 > 정확한 턴` 형식임. 상담 턴을 찾지 못한 경우에만 청크의 턴 범위를 표시함.  
약관은 발췌문이 속한 항을 청크 본문에서 찾아 표시함.

2026-09-10 실제 실행 결과는 `data/slide21/prompt_test_kure_v12.json`과  
`data/slide21/answer_test_kure_v12.json`에 저장함. 사람이 읽는 결과와 검증 내용은  
`data/slide21/test_report_kure_v12.md`에서 확인 가능함.

## 구현 참고

- [Chroma 코사인 컬렉션 설정](https://docs.trychroma.com/docs/collections/configure)
- [Chroma 메타데이터 필터](https://docs.trychroma.com/docs/querying-collections/metadata-filtering)
- [Sentence Transformers 임베딩](https://www.sbert.net/examples/sentence_transformer/applications/computing-embeddings/README.html)
- [KURE-v1 모델 카드](https://huggingface.co/nlpai-lab/KURE-v1)
