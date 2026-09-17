# 기존 소스 분석 (1단계)

대상: `hybrid-ai-lab/` 의 s2.3(추출·정제) → s3.1(청킹) → s3.2(임베딩·적재·검색) → s3.3(Hybrid·리랭킹)  
목적: 같은 기능을 LangChain·LangGraph 기반 Indexer·Retriever 앱 2개로 재구현하기 위한 근거 정리  
작업 방식: 팀원 4명(지식니·플로니·커넥니·스택니)이 읽기 전용으로 병렬 분석, 클로니가 통합.  
소요 시간 실측(6절)은 클로니가 별도 스크립트로 수행함. 줄 번호 기준: 2026-09-13 작업트리

용어 한 줄 풀이  
- 청킹 = 긴 문서를 검색하기 좋은 크기로 자르기  
- 임베딩 = 글을 숫자 목록(벡터)으로 바꿔 뜻이 비슷한 것끼리 가깝게 놓기  
- BM25 = 같은 단어가 많이 나오는 문서에 점수를 주는 고전 검색  
- 리랭킹 = 뽑아온 후보를 다시 줄 세우기  
- StateGraph(상태 그래프) = 노드(단계)들이 주고받는 값을 한 곳(State)에 모아두고 순서대로 실행하는 구조

## 목차
1. 재개발 대상 함수 목록과 시그니처 (1절)
2. 기존 파라미터 승계표 (2절)
3. 기존 입력 검증·예외 규칙 목록 (3절)
4. 기능별 LangChain 대체 컴포넌트 매핑표 (4절)
5. 승계하지 않는 항목과 사유 (5절)
6. 단계별 소요 시간 실측값과 예산 제안값 (6절)
7. 부록 A: 메타데이터 키 전체 목록 / 부록 B: 기존 실측 수치 대조 / 부록 C: 실행 흐름·종료 코드 /  
   부록 D: LLM 어댑터·키 로딩 / 부록 E: 계층·CLI·HTTP 진입점 / 부록 F: 환경 선검증 결과

---

## 1. 재개발 대상 함수 목록과 시그니처 (지식니)

### 1-1. s2.3 추출·정제 (`s2.3/docprep/`)

| 소스 위치 | 시그니처 | 한 줄 책임 |
|-----------|----------|-----------|
| `application/ports.py:6` | `PdfReader.__call__(path: Path, remove_margins: bool = True) -> tuple[list[dict], dict]` | PDF 추출기 계약(문서 목록 + 보고서) |
| `application/ports.py:10` | `DocumentStore.read_text / load_markdown / save` | 파일 입출력 계약 |
| `application/pipeline.py:16` | `Options(input, output, split_by, pseudonymize, remove_margins, report, validate, segment)` | 처리 옵션 묶음(frozen dataclass) |
| `application/pipeline.py:28` | `select_sources(location: Path, segment: int \| None = None) -> list[Path]` | 허용된 D1·D2 PDF와 D3 상담 TXT만 골라냄 |
| `application/pipeline.py:45` | `check_documents(documents: list[dict], schema: dict) -> dict` | 스키마 기준 일괄 검증 결과 집계 |
| `application/pipeline.py:79` | `Pipeline.run(options, profiles: dict, schema: dict) -> dict` | 선택 → 추출 → 프로필 병합 → 검증 → 저장 조립 |
| `application/pipeline.py:129` | `Pipeline.validate_saved(location: Path, schema: dict) -> dict` | 저장된 Markdown만 다시 검사 |
| `domain/consultations.py:15` | `to_pseudo(value: str, prefix: str = "m") -> str` | SHA-256 앞 16자리로 가명 ID 생성 |
| `domain/consultations.py:24` | `_fields(block: str, label: str) -> dict[str, str]` | `[접수정보]` 같은 머리줄에서 키:값 추출 |
| `domain/consultations.py:31` | `_clean(text, intake, identity, member, age_band) -> str` | 이름·연락처·카드번호·나이 제거·치환 |
| `domain/consultations.py:65` | `parse_consultations(text, source, split_by="header", pseudonymize=False) -> list[dict]` | 상담 1건 = Document 1건으로 분리 |
| `domain/validation.py:9` | `validate_document(doc: dict, enum_overrides: dict \| None = None) -> list[str]` | 문서 1건의 메타데이터·개인정보 잔존 검사 |
| `infrastructure/pdf_reader.py:9` | `_lines(page)` | 페이지의 줄 좌표·글자 추출 |
| `infrastructure/pdf_reader.py:19` | `_margin(rect, height) -> bool` | 머리말·꼬리말 영역 판정 |
| `infrastructure/pdf_reader.py:23` | `_row_text(lines)` | 테두리 없는 표의 가로 관계를 ` \| ` 로 보존 |
| `infrastructure/pdf_reader.py:42` | `_metadata(text, filename) -> dict` | 원문에서 시행일·버전·공개등급만 읽음(추론 금지) |
| `infrastructure/pdf_reader.py:60` | `extract_pdf(path: Path, remove_margins: bool = True) -> tuple[list[dict], dict]` | 물리 페이지 1장 = 문서 1건 + 추출 보고서 |
| `infrastructure/file_store.py:13` | `markdown(doc: dict) -> str` | YAML 머리말 + 본문 Markdown 직렬화 |
| `infrastructure/file_store.py:17` | `safe_name(value: str) -> str` | 결과 파일명 안전성 검사 |
| `infrastructure/file_store.py:44` | `FileStore.save(output, documents, reports, validation, write_report, manifest) -> None` | 원자적 저장 + 이전 생성물 정리 |

### 1-2. s3.1 청킹 (`s3.1/`)

| 소스 위치 | 시그니처 | 한 줄 책임 |
|-----------|----------|-----------|
| `lab_io.py:11` | `load_documents(path: Path) -> list[dict]` | 개별 Markdown 우선, 없으면 `documents.jsonl` 읽음 |
| `lab_io.py:36` | `validate_documents(documents: list[dict]) -> None` | 청킹 입력 자격 검사(가명화·중복 확인) |
| `lab_io.py:65` | `normalize_table(text: str) -> str` | D2의 테두리 없는 표를 Markdown 표로 변환 |
| `lab_io.py:85` | `prepare_units(documents) -> tuple[list[dict], list[dict]]` | 페이지 → 조항·혜택·상담 "입력 단위"로 재구성, 제외분 기록 |
| `src/chunking.py:27` | `make_chunk(text, meta, doc_key, idx, **extra) -> Chunk` | 꼬리표 복사 + `chunk_id`·`char_len` 부착 |
| `src/chunking.py:38` | `_doc_key(meta) -> str` | `D1`/`D2` 문서 키 결정 |
| `src/chunking.py:48` | `_sections(text)` | 조(제N조) 경계 우선, 없으면 `##` 제목 경계 |
| `src/chunking.py:67` | `_units(body) -> list[str]` | 항 `(1)`·`①` 단위 분해 |
| `src/chunking.py:73` | `_cut(text, capacity) -> tuple[str, str]` | 문장·줄 경계 우선 자르기 |
| `src/chunking.py:82` | `_split_prose(title, body, max_chars, overlap)` | 줄글 분할 + 같은 조 안에서만 중첩 |
| `src/chunking.py:113` | `_table_parts(title, body)` | 표 블록과 반복 문맥 분리 |
| `src/chunking.py:134` | `_attribute_table(block) -> bool` | D2 "항목 \| 조건" 속성표 판정 |
| `src/chunking.py:139` | `_table_text(prefix, block, rows) -> str` | 문맥 + 머리글 2줄 + 선택 행 재조립 |
| `src/chunking.py:143` | `_exception_metadata(text, max_chars) -> dict` | 글자 상한 초과 예외 꼬리표 생성 |
| `src/chunking.py:150` | `_split_table(title, body, max_chars)` | 표를 행 묶음으로 분할, 중복 후보 제거 |
| `src/chunking.py:192` | `_cell_parts(row) -> list[str]` | `\|` 이스케이프를 지킨 셀 분해 |
| `src/chunking.py:197` | `enforce_token_limit(chunk: Chunk, counter, max_tokens: int) -> list[Chunk]` | 실제 토크나이저로 재검사·재분할 |
| `src/chunking.py:290` | `chunk_by_clause(doc_text, meta, max_chars=600, overlap=80) -> list[Chunk]` | D1·D2 청킹 본체 |
| `src/chunking.py:329` | `chunk_by_turn(record_text, meta, turns_per_chunk=4, overlap_turns=1) -> list[Chunk]` | D3 상담 턴 청킹 본체 |
| `token_budget.py:6` | `TokenBudget(path: Path, limit: int, prefix: str = '')` | 로컬 `tokenizer.json` 기반 토큰 계산기 |
| `token_budget.py:20` | `TokenBudget.count(text: str) -> int` | 접두어 포함 실제 토큰 수 |

### 1-3. s3.2 임베딩·적재·검색 (`s3.2/src/`)

| 소스 위치 | 시그니처 | 한 줄 책임 |
|-----------|----------|-----------|
| `models.py:5` | `Chunk(text: str, chunk_id: str, metadata: dict)` | 청크 데이터 모양 |
| `models.py:12` | `Hit(text: str, score: float, metadata: dict, rerank_score: float \| None = None)` | 검색 결과 데이터 모양 |
| `helpers.py:16` | `Settings(db_path, collection, embedding_backend, model)` | 실행 설정 묶음 |
| `helpers.py:31` | `configure(*, db_path=None, collection=None, embedding_backend=None, model=None) -> Settings` | 전역 설정 교체 |
| `helpers.py:56` | `get_collection(name: str = 'card_docs')` | 코사인 컬렉션 열기 + 모델 서명 검사 |
| `helpers.py:84` | `embed_texts(texts: list[str], kind: str = 'passage') -> list[list[float]]` | 접두어 처리·토큰 한도 검사·정규화 임베딩 |
| `helpers.py:120` | `sanitize_metadata(metadata: dict) -> dict` | None 제거, 구조값 JSON 문자열화, 권한 키 강제 검사 |
| `indexing_ref.py:11` | `embed_and_upsert(chunks: list[Chunk], batch_size: int = 32) -> dict` | 배치 적재 + 1회 재시도, `{"ok","failed"}` 반환 |
| `retrieval_ref.py:7` | `ROLE_ACCESS = {"agent": [...], "auditor": [...]}` | 역할 → 열람 가능 등급 매핑 |
| `retrieval_ref.py:13` | `search(query, top_k=5, filters=None, user_role="agent") -> list[Hit]` | 권한·조건 필터 + Top-K 벡터 검색 |
| `answering_ref.py:26` | `answer_with_sources(question, hits, threshold=THRESHOLD, ask_fn=ask_llm) -> dict` | 유사도 관문 + LLM 답변 + 근거 검증 |

### 1-4. s3.3 Hybrid·리랭킹 (`s3.3/src/`)

