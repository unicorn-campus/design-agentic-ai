# BM25 인덱싱 슬라이드 스크립트

## 슬라이드 1. BM25 인덱싱: 정확한 단어가 있는 청크 찾기

### 한 문장 목적

BM25는 질문의 핵심 단어·카드명·코드가 들어 있는 청크를 빠르게 찾도록 텍스트 검색표를 미리 만듭니다.

### 화면 구성

- 비율: 16:9, 흰색 배경
- 글꼴: Pretendard
- 제목: 48pt ExtraBold, `#1E2A5C`
- 본문: 16 ~ 18pt, 최소 14pt
- 색상: Deep Navy `#1E2A5C`, Bright Blue `#2E74C6`, Light Blue `#EEF3FA`
- 구성: 상단 목적 문장, 중앙 4단계 흐름, 하단 좌측 적용 기술, 하단 우측 설계값 표

### 중앙: 4단계 색인 흐름

네 개의 둥근 사각형을 왼쪽에서 오른쪽으로 연결합니다. 단계마다 번호 배지와 대표 산출물을 함께 표시합니다.

1. **정제 청크**
   - `PreparedChunk 1개 → corpus 1행`
   - 본문과 `chunk_id`·출처 메타데이터를 함께 기록
2. **Kiwi 토큰화**
   - NFKC 정규화, 영문 소문자화, 숫자 사이 쉼표 제거
   - 내용어 형태소와 카드명·숫자·코드 원형 보존
   - 카드명 사전 아이콘을 옆에서 합류시킴
3. **bm25s 색인**
   - 청크별 토큰의 빈도와 문서 내 중요도를 계산
   - `Lucene 방식 · k1 1.5 · b 0.75`
4. **저장·검증**
   - `corpus.jsonl`·`card_names.dict`·BM25 파일·manifest 저장
   - 개수와 해시를 확인한 뒤 `active_index.json`을 마지막에 교체

단계 2 아래에 작은 변환 예시를 둡니다.

> **정규화만 보여 주는 설명 예시**  
> `30,000원 KB-PAY` → `30000원 kb-pay`  
> 형태소 분석 결과를 뜻하지 않음

### 하단 좌측: 실제 적용 기술

카드 두 개를 세로로 배치합니다.

**Kiwi 형태소 분석기**

- 조사·어미 중심의 토큰은 거르고 명사·용언·수사·영문·한자 등 내용어 품사를 남김
- 숫자, `-`·`_`·`/`가 든 코드, 사전어, 내용어 복합어는 검색에 쓸 원형도 보존

**D2 카드명 동적 사전**

- D2 메타데이터의 카드명을 매번 `NNP`로 생성하여 Kiwi에 등록
- 저장된 현재 세대: 64개
- 실제 사전 항목 예: `한빛 가족돌봄    NNP    0.0`

### 하단 우측: 우리 코드의 설계값

| 설계 항목 | 실제 값 | 읽는 법 |
|---|---|---|
| 색인 단위 | 정제 청크 1개 = corpus 1행 | 검색 결과가 청크 단위로 돌아옴 |
| 토큰 정책 | 내용어 + 필요한 원형 보존 | 정확한 단어와 코드 검색을 함께 지원 |
| 사전 | D2 카드명 동적 등록 | 정적 사용자 사전은 지원하지만 기본 연결 없음 |
| BM25 계수 | `bm25s 0.3.11`, Lucene, `k1=1.5`, `b=0.75` | 현재 저장 세대 manifest 기준 |
| 동기화 | corpus·사전·토크나이저 서명·BM25 해시 검증 | 일부만 바뀐 색인이 검색에 노출되지 않게 함 |

표 아래에 14pt 회색 캡션을 둡니다.

`현재 저장 세대: 192청크 · 정적 사용자 사전 해시 비어 있음 · OOV 후보 추출 0개(기본 비활성)`

### 발표자 말할 내용

