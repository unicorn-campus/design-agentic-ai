# 임베딩 교육 슬라이드 명세

## 슬라이드 기본 정보

- 슬라이드 수: 정확히 1장
- 크기: 16 × 9인치
- 제목: `임베딩: 본문을 의미 좌표로 바꾸는 과정`
- breadcrumb: `벡터DB 구성 원리 › 임베딩`
- 핵심 메시지: `우리 코드는 정제된 본문만 임베딩하고, 메타데이터는 검색 필터와 출처 표시에 따로 사용함`
- 서체: Pretendard
- 배경: 흰색 `#FFFFFF`
- 색상: Deep Navy `#1E2A5C`, Bright Blue `#2E74C6`, Ink `#2B3242`, Slate `#4A5364`,
  Sub Gray `#7C8598`, Light Blue `#EEF3FA`, Pale Blue `#F5F8FC`, Border `#D9E0EC`
- 최소 글자 크기: 14pt
- 대상 독자: 임베딩과 벡터DB를 처음 접하는 학습자
- 패턴: 상단 편집 가능한 흐름도 + 하단 데이터 표

## 한 장의 읽는 순서

1. 상단 왼쪽의 청크에서 `본문`과 `메타데이터`를 구분함
2. 본문만 임베딩 모델을 통과해 768개 숫자로 바뀌는 흐름을 읽음
3. 메타데이터는 모델을 거치지 않고 저장소로 바로 들어가는 옆길을 확인함
4. 상단 오른쪽의 가상 의미공간에서 비슷한 문장이 가까워지는 뜻을 이해함
5. 하단 표에서 Local과 Cloud의 대표 모델을 비교함

## 화면에 들어갈 문구

### 제목 영역

- breadcrumb: `벡터DB 구성 원리 › 임베딩`
- 제목: `임베딩: 본문을 의미 좌표로 바꾸는 과정`
- 리드문: `문장의 뜻을 숫자 좌표로 바꾸면, 표현이 달라도 의미가 비슷한 문서를 찾을 수 있습니다.`

### 상단 흐름도

- 입력 묶음 제목: `정제된 청크`
- 본문 라벨: `본문 text`
- 본문 예시: `연회비 면제 조건이 궁금해요`
- 메타데이터 라벨: `메타데이터`
- 메타데이터 예시: `source · page · access_level`
- 본문 경로 라벨: `우리 코드의 임베딩 입력`
- 모델 상자: `KURE-v2`
- 모델 부연: `우리 코드 · Local`
- 벡터 상자: `[0.12, -0.07, …]`
- 벡터 부연: `768차원 단일 벡터`
- 저장소 제목: `Chroma`
- 저장 항목: `documents · embeddings · metadatas`
- 메타데이터 옆길 라벨: `필터와 출처 표시용`

### 의미공간

- 제목: `가상 의미공간`
- 가까운 문장 A: `연회비 면제 조건이 궁금해요`
- 가까운 문장 B: `연회비를 안 내려면 어떻게 하나요`
- 먼 문장 C: `비밀번호를 바꾸고 싶어요`
- 캡션: `설명용 가상 위치 · 실제 768차원을 2차원으로 단순화`

### 하단 표

- 표 제목: `대표 임베딩 모델 예시`
- 표 위 보조 문구: `순위가 아닌 선택지 예시이며, 품질·보안·비용·운영 환경에 맞춰 평가합니다.`

| 실행 방식 | 모델 | 한 줄 특징 |
|---|---|---|
| Local | `KURE-v2` | 우리 코드에서 사용하는 한국어 모델 · 768차원 단일 벡터 |
| Local | `BGE-M3` | 다국어 · dense, sparse, multi-vector 지원 |
| Local | `multilingual-e5-large` | 다국어 검색 모델 · 1024차원 |
| Cloud API | `OpenAI text-embedding-3-small / large` | 기본 1536 / 3072차원 · 차원 축소 설정 가능 |
| Cloud API | `Cohere embed-v4.0` | 텍스트·이미지 지원 · 256~1536차원 선택 가능 |

## 레이아웃 명세

### 공통 헤더

- breadcrumb: x 0.55, y 0.35, w 14.9, h 0.25, 15pt SemiBold, `#7C8598`
- 제목: x 0.55, y 0.62, w 14.9, h 0.62, 40pt ExtraBold, `#1E2A5C`
- 리드문: x 0.55, y 1.25, w 14.9, h 0.34, 18pt Regular, `#4A5364`
- 언더라인: y 1.66, 전체 폭 3pt `#D9E0EC`, 왼쪽 2.1인치 구간 `#2E74C6`
- 한 장 안에 상단 그림과 하단 표를 함께 넣어야 하므로 제목은 48pt 대신 40pt 사용함

### 상단 왼쪽 흐름도

