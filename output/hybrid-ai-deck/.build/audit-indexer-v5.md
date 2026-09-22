# Indexer 교육 PPT 4 ~ 23페이지 소스 감사

## 감사 기준

- 검토 대상: `review-v4-content.json`의 4 ~ 23페이지 본문·표·발표자 노트
- 정본: `hybrid-ai-lab/vector/indexer/app`, `config`, `tests`, 현재 로컬 색인 데이터
- 판정 기준: 노드 책임, 입력·출력, 분기, 상수, 용어, 코드 문법, 실행 데이터 근거의 실제 구현 일치 여부
- 코드 발췌 원칙: 설명용 의사 코드가 아니라 현재 소스의 실행 가능한 범위 사용

## 4페이지 — 수정 필요

- 본문 `Indexing (1/3)`은 구간 표지로 사용 가능함.
- 발표자 노트의 자동화·골든서클·사람 최종 승인 설명은 Indexer 소스와 무관함.
- Claude 프롬프트 문서 링크도 이 페이지의 Indexer 설명 근거가 아님.
- 근거: `app/application/graph.py:23-31`, `app/application/graph.py:250-258`
- 추천 문구: `8개 노드가 원문 선택부터 벡터·키워드 검색 세대 발행까지 순서대로 처리함.`
- 추천 발췌 범위: `app/application/graph.py:23-31`, `app/application/graph.py:250-258`

## 5페이지 — PASS

- 파일 입력이면 해당 파일, 폴더 입력이면 바로 아래 항목을 정렬해 검사하는 설명과 일치함.
- D1·D2 PDF 및 `D3_S01` ~ `D3_S06` 상담 파일명 판정과 문서·세그먼트 필터 설명이 정확함.
- 결과는 `path.resolve()`로 만든 절대 경로의 `sources` 목록임.
- 선택 결과가 없으면 `status=error`, `exit_code=1`로 종료하는 설명과 일치함.
- 근거: `app/application/graph.py:137-144`, `app/application/graph.py:337-363`
- 정확 발췌 범위: `app/application/graph.py:341-363`

## 6페이지 — 수정 필요

- `select_sources`가 만드는 값은 `Document` 배열이 아니라 절대 경로 목록인 `sources`임.
- `documents` 배열은 다음 `extract` 노드가 PDF·상담 추출 결과를 합쳐 생성함.
- `selected = [{약관 파일 경로}, ...]`는 실제 Python 문법도 아니며 실제 State 이름도 아님.
- 근거: `app/application/graph.py:337-363`, `app/application/graph.py:365-396`
- 추천 제목: `select_sources · extract : 경로에서 문서로`
- 추천 문구: `select_sources → sources(절대 경로 목록)`, `extract → documents(Document 목록)`
- 추천 코드: `return {"sources": selected}`와 `documents.extend(extracted)`를 두 단계로 분리 제시
- 정확 발췌 범위: `app/application/graph.py:362-363`, `app/application/graph.py:371-396`

## 7페이지 — PASS

- 원문별 SHA-256 계산, PDF·상담 분기, `documents·reports·fingerprints` 반환 설명과 일치함.
- PDF는 페이지마다 `Document`를 만들고 상담 TXT는 상담 한 건마다 `Document`를 만듦.
- `doc_type`이 각 `Document.metadata`에 들어간다는 설명도 정확함.
- 근거: `app/application/graph.py:365-396`, `app/infrastructure/pdf_reader.py:389-418`,
  `app/domain/consultations.py:155-190`
- 정확 발췌 범위: `app/application/graph.py:371-396`

## 8페이지 — PASS

- `page.get_text("dict")`의 `block → lines → spans` 구조 설명과 일치함.
- `bbox`를 좌표로 설명하고 같은 줄의 span 텍스트를 합치는 설명이 정확함.
- 화면의 좌표와 텍스트는 소스 주석에 명시된 설명용 예시임.
- 근거: `app/infrastructure/pdf_reader.py:30-68`, `app/infrastructure/pdf_reader.py:87-93`
- 정확 발췌 범위: 구조 예시는 `app/infrastructure/pdf_reader.py:35-47`

## 9페이지 — 수정 필요

- 처리 내용과 반환 형식은 맞지만 `def _lines(page):` 없이 들여쓴 `for`문부터 제시해 단독 코드로 실행 불가함.
- 원본 보존이라는 이유로 문법이 깨진 발췌를 유지하면 안 됨.
- 근거: `app/infrastructure/pdf_reader.py:11-12`, `app/infrastructure/pdf_reader.py:87-93`
- 추천 제목: 기존 제목 유지 가능함.
- 추천 코드 구성: `def _lines(page):` 다음에 `result = []`부터 `return result`까지 제시
- 정확 발췌 범위: 함수 선언 `app/infrastructure/pdf_reader.py:11`, 함수 본문
  `app/infrastructure/pdf_reader.py:87-93`

