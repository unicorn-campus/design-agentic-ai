# 청킹 교육 슬라이드 설명 스크립트

## 제작 메모

전체 분량은 3장입니다. 16:9 화면과 Pretendard 글꼴을 사용합니다.  
표와 도식은 PowerPoint에서 직접 수정할 수 있는 표·도형·연결선으로 구성합니다.

## 1. 한 청크의 구성

### 핵심 메시지

청크는 검색할 본문과 그 본문의 출처·조건을 함께 담습니다.

### 화면 구성

하나의 큰 청크 도형을 메타데이터와 본문 영역으로 나눕니다.

- 메타데이터: 출처와 검색 조건
- 본문: 질문의 답을 찾는 내용

화면의 청크는 다음과 같은 가상 약관 예시입니다.

| 메타데이터 | 본문 |
|---|---|
| 출처: 카드약관.pdf | 제3조 연회비 반환 |
| 쪽: 12 | 카드를 해지하면 남은 기간에 해당하는 연회비를 반환합니다. |
| 조항: 제3조 | 다만, 발급 비용은 제외합니다. |
| 공개 등급: public |  |

청크 왼쪽에는 메타데이터가 출처 표시와 검색 범위 제한에 쓰인다는 설명을 둡니다.  
오른쪽에는 본문이 관련 내용 검색과 답변 근거에 쓰인다는 설명을 둡니다.

### 발표자 설명

청크는 하나의 검색 단위입니다. 메타데이터는 출처 표시, 필터링, 접근 범위 판단에 사용합니다.  
본문은 관련 내용을 찾고 답변의 근거를 제시하는 데 사용합니다.

화면의 약관 파일과 문구는 설명을 위해 만든 가상 예시이며 실제 규정이 아닙니다.  
임베딩 벡터를 색인에 함께 저장할 수 있지만, 이 장에서는 사용자가 요청한 본문과 메타데이터에 초점을 맞춥니다.

상품명처럼 의미 검색과 정확한 필터에 모두 필요한 값은 본문과 메타데이터 양쪽에 둘 수 있습니다.  
이 구조는 LangChain `Document`의 `page_content`와 `metadata`에 대응합니다.

### 출처

- LangChain TextSplitter:
  <https://github.com/langchain-ai/langchain/blob/master/libs/text-splitters/langchain_text_splitters/base.py>

## 2. 청킹 설계의 결정 항목

### 핵심 메시지

청킹 설계에서는 무엇을 물려주고, 어디서 나누며, 얼마나 겹칠지 함께 정합니다.

### 화면 구성

왼쪽 표에는 여섯 가지 설계 항목을 정리합니다.

| 설계 항목 | 정의할 내용 |
|---|---|
| 메타데이터 구조 | 필드·자료형·필수 여부, 공통값 상속과 범위별 값 계산 |
| 구분자 | 조항·문단·발화 등 경계 우선순위, 구분자 보존과 긴 단위의 추가 분할 |
| 청킹 크기 | 목표·최대 크기와 단위, 토큰 측정기와 모델 입력 한도 |
| 오버랩 크기 | 반복할 문맥의 크기와 단위, 중첩을 적용할 경계 |
| 정제·가명처리 | 적용 규칙과 청킹 전·후 시점, 본문·메타데이터 처리 범위 |
| 검증·평가 | 개인정보 잔존·필수값·최종 길이, 평가 질문의 정답 근거 검색 여부 |

오른쪽에는 크기와 오버랩의 관계를 보여 줍니다.  
A부터 G까지는 각각 100토큰인 가상 구간입니다. 청크 1은 A~D, 청크 2는 D~G로 구성합니다.  
두 청크가 D 구간 100토큰을 공유하므로 각 청크 크기는 400토큰이고 오버랩은 100토큰입니다.

### 발표자 설명

청킹 설계는 숫자 두 개만 정하는 일이 아닙니다. 먼저 검색과 출처 표시에 필요한 메타데이터의 필드, 자료형,
필수 여부를 정합니다. 문서 전체의 공통값은 상속하고, 청크 범위에 따라 달라지는 값은 구조나 위치를 보고 계산합니다.

명확한 구분자가 있으면 그 경계를 우선합니다. 하나의 의미 단위가 너무 길 때 어떻게 더 나눌지도 정합니다.  
크기와 오버랩은 문자와 토큰 중 어떤 단위를 쓰는지 함께 기록합니다. 토큰을 사용한다면 모델에 맞는 측정기를 정합니다.