- 범위: x 0.55, y 1.92, w 9.65, h 3.15
- 모든 요소를 PowerPoint 기본 도형과 연결선으로 구성하여 편집 가능하게 유지함
- 장식용 그림이나 비트맵을 사용하지 않음
- 입력 묶음은 x 0.70, y 2.22, w 2.40, h 1.75의 흰색 RoundRect로 구성함
- 입력 묶음 안을 가로선으로 나눔
  - 위 1.02인치: 본문 영역, `#EEF3FA`, 라벨 16pt Bold, 예문 17pt
  - 아래 0.55인치: 메타데이터 영역, `#F5F8FC`, 라벨 15pt Bold, 예시 14pt
- 본문 중심에서 모델 상자로 굵기 2.5pt Bright Blue 수평 연결선을 그림
- 연결선 위에 `우리 코드의 임베딩 입력`을 14pt Bright Blue로 배치함
- 모델 상자는 x 3.65, y 2.18, w 1.65, h 1.12의 RoundRect로 구성함
  - 채우기 `#1E2A5C`, 흰색 제목 21pt Bold, 흰색 부연 14pt
- 모델에서 벡터 상자로 굵기 2.5pt Bright Blue 수평 연결선을 그림
- 벡터 상자는 x 5.85, y 2.18, w 1.72, h 1.12의 RoundRect로 구성함
  - 채우기 `#EEF3FA`, 테두리 `#2E74C6`
  - 숫자 19pt SemiBold, 부연 14pt
- 저장소 상자는 x 8.10, y 2.05, w 1.82, h 1.48의 RoundRect로 구성함
  - 흰색 채우기, 테두리 `#1E2A5C` 1.5pt
  - `Chroma` 20pt Bold, 저장 항목 14pt
- 벡터에서 저장소로 굵기 2.5pt Bright Blue 수평 연결선을 그림
- 메타데이터 영역 오른쪽에서 저장소 아래쪽으로 Slate 1.8pt 직각 연결선을 그림
- 메타데이터 연결선 위에 `필터와 출처 표시용`을 14pt Slate로 배치함
- 흐름도 아래 x 0.70, y 4.28에 16pt Bold 문구를 둠
  - `우리 코드 기준: embed(chunk.text)`
- 바로 아래 14pt Slate 설명을 둠
  - `documents, embeddings, metadatas는 저장소에서 서로 다른 필드로 보관`

### 상단 오른쪽 의미공간

- 범위: x 10.55, y 1.92, w 4.90, h 3.15
- 제목 `가상 의미공간`을 x 10.75, y 2.02, 20pt Bold, `#1E2A5C`로 배치함
- 얇은 x축과 y축을 Slate 1pt로 그림. 축에는 수치 눈금을 넣지 않음
- 문장 A와 B는 Bright Blue 원 두 개를 서로 가깝게 배치함
- 문장 C는 Dark Slate 원 하나를 오른쪽 아래에 멀리 배치함
- 각 원에서 짧은 직선 리더를 뻗어 문장 라벨을 14pt로 붙임
- A와 B 사이에 옅은 Blue 점선 타원을 두어 `뜻이 비슷함`을 14pt Bold로 표시함
- 하단 캡션은 14pt Sub Gray로 표시함
  - `설명용 가상 위치 · 실제 768차원을 2차원으로 단순화`
- 점의 좌표나 거리를 실제 모델 측정값처럼 보이게 하는 숫자는 넣지 않음

### 하단 모델 표

- 범위: x 0.55, y 5.33, w 14.90, h 2.70
- 제목: x 0.55, y 5.25, w 4.5, h 0.30, 22pt Bold, `#1E2A5C`
- 보조 문구: x 5.1, y 5.29, w 10.35, h 0.25, 14pt, `#7C8598`, 오른쪽 정렬
- 표는 `addTable()`로 작성하여 모든 셀을 편집 가능하게 유지함
- 열 너비: 실행 방식 1.55인치, 모델 4.20인치, 한 줄 특징 9.15인치
- 헤더 행 높이 0.40인치, 본문 행 높이 각 0.38인치
- 헤더: `#E2EEF9`, 15pt Bold, `#1E2A5C`
- 본문: 14pt, 홀수 행 흰색, 짝수 행 `#F5F8FC`
- 행 구분선: `#EDF0F6` 1pt
- Local / Cloud API 셀은 14pt Bold로 표시하되 별도 배지나 카드로 만들지 않음
- 푸터 영역은 y 8.30 아래로 확보함

## 발표자 노트

임베딩은 문장을 숫자 목록으로 바꾸는 과정입니다. 숫자 하나하나에 사람이 붙인 고정 의미가 있는 것은 아닙니다.
모델은 문장 전체를 좌표로 옮기고, 검색기는 좌표 사이의 거리를 이용해 의미가 가까운 문서를 찾습니다.