## 10페이지 — 수정 필요

- 슬라이드의 `if`문에는 콜론이 빠져 있어 실행 불가함.
- 실제 원본에는 콜론이 있으며, 실행 코드는 집합 내포로 여백 문구를 수집함.
- `원본 코드 유지: if 줄 끝의 콜론 생략에 유의`는 원본과 반대인 설명이므로 삭제 필요함.
- 상단 5.5%, 하단 5% 판정 설명은 정확함.
- 근거: `app/infrastructure/pdf_reader.py:96-99`, `app/infrastructure/pdf_reader.py:241-255`
- 추천 문구: `상·하단 여백에서 페이지별 중복을 제거한 문구를 모아 반복 횟수를 계산함.`
- 정확 발췌 범위: 실행 코드 `app/infrastructure/pdf_reader.py:243-249`
- 여러 줄 교육용 버전 사용 시 정확 범위: `app/infrastructure/pdf_reader.py:251-255`

## 11페이지 — PASS

- 감지 표의 셀 글자와 표 영역 원문 글자를 공백 제외 글자 빈도로 비교하는 설명과 일치함.
- 일치하면 Markdown 표로 바꾸고 원문 줄을 제거하며, 불일치하면 경고 후 위치 기반 텍스트를 유지함.
- D2 테두리 없는 표 정규화, 텍스트 계층 없음 경고, 암호화 PDF 중단 설명도 정확함.
- 근거: `app/infrastructure/pdf_reader.py:232-249`, `app/infrastructure/pdf_reader.py:298-387`
- 관련 시험: `tests/test_pdf_reader.py:54-82`
- 정확 발췌 범위: `app/infrastructure/pdf_reader.py:308-385`

## 12페이지 — 수정 필요

- 상담ID 머리글 분리, 개인정보 삭제·일반화·가명화, 잔존 검사, `Document` 생성 흐름은 정확함.
- 다만 `상담사 ID` 입력은 존재하지 않음. 실제 입력은 `접수정보`의 `상담사명`이며 이를 해시해
  `agent_pseudo_id`를 생성함.
- 회원 값은 머리글의 `회원번호`를 해시해 `member_pseudo_id`로 저장함.
- 상담의 `restricted` 등급은 후속 메타데이터 검증에서 강제함.
- 근거: `app/domain/consultations.py:12-20`, `app/domain/consultations.py:131-189`,
  `app/domain/validation.py:122-139`
- 추천 표 문구: `회원번호·상담사명 → 해시 기반 member_pseudo_id·agent_pseudo_id`
- 관련 시험: `tests/test_consultations.py:22-33`
- 정확 발췌 범위: `app/domain/consultations.py:182-189`

## 13페이지 — 수정 필요

- 화면 코드는 `_clean()` 함수 중간만 잘라 첫 줄과 나머지 줄의 들여쓰기가 달라 실행 가능한 발췌가 아님.
- 이름·생년월일·원문 카드번호·끝 4자리 치환이 앞부분에 있는데 이를 생략해 전체 개인정보 처리처럼 보임.
- 회원번호 가명화는 `MEMBER.sub(...)`에 포함되지만 상담사 가명 ID 생성은 별도 코드임.
- 근거: `app/domain/consultations.py:31-37`, `app/domain/consultations.py:52-81`,
  `app/domain/consultations.py:182-189`
- 추천 제목: `extract : 개인정보 치환의 일부와 가명 ID 생성`
- 추천 구성: `_clean()` 전체를 설명하려면 `52-81`을 사용하고, 공간이 부족하면 치환 범위를 명시함.
- 정확 발췌 범위: 치환 `app/domain/consultations.py:52-81`, 가명 함수
  `app/domain/consultations.py:31-37`, ID 저장 `app/domain/consultations.py:182-185`

## 14페이지 — PASS

- 각 문서의 `metadata.source`로 같은 이름의 프로필을 찾고 모든 프로필 값을 적용하는 설명과 일치함.
- 결과는 새 `Document` 목록이며 `source·doc_type·page` 등의 금지 키 덮어쓰기는 별도 차단됨.
- 근거: `app/application/graph.py:398-409`, `app/domain/validation.py:18-54`
- 설정 근거: `config/document_profiles.json:1-13`
- 정확 발췌 범위: `app/application/graph.py:404-409`

## 15페이지 — 수정 필요

- 본문 코드는 현재 구현과 일치함.
- 발표자 노트의 `원본 핵심 코드 출처: 페이지`는 미완성 자리표시자이므로 수정 필요함.
- 근거: `app/application/graph.py:404-409`
- 추천 출처 문구: `원본 핵심 코드: app/application/graph.py 404-409행`
- 정확 발췌 범위: `app/application/graph.py:404-409`