오버랩은 앞 청크의 일부를 다음 청크에도 넣어 경계의 문맥을 이어 주는 방법입니다.  
화면의 400토큰과 100토큰은 관계를 설명하기 위한 가정이며 권장 최적값이나 실제 측정 결과가 아닙니다.

정제 규칙이 구분자와 필요한 구조 정보를 보존한다면 청킹 전에 정제할 수 있습니다.  
처리 시점은 설계 결정이며 특정 프레임워크가 청킹 전·후의 표준 순서를 강제하지 않습니다.  
저장 전에는 최종 본문과 메타데이터를 검사하고, 검색 품질은 평가 질문으로 확인합니다.

### 출처

- LangChain TextSplitter:
  <https://github.com/langchain-ai/langchain/blob/master/libs/text-splitters/langchain_text_splitters/base.py>
- LangChain RecursiveCharacterTextSplitter:
  <https://github.com/langchain-ai/langchain/blob/master/libs/text-splitters/langchain_text_splitters/character.py>
- Microsoft Azure AI Search:
  <https://learn.microsoft.com/en-us/azure/search/vector-search-how-to-chunk-documents>

## 3. 청킹 Best Practice

### 핵심 메시지

LangChain의 메타데이터 전달과 Azure AI Search의 크기·중첩 권고를 참고하되,
문서 구조와 평가 질문에 맞게 조정합니다.

### 화면 구성

화면 왼쪽에는 LangChain의 메타데이터 전달 과정을 배치합니다.  
`source: 약관.pdf`, `page: 12`를 가진 입력 문서가 본문 A와 본문 B로 나뉘며,
두 청크가 동일한 `source`와 `page`를 물려받습니다.

화면 오른쪽에는 Azure AI Search의 초기 권고값을 도식화합니다.  
두 청크의 크기는 각각 512토큰이며, 같은 128토큰을 공유합니다.  
128토큰은 전체 512토큰의 25%입니다.

하단에는 다음 주의 문구를 둡니다.

> 정제 시점은 별도 설계 결정입니다. 두 사례가 청킹 전·후의 순서를 강제하지는 않습니다.

### 발표자 설명

왼쪽은 LangChain `TextSplitter`의 실제 동작을 설명한 도식입니다. `split_documents`는 입력 문서의 본문과
메타데이터를 `create_documents`에 전달합니다. `create_documents`는 분할 청크마다 메타데이터를 깊은 복사합니다.

화면의 `source`와 `page`는 동작을 설명하기 위한 가상 예시입니다. 여러 페이지를 합친 문서에 원래 페이지 하나를
복사한다고 해서 청크별 페이지가 자동 계산되지는 않습니다. 페이지와 조항처럼 청크 범위에 따라 달라지는 값은 따로 계산합니다.

`RecursiveCharacterTextSplitter`는 지정한 구분자 순서로 긴 텍스트를 재귀적으로 나눕니다.  
기본 구분자는 문단, 줄바꿈, 공백, 문자 수준입니다.

오른쪽은 Azure AI Search 공식 문서가 제시하는 초기 권고값입니다. 512토큰 크기와 25% 중첩인 128토큰을 보여 줍니다.  
이 값은 보편적인 최적값이나 이 프로젝트의 실측 결과가 아닙니다. 구조와 문장 경계에 따라 실제 길이와 중첩은 달라질 수 있습니다.

Azure 문서는 구조가 명확한 데이터에는 더 적은 중첩이 적합할 수 있다고 설명합니다.  
따라서 공식 사례를 출발점으로 삼고, 문서 구조와 평가 질문에 맞춰 크기와 중첩을 조정합니다.  
LangChain과 Azure AI Search 사례 모두 개인정보 정제 시점을 강제하지 않습니다.

### 출처

- 확인일: 2026-10-01
- LangChain TextSplitter:
  <https://github.com/langchain-ai/langchain/blob/master/libs/text-splitters/langchain_text_splitters/base.py>
- LangChain RecursiveCharacterTextSplitter:
  <https://github.com/langchain-ai/langchain/blob/master/libs/text-splitters/langchain_text_splitters/character.py>
- Microsoft Azure AI Search:
  <https://learn.microsoft.com/en-us/azure/search/vector-search-how-to-chunk-documents>