| 소스 위치 | 시그니처 | 한 줄 책임 |
|-----------|----------|-----------|
| `hybrid_utils.py:10` | `ROLE_ACCESS = {"agent": {...}, "auditor": {...}}` | s3.2와 같은 권한 매핑(집합 형태) |
| `hybrid_utils.py:17` | `get_bm25_index() -> tuple[dict, list[str], BM25Okapi \| None]` | Chroma 전체 청크를 읽어 BM25 색인 1회 생성(lru_cache) |
| `hybrid_utils.py:41` | `get_top_chunk_ids(scores, chunk_ids, count) -> set[str]` | BM25 상위 후보 ID 집합 |
| `hybrid_utils.py:49` | `map_scores_to_chunk_ids(scores, chunk_ids) -> dict[str, float]` | 점수 배열 → ID:점수 사전 |
| `hybrid_utils.py:57` | `normalize_scores(scores_by_id, candidate_ids) -> dict[str, float]` | 후보 집합 안에서 최소-최대 정규화 |
| `hybrid_utils.py:71` | `apply_filters(scores_by_id, chunks, filters, user_role) -> dict[str, float]` | BM25 신규 후보에도 권한·조건 재적용 |
| `hybrid_utils.py:90` | `to_hits(scores_by_id, chunks, top_k) -> list[Hit]` | 최종 정렬 후 `Hit` 변환(점수 6자리 반올림) |
| `hybrid_search_ref.py:17` | `search_hybrid(query, top_k=5, w_bm25=0.4, w_vec=0.6, filters=None, user_role="agent")` | 벡터·BM25 가중합 융합 |
| `rerank.py:22` | `rerank(query: str, hits: list, top_n: int = 5) -> list` | Cross-Encoder로 후보 재정렬 |
| `rerank.py:49` | `rerank_each_query_and_merge(...)` | **이식 제외** |

이식 제외 표기  
- `rerank.py:49` `rerank_each_query_and_merge()` — 질문 변환(다중 질의·분해) 전제 함수  
- `rerank.py:10` `from .adaptive_search import weighted_rrf` — 위 함수만 쓰는 의존  
- `src/adaptive_search.py`, `src/query_transform.py`, `query_transform_ref.py` — 적응형 검색·질문 변환·LLM 라우팅  
- 단, `rerank.py:13,16` 의 모델·`max_length` 상수는 `rerank()` 가 직접 쓰므로 승계 대상임

---

## 2. 기존 파라미터 승계표 (지식니)

| 구분 | 항목 | 값 | 소스 위치 | 승계 판단 |
|------|------|-----|-----------|-----------|
| 추출 | `remove_margins` 기본 | `True` (`--keep-margins` 로만 해제) | `pipeline.py:22`, `presentation/cli.py:28,45` | 그대로 |
| 추출 | 여백 판정 범위 | 위 5.5% 미만 / 아래 95% 초과 | `pdf_reader.py:20` | 그대로 |
| 추출 | 여백 줄 제거 조건 | 번호 형태이거나 2쪽 이상 반복 | `pdf_reader.py:93-94` | 그대로 |
| 추출 | 표 셀 가로 간격 기준 | 12pt 초과면 ` \| `, 이하면 공백 | `pdf_reader.py:36-37` | 그대로 |
| 추출 | 허용 입력 파일명 | D1·D2 PDF 2종 + `D3_S01 ~ S06_*_상담이력_합성.txt` | `pipeline.py:12-13` | 그대로 |
| 상담 분리 | `split_by` 기본 | `header` (선택지 `header`/`rule`/`date`) | `pipeline.py:20`, `cli.py:26` | `header` 고정 |
| 상담 분리 | 머리줄 형식 | `[상담ID] C-\d{8}-\d{3} \| YYYY-MM-DD \| 채널: … \| 회원번호: M-\d+` | `consultations.py:8` | 그대로 |
| 상담 분리 | 대화 유지 기준 | `고객:`/`상담사:` 로 시작하는 줄과 이어지는 줄만 | `consultations.py:104-113` | 그대로 |
| 가명화 | `pseudonymize` 기본 | `False` (실측 산출물은 `True`) | `pipeline.py:21`, `data/parsed/manifest.json` | 항상 `True`로 변경 |
| 가명화 | 가명 ID 형식 | `m_`/`a_` + SHA-256 앞 16자리 | `consultations.py:15-21` | 그대로 |
| 가명화 | 나이 → 연령대 | 60 이상은 `60대 이상`, 나머지는 10년 단위 내림 | `consultations.py:60-61,97` | 그대로 |
| 가명화 | 제거 대상 패턴 | 전화·이메일·PAN·`M-\d+`·`가상고객N`·`가상상담사N`·끝4자리 | `consultations.py:9-12,53-58` | 그대로 |
| 프로필 | D1 | `owner_dept=product_planning`, `access_level=public`, `supersedes=1.1` | `config/document_profiles.json:2-7` | 그대로 |
| 프로필 | D2 | `owner_dept=benefit_ops`, `access_level=public` | `config/document_profiles.json:8-12` | 그대로 |
| 스키마 | 필수 키 6종 | `doc_type, created_at, version, owner_dept, access_level, source` | `config/metadata_schema.json:2` | 그대로 |
| 스키마 | 허용 키 | 24종(부록 A 참조) | `config/metadata_schema.json:3-7` | 그대로 |
| 스키마 | 허용 값 | `doc_type` 3종 / `owner_dept` 3종 / `access_level` 3종 | `config/metadata_schema.json:8-12` | 그대로 |
| 청킹 | `max_chars` | `600` | `s3.1/src/chunking.py:290`, `s3.1/run_chunking.py:130` | 변경 금지 |
| 청킹 | `overlap` (D1) | `80` | `chunking.py:291`, `run_chunking.py:131` | 변경 금지 |
| 청킹 | `d2_overlap` (D2) | `0` | `run_chunking.py:132`, 적용부 `run_chunking.py:45` | 변경 금지 |
| 청킹 | `turns_per_chunk` (D3) | `4` | `chunking.py:329`, `run_chunking.py:133` | 변경 금지 |
| 청킹 | `overlap_turns` (D3) | `1` | `chunking.py:330`, `run_chunking.py:134` | 변경 금지 |
| 청킹 | 턴 정의 | 화자 병합 후 2마디 = 1턴 | `chunking.py:353-354` | 그대로 |
| 청킹 | 꼬리 흡수 규칙 | 남은 턴이 1 ~ 2개면 현재 조각에 흡수 | `chunking.py:360-361` | 그대로 |
| 청킹 | `chunk_id` 형식 | `{doc_key}_{idx:04d}` (예 `D1_0000`) | `chunking.py:30` | 변경 금지 |
| 토큰 | 토크나이저 | `nlpai-lab/KURE-v1` 로컬 `tokenizer.json` | `s3.1/data/chunked/report.json` `parameters.tokenizer_json` | 그대로 |
| 토큰 | `max_input_tokens` | `8192` | 같은 파일 `parameters.max_input_tokens` | 그대로 |
| 토큰 | `token_prefix` | `""` | 같은 파일 `parameters.token_prefix`, 기본값 `run_chunking.py:137` | 그대로 |
| 토큰 | 절단·패딩 | 계산 왜곡 방지를 위해 해제 | `token_budget.py:13-14` | 그대로 |
| 임베딩 | 모델 | `nlpai-lab/KURE-v1` | `helpers.py:21,27` | 그대로 |
| 임베딩 | 차원 | `1024` | `s3.2/README.md:95` (코드에 상수 없음). 6절 실측으로 확인 | 그대로 |
| 임베딩 | 접두어 | e5 계열만 `query: `/`passage: `, KURE-v1은 접두어 없음 | `helpers.py:106-111` | 그대로 |
| 임베딩 | 정규화 | `normalize_embeddings=True` | `helpers.py:116` | 그대로 |
| 임베딩 | 입력 한도 검사 | `model.max_seq_length` 초과 시 중단 | `helpers.py:112-114` | 그대로 |
| 임베딩 | `kind` 값 | `passage`(적재)/`query`(검색) 2종 | `helpers.py:84,86-87` | 그대로 |
| 임베딩 | smoke 백엔드 | 384차원 SHA-256 바이그램 해시 벡터 | `helpers.py:93-103` | 시험용만 |
| 적재 | `batch_size` | `32` | `indexing_ref.py:11` | 그대로 |
| 적재 | 재시도 | 최초 1회 + 재시도 1회(총 2회) | `indexing_ref.py:26` | 그대로 |
| 적재 | 같은 ID 처리 | `upsert` = 덮어쓰기 | `indexing_ref.py:12,30` | 그대로 |
| DB | 기본 경로 | `s3.2/data/chroma/group1` (`DB_PATH` 로 교체) | `helpers.py:24-28` | 새 경로 `vector/indexer/data/chroma` |
| DB | 컬렉션 | 골격 `card_docs`, 완성본 `card_docs_ref` | `helpers.py:19`, `s3.3/src/s32_bridge.py:33` | `card_docs` 고정 |
| DB | 거리 함수 | `cosine` (다르면 중단) | `helpers.py:65,70-71` | 변경 금지 |
| DB | 모델 서명 | `sentence-transformers:{model}:prompt-policy-v2` | `helpers.py:60-61` | 그대로 |
| 검색 | `top_k` 기본 | `5` | `retrieval_ref.py:13` | 그대로 |
| 검색 | 점수 환산 | `round(1 - distance, 3)` | `retrieval_ref.py:41` | 그대로 |
| 검색 | 권한 필터 | `{"access_level": {"$in": ROLE_ACCESS[user_role]}}` | `retrieval_ref.py:17` | 그대로 |
| 검색 | 조건 결합 | `{"$and": [권한] + [조건들]}` | `retrieval_ref.py:23` | 그대로 |
| Hybrid | `w_bm25` | `0.4` | `hybrid_search_ref.py:20` | 그대로 |
| Hybrid | `w_vec` | `0.6` | `hybrid_search_ref.py:21` | 그대로 |
| Hybrid | 후보 수 | `top_k * 4` (양쪽 각각) | `hybrid_search_ref.py:37,40,52-54` | 그대로 |
| Hybrid | BM25 구현 | `rank_bm25.BM25Okapi` | `hybrid_utils.py:5,38` | 그대로 |
| Hybrid | 토큰화 | 공백 분리 `text.split()`/`query.split()` | `hybrid_utils.py:30`, `hybrid_search_ref.py:43` | 그대로(동등성 유지) |
| Hybrid | 점수 정규화 | 후보 집합 최소-최대, 전부 같으면 0 | `hybrid_utils.py:62-67` | 그대로 |
| Hybrid | 최종 정렬 | 점수 내림차순, 동점은 `chunk_id` 오름차순 | `hybrid_utils.py:93` | 그대로 |
| 리랭킹 | 모델 | `BAAI/bge-reranker-v2-m3` | `rerank.py:13` | 그대로 |
| 리랭킹 | `max_length` | `512` | `rerank.py:16` | 그대로 |
| 리랭킹 | 활성화 함수 | `torch.nn.Sigmoid()` | `rerank.py:35` | 그대로 |
| 리랭킹 | `top_n` 기본 | `5` | `rerank.py:22` | 그대로 |
| 리랭킹 | 정렬 키 | `(-rerank_score, -score)` | `rerank.py:45` | 그대로 |
| 리랭킹 | 모델 적재 시점 | 모듈 임포트 시 1회 | `rerank.py:16` | 최초 사용 시 지연 로드로 변경 |
| 리랭킹 | 후보 수 / 최종 수 | `RETRIEVE_K=10`, `JUDGE_K=5` | `measure_slide28_rerank.py:26-27` | 후보 = Top-K × 4 (목표 확정값) |
| 답변 관문 | 유사도 임계값 | `0.62` | `s3.2/src/answering.py:25`, 사용부 `answering_ref.py:26,29` | 그대로 |

