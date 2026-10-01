# 벡터DB Upsert 교육 슬라이드 명세

## 슬라이드 기본 정보

- 슬라이드 수: 정확히 1장
- 크기: 16 × 9인치
- breadcrumb: `벡터DB 구성 원리 › 적재`
- 제목: `Upsert: 같은 ID는 갱신하고 새 ID는 추가`
- 핵심 문장: `청크 ID를 기준으로 본문·벡터·메타데이터를 한 묶음으로 저장합니다.`
- 서체: Pretendard
- 제목: 48pt ExtraBold
- 본문: 14pt 이상
- 배경: 흰색 `#FFFFFF`
- 색상: Deep Navy `#1E2A5C`, Bright Blue `#2E74C6`, Ink `#2B3242`, Slate `#4A5364`
- 보조 색상: Light Blue `#EEF3FA`, Pale Blue `#F5F8FC`, Border `#D9E0EC`, Line `#EDF0F6`

## 화면 문구

### 코드 영역 제목

`우리 코드가 Chroma에 보내는 값`

### 실제 코드 발췌

아래 호출을 11줄로 표시함. `metadatas` 리스트 표현식은 슬라이드에서 읽기 쉽도록 여러 줄로만 펼쳤으며,
실제 처리 내용은 원본과 같음.

```python
ids = [chunk.chunk_id for chunk in chunks]
collection = self._open(generation)
collection.upsert(
    ids=ids,
    documents=[chunk.text for chunk in chunks],
    embeddings=vectors,
    metadatas=[
        _clean_metadata(chunk.metadata, chunk.chunk_id)
        for chunk in chunks
    ],
)
```

### 인자 설명

| 인자 | 쉬운 설명 |
|---|---|
| `ids` | 청크를 찾고 갱신할 고유 이름 |
| `documents` | 검색 결과에서 보여 줄 정제된 본문 |
| `embeddings` | 본문의 의미를 나타내는 숫자 벡터 |
| `metadatas` | 출처·페이지·접근 수준 같은 필터와 표시 정보 |

### Upsert 동작 예시

- 예시 라벨: `설명용 ID`
- 첫 입력: `A` + `연회비 안내 v1` → `A 추가`
- 같은 컬렉션에 다시 입력: `A` + `연회비 안내 v2` → `A 갱신`
- 새로운 입력: `B` + `분실 신고 안내` → `B 추가`
- 한 줄 정리: `같은 ID는 현재 값을 바꾸고, 처음 보는 ID는 새 레코드를 만듭니다.`

### 우리 구현의 주의점

- 주의 제목: `본문이 바뀌면 항상 같은 ID일까?`
- 화면 답변: `아닙니다. 우리 chunk_id에는 정제 본문의 해시가 들어가므로 본문이 바뀌면 보통 새 ID가 됩니다.`
- ID 구성: `document_id + text_hash 앞 16자리 + 동일 본문 발생 순번`
- 메타데이터만 바뀌고 본문이 같으면 본문 해시는 유지될 수 있음

### 세대 전환 문구

`우리 구현: 새 generation에 upsert → 무결성 검증 → 활성 포인터 교체`

`구축 중에는 기존 활성 generation이 검색을 계속 담당합니다.`

## 레이아웃 명세

### 헤더

- breadcrumb: x 0.55, y 0.35, w 14.9, h 0.25, 15pt SemiBold, `#7C8598`
- 제목: x 0.55, y 0.68, w 14.9, h 0.68, 48pt ExtraBold, `#1E2A5C`
- 핵심 문장: x 0.55, y 1.38, w 14.9, h 0.32, 18pt, `#4A5364`
- 언더라인: y 1.78, 전체 폭 3pt `#D9E0EC`, 왼쪽 2.1인치 구간 `#2E74C6`

### 왼쪽 코드

- 영역: x 0.60, y 2.05, w 7.45, h 3.15
- 영역 제목: 22pt Bold, `#1E2A5C`
- 코드 상자: x 0.70, y 2.55, w 7.20, h 2.55
  - 배경 `#1E2A5C`, 테두리 없음, 모서리 0.08인치
  - 코드 17pt, 흰색, 글꼴은 Pretendard 사용
  - 키워드 강조를 위해 다른 글꼴이나 14pt 미만 글자를 사용하지 않음

### 오른쪽 인자 설명

- 영역: x 8.35, y 2.05, w 7.00, h 3.15
- 영역 제목: `네 인자가 한 레코드를 이룸`, 22pt Bold, `#1E2A5C`
- 인자 표: x 8.45, y 2.55, w 6.75, h 2.55
  - `addTable()`로 작성하여 편집 가능하게 유지함
  - 열 너비: 1.70인치 / 5.05인치
  - 헤더 행: `인자` / `저장하는 값`, 16pt Bold, `#1E2A5C`, 배경 `#E2EEF9`
  - 본문 왼쪽 셀 15pt Bold `#1E2A5C`, 오른쪽 셀 15pt `#2B3242`
  - 홀수 행 흰색, 짝수 행 `#F5F8FC`, 구분선 `#EDF0F6`

### 하단 Upsert 예시

