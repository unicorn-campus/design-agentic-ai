# 임베딩 대상 결정 슬라이드 스크립트

## 슬라이드 1. 무엇을 임베딩할까? 본문 해시와 모델 계약으로 결정

### 핵심 문장

우리 코드는 정제된 본문이 달라졌거나 기존 벡터를 안전하게 재사용할 수 없을 때만 새 임베딩을 계산합니다.

### 화면 구성

- 비율: 16:9, 흰색 배경
- 글꼴: Pretendard
- 제목: 48pt ExtraBold, `#1E2A5C`
- 본문: 16 ~ 18pt, 최소 14pt
- 색상: Deep Navy `#1E2A5C`, Bright Blue `#2E74C6`, Light Blue `#EEF3FA`
- 구성: 상단 사전 종료 조건, 중앙 좌측 3체크 결정도, 중앙 우측 사례표, 하단 세 가지 원칙

### 상단: 먼저 확인하는 사전 종료 조건

가로로 긴 연한 회색 띠를 배치합니다.

**원천 지문과 모든 처리 계약이 그대로이고 `full_reindex`도 아니면 → `no_op`**

하단 작은 문구:

`원천 SHA-256 · 문서 키 · 분할/정제 정책 · 프로필 · 모델 서명 · 임베딩 계약이 모두 같음`

오른쪽에 작은 배지로 `새 계산 0 · 저장 변경 0`을 표시합니다.

### 중앙 좌측: 3체크 결정도

`이번 정제 청크`에서 시작해 세 개의 체크 카드를 세로로 연결합니다. 어느 단계든 ‘아니요’이면 오른쪽의 주황 결과 카드
**새로 임베딩**으로 연결하고, 세 단계가 모두 ‘예’이면 아래의 파란 결과 카드 **기존 벡터 재사용**으로 연결합니다.

1. **재사용 가능한 실행인가?**
   - 활성 세대가 있음
   - 모델 서명과 임베딩 계약이 모두 같음
   - `full_reindex=false`
2. **같은 `text_hash`가 있는가?**
   - 같은 ID의 이전 청크를 먼저 확인
   - 없으면 ID가 달라도 활성 세대 전체에서 같은 본문 해시를 확인
3. **그 벡터가 저장소에 실제로 있는가?**
   - 읽은 벡터가 있으면 재사용
   - 누락되었으면 새로 임베딩

두 번째 체크 옆에는 두 경로를 작은 보조 문구로 표시합니다.

- 같은 ID의 이전 청크와 본문 해시가 같음
- ID가 달라도 활성 세대에 같은 본문 해시가 있음

파란 결과 카드 아래에 한 줄을 강조합니다.

`메타데이터가 달라도 정제 본문이 같으면 보통 벡터를 재사용함`

주황 결과 카드 아래에 한 줄을 강조합니다.

`저장된 벡터를 읽지 못하면 같은 본문 해시여도 다시 계산함`

### 중앙 우측: 사례로 읽기

| 상황 | 판단 | 이유 |
|---|---|---|
| 본문 동일, 메타데이터만 변경 | 기존 벡터 재사용 | `text_hash`가 같고 모델 계약이 호환됨 |
| 청크 ID 변경, 정제 본문 동일 | 기존 벡터 재사용 | ID보다 같은 본문 해시를 한 번 더 찾음 |
| 정제 본문 변경, 같은 해시 없음 | 새로 계산 | 기존 벡터가 새 본문의 의미를 나타내지 못함 |
| 모델·revision·차원·입력 계약 변경 | 새로 계산 | 모델 서명 또는 임베딩 계약이 달라짐 |
| `full_reindex=true` | 모두 새로 계산 | 재사용 조건을 명시적으로 끔 |
| 원천에서 사라진 청크 | 삭제 제외 | 새 세대의 `desired_ids`에 포함되지 않음 |

### 하단: 세 가지 원칙

세 개의 가로 카드로 배치합니다.

1. **삭제 청크**  
   `기존 ID − 이번 desired_ids`를 `deleted_ids`로 기록하고 새 세대에서 제외
2. **재사용 청크**  
   벡터는 재사용해도 이번 청크의 최신 메타데이터와 함께 새 세대에 적재
3. **모델 입력**  
   정제된 `chunk.text`만 전달하며 메타데이터는 모델 입력에 넣지 않음

### 발표자 말할 내용