미확인 항목  
- 리랭커 배치 크기: `RERANKER.predict()` 에 `batch_size` 미지정(`rerank.py:33-37`) → 라이브러리 기본값 의존  
- 임베딩 배치 크기: `model.encode()` 에 `batch_size` 미지정(`helpers.py:116`). 적재 배치(32)와 별개  
- `BM25Okapi` 의 `k1`·`b`: 인자 없이 생성(`hybrid_utils.py:38`) → 기본값

---

## 3. 기존 입력 검증·예외 규칙 목록 (지식니)

"동작": 중단 = 예외로 처리 종료, 기록 = 보고서·검토 파일로 남기고 계속, 경고 = 메시지만 남김

### 3-1. 추출·정제 (s2.3)

| 규칙 | 소스 위치 | 동작 |
|------|-----------|------|
| 허용 목록 밖 파일만 존재 | `pipeline.py:40-41` | 중단 |
| 심볼릭 링크·`_instructor` 경로 | `pipeline.py:34` | 조용히 제외 |
| **결과 폴더가 원문 폴더 안이면 저장 금지** | `pipeline.py:83-84` | 중단 |
| **상담 분리 건수 ≠ `[상담ID]` 등장 수** | `pipeline.py:93-95` | 중단 |
| **프로필이 출처·식별 키 덮어쓰기 시도**(`source, page, record_id, member_id, member_pseudo_id, pseudonymized`) | `pipeline.py:105-107` | 중단 |
| 프로필 적용 후에도 필수 키가 빔 | `pipeline.py:113-116` | 경고 |
| 가명화 미실행 상태로 상담 처리 | `pipeline.py:103` | 경고 |
| 스키마 `allowed_keys` 밖 키 | `pipeline.py:54-56` | 기록 |
| 스키마 `required` 누락·빈 값 | `pipeline.py:57-59` | 기록 |
| `enums` 허용 목록 밖 값 | `pipeline.py:60-62`, `validation.py:23-31` | 기록 |
| **상담 ID(`record_id`) 중복** | `pipeline.py:63-67` | 기록 |
| 머리줄 없음 / 형식 오류 | `consultations.py:70,72` | 중단 |
| `split_by` 허용 3종 밖 | `consultations.py:73-74` | 중단 |
| `split_by=date` 사용 | `consultations.py:75-77` | 중단(항상 실패) |
| `split_by=rule` 경계 오류 | `consultations.py:78-81` | 중단 |
| 같은 파일 안 상담 ID 중복 | `consultations.py:87-88` | 중단 |
| 대화 없는 상담 | `consultations.py:114-115` | 중단 |
| 가명화 필요 항목 누락 | `consultations.py:116-122` | 중단 |
| 암호화 PDF | `pdf_reader.py:73-74` | 중단 |
| 표 인식 실패/글자 수 불일치 | `pdf_reader.py:102-104,116` | 경고 후 텍스트 유지 |
| 텍스트 레이어 없는 페이지 | `pdf_reader.py:133-134` | 경고(OCR 미사용) |
| 원문에서 못 읽은 메타데이터 | `pdf_reader.py:85-87` | 경고 |
| 상담은 정제 후에도 `restricted` 필요 | `validation.py:58-59` | 기록 |
| 정제 결과에 `member_id` 잔존 | `validation.py:73-74` | 기록 |
| 연락처·카드번호·원문 회원 ID 잔존 | `validation.py:68-70` | 기록 |
| 알려진 이름·정확한 나이 잔존 | `validation.py:71-72` | 기록 |
| `created_at` ≠ `consult_date` | `validation.py:56-57` | 기록 |
| 규정·혜택의 `effective_date`·`supersedes`·`page` 누락 | `validation.py:42-45` | 기록 |
| 파일명 불안전 / 경로 이탈 | `file_store.py:17-19,86-89` | 중단 |
| 중복 출처·상담 ID 파일 충돌 | `file_store.py:56-57` | 중단 |

### 3-2. 청킹 (s3.1)

| 규칙 | 소스 위치 | 동작 |
|------|-----------|------|
| 필수 문자열 6종 누락 | `lab_io.py:42-44` | 중단 |
| `doc_type` 3종 밖 | `lab_io.py:47-48` | 중단 |
| 상담에 `record_id`·`consult_date`·`channel`·`member_pseudo_id` 누락 | `lab_io.py:49-52` | 중단(가명화 결과 요구) |
| 상담이 `restricted` 아니거나 `member_id` 잔존 | `lab_io.py:53-54` | 중단 |
| 같은 (출처, 페이지) 또는 같은 상담 ID 중복 | `lab_io.py:60-62` | 중단 |
| 표지·메타정보·목차·출처 페이지 | `lab_io.py:108-109` | 기록(`skipped`) |
| D2 표지·목차·참고 목록 | `lab_io.py:138-139` | 기록(`skipped`) |
| 카드/혜택 경계 없는 참고 본문 | `lab_io.py:156-157` | 기록(`skipped`) |
| 연결할 조항·카드 없는 본문 | `lab_io.py:117,163` | 중단 |
| 카드명 연결 실패 | `lab_io.py:168-169` | 중단 |
| `0 <= overlap < max_chars` 위반 | `run_chunking.py:18-23`, `chunking.py:295-296,334-335` | 중단 |
| 결과 폴더가 입력 폴더 안 | `run_chunking.py:24-25` | 중단 |
| `--tokenizer-json`·`--max-input-tokens` 짝 불일치 | `run_chunking.py:26-27` | 중단 |
| 제목+overlap 이 `max_chars` 이상 | `chunking.py:84-85` | 중단 |
| 표 머리글·구분선 형식 오류 | `chunking.py:127-128` | 중단 |
| 데이터 행 없는 표의 문맥이 상한 초과 | `chunking.py:178-180` | 중단 |
| **단일 행+필수 문맥이 `max_chars` 초과** | `chunking.py:143-147` | 기록(`size_exception=True`, `token_check="required"`) |
| 길이 예외인데 토큰 검사기 미설정 | `run_chunking.py:54-57` | 기록(보류) |
| 분할 뒤에도 토큰 한도 초과 | `chunking.py:216` | 중단 → 상위에서 보류 전환(`run_chunking.py:58-62`) |
| 토큰 초과 일반 본문(표 아님) | `chunking.py:233` | 중단 → 보류 |
| **필수 조건행을 문장 단위로 쪼개야 하는 경우** | `chunking.py:239-240,278` | 중단 → 보류(의미 훼손 방지) |
| 긴 셀에 안전한 문장 경계 없음 | `chunking.py:243-244` | 중단 → 보류 |
| `chunk_id` 중복 / `char_len` 불일치 | `run_chunking.py:74-80` | 중단 |

### 3-3. 임베딩·적재·검색 (s3.2·s3.3)

| 규칙 | 소스 위치 | 동작 |
|------|-----------|------|
| `batch_size` 가 양의 정수 아님 | `indexing_ref.py:13-14` | 중단 |
| 입력에 중복 `chunk_id` | `indexing_ref.py:16-17` | 중단 |
| 본문 빈 청크 | `indexing_ref.py:21-22` | 기록(`failed`) |
| 배치 2회 시도 실패 | `indexing_ref.py:38-42` | 기록(`failed` + warning) |
| `access_level` 누락·허용 값 밖 | `helpers.py:122-123` | 중단 |
| `doc_type` 누락·허용 값 밖 | `helpers.py:124-125` | 중단 |
| 키가 문자열 아님 / 유한하지 않은 실수 | `helpers.py:130-133` | 중단 |
| 값이 문자열·정수·실수·불리언 아님 | `helpers.py:134` | JSON 문자열로 변환 |
| 컬렉션 임베딩 서명 불일치 | `helpers.py:68-69` | 중단 |
| 컬렉션 거리 함수가 cosine 아님 | `helpers.py:70-71` | 중단 |
| `kind` 가 `passage`/`query` 밖 | `helpers.py:86-87` | 중단 |
| 빈 문자열 임베딩 입력 | `helpers.py:88-89` | 중단 |
| **모델 입력 토큰 한도 초과** | `helpers.py:112-114` | 중단(`S3.1에서 재분할 필요`) |
| **모르는 역할(`user_role`)** | `retrieval_ref.py:16-17` | 중단(`KeyError`, 조건문 밖에 의도적 배치) |
| `top_k` 양의 정수 아님 / 빈 질문 | `retrieval_ref.py:18-21` | 중단 |
| 컬렉션이 비어 있음 | `retrieval_ref.py:25-27` | 빈 목록 반환 |
| Hybrid: 빈 질문 / `top_k<=0` / 가중치 음수·합 0 | `hybrid_search_ref.py:26-31` | 중단 |
| Hybrid: BM25 색인 없음 | `hybrid_search_ref.py:34-35` | 빈 목록 반환 |
| Hybrid: BM25 신규 후보에도 권한·조건 재검사 | `hybrid_utils.py:71-87` | 미충족분 제외 |
| 리랭킹: 빈 질문 / `top_n<=0` | `rerank.py:25-27` | 중단 |
| 리랭킹: 후보 없음 | `rerank.py:28-29` | 빈 목록 반환 |
| 답변: 근거 없음 또는 Top-1 점수 < 0.62 | `answering_ref.py:29-30` | 관문 차단 |

권한 매핑 정리  
- `agent` → `public`, `internal` (`retrieval_ref.py:8`, `hybrid_utils.py:11`)  
- `auditor` → `public`, `internal`, `restricted` (`retrieval_ref.py:9`, `hybrid_utils.py:12`)  
- 모르는 역할은 매핑 조회에서 `KeyError` 로 즉시 중단 — 기본 거부 방식임  
- 실데이터는 `public` 389건 + `restricted` 96건, `internal` 은 0건임

---

## 4. 기능별 LangChain 대체 컴포넌트 매핑표 (지식니)

판단 3종: **그대로**(설정만으로 대체) / **감싸서**(컴포넌트 + 얇은 래퍼) / **직접 유지**(기존 구현 이식)