- 영역: x 0.70, y 5.40, w 14.65, h 1.55
- 영역 제목: `ID를 기준으로 추가하거나 갱신`, 22pt Bold, `#1E2A5C`
- `설명용 ID` 필 라벨을 제목 오른쪽에 14pt로 배치함
- 두 개의 수평 흐름을 좌우로 배치함
  - 왼쪽: `기존 ID A` → `A의 본문·벡터·메타데이터 갱신`
  - 오른쪽: `새 ID B` → `B 레코드 추가`
  - 연결선: Bright Blue 2.5pt
- 두 흐름 아래에 Light Blue 콜아웃을 배치함
  - 제목: `본문 변경 시 ID도 확인`
  - 본문: `우리 chunk_id는 본문 해시를 포함하므로 본문이 바뀌면 보통 새 ID가 됩니다.`
  - 보조식: `document_id + text_hash[:16] + duplicate_index`
- `A 갱신` 예시는 Chroma upsert의 일반 동작을 설명하는 가상 예시라고 캡션을 14pt로 표시함

### 하단 세대 전환 띠

- 영역: x 0.70, y 7.25, w 14.65, h 0.65
- 하나의 평평한 흐름으로 구성하며 카드 묶음처럼 보이지 않게 함
- 세 단계 텍스트를 네이비 선과 화살표로 연결함
  - `새 generation에 upsert`
  - `무결성 검증`
  - `활성 포인터 교체`
- 아래 14pt Slate 캡션
  - `구축 중에는 기존 활성 generation이 검색을 계속 담당`
- 푸터 영역은 y 8.25 아래로 확보함

## 짧은 발표문

Upsert는 청크 ID를 기준으로 저장 값을 추가하거나 갱신하는 동작입니다. 같은 컬렉션에 ID A를 다시 보내면
A의 본문·벡터·메타데이터가 새 값으로 바뀌고, 처음 보는 ID B를 보내면 B가 추가됩니다. 우리 코드는 이 네 가지
값을 Chroma에 한 번에 전달합니다. 다만 우리 `chunk_id`에는 정제된 본문의 해시가 들어갑니다. 같은 문서라도
본문이 바뀌면 보통 새 ID가 되므로, 언제나 기존 ID를 갱신한다고 보면 안 됩니다. 또한 실제 서비스에서는 새
generation을 따로 채우고 검증한 뒤 활성 포인터를 바꿉니다. 적재 중에는 기존 generation이 검색을 계속합니다.

## 발표자 노트

- `collection.upsert()`의 기준 키는 `ids`임
- 한 배치에서는 코드가 ID 중복, 청크·벡터 개수, 벡터 차원과 숫자 유효성을 먼저 검사함
- 일반적인 upsert 설명에서는 같은 컬렉션의 같은 ID를 다시 쓰면 갱신, 새 ID는 추가라고 설명함
- 화면의 A와 B는 개념을 설명하기 위한 가상 ID임
- 우리 코드의 기본 청크 ID는 정제 본문의 SHA-256 해시 앞 16자리를 포함함
- 응용 계층이 같은 문서 안에서 같은 본문이 반복될 때 `_0000`, `_0001` 같은 발생 순번을 붙임
- 따라서 본문이 바뀌면 해시가 달라져 대개 다른 ID가 됨. 같은 문서라는 이유만으로 같은 ID가 보장되지 않음
- 메타데이터만 바뀌고 정제 본문이 같으면 본문 기반 ID와 기존 벡터를 재사용할 수 있음
- 저장은 현재 활성 컬렉션을 즉시 바꾸는 방식이 아님. `begin()`이 비활성 generation을 준비하고,
  `publish()`가 검증을 마친 뒤 활성 포인터를 마지막에 교체함
- 이번 작업은 코드 설명 슬라이드 명세 작성이며 인덱스와 Chroma를 실제로 실행하지 않음

## 코드 근거

- `hybrid-ai-lab/indexer/vector-bm25/app/infrastructure/index_repository.py:210`
  - `collection.upsert()`에 ID·본문·벡터·메타데이터를 전달함
- `hybrid-ai-lab/indexer/vector-bm25/app/infrastructure/processor.py:79`
  - 정제 본문으로 `text_hash`를 생성함
- `hybrid-ai-lab/indexer/vector-bm25/app/infrastructure/processor.py:82`
  - `document_key`와 `text_hash[:16]`으로 기본 `chunk_id`를 만듦
- `hybrid-ai-lab/indexer/vector-bm25/app/application/indexing_service.py:391`
  - 같은 문서의 동일 본문 발생 순번을 청크 ID 뒤에 붙임
- `hybrid-ai-lab/indexer/vector-bm25/app/infrastructure/index_repository.py:498`
  - 검증 후 활성 포인터를 교체함

## Builder 확인 사항

- 정확히 1장만 생성함
- 16 × 9인치, Pretendard, 제목 48pt, 모든 본문 14pt 이상을 유지함
- 실제 호출을 11줄로 표시하며 `metadatas`만 읽기 좋게 줄바꿈함
- 인자 네 개를 코드와 같은 순서로 설명함
- A 갱신과 B 추가를 설명용 가상 예시로 표시함
- 본문 변경 시 보통 새 ID가 된다는 주의 문구를 화면에서 숨기지 않음
- 새 generation 적재와 활성 포인터 교체를 하단 흐름으로 구분함
- 코드·표·도형을 편집 가능한 PowerPoint 객체로 작성함
- PPT 빌드 후 코드 줄바꿈, 화살표 겹침, 14pt 미만 글자 여부를 확인함