## 16페이지 — PASS

- 출력 경로가 원문 경로와 겹치지 않는지 먼저 확인하고 메타데이터·가명화 상태를 검증함.
- `documents.jsonl`, `manifest.json`, `report.json`, `validation.json`의 설명이 실제 저장 내용과 일치함.
- 유효하지 않은 문서가 있으면 래퍼가 오류 상태로 바꾸고 `chunk`로 진행하지 않음.
- `schema` 전체를 해석하는 것이 아니라 현재 구현에서는 `schema.enums`를 허용값 재정의에 사용함.
- 근거: `app/application/graph.py:161-168`, `app/application/graph.py:419-453`,
  `app/domain/validation.py:57-149`
- 정확 발췌 범위: `app/application/graph.py:425-453`

## 17페이지 — 수정 필요

- D1 600자·80자 중첩, D2 600자·중첩 없음, D3 4턴·1턴 중첩 기본값은 정확함.
- 다만 D3의 `턴`은 화자 발화 하나가 아님. 연속 발화를 정리한 뒤 발화 두 개를 한 턴으로 묶음.
- 긴 속성표는 전체 조건행을 보존하며 제한을 넘으면 `size_exception`으로 기록함.
- 근거: `app/settings.py:183-188`, `app/domain/chunking.py:121-169`,
  `app/domain/chunking.py:255-312`
- 추천 문구: `D3 상담: 발화 두 개를 한 턴으로 묶고, 4턴 단위·1턴 중첩으로 분할함.`
- 정확 발췌 범위: 턴 구성 `app/domain/chunking.py:282-311`, 기본값 전달
  `app/application/graph.py:471-486`

## 18페이지 — 수정 필요

- 본문·메타데이터 해시가 모두 같을 때만 생략하고, 둘 중 하나라도 바뀌면 다시 임베딩하는 설명은 정확함.
- 임베딩 서명 또는 청킹 설정 변경 시 전량 임베딩 계획으로 승격하는 설명도 정확함.
- 다만 `index_manifest`는 State 입력 필드가 아니라 `output_path/index_manifest.json`에서 읽는 파일임.
- 기본 모델 이름은 KURE-v2지만, 768차원은 코드 상수가 아니라 저장소 또는 모델에서 실행 시 측정하는 값임.
- 현재 로컬 `card_docs` 컬렉션은 SQLite 읽기 전용 조회 결과 768차원·485건이나 다른 실행을 보장하지 않음.
- 근거: `app/settings.py:138`, `app/application/graph.py:565-597`,
  `app/infrastructure/embedder.py:93-160`, `app/application/graph.py:724-748`
- 추천 입력 문구: `chunks + 기존 output_path/index_manifest.json`
- 추천 하단 문구: `기본 모델: KURE-v2 · 벡터 차원은 실행 시 검증(현재 로컬 스냅샷: 768)`
- 정확 발췌 범위: 증분 판정 `app/infrastructure/embedder.py:114-160`

## 19페이지 — 수정 필요

- `SentenceTransformer` 지연 적재, 배치 인코딩, 정규화 설명은 정확함.
- 실제 `embed()`는 첫 줄에서 `del kind`를 실행하지만 화면 코드가 이를 누락함.
- 화면의 모델 적재 한 줄과 `embed()`는 서로 떨어진 범위를 이어 붙인 코드이므로 한 함수처럼 보이면 안 됨.
- 근거: `app/infrastructure/embedder.py:50-79`
- 추천 구성: `_load()`와 `embed()`를 두 코드 상자로 분리하고 `del kind`를 포함함.
- 추천 문구: `kind는 인터페이스 호환용이며 현재 구현에서는 즉시 버림.`
- 정확 발췌 범위: 모델 적재 `app/infrastructure/embedder.py:50-62`, 인코딩
  `app/infrastructure/embedder.py:70-79`

## 20페이지 — PASS

- `pending_ids`에 해당하는 본문·메타데이터와 `.npy` 벡터를 같은 순서로 묶어 배치 upsert함.
- 저장 전 ID 집합으로 신규·갱신을 구분하고 성공 ID·실패 목록·저장 전 건수를 반환함.
- 증분 실행은 삭제 API를 호출하지 않으므로 원문에서 사라진 기존 ID를 자동 삭제하지 않는다는 설명이 정확함.
- 근거: `app/application/graph.py:653-715`
- 관련 시험: `tests/test_knowledge_domain.py:102-110`, `tests/test_knowledge_domain.py:197-233`
- 정확 발췌 범위: `app/application/graph.py:659-715`

## 21페이지 — 수정 필요