| 기존 함수 | LangChain·LangGraph 컴포넌트 | 판단 | 사유 |
|-----------|------------------------------|------|------|
| `pdf_reader.extract_pdf()` | `langchain_community.document_loaders.PyMuPDFLoader` | 직접 유지 | 여백 5.5%/95% 규칙·표 글자 수 대조·`section_kind` 판정이 로더에 없음 |
| `consultations.parse_consultations()` | 정규식 기반 분할기 | 직접 유지 | 분리 건수 대조·중복 ID 중단 같은 "조용한 유실 금지" 규칙이 없음 |
| `consultations._clean()` (가명화) | 대응 컴포넌트 없음 | 직접 유지 | 개인정보 정제는 도메인 규칙 |
| `validation.validate_document()` | `pydantic.BaseModel` + LangGraph 노드 | 감싸서 | Pydantic 모델로 스키마 선언, 검사 규칙을 validator로 이식 |
| 문서 표현 `{"page_content","metadata"}` | `langchain_core.documents.Document(page_content=…, metadata=…)` | 그대로 | context7 확인: `BaseMedia` 가 `id`·`metadata` 보유, 구조 1:1 |
| `chunking.chunk_by_clause()` | `langchain_text_splitters.RecursiveCharacterTextSplitter` | 직접 유지 | 조·항 경계 우선, 표 행 묶음 분할, 길이 예외 후보 생성 재현 불가 |
| `chunking.chunk_by_turn()` | 대응 컴포넌트 없음 | 직접 유지 | 화자 병합 → 2마디=1턴 → 꼬리 흡수는 대화 전용 규칙 |
| `chunking.enforce_token_limit()` | `TextSplitter.from_huggingface_tokenizer(...)` | 감싸서 | 토큰 계산은 위임 가능, 조건행 분리 금지·보류 처리는 래퍼 유지 |
| `token_budget.TokenBudget` | `tokenizers.Tokenizer` / `transformers.AutoTokenizer` | 그대로 | 이미 직접 사용 중. `sha256` 기록만 래퍼 |
| `helpers.embed_texts()` | `langchain_huggingface.HuggingFaceEmbeddings(model_name="nlpai-lab/KURE-v1", encode_kwargs={"normalize_embeddings": True})` | 감싸서 | context7 확인: `model_name`·`model_kwargs`·`encode_kwargs` 지원. `max_seq_length` 초과 중단·접두어 정책은 래퍼 |
| `indexing_ref.embed_and_upsert()` | `langchain_chroma.Chroma.add_documents(documents, ids=…)` | 감싸서 | context7 확인: `Chroma` 는 `embedding_function` 로 생성. 배치 32·재시도 1회·`failed` 집계는 래퍼 |
| `helpers.get_collection()` | `langchain_chroma.Chroma(collection_name=…, persist_directory=…, collection_metadata=…)` | 감싸서 | cosine 강제·모델 서명 검사를 생성 직후 단계로 이동. `collection_metadata={"hnsw:space":"cosine"}` 유효성은 4단계 구현 시 실행으로 확인 |
| `helpers.sanitize_metadata()` | `langchain_community.vectorstores.utils.filter_complex_metadata` | 감싸서 | 기존은 복합 값을 버리지 않고 JSON 문자열로 보존하고 권한 키를 강제 검사함 |
| `retrieval_ref.search()` | `Chroma.similarity_search_with_score(query, k, filter)` | 감싸서 | `$and`/`$in` 필터는 그대로 전달 가능. 역할→등급 매핑·`round(1-distance,3)` 은 래퍼 |
| `hybrid_utils.get_bm25_index()` | `langchain_community.retrievers.BM25Retriever.from_documents(documents, bm25_params=…, preprocess_func=…)` | 감싸서 | context7 확인: 해당 시그니처 제공. 공백 분리 토큰화를 `preprocess_func` 로 이식 가능 |
| `hybrid_search_ref.search_hybrid()` | `langchain.retrievers.EnsembleRetriever(retrievers=[…], weights=[0.4, 0.6])` | 감싸서(주의) | EnsembleRetriever 기본은 RRF 융합, 기존은 최소-최대 정규화 후 가중합. 순위가 달라짐 → 융합부는 직접 유지 권고 |
| `hybrid_utils.normalize_scores()`/`apply_filters()` | 대응 컴포넌트 없음 | 직접 유지 | BM25 신규 후보에 권한을 다시 거는 규칙은 프레임워크가 대신하지 않음 |
| `rerank.rerank()` | `HuggingFaceCrossEncoder(model_name="BAAI/bge-reranker-v2-m3")` + 자체 정렬 | 감싸서 | context7 확인: `HuggingFaceCrossEncoder(model_name, model_kwargs)` 제공. `max_length=512`·Sigmoid·`rerank_score` 별도 보존은 압축기 인터페이스에 없어 래퍼 필요 |
| `answering_ref` 의 0.62 관문 | LangGraph 조건부 분기 | 그대로 | 점수 비교 후 분기 구조라 그래프 분기로 자연 이식 |

context7 조회 근거 (라이브러리 ID `/websites/reference_langchain`)  
- `langchain-huggingface/embeddings/huggingface/HuggingFaceEmbeddings` — `model_name`·`model_kwargs`·`encode_kwargs` 확인  
- `langchain-community/retrievers/bm25/BM25Retriever` — `from_documents(documents, bm25_params, preprocess_func)` 확인  
- `langchain-community/cross_encoders/huggingface/HuggingFaceCrossEncoder` — `model_name`·`model_kwargs` 확인  
- `langchain-core/documents/base/BaseMedia` — `id`·`metadata` 필드 확인  
- `langchain_chroma.Chroma` — `embedding_function` 생성·`delete_collection()` 확인, cosine 설정 키 미확인

---

## 5. 승계하지 않는 항목과 사유

### 5-1. 데이터 경로 (지식니)

| 미승계 항목 | 소스 위치 | 사유 |
|-------------|-----------|------|
| 적응형 검색(라우팅) | `s3.3/src/adaptive_search.py`, `run_adaptive.py` | 질문마다 기법을 고르는 LLM 라우팅. 범위 밖 |
| 질문 변환(Rewrite·HyDE·Step-back·Multi-Query·Decomposition) | `s3.3/src/query_transform.py`, `query_transform_ref.py` | LLM 기반 질의 확장. 데이터 경로가 아닌 질의 전처리 축 |
| `rerank_each_query_and_merge()` + `weighted_rrf` 의존 | `s3.3/src/rerank.py:49,10` | 질문 변환 전제 함수. `rerank()` 만 이식 |
| Decomposition 가중치(원 질문 0.1 / 하위 0.9) | `rerank.py:18-19`, `s3.3/README.md:40,253-254` | 위 함수 전용 상수 |
| `_ref.py` 빈칸 골격 쌍(`indexing.py`·`retrieval.py`·`answering.py`·`hybrid_search.py`) | `s3.2/src/`, `s3.3/src/` | 교육용 빈칸 실습본. 재구현엔 완성본 1벌만 |
| 조별 DB 경로 분리(`group1` ~ `group6`) | `s3.2/README.md:56` | 수업 진행용. 운영은 환경변수 1개로 충분 |
| `s32_bridge` 동적 모듈 적재 | `s3.3/src/s32_bridge.py` | 코드 복사 회피용 실습 우회. 단일 패키지면 불필요 |
| `--split-by rule`/`date` 실패 비교 경로 | `consultations.py:75-81` | 교육용 실패 시연. 운영은 `header` 고정 |
| `--keep-margins` 비교 경로 | `cli.py:28` | 교육용 대조 실행. 여백 제거 항상 수행 |
| `--pseudonymize` 선택 옵션 | `cli.py:26` | 가명화 항상 수행. 끄는 옵션을 만들지 않음 |
| PDF 합본 `.md` 생성 | `file_store.py:59-63` | 페이지별 메타데이터가 없어 색인 입력으로 부적합 |
| `normalize_table()` 의 D2 전용 문구 예외 | `s3.1/lab_io.py:77` | 특정 합성 문서 문구에 묶인 임시 규칙 (동등성 유지를 위해 코드는 이식하되 확장 대상 아님) |
| `pdf_reader._metadata()` 의 파일명 기반 `doc_type` 추정 | `pdf_reader.py:48` | D1/D2 파일명 규칙 의존, 새 문서 추가 시 확장 필요 |

### 5-2. LLM 경로 (커넥니)

| # | 항목 | 기존 → 변경 | 구분 | 사유 |
|---|---|---|---|---|
| 1 | Claude 기본 모델 | `claude-sonnet-5` → `claude-opus-5` | 변경 | 총괄 지시. 옵션 경로이며 실측 검증은 groq로 수행 |
| 2 | 기본 제공자 | Claude 고정 → `LLM_PROVIDER` 기본 `groq` | 변경 | 제공자가 import에 묶여 있던 구조를 설정값으로 뺌 |
| 3 | JSON 파싱 | `find`/`rfind` 슬라이스 → Structured Output | 변경 | 모델이 JSON 밖에 설명을 붙이는 경우를 휴리스틱으로 막던 코드임. 스키마 강제로 대체 |
| 4 | `max_tokens` | 1800·4000·500 혼재 → 답변 2000·판정 256 | 변경 | 용도별로 값이 흩어져 단가 예측이 불가능했음 |
| 5 | 재시도 정책 | Claude 1회·Groq 0회 → 429·5xx·연결만 2회 | 변경 | 같은 실행에서 재시도 횟수가 갈렸음. 4xx를 재시도하지 않는 규칙이 기존에는 없었음 |
| 6 | 예외 전달 | `from None`으로 체인 차단 → 분류 예외로 재포장 | 변경 | 현재는 429와 401을 코드로 구분할 방법이 없어 재시도 판정이 불가능함 |
| 7 | Groq 호출 수단 | `httpx.post` 직접 → `ChatGroq` | 변경 | 키를 문자열로 조립하는 지점이 사라짐 |
| 8 | JSON 강제 수준 | Groq만 API 수준, Claude는 프롬프트 문장만 | 변경 | 양쪽 모두 API 수준(Structured Output)으로 맞춤 |
| 9 | `.env` 탐색 폭 | Claude 2곳·Groq 1곳 → 공통 5단계 | 변경 | "키를 어디에 넣어야 하는가"의 답이 두 개가 되지 않게 함 |
| 10 | `thinking`·`effort` 분기 | `claude-fable` 전용 분기(`llm_client.py:40-47`) | 미승계 | 목표 모델 목록에 `claude-fable` 계열이 없음 |
| 11 | `CLAUDE_TEMPERATURE` | Claude에만 존재(`llm_client.py:49-51`) | 미승계 | 비대칭 설정. 온도는 제공자 기본값 사용 |
| 12 | 검증 실패 재호출 | `s3.3/answering.py:240-249`의 1회 재호출 | 승계 | 품질 재시도임. 전송 재시도(지수 백오프)와 분리하여 상한 2회 |
| 13 | 원문 발췌 검증 | `build_evidence_answer` (`evidence.py:27-103`) | 승계 필수 | Structured Output은 스키마만 보장하고 인용이 원문에 있는지는 보장하지 않음 |

---

## 6. 단계별 소요 시간 실측값과 예산 제안값 (클로니 실측)

측정 방법: `vector/.venv`(신규, torch 2.14.0+cpu)에서 기존 s2.3·s3.1 진입점을 **출력 경로만 임시 폴더로 바꿔** 1회씩
실행하고, s3.1 기존 `chunks.jsonl` 485건을 `sentence-transformers`로 임베딩함. 기존 산출물은 읽기만 하고 수정하지 않음.  
측정 스크립트: 세션 스크래치 `measure_stage1.py`, 결과 `measure/timings.json`. 측정일 2026-09-13.  
실행 환경: Windows 11, Python 3.13.13, CPU 실행(기존 s3.2 가상환경도 `torch+cpu`였음). RTX 4090 Laptop GPU는 미사용

| 단계 | 실행 명령(요지) | 실측 `elapsed_ms` | 결과 수치(기존 대조) | 예산 제안(+30%) |
|------|-----------------|------------------:|----------------------|----------------:|
| 추출·정제 1회 | `s2.3/parse_docs.py --in docs --out <임시> --pseudonymize --report --validate` | 9,078 | 문서 259(regulation 15 · benefit_guide 196 · consult_log 48), 검사 259 / 오류 0 — **일치** | 11,800 ms |
| 청킹 1회 | `s3.1/run_chunking.py --input <임시 parsed> --output <임시> --doc all --tokenizer-json <KURE tokenizer.json> --max-input-tokens 8192` | 1,292 | 청크 485(D1 53 · D2 336 · D3 96), 입력 단위 435 · 제외 16 · 보류 0 · 예외 56 — **일치** | 1,700 ms |
| KURE-v1 모델 로드 | `SentenceTransformer("nlpai-lab/KURE-v1", device="cpu")` | 14,721 | `max_seq_length` 8192 | 타임아웃 대상 제외, 로그 기록 |
| 임베딩 485건 1회 | `model.encode(texts, batch_size=32)` | 486,463 | 차원 **1,024** 확인(코드 상수가 아니라 실측으로 확정) | 632,400 ms (≈ 10.5분) |
| 임베딩 배치 1건(32건) | 위 값 ÷ 16 배치 | ≈ 30,400 | — | 노드 확정값 120초와 비교: 약 4배 여유 |