“BM25 색인의 목적은 질문에 나온 단어가 정확히 들어 있는 청크를 빠르게 찾는 것입니다. 우리 코드는 정제된 청크 하나를
corpus 한 행으로 만들고, Kiwi로 검색에 의미가 있는 형태소를 남깁니다. 이때 D2 메타데이터의 카드명을 동적 사전으로
등록하므로 카드명이 일반 단어처럼 잘못 나뉘는 일을 줄입니다. 토큰은 bm25s의 Lucene 방식으로 색인하며, 현재 저장 세대의
계수는 k1 1.5와 b 0.75입니다. 모든 파일과 manifest를 저장하고 개수·해시를 확인한 다음 활성 포인터를 마지막에 바꾸므로,
검색기는 완성된 한 세대만 읽습니다.”

### 발표자 노트

- 화면의 `30,000원 KB-PAY → 30000원 kb-pay`는 `normalize_korean_text()`의 정규화 동작만 보여 주는 설명 예시임.
  Kiwi가 반환한 실제 형태소 목록으로 표현하지 않음.
- 정적 사용자 사전을 읽는 기능은 있으나 `bootstrap.py`가 `LexicalIndexBuilder()`를 인자 없이 생성하므로 기본 실행에는
  연결되지 않음. 반면 D2 카드명 동적 사전은 `_build_into()`에서 항상 생성하고 등록함.
- `oov_candidates=False`가 기본이며 후보를 자동 등록하지 않음. 필요 시 사람 검토용 후보 파일을 만드는 선택 기능임.
- 토크나이저 서명의 `typo_policy="basic"`은 검색 측 계약 기록임. 인덱싱 단계의 Kiwi 생성에는 오타 교정 인자를 전달하지
  않으므로 “오타 교정 적용”으로 설명하지 않음.
- 저장된 현재 세대의 192청크, 카드명 64개, bm25s 0.3.11은 실행을 새로 한 결과가 아니라 저장소 산출물에서 확인한 값임.

### 코드 근거

- `hybrid-ai-lab/indexer/vector-bm25/app/infrastructure/lexical_index.py:92`  
  청크 하나를 corpus 레코드 하나로 만드는 `corpus_record()`
- `hybrid-ai-lab/indexer/vector-bm25/app/infrastructure/lexical_index.py:133`  
  D2 메타데이터에서 카드명 동적 사전을 만드는 `_card_dictionary_words()`
- `hybrid-ai-lab/indexer/vector-bm25/app/infrastructure/lexical_index.py:162`  
  `k1=1.5`, `b=0.75`, `oov_candidates=False` 기본값
- `hybrid-ai-lab/indexer/vector-bm25/app/infrastructure/lexical_index.py:291`  
  사전 생성 → Kiwi 토큰화 → bm25s 색인 → 산출물·manifest·활성 포인터 저장 흐름
- `hybrid-ai-lab/indexer/vector-bm25/app/infrastructure/korean_tokenizer.py:16`  
  색인에 남기는 내용어 품사 목록
- `hybrid-ai-lab/indexer/vector-bm25/app/infrastructure/korean_tokenizer.py:39`  
  NFKC·소문자·숫자 쉼표 제거 정규화
- `hybrid-ai-lab/indexer/vector-bm25/app/infrastructure/korean_tokenizer.py:195`  
  숫자·코드·사전어·내용어 복합어의 원형 보존 기준
- `hybrid-ai-lab/indexer/vector-bm25/app/bootstrap.py:47`  
  인자 없는 `LexicalIndexBuilder()` 기본 주입
- `hybrid-ai-lab/indexer/vector-bm25/data/generations/gen-20260930T135203Z-8582349c-9648f63d/`
  `search_indexes/generations/gen-20260930T135203Z-8582349c-9648f63d/manifest.json:431`  
  저장된 세대의 192청크, 카드명 64개, OOV 0개, bm25s 0.3.11, Lucene, k1 1.5, b 0.75
- `hybrid-ai-lab/indexer/vector-bm25/data/generations/gen-20260930T135203Z-8582349c-9648f63d/`
  `search_indexes/generations/gen-20260930T135203Z-8582349c-9648f63d/card_names.dict:1`  
  실제 생성된 카드명 사전 항목