- Chroma의 영속 경로, cosine HNSW 구성, 임베딩 서명 기록 코드는 현재 구현과 일치함.
- 다만 `signature는 모델 일치 검사에 사용`은 일반 초기화에서 자동 검사가 수행되는 것처럼 보일 수 있음.
- 실제로는 메타데이터에 기록하고 `check_signature()`로 비교 가능하며, 현재 자동 호출은 reset 직후에만 존재함.
- 근거: `app/infrastructure/chroma_store.py:126-176`, `app/infrastructure/chroma_store.py:205-210`
- 추천 문구: `signature는 컬렉션 메타데이터에 기록하며 check_signature()로 비교 가능함.`
- 정확 발췌 범위: 구성 `app/infrastructure/chroma_store.py:138-147`, 검사
  `app/infrastructure/chroma_store.py:205-210`

## 22페이지 — PASS

- `chunk_id`를 메타데이터에 넣고 `sanitize_metadata()`를 거쳐 Chroma 하부 컬렉션에 upsert하는 코드와 일치함.
- ID·본문·벡터·메타데이터 배열의 같은 위치가 한 레코드를 이룬다는 설명이 정확함.
- `sanitize_metadata()`는 `None`을 제거하고 복합 값을 JSON 문자열로 바꾸며 필수 분류값도 검사함.
- 근거: `app/infrastructure/chroma_store.py:150-168`, `app/domain/validation.py:152-166`
- 정확 발췌 범위: `app/infrastructure/chroma_store.py:150-168`

## 23페이지 — 수정 필요

- 벡터 건수·ID 검사, 전체 corpus 구성, Kiwi 토큰화, BM25S 생성, generation 저장,
  `active_index.json`의 마지막 교체 흐름은 정확함.
- 카드명 64개와 청크 485개는 현재 로컬 활성 세대 파일로 확인 가능함.
- corpus를 읽어 집계한 현재 분포도 D1 53개·D2 336개·D3 96개와 일치함.
- 다만 활성 세대의 실제 생성 시각은 2026-09-18 UTC임. 화면의 `2026.09.20 확인`은 생성 시각처럼 오해될 수 있음.
- 실행에 따라 바뀌는 수치를 상수처럼 본문에 두기보다 스냅샷임을 명시하거나 핵심 흐름 슬라이드에서 제거하는 편이 안전함.
- 근거: `app/application/graph.py:717-845`, `app/infrastructure/lexical_index.py:97-133`,
  `app/infrastructure/lexical_index.py:169-217`, `app/infrastructure/lexical_index.py:233-292`
- 데이터 근거: `data/search_indexes/active_index.json:3-12`, 활성 세대 `manifest.json:3-17`
- 추천 문구: `로컬 활성 세대 스냅샷(생성 2026-09-18 UTC): 485청크, 카드명 사전 64개`
- 변동 수치를 빼는 경우 추천 문구: `발행 결과 수치는 active_index.json의 chunk_count와
  card_dictionary_count로 확인함.`
- 관련 시험: `tests/test_lexical_index.py:61-85`, `tests/test_lexical_index.py:88-120`,
  `tests/test_lexical_index.py:142-161`, `tests/test_lexical_index.py:164-212`

## 중요한 오류 요약

1. 6페이지의 노드 책임 혼합
   - `select_sources → sources`, `extract → documents`로 즉시 분리 필요함.
2. 9·10·13페이지의 실행 불가능한 코드
   - 함수 선언 누락, 콜론 누락, 중간 발췌의 들여쓰기 파손 제거 필요함.
3. 10페이지의 원본 설명 오류
   - 실제 원본에 콜론이 있는데 `원본 코드의 콜론 생략`으로 설명한 문구 삭제 필요함.
4. 12·13페이지의 개인정보 용어 오류
   - `상담사 ID`가 아니라 `상담사명`을 해시해 `agent_pseudo_id`를 생성함.
5. 17페이지의 상담 턴 정의 누락
   - 발화 두 개를 한 턴으로 묶는 구현을 명시해야 4턴 분할 의미가 정확해짐.
6. 18페이지의 벡터 차원 고정값 표현
   - 768은 현재 로컬 저장소의 실행 스냅샷이며 코드 상수가 아님.
7. 19페이지의 `del kind` 누락
   - 실제 구현의 query·passage 미구분 근거이므로 코드에 포함 필요함.
8. 21페이지의 자동 검사 과장
   - 서명은 기록·비교 가능하나 일반 초기화에서 자동 검사하지 않음.
9. 23페이지의 실행 수치·날짜 표현
   - 수치는 파일 근거가 있으나 활성 세대 생성일은 2026-09-18 UTC임.
   - 수치를 유지하려면 스냅샷과 파일 근거를 표시하고, 아니면 동적 확인 문구로 교체 필요함.