해석  
- 추출·청킹은 초 단위라 확정된 노드 타임아웃(PDF 1건 60초·청킹 1문서 30초) 안에 충분히 들어옴  
- CPU 임베딩은 485건에 약 8분이 걸림. 1건당 약 1초임. 증분 적재(해시 동일 시 건너뜀)가 비용 가드레일의 핵심임  
- GPU(CUDA) torch를 쓰면 임베딩·리랭킹이 수십 배 빨라지지만, 기존 실측 기준선이 CPU였고 교육생 환경에 GPU가
  없을 수 있어 **기본은 CPU 유지**를 제안함. GPU 사용 여부는 G1에서 사용자 결정 항목으로 올림
- 리랭킹·검색 지연은 기존 실측(검색 61 ~ 114ms, 리랭킹 2,762 ~ 9,798ms)을 그대로 예산 근거로 사용함(5단계에서 재실측)

---

## 부록 A. 메타데이터 키 전체 목록 (지식니)

### A-1. `s2.3/data/parsed/documents.jsonl` (문서 259건)

| 키 | regulation(15) | benefit_guide(196) | consult_log(48) | 값 예 |
|----|:---:|:---:|:---:|-------|
| `source` | O | O | O | `D1_개인회원표준약관_합성.pdf` |
| `doc_type` | O | O | O | `regulation`/`benefit_guide`/`consult_log` |
| `created_at` | O | O | O | `2026-09-10` |
| `version` | O | O | O | `1.2`/`1.0`/`v2` |
| `owner_dept` | O | O | O | `product_planning`/`benefit_ops`/`customer_service` |
| `access_level` | O | O | O | `public`/`restricted` |
| `effective_date` | O | O | - | `2027-01-15` |
| `supersedes` | O | O | - | `1.1`/`null` |
| `page` | O | O | - | `1` (1 이상 정수) |
| `synthetic` | O | O | - | `true` |
| `metadata_origin` | O | O | - | `source_text; missing values require instructor configuration` |
| `created_at_origin` | O | O | - | `pdf_creationDate (file creation, not business publication)` |
| `classification_basis` | O | O | - | `교육용 합성 약관의 고객 공개본으로 분류함` |
| `table_count` | O | O | - | `0` |
| `section_kind` | O | - | - | `body`/`contents` |
| `product_id` / `product_ids` | - | O | - | `D2-C001` / 목록 |
| `record_id` | - | - | O | `C-20260314-001` |
| `consult_date` | - | - | O | `2026-03-14` |
| `channel` | - | - | O | `앱 채팅`/`콜센터`/`영업점` |
| `pseudonymized` | - | - | O | `true` |
| `topic` | - | - | O | `앱 인증 불편 완화` |
| `member_pseudo_id` | - | - | O | `m_` + 16자리 |
| `agent_pseudo_id` | - | - | O | `a_` + 16자리 |
| `age_band` | - | - | O | `30대` |
| `member_id` | - | - | (가명화 미실행 시만) | 가명화 결과에는 금지 |

스키마 `allowed_keys` 24종(`metadata_schema.json:3-7`)에는 위 키 외 `member_id` 포함. 가명화 결과에는 나타나지
않으며 존재 자체를 오류로 잡음(`validation.py:73-74`).

### A-2. `s3.1/data/chunked/chunks.jsonl` (청크 485건)

최상위 키 3종: `text`, `chunk_id`, `metadata` (`chunking.py:20-24`, `run_chunking.py:109`).  
문서 메타데이터(A-1) 전체를 복사한 뒤 아래 키 추가됨.

| 추가 키 | 소스 위치 | 의미 | 나타나는 곳 |
|---------|-----------|------|------------|
| `doc_key` | `lab_io.py:123,142,155,172` | `D1`/`D2` | D1·D2 |
| `page_end` | `lab_io.py:119,123,161` | 조항이 걸친 마지막 페이지 | D1·D2 |
| `footnote_page` | `lab_io.py:128` | 붙인 각주 출처 페이지 | D1 일부 |
| `card_id`/`card_name` | `lab_io.py:155,172-173` | 카드 식별자·이름 | D2 |
| `clause_no` | `chunking.py:321-322` | `제10조 제1항` 형태 | D1·D2 |
| `turn_range` | `chunking.py:364` | `1-4` 형태 턴 범위 | D3 |
| `chunk_index` | `chunking.py:29` | 문서 안 순번 | 전체 |
| `char_len` | `chunking.py:29` | Python `len()` 글자 수 | 전체 |
| `size_exception`/`max_chars`/`exception_reason`/`exception_id` | `chunking.py:146-147`, `run_chunking.py:51-52` | 글자 상한 예외 표시 | 예외 56건 |
| `token_check`/`token_count`/`token_limit` | `chunking.py:214` | 실제 토큰 검사 결과 | 전체(`passed`) |
| `tokenizer_sha256`/`token_prefix` | `run_chunking.py:67-68` | 토크나이저 지문 | 전체 |
| `parent_chunk_id`/`token_part_index` | `chunking.py:218` | 토큰 재분할 시 부모 연결 | 이번 실행 미발생 |

`chunk_id` 형식 확인  
- D1·D2: `{doc_key}_{index:04d}` — 실제 값 `D1_0000`, `D1_0001` (4자리 0 패딩)  
- D3: `chunking.py:363`이 `D3_{record_id}_{n:04d}`로 만든 뒤 저장 단계(`run_chunking.py:63,69`)가 `D3_{n:04d}`로 다시 매김.
  **정본 ID = 저장 시점 `{doc_key}_{index:04d}`** (평가셋 정답 `D1_0010`·`D2_0003`도 이 형식)  
- 토큰 재분할 시: `{chunk_id}_part{index:04d}` (`chunking.py:227`)

`access_level` 값 분포(485건 집계): `public` 389(D1 53 + D2 336) · `restricted` 96(D3 전량) · `internal` 0.  
→ `agent`는 389건, `auditor`는 485건 열람 가능. `internal` 경로는 실데이터가 없어 단위 시험으로만 검증함

---

## 부록 B. 기존 실측 수치 대조 (지식니 확인 + 클로니 재실행)

| 항목 | 프롬프트 제시값 | 기존 산출물 확인값 | 클로니 1단계 재실행값 | 차이 |
|------|------------|--------|----------|------|
| 문서 총건수 | 259 | 259 (`manifest.json`, `validation.json`) | 259 | 없음 |
| 문서 내역 | 196·48·15 | benefit_guide 196 / consult_log 48 / regulation 15 | 동일 | 없음 |
| 검증 오류 | (미제시) | `invalid: 0` | 검사 259 / 오류 0 | - |
| 청킹 입력 단위 | 435 | 435 | 435 | 없음 |
| 제외 페이지 | 16 | 16 | 16 | 없음 |
| 검토 보류 | 0 | 0 | 0 | 없음 |
| 길이 예외 후보 | 56 | 56 | 56 | 없음 |
| 청크 총수 | 485 | 485 | 485 | 없음 |
| 청크 내역 | 53·336·96 | D1 53 / D2 336 / D3 96 | 동일 | 없음 |
| 평균·최대 글자 | (미제시) | D1 171.45/583, D2 482.24/623, D3 385.49/557 | - | - |
| 임베딩 차원 | 1,024 | README 기재값 | **1,024 실측** | 없음 |
| vector_top5 포함률 | 6/7 | `passed 6 / scored 7` (0.8571) | (5단계 재실측) | - |
| vector_top5 평균 순위 | 2.125 | 2.125 | (5단계) | - |
| hybrid_top5 포함률 | 6/7 | 6/7 | (5단계) | - |
| hybrid_top5 평균 순위 | 2.375 | 2.375 | (5단계) | - |

평가셋(`s3.3/templates/baseline_questions.json`): 질문 8건, q7은 정답 미매핑으로 제외 → 채점 7건.
정답 청크는 `D1_0010`(제10조 제1항)·`D2_0003`(한빛 모아생활 · 생활 포인트 적립) 2종, q6은 두 청크 모두 요구.
Top-K 밖이면 순위 페널티 6(`slide28_rerank_actual.json` `controls.missing_rank_penalty`).
같은 파일의 질문 변환 결과(7/7·1.125 등)는 이식 제외 범위이므로 비교 기준으로 쓰지 않음

---

## 부록 D. LLM 어댑터·키 로딩·오류 처리 (커넥니)

### D-1. 기존 LLM 호출 함수와 제공자별 차이

| 항목 | Claude 어댑터 `ask_llm` | Groq 어댑터 `ask_groq` |
|---|---|---|
| 위치 | `s3.2/src/llm_client.py:21-69` | `s3.3/src/groq_client.py:26-84` |
| 인자 | `system, user, max_tokens=1800, temperature=None` | `system, user, max_tokens=4000, temperature=None` |
| 호출 수단 | 공식 SDK `anthropic.Anthropic`(`:33`) | `httpx.post` 직접(`:53-61`), 엔드포인트 `api.groq.com/openai/v1/chat/completions` |
| 타임아웃 / 재시도 | `timeout=60.0`, SDK `max_retries=1`(`:33`) | `timeout=60.0`(`:60`), 재시도 **없음** |
| 프롬프트 분리 | 최상위 `system` 필드 + user 메시지 1건(`:37-38`) | `messages`에 `role:system`·`role:user` 2건(`:40-43`) |
| 토큰 상한 키 | `max_tokens` | `max_completion_tokens`(이름 다름, `:44`) |
| JSON 강제 | 프롬프트 문장만 | `response_format={"type":"json_object"}`(`:46`) |
| 반환형 | `dict{content, stop_reason, usage{input_tokens,output_tokens}, model}` | 좌측 + `elapsed_ms`(`:75-83`) |
| 예외 | `ValueError`(키 없음), `RuntimeError`(HTTP·연결, `from None`) | 동일 구조(`:65,69`) |

상위 호출자: `answering_ref.answer_with_sources()`(Claude, 1800), `s3.3/answering.answer_with_condition_prompt()`
(Groq, 4000, 검증 실패 시 힌트 붙여 1회 재호출 `:240-249`), 질문 변환·라우팅(Claude, 500 — 이식 제외).
JSON 파싱은 정규식이 아니라 `find("{")`·`rfind("}")` 슬라이스 + `json.loads`(`evidence.py:9-24`).
`build_evidence_answer()`(`evidence.py:27-103`)가 `ref` 범위·원문 발췌 대조를 하여 `verification`을 붙임 → **승계 필수**

### D-2. 키 로딩 현황

| 어댑터 | 병합식 | 실제 우선순위 | 소스 |
|---|---|---|---|
| Claude | `{**dotenv(루트/.env), **dotenv(s3.2/.env), **os.environ}` → `.get(name) or default` | 환경변수 > `s3.2/.env` > 루트 `.env` > 기본값 | `llm_client.py:12-18` |
| Groq | `{**dotenv(루트/.env), **os.environ}` | 환경변수 > 루트 `.env` > 기본값 (앱 `.env` 안 읽음) | `groq_client.py:17-23` |