우리 코드를 보면 임베딩 입력이 명확합니다. `IndexingWorkflow.embed()`는 정제된 청크에서 `chunk.text`만 꺼내
임베더에 전달합니다. `source`, `page`, `access_level` 같은 메타데이터는 모델 입력에 섞지 않습니다.
저장할 때는 Chroma의 `documents`, `embeddings`, `metadatas` 필드에 본문, 벡터, 메타데이터를 각각 넣습니다.
그래서 메타데이터는 접근 범위 필터, 출처 표시, 문서 유형 필터에 사용하고, 벡터 유사도는 본문의 의미를 비교합니다.

오른쪽 그림은 이해를 돕는 가상 위치입니다. 실제 모델은 768차원 공간을 사용하므로 화면에 그대로 그릴 수 없습니다.
`연회비 면제 조건이 궁금해요`와 `연회비를 안 내려면 어떻게 하나요`는 표현이 달라도 뜻이 비슷하므로 가까이
놓았습니다. `비밀번호를 바꾸고 싶어요`는 주제가 달라 멀리 놓았습니다. 이 점의 위치는 실제 KURE-v2 출력값이나
측정 결과가 아닙니다.

우리 구현은 KURE-v2로 768차원 단일 벡터를 만듭니다. 다른 선택지로는 로컬에서 운영할 수 있는 BGE-M3와
multilingual-e5-large가 있고, API로 호출하는 OpenAI text-embedding-3 계열과 Cohere embed-v4.0이 있습니다.
이 표는 시장 순위가 아닙니다. 실제 선택에서는 한국어 검색 품질, 데이터 반출 허용 범위, 응답 시간, 운영 비용을
같은 평가셋으로 비교해야 합니다.

별도 설계에서는 문서 제목이나 섹션 제목을 본문 앞에 붙인 문자열을 임베딩할 수 있습니다. 그 경우 제목도 모델
입력의 일부가 됩니다. 현재 우리 코드의 `embed()`는 이미 준비된 `chunk.text`만 전달하므로, 제목 결합 여부는
청크를 준비하는 앞 단계에서 명시적으로 결정해야 합니다.

## 근거와 출처

### 우리 코드

- `hybrid-ai-lab/indexer/vector-bm25/app/application/indexing_service.py`
  - `embed()`가 `self.embedder.embed([chunks[chunk_id].text ...])`로 본문만 전달함
- `hybrid-ai-lab/indexer/vector-bm25/app/infrastructure/index_repository.py`
  - `collection.upsert()`가 `documents`, `embeddings`, `metadatas`를 분리하여 저장함
- `hybrid-ai-lab/indexer/vector-bm25/app/infrastructure/embedder.py`
  - 단일 벡터 변환과 L2 정규화 계약을 정의함
- `hybrid-ai-lab/indexer/vector-bm25/evaluation/results/index-audit.json`
  - KURE-v2, 768차원, 단일 벡터 계약을 기록함

### 모델 공식 문서

- [BGE-M3 모델 카드](https://huggingface.co/BAAI/bge-m3)
  - 다국어, dense·sparse·multi-vector 기능, 1024차원 모델 사양
- [multilingual-e5-large 모델 카드](https://huggingface.co/intfloat/multilingual-e5-large)
  - 다국어 검색 모델, 1024차원, query·passage 접두어 사용법
- [OpenAI Embeddings 가이드](https://developers.openai.com/api/docs/guides/embeddings)
  - `text-embedding-3-small`, `text-embedding-3-large`, 기본 차원과 dimensions 설정
- [Cohere Embed 문서](https://docs.cohere.com/docs/cohere-embed)
  - `embed-v4.0`, 텍스트·이미지 입력, 선택 가능한 출력 차원

## Builder 확인 사항

- 슬라이드 수를 1장으로 유지함
- 16 × 9인치 사용자 정의 레이아웃 사용
- Pretendard만 사용하고 모든 글자를 14pt 이상으로 유지함
- 지정한 네이비·블루·흰색 팔레트와 보조 색만 사용함
- 상단 흐름도와 의미공간을 PowerPoint 기본 도형·연결선으로 만들어 편집 가능하게 유지함
- 모델 비교는 `addTable()`로 작성함
- 의미공간에 `설명용 가상 위치` 캡션을 반드시 표시함
- 본문만 임베딩한다는 설명 앞에 `우리 코드 기준`을 반드시 붙임
- Local·Cloud 모델을 순위나 우열로 표현하지 않음
- 제목 결합 가능성은 화면에 추가하지 않고 발표자 노트에만 유지함
- 최종 렌더에서 연결선이 텍스트를 가리지 않는지 확인함
- y 8.30 아래 푸터 영역에 콘텐츠가 침범하지 않는지 확인함