“먼저 원천 지문과 모든 처리 계약이 그대로라면 실행 자체를 no-op으로 끝냅니다. 변경이 있으면 이번에 필요한 청크 목록과
활성 세대를 비교합니다. 이번 목록에서 사라진 기존 청크는 삭제 대상으로 기록하고 새 세대에서 제외합니다. 남은 청크는
모델 서명과 임베딩 계약이 같고 전체 재색인이 아닐 때 재사용을 검토합니다. 같은 본문 해시가 있으면 청크 ID가 바뀌었어도
기존 벡터를 재사용할 수 있습니다. 다만 저장소에서 그 벡터를 실제로 읽지 못하면 다시 임베딩합니다. 모델에 전달하는 입력은
메타데이터가 아니라 정제된 본문입니다.”

### 발표자 노트

- `text_hash`는 정제된 청크 본문을 비교하는 기준임. 메타데이터는 `metadata_hash`로 별도 기록되므로 메타데이터만 바뀐
  경우에는 본문 벡터를 재사용하면서 새 메타데이터를 게시할 수 있음.
- 호환 조건은 활성 manifest의 `embedding_signature`와 `embedding_contract`가 현재 값과 모두 같은지 비교함. 계약에는
  모델명, revision, 최대 입력 길이, 출력 차원, 정규화와 풀링 방식이 포함됨.
- `embedding_signature`는 모델명과 프롬프트 정책을 식별하지만 revision 전체를 담지 않음. 그래서 서명이 같아도 contract의
  revision이 다르면 다시 임베딩함.
- 같은 본문 해시가 여러 ID에 있어도 활성 세대에서 찾은 기존 벡터를 재사용할 수 있음. 의미가 같은 정제 본문이라는 전제임.
- 삭제는 기존 활성 저장소에서 즉시 지우는 절차가 아님. 필요한 청크만 담은 새 비활성 세대를 만들고 검증한 뒤 게시하므로,
  사라진 ID가 새 세대에 포함되지 않는 방식임.
- 부분 실행에서는 선택하지 않은 원천의 활성 청크를 `desired` 목록에 유지함. 따라서 이 청크는 삭제 대상으로 계산되지 않음.
- 사전 `no_op` 판정이 성공하면 `prepare_embed()`에 도달하지 않으므로 저장 벡터 누락 여부를 다시 확인하지 않음.
- 이 슬라이드는 코드의 판단 규칙을 설명한 것이며 실제 재색인을 실행해 얻은 건수나 성능 결과가 아님.

### 코드 근거

- `hybrid-ai-lab/indexer/vector-bm25/app/application/indexing_service.py:249`  
  원천 지문과 처리 계약을 비교하는 `_is_no_op()`
- `hybrid-ai-lab/indexer/vector-bm25/app/application/indexing_service.py:280`  
  부분 실행에서 선택하지 않은 활성 청크를 보존하고 정제 청크를 준비하는 `load_split_clean()`
- `hybrid-ai-lab/indexer/vector-bm25/app/application/indexing_service.py:409`  
  모델 호환성, `full_reindex`, `text_hash`, 저장 벡터 존재 여부로 대상을 나누는 `prepare_embed()`
- `hybrid-ai-lab/indexer/vector-bm25/app/application/indexing_service.py:469`  
  기존 ID와 이번 `desired_ids`의 차이로 `deleted_ids`를 계산하는 코드
- `hybrid-ai-lab/indexer/vector-bm25/app/application/indexing_service.py:484`  
  `chunk.text`만 모델에 전달하는 `embed()`
- `hybrid-ai-lab/indexer/vector-bm25/app/infrastructure/settings.py:42`  
  모델명·revision·입력 상한·차원·정규화·풀링을 담는 `embedding_contract`
- `hybrid-ai-lab/indexer/vector-bm25/app/infrastructure/embedder.py:52`  
  모델명과 프롬프트 정책으로 구성한 `embedding_signature`
- `hybrid-ai-lab/indexer/vector-bm25/tests/test_service.py:384`  
  메타데이터만 변경된 경우 벡터 재사용을 보증하는 시험
- `hybrid-ai-lab/indexer/vector-bm25/tests/test_service.py:410`  
  서명이 같아도 임베딩 계약 revision이 바뀌면 재임베딩하는 시험
- `hybrid-ai-lab/indexer/vector-bm25/tests/test_service.py:440`  
  ID가 달라도 같은 본문 해시의 기존 벡터를 재사용하는 시험