읽는 변수: `CLAUDE_API_KEY`(필수), `CLAUDE_MODEL`(기본 `claude-sonnet-5`), `CLAUDE_EFFORT`, `CLAUDE_TEMPERATURE`,
`GROQ_API_KEY`(필수), `GROQ_MODEL`(기본 `openai/gpt-oss-120b`), `GROQ_REASONING_EFFORT`.  
루트 `hybrid-ai-lab/.env`에 실재하는 키 이름(값 미확인): `CLAUDE_API_KEY`·`OPENAI_API_KEY`·`GROQ_API_KEY`.
`s3.2/.env`·`s3.3/.env`는 파일 없음. LLM용 CLI 인자(제공자·모델·키)는 기존 CLI 어디에도 없음  
함정: `.env.example`을 복사하면 빈 `CLAUDE_API_KEY=`가 루트 값을 덮고 `or default`가 `""`로 떨어져 키가 있어도 오류 발생.
**빈 문자열은 "없음"으로 보고 다음 단계로 내려가야 함**

### D-3. 오류 처리 현황

| 지점 | 잡는 예외 | 재시도 | 키 노출 | 소스 |
|---|---|---|---|---|
| Claude HTTP 오류 | `anthropic.APIStatusError` 전체(401·429·5xx 구분 없음) → `RuntimeError from None` | 없음 | 없음 | `llm_client.py:55-58` |
| Claude 연결 오류 | `APIConnectionError` → `RuntimeError from None` | 없음 | 없음 | `:59-60` |
| Groq HTTP 오류 | `httpx.HTTPStatusError` 전체 → `RuntimeError from None` | 없음 | 없음 | `groq_client.py:63-67` |
| Groq 응답 해석 | 처리 없음(`JSONDecodeError`·`KeyError` 전파) | 없음 | 없음 | `:72-73` |
| S3.2 답변 상위 | `ValueError`만 잡고 `RuntimeError`는 전파 | 없음 | 없음 | `answering.py:62-65` |
| S3.3 답변 상위 | 어댑터 예외 안 잡음. 검증 실패 시 1회 재호출 | 품질 1회 | 없음 | `s3.3/answering.py:240-249` |

공통 관찰: `from None`이 원인 체인을 끊어 **429와 401을 코드로 구분할 수 없음** → 재시도 판정 불가.
키 값이 메시지·반환·로그로 나가는 경로는 없음. 디버그 덤프(`attempts`) 범위는 응답만으로 제한할 것

### D-4. LangChain 대체 매핑 (context7 `/websites/reference_langchain` 확인)

| 기존 | 대체 | 주요 생성 인자 | Structured Output |
|---|---|---|---|
| `ask_groq` | `langchain_groq.ChatGroq` | `model="openai/gpt-oss-120b"`, `api_key`, `timeout=60`, `max_retries=0`, `max_tokens=2000` | `with_structured_output(schema, method=..., include_raw=True)` — Groq 허용 `method` 값은 4단계 실호출로 확정 |
| `ask_llm` | `langchain_anthropic.ChatAnthropic` | `model="claude-opus-5"`, `api_key`, `timeout=60`, `max_retries=0`, `max_tokens=2000` | `method="json_schema"`(context7 확인: `function_calling`·`json_schema`) |
| 없음(신규) | `langchain_openai.ChatOpenAI` | `model=<Config>`, `api_key`, `timeout=60`, `max_retries=0` | `method="json_schema"` |
| 제공자 분기 | 자체 팩터리 함수(`LLM_PROVIDER`) | 제공자별 `method`·전용 인자 차이를 팩터리가 흡수 | — |
| `parse_json_response` | Structured Output 파싱 결과(Pydantic 모델) | — | `include_raw=True` → `{"raw","parsed","parsing_error"}` |
| SDK `max_retries=1` | `max_retries=0` + 어댑터 자체 재시도 | SDK 재시도와 겹치면 시도 수가 **곱해져** 180초 초과 위험 | — |

재시도 대상 골라내기: `with_retry(retry_exception_types=...)`는 예외 **타입**만 받음. 제공자 SDK 예외 클래스가 3벌이라
**어댑터가 상태 코드를 보고 자체 예외(`LLMRetryableError` 등)로 재분류한 뒤 그 타입만 재시도**하는 방식을 채택.
지수 백오프(초기 1초·배수 2·지터 ±20%·2회)는 어댑터 안에서 직접 구현하여 총 대기 180초 상한을 계산으로 보장

### D-5. 제공자 추상화 초안

Protocol 2메서드: `complete(system, user, *, max_tokens=2000) -> LLMResult`,
`complete_structured(system, user, schema, *, max_tokens=256) -> StructuredResult`.  
반환형: `LLMResult(content, model, input_tokens, output_tokens, stop_reason, elapsed_ms)`,
`StructuredResult(parsed, raw, parsing_error, usage, elapsed_ms)`

예외 분류표

| 분류 | 자체 예외 | 판정 기준 | 재시도 | 사용자 메시지 |
|---|---|---|---|---|
| 일시 장애 | `LLMRetryableError` | HTTP 429, 500 ~ 599, 연결 실패·타임아웃 | 대상(2회) | `일시적 혼잡으로 재시도 중임` |
| 인증 오류 | `LLMAuthError` | HTTP 401·403 | 비대상 | `키 권한 확인 필요`(키 값 미포함) |
| 요청 오류 | `LLMRequestError` | HTTP 400·404·422 | 비대상 | `모델명 또는 요청 형식 확인 필요` |
| 설정 누락 | `LLMConfigError` | 키·모델 미설정 | 비대상 | `{변수명}을 설정해야 함`(이름만) |
| 응답 검증 실패 | `LLMValidationError` | 스키마 불일치·인용 대조 실패 | 비대상(품질 재시도는 그래프 루프) | `확인 필요` |

Config 키 이름: `LLM_PROVIDER`(기본 `groq`), `GROQ_API_KEY`(LangChain 기대 이름과 일치), `OPENAI_API_KEY`(일치),
`CLAUDE_API_KEY` — LangChain은 `ANTHROPIC_API_KEY`를 기대하므로 **Config가 `CLAUDE_API_KEY` → `ANTHROPIC_API_KEY` 순으로
찾아 `ChatAnthropic(api_key=...)` 생성 인자로 명시 전달**(환경변수 복사 금지). 모델: `GROQ_MODEL`·`CLAUDE_MODEL`·`OPENAI_MODEL`

---

## 부록 E. 계층·CLI·HTTP 진입점 (스택니)

### E-1. s2.3 계층 분리 기준표

| 계층 | 들어 있는 파일·함수 | 담당 책임 | 다른 계층을 부르는 방식 | 외부 I/O |
|---|---|---|---|---|
| `presentation/` | `cli.py:21 main`, `:14 read_object` | argparse 옵션 해석, 기본 경로 결정, 사람용 결과 출력, 종료 코드 | 응용 직접 import(`cli.py:7`). 인프라 구현체는 `Pipeline(extract_pdf, FileStore())`로 **주입**(`cli.py:36`) | stdout·stderr·설정 JSON 읽기 |
| `application/` | `pipeline.py:16 Options`, `:28 select_sources`, `:45 check_documents`, `:75 Pipeline`, `:79 run` | 선택 → 추출 → 정제 → 검증 → 저장 **순서 조립**, 출력 경로 안전성 판정 | 도메인 직접 import. 인프라는 `ports.py`의 Protocol 타입으로만 알고 생성자로 받음 | 존재 확인·해시만 직접, 읽기·쓰기는 `store` 경유 |
| `application/ports.py` | `PdfReader.__call__(path, remove_margins=True) -> tuple[list[dict], dict]`, `DocumentStore.read_text/load_markdown/save` | 입출력 **계약만** 선언 | 없음 | 없음 |
| `domain/` | `consultations.py`, `validation.py` | 상담 분리·가명화·메타데이터 검사 규칙 | 같은 도메인만 import | 없음(표준 라이브러리만) |
| `infrastructure/` | `file_store.py FileStore`, `pdf_reader.py extract_pdf` | PyYAML·PyMuPDF 어댑터, 원자적 파일 교체, 경로 탈출 차단 | 상위 계층을 부르지 않음 | 파일·PDF 읽기·쓰기 |

핵심: `application → infrastructure` 직접 import **0건**. 표현 계층이 CLI 1개에서 CLI + HTTP 2개로 늘어도 응용 계층이
그대로 재사용되는 근거임. 표현 계층 전용 테스트는 기존에 없음 → 새 앱에서 `TestClient` 라우트 시험이 메꿈

### E-2. 기존 CLI 진입점 규격과 목표 옵션 대조

| 실습 | 진입 파일 | 결과 출력 | 종료 코드 |
|---|---|---|---|
| s2.3 | `parse_docs.py` → `cli.main` | 텍스트 stdout + 파일 | 0 / 1 예외 / 2 검사 오류 |
| s3.1 | `run_chunking.py main` | 요약 stdout + 파일 6종 | 0 / 2 검토 보류 / 1 예외 |
| s3.2 | `run_lab(_ref).py` → `lab_cli.main` | stdout JSON + `--output` | 0 / 2 failed 존재 / 3 미구현 / 1 예외 |
| s3.3 | `lab_cli.py`·`run_rerank.py`·`run_answer.py` | stdout JSON + 파일 | 0 / 3 미구현 / 1 예외 (`run_*`는 예외 미처리) |

목표 옵션 판정(승계/이름 변경/신설/폐기)

| 앱 | 옵션 | 기존 대응 | 판정 |
|---|---|---|---|
| Indexer | `--in`, `--out` | s2.3 `--in`/`--out`(`cli.py:23-24`), s3.1·s3.2 `--input`/`--output` | 승계(s3.1·s3.2는 이름 변경) |
| Indexer | `--doc {D1,D2,D3,all}` | s3.1 `--doc` 기본 `D1`(`run_chunking.py:128`) | 승계. **새 앱 기본값은 `all`** |
| Indexer | `--segment {1..6}` | s2.3·s3.1 동일 | 승계 |
| Indexer | `--embedding-backend {sentence-transformers,smoke}` | s3.2 `--embedding-backend`(`lab_cli.py:32`) | 승계 |
| Indexer | `--thread-id`, `--full-reindex`, `--dry-run` | 없음(전수 grep 0건) | 신설 |
| Retriever | `--query`, `--role`(choices agent/auditor), `--prompt-only` | s3.2·s3.3 | 승계 |
| Retriever | `--top-k` | s3.2 `--top-k`(5), s3.3 `--retrieve-k`(10)·`--judge-k`(3)·`--top-n`(5) | 이름 통합. **`--top-k` = 최종 건수, 후보 수 = Top-K × 4 고정** |
| Retriever | `--mode {vector,hybrid,hybrid_rerank}` | s3.3 `--mode`는 질문 변환 기법 5종 | 이름 승계 + 뜻 교체(질문 변환은 범위 제외) |
| Retriever | `--thread-id`, `--dry-run`, `--max-llm-calls` | 없음(호출 수를 세는 코드만 있음) | 신설 |
| 서버 | `--host`, `--port`, `--reload` | 없음. 포트 8001도 소스에 없음 | 신설 |

목표 소유표에 없는 기존 옵션(`--split-by`·`--pseudonymize`·`--keep-margins`·`--max-chars`·`--overlap`·`--filters`·`--group`·
`--db-path`·`--collection`·`--model`·`--batch-size` 등)은 폐기하고 고정값 또는 Config 키로 이동함

### E-3. HTTP 진입점 부재 확인 (grep 결과)

```
$ grep -rniE 'fastapi|uvicorn|flask|starlette|http\.server|aiohttp|sse_starlette|EventSourceResponse' \
    s2.3 s3.1 s3.2 s3.3 --exclude-dir=.venv --exclude-dir=__pycache__ --exclude-dir=data --exclude-dir=results
[exit=1]  (일치 0건)
```

`requirements*.txt` 6개 전문(11줄)에도 웹 프레임워크·ASGI 서버 0건 → 라우트 4종·`X-Role` 검증·오류 응답은 **전부 신규 개발**.  
곁가지: `s3.3/src/groq_client.py:9`가 `httpx`를 import하지만 어느 requirements에도 없음(전이 의존) → 새 앱은 명시 선언

### E-4. CLI + API 공용 응용 계층 경계 설계 근거

응용 함수 후보(유스케이스 1개 = 함수 1개, 라우트는 이 함수 하나만 호출)

| 응용 함수 | CLI 호출자 | API 호출자 | 근거 |
|---|---|---|---|
| `run_indexing(req) -> IndexResult` | Indexer CLI | 없음 | `s3.2/lab_cli.py:57-65`가 같은 값 묶음을 이미 만듦 |
| `search_documents(req) -> SearchResult` | Retriever CLI | `POST /search` | `search()`·`search_hybrid()` 인자 집합이 사실상 같음 |
| `answer_question(req) -> AnswerResult` | Retriever CLI | `POST /answer` | `run_answer.py:57-110`이 한 흐름으로 이미 수행 |
| `stream_answer(req) -> AsyncIterator` | 없음 | `GET /answer/stream` | 신규 |
| `check_health() -> HealthResult` | (`--dry-run`) | `GET /health` | `lab_cli.py:66-72 inspect`가 `count`·차원·컬렉션을 뽑음 |

라우트에 두지 않을 것: 검색 방식 분기(`s3.3/lab_cli.py:56-124`), 점수·가중치 계산(`run_rerank.py:138-148`이 `run_answer.py:54-55`에
복사된 것이 위험의 실물 증거), 권한 매핑(`retrieval_ref.py:7-10`). 표현 계층은 `X-Role` 값을 꺼내 형식만 확인하고 넘김

같은 검색 결과가 네 가지 모양으로 나가던 기존 문제(`asdict(hit)` / `rank·chunk_id·score·source·location` /
`search_score` / `card_name`) → **Pydantic 모델 1벌을 응용 계층에 두고 CLI·API·State가 공유**. 키 이름은 기존 값 승계:
`chunk_id`·`score`·`rerank_score`·`text`·`metadata`(`models.py:7-16`), `conclusion`·`evidence`·`sources`·`verification`
(`evidence.py:30-72`), `llm_calls`(`run_answer.py:106-110`), `ok`·`failed`·`count_before`·`count_after`(`lab_cli.py:61-64`)

종료 코드 ↔ HTTP 상태 코드 대응표 초안

| 종료 코드 | 뜻 | HTTP | 발생 조건 |
|---|---|---|---|
| 0 | 정상 | 200 | — |
| 1 | 입력·설정 오류 | 400 | 빈 질문, `top_k` 비양수, 잘못된 `mode`, `X-Role` 누락·모르는 값 |
| 2 | 청킹 검토 보류(Indexer 전용) | 없음 | — |
| 3 | 일부 적재 실패(Indexer 전용) | 없음 | — |
| — | LLM 호출 상한 초과 | 429 | 요청당 2회·누적 200회 초과. 상류 429는 재시도 소진 후 429 |
| — | 인덱스 없음·모델 미준비 | 503 | 컬렉션 0건, 서명·cosine 불일치, 모델 로드 실패 |
| — | 요청 마감 초과 | 504 | 120초(신규) |
| — | 그 외 | 500 | — |

FastAPI 구현 근거(context7 `/websites/fastapi_tiangolo`): `Annotated[str, Header()]` 필수 헤더(`x_role` → `X-Role` 자동 변환),
`RequestValidationError` 핸들러로 422 본문을 `{error_code, message, detail}`·400으로 변환, `lifespan`에서 모델 1회 적재.
`sse-starlette`(context7 `/sysid/sse-starlette`): `EventSourceResponse(content, ping=15, send_timeout=...)`, `ping`=하트비트 초,
끊김은 `await request.is_disconnected()`로 감지. `TestClient(app).get/post(url, headers=..., json=...)`

단일 워커 근거: 전역 설정이 프로세스 지역 상태, 모델 2개 중복 적재 방지, `PersistentClient` 다중 프로세스 쓰기 미검증.
**`s3.3/src/rerank.py:16`은 import 시점에 CrossEncoder를 적재함 → 새 앱은 지연 로드(`lifespan`·최초 사용)로 옮김**

### E-5. `requirements.txt`·`.gitignore`·`.env.example` 초안

공통: `langchain`·`langchain-core`·`langgraph`·`langgraph-checkpoint-sqlite`·`langchain-huggingface`·`langchain-chroma`·
`chromadb`·`sentence-transformers`·`torch`·`python-dotenv`·`pydantic`·`PyYAML`(s2.3 Markdown 머리말에 실사용).  
Indexer 전용: `PyMuPDF`. Retriever 전용: `fastapi`·`uvicorn`·`sse-starlette`·`httpx`·`rank-bm25`·`langchain-groq`·
`langchain-anthropic`·`langchain-openai`. 버전은 부록 F의 설치 실측값으로 핀함

`.gitignore`(두 앱 동일): `.venv/`, `.env`, `__pycache__/`, `*.pyc`, `data/`  
`.env.example` 키 후보: `CHROMA_PATH`, `CHROMA_COLLECTION`, `EMBED_MODEL`, `RERANK_MODEL`, `LLM_PROVIDER`, `GROQ_API_KEY`,
`GROQ_MODEL`, `CLAUDE_API_KEY`, `CLAUDE_MODEL`, `OPENAI_API_KEY`, `OPENAI_MODEL`, `API_HOST`, `API_PORT` (값은 비움)

---

## 부록 C. 실행 흐름·종료 코드·LangGraph 대체 구조 (플로니)

### C-1. 기존 실행 흐름 요약 (진입점 → 주요 분기)

| 실습 | 진입점 | 흐름(요지) | 중단·건너뜀 지점 |
|---|---|---|---|
| s2.3 | `parse_docs.py:4` → `cli.main()` | `select_sources` → 파일별 `sha256` → PDF는 `extract_pdf`, TXT는 `parse_consultations` → 프로필 병합 → (옵션)검증 → `FileStore.save` | 출력이 입력 안(`pipeline.py:84`), 분리 건수 불일치(`:94-95`), 프로필 금지 키(`:106-107`) → 중단. `_instructor`·symlink 조용히 제외(`:34`) |
| s3.1 | `run_chunking.py:147` → `run(args)` | 파라미터 검증 5종 → `load_documents` → `validate_documents` → `prepare_units`(제외 페이지 기록) → 단위별 `chunk_by_turn`/`chunk_by_clause` → `enforce_token_limit` → 저장 6종 | `ValueError`는 `reviews`로 격하 후 계속(`:60-62,72-73`). `chunk_id` 중복·`char_len` 불일치는 중단(`:74-81`). `return 2 if reviews else 0`(`:121`) |
| s3.2 | `lab_cli.main()` | `configure()` 전역 설정 → action 분기(index/search/prompt/answer) → `embed_and_upsert`(배치 32, 재시도 1회) / `search` → `build_rag_prompt` → `answer_with_sources`(0.62 관문) | 컬렉션 서명·cosine 불일치 중단(`helpers.py:69,71`). 배치 2회 실패는 `failed` 기록 후 계속(`indexing_ref.py:38-42`). `return 2 if failed else 0`(`lab_cli.py:132`) |
| s3.3 | `lab_cli.py`·`run_rerank.py`·`run_answer.py` 3개 병존 | `configure_s32()` → `search_hybrid`(BM25 `lru_cache` 1회 색인 → 벡터 → 정규화 → 가중합 → 권한 재필터) → `rerank` → `build_answer_prompt` → `answer_with_condition_prompt`(검증 실패 시 힌트 붙여 1회 재호출) | `run_rerank`·`run_answer`는 `try/except` 없음 → 트레이스백 노출. 질문 변환 실패는 `keep`으로 조용히 격하(`adaptive_search.py:168-170`) |

기존 실측 지연(`s3.3/results/slide28_rerank_actual.json`, warm): vector_top5 검색 74.3ms, hybrid_top5 77.7ms,
리랭킹 평균 4,923ms · 최대 9,798ms

### C-2. 단계 경계 → 노드 대응표

Indexer (9노드)

| 노드 | 묶이는 기존 함수 | 소스 위치 | State: in → out |
|---|---|---|---|
| `select_sources` | `select_sources()` | `pipeline.py:28-42` | in `input_path`,`segment` → out `sources`(덮어쓰기) |
| `extract` | `Pipeline.run()` PDF/TXT 분기 + `extract_pdf()` + `parse_consultations()` 구조 분해부 | `pipeline.py:86-102`, `pdf_reader.py:60-151`, `consultations.py:65-115` | in `sources` → out `documents`(누적), `reports`(누적), `fingerprints`(누적) |
| `pseudonymize` | `parse_consultations()` 가명화 블록 + `_clean()` + `to_pseudo()` — **현재는 `extract`와 한 함수라 분리 필요** | `consultations.py:116-128, 31-62, 15-21` | in `documents` → out `documents`(덮어쓰기), `pseudonymized`(덮어쓰기) |
| `apply_profile` | `Pipeline.run()` 프로필 병합부 | `pipeline.py:104-109` | in `documents`,`profiles` → out `documents`(덮어쓰기) |
| `validate_metadata` | `check_documents()` + `validate_document()` + 필수 키 경고 재계산 | `pipeline.py:45-72`, `validation.py:9-77`, `pipeline.py:111-116` | in `documents`,`schema` → out `validation`(덮어쓰기), `warnings`(누적) |
| `chunk` | `prepare_units()` + `chunk_by_clause()`/`chunk_by_turn()` + `make_chunk()` + `enforce_token_limit()` + 조립 루프 — **함수 5개가 한 노드** | `s3.1/lab_io.py:85-174`, `chunking.py:290·329·27·197`, `run_chunking.py:38-81` | in `documents` → out `chunks`,`reviews`,`exceptions`,`skipped`(모두 누적) |
| `embed` | `embed_texts(kind="passage")` — **`embed_and_upsert()`에서 분리 필요** | `helpers.py:84-117` | in `chunks` → out `vectors`(덮어쓰기, 배치 단위) |
| `upsert` | `embed_and_upsert()` 배치 루프 + `sanitize_metadata()` + `get_collection()` | `indexing_ref.py:11-46`, `helpers.py:120-134, 56-72` | in `vectors`,`chunks` → out `ok_count`(누적), `failed_ids`(누적) |
| `finalize_index` | `lab_cli` 적재 결과 대조부 | `s3.2/lab_cli.py:60-65` | → out `count_before`,`count_after`,`accounting_ok`(덮어쓰기) 및 manifest 저장 |

Retriever (8노드)

| 노드 | 묶이는 기존 함수 | 소스 위치 | State: in → out |
|---|---|---|---|
| `check_query` | `search()`·`search_hybrid()` 앞부분 검증(빈 질문·top_k·역할) | `retrieval_ref.py:17-21`, `hybrid_search_ref.py:27-31` | in `query`,`role`,`top_k`,`mode` → out `status`(덮어쓰기) |
| `vector_search` | `retrieval_ref.search()` + `embed_texts(kind="query")` | `retrieval_ref.py:13-42` | → out `vector_hits`(덮어쓰기) |
| `bm25_search` | `get_bm25_index()` + `get_scores()` + `map_scores_to_chunk_ids()` + `get_top_chunk_ids()` | `hybrid_utils.py:16-54`, `hybrid_search_ref.py:43` | → out `bm25_scores`(덮어쓰기) |
| `fuse_scores` | `search_hybrid()` 병합부 + `normalize_scores()` + `apply_filters()` + `to_hits()` | `hybrid_search_ref.py:46-72`, `hybrid_utils.py:57-101` | → out `candidates`(덮어쓰기) |
| `rerank` | `rerank()` | `rerank.py:22-46` | → out `hits`(덮어쓰기) |
| `build_prompt` | `build_rag_prompt()` + `check_prompt()` + 재시도 힌트 | `answering_ref.py:10-23`, `s3.2/lab_cli.py:141-158`, `s3.3/answering.py:154-169` | → out `prompt`(덮어쓰기) |
| `generate_answer` | `answer_with_sources()` 관문 + `ask_llm()`/`ask_groq()` | `answering_ref.py:26-39`, 어댑터 2종 | → out `raw_answer`(덮어쓰기), `llm_calls`(누적) |
| `verify_evidence` | `build_evidence_answer()` + `_validate_response()` + `_repair_hints()` | `evidence.py:27-104`, `s3.3/answering.py:139-151·172-216` | → out `answer`(덮어쓰기), `retry_count`(누적) |

쪼개지는 기존 함수: `parse_consultations()` → `extract`+`pseudonymize`, `embed_and_upsert()` → `embed`+`upsert`,
`search_hybrid()` → `vector_search`+`bm25_search`+`fuse_scores`(두 검색은 독립이라 병렬 분기 가능),
`answer_with_condition_prompt()` → `build_prompt`→`generate_answer`→`verify_evidence` 루프

### C-3. 기존 재시도·타임아웃·종료 코드 현황

재시도

| 항목 | 현재 동작 | 소스 | 목표 규약과의 차이 |
|---|---|---|---|
| s3.2 적재 배치 | 총 2회, `NotImplementedError` 외 모든 예외, 백오프 없음 | `indexing_ref.py:26-45` | 토큰 한도 `ValueError`까지 재시도함. 목표: 429·5xx·연결만 |
| s3.3 답변 검증 재시도 | `max_retries=1`, 검증 실패 시 힌트 붙여 재호출(품질 재시도) | `s3.3/answering.py:224, 240-249` | 목표 규약에 대응 항목 없음 → 그래프 엣지 루프(상한 2회)로 이식 |
| Claude SDK 내장 | `max_retries=1` | `llm_client.py:33` | 그래프 재시도와 곱해짐 → SDK 재시도 0으로 끄고 어댑터가 담당 |
| Groq 호출 | 없음 | `groq_client.py:53-69` | 429도 즉시 실패 |
| 리랭킹·BM25 색인 | 없음 / `lru_cache` 1회 | `rerank.py:33-37`, `hybrid_utils.py:16-38` | 로컬 연산이라 타임아웃만 필요 |

타임아웃: 외부 HTTP 2곳(Claude·Groq 60초)에만 있고 PDF 추출·청킹·임베딩·Chroma·리랭킹·BM25 색인 6곳은 없음

종료 코드

| 값 | 현행 조건 | 소스 | 목표 규약(0/1/2/3)과의 차이 |
|---|---|---|---|
| 0/1 | 정상 / `ValueError`·`OSError`·`TypeError`·`KeyError` | 4개 실습 공통 | 일치 |
| 2 | s2.3 메타데이터 검증 오류 | `cli.py:41,54` | **불일치**(목표 2 = 청킹 검토 보류) |
| 2 | s3.1 검토 보류 존재 | `run_chunking.py:121` | 일치(목표 2의 원본) |
| 2 | s3.2 일부 적재 실패 | `lab_cli.py:132` | **불일치**(목표는 3) |
| 3 | s3.2·s3.3 `NotImplementedError`(학생 미구현) | `lab_cli.py:133-135` | 개념 소멸 → 3을 "일부 적재 실패"로 재배정 |

예외가 삼켜지는 곳 — `indexing_ref.py:38-42`(모든 예외 → failed), `pdf_reader.py:102-104`(표 검출 실패 → 경고),
`llm_client.py:58,60`·`groq_client.py:67,69`(`from None`으로 상태 코드 소실 → 429/5xx 판별 불가).  
`needs_check`의 `automatic_valid` 값이 s3.2(`True`)와 s3.3(`False`)에서 반대임 → 계약에서 단일화 필요

### C-4. LangGraph 대체 구조 제안

Reducer 후보 — Indexer: `documents`·`reports`·`warnings`·`chunks`·`reviews`·`exceptions`·`skipped`·`failed_ids`는 누적,
`sources`·`validation`·`vectors`(배치 단위)·`count_*`는 덮어쓰기. Retriever: `llm_calls`·`retry_count`·`timings`(dict merge)는 누적,
검색 결과·프롬프트·답변은 덮어쓰기. 병렬 분기(`vector_search`‖`bm25_search`)가 같은 키(`timings`)에 쓰면 반드시 누적 Reducer

체크포인트 재개 가치가 큰 경계: `extract` 뒤(PDF 추출 비쌈), `chunk` 뒤(기존에도 `chunks.jsonl` 파일 경계),
`embed` 뒤(배치 커서만 저장하고 벡터는 State에 누적하지 않음), `rerank` 뒤(2.7 ~ 9.8초), `generate_answer` 뒤(LLM 비용)

노드별 타임아웃·재시도 후보

| 노드 | 타임아웃(확정값) | 여유 배수(실측 대비) | 재시도 | 대상 |
|---|---|---|---|---|
| `extract` | PDF 1건 60초 | 8건 합계 9.1초 → 충분 | 0회 | PyMuPDF 오류는 재시도 무의미 |
| `chunk` | 1문서 30초 | 전체 1.3초 → 충분 | 0회 | `ValueError`는 `reviews`로 격하 |
| `embed` | 배치 120초 | 배치 32건 ≈ 30.4초 → 약 4배 | 2회 백오프 | 모델 로딩·일시 OOM. 토큰 한도 `ValueError`는 제외 |
| `upsert` | 배치 120초 | — | 2회 백오프 | Chroma I/O(`OSError`는 `retry_on` 명시 필요) |
| `vector_search` | 10초 | 74 ~ 115ms → 약 42배 | 2회 | Chroma 조회 오류 |
| `bm25_search` | 10초 | warm 기준. **콜드 색인 생성은 미실측** | 1회 | 색인은 기동 시 워밍업으로 빼는 안 제안 |
| `rerank` | 60초 | 최대 9.8초 → 약 6배 | 0회 | 타임아웃 시 후보 그대로 통과(폴백) |
| `generate_answer` | 60초 | — | 2회 백오프 | 429·5xx·연결. 상태 코드 보존 예외가 선결 과제 |
| `verify_evidence` | 없음 | — | 노드 재시도 아님 | 엣지 루프 `→ build_prompt` 상한 2회 |

`recursion_limit` 25 수렴 계산  
- Indexer: 직렬 9 + (`finalize_index → embed` 루프 3 × 2회) = 15 ≤ 25
- Retriever: 직렬 8 + (`verify_evidence → build_prompt` 루프 3 × 2회) = 14 ≤ 25  
- 두 그래프를 합치면 17 + 6 + 6 = 29 > 25 → **별개 StateGraph 2개 유지가 필수**  
- 노드 재시도가 super-step을 소모하는 최악 가정에서도 19·18로 25 이내

파일 I/O 담당 노드: `documents.jsonl`·`manifest.json`·`report.json`·`validation.json`은 `validate_metadata`,
`chunks.jsonl`·`review.jsonl`·`exceptions.jsonl`·`report.json`은 `chunk`, 적재 결과는 `finalize_index`.
Retriever 결과 JSON은 그래프 밖(CLI·API)이 저장. 저장은 mkstemp → `os.replace`로 멱등하게

---

## 부록 F. 환경 선검증 결과 (클로니 실측, 2026-09-13)

`vector/.venv`에 아래 버전을 설치한 뒤 최소 그래프(노드 3개)로 실행함. 스크립트: 세션 스크래치 `env_smoke.py`·`env_smoke2.py`

| 패키지 | 설치 버전 | 패키지 | 설치 버전 |
|---|---|---|---|
| langchain | 1.4.0 | langgraph | 1.2.11 |
| langchain-core | 1.6.3 | langgraph-checkpoint-sqlite | 3.1.1 |
| langchain-huggingface | 1.2.2 | langchain-chroma | 1.1.0 |
| langchain-groq | 1.1.3 | langchain-anthropic | 1.7.2 |
| langchain-openai | 1.6.2 | chromadb | 1.5.9 (기존 s3.2와 동일) |
| sentence-transformers | 6.0.1 | torch | 2.14.0 (+cpu) |
| PyMuPDF | 1.28.2 (기존 s2.3은 1.27.2.3) | rank-bm25 | 0.2.2 (기존과 동일) |
| fastapi | 0.141.1 | uvicorn | 0.52.4 |
| sse-starlette | 3.4.11 | httpx | 0.28.1 |
| pydantic | 2.13.5 | python-dotenv | 1.2.3 |
| groq | 0.37.1 | anthropic | 1.5.0 (기존 0.125.0) |
| openai | 3.13.0 | transformers | 5.17.0 |

확인된 사실 3가지

| # | 확인 항목 | 결과 | 설계 반영 |
|---|---|---|---|
| 1 | `SqliteSaver` + `invoke(None, config)` 재개 | 노드 b에서 강제 예외 → `update_state`로 원인 제거 → `invoke(None, cfg)` 실행 시 호출 순서 `['a','b','b','c']`. **a 재실행 없음** | 재개 시험 방식으로 확정 |
| 2 | `astream_events(version="v2")` 이벤트 | 각 노드마다 `on_chain_start`/`on_chain_end`가 `name=노드명`, `metadata.langgraph_node=노드명`으로 옴. 그래프 전체 이벤트는 `name="LangGraph"`, `langgraph_node=None` | SSE `node_start`/`node_end` 매핑 근거. 루트 이벤트는 걸러냄 |
| 3 | 동기 `SqliteSaver`로 컴파일한 그래프에 `astream_events` 호출 | **`NotImplementedError: The SqliteSaver does not support async methods. Consider using AsyncSqliteSaver`** 발생 | 프롬프트 확정값(`SqliteSaver` 동기 + `astream_events`) 사이의 충돌. G1 결정 항목으로 올림. `AsyncSqliteSaver`(aiosqlite 0.22.1 설치됨)는 같은 sqlite 파일을 쓰며 정상 동작 확인 |

추가 확인: `langgraph.types.RetryPolicy(max_attempts, initial_interval, backoff_factor, jitter, retry_on)`를
`add_node(..., retry_policy=...)`로 노드에 붙일 수 있음(context7 확인). 노드별 `timeout=`은 async 노드 전용이라
동기 `invoke` 경로(Indexer)의 타임아웃은 인프라 호출 단위(PDF 열기·임베딩 배치·HTTP)에서 걸어야 함
