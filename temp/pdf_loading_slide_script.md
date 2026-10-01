# 문서 로드·PDF 슬라이드 스크립트

## 슬라이드 1. PDF 로드: 글자와 위치를 다음 단계에 넘기기

### 목적 한 문장

PDF 로드는 화면에 보이는 내용을 검색 가능한 본문으로 읽고, 페이지와 제거 예정 구간을 청킹·정제 단계에 전달합니다.

### 화면 구성

- 비율: 16:9, 흰색 배경
- 글꼴: Pretendard
- 제목: 48pt ExtraBold, `#1E2A5C`
- 본문: 16 ~ 18pt, 최소 14pt
- 색상: Deep Navy `#1E2A5C`, Bright Blue `#2E74C6`, Light Blue `#EEF3FA`
- 구성: 상단 실제 처리 흐름, 중앙 왼쪽 코드, 중앙 오른쪽 제품 비교, 하단 설계 항목

### 상단: 우리 코드의 PDF 처리 흐름

다섯 개의 편집 가능한 도형을 왼쪽에서 오른쪽으로 연결합니다.

`PDF` → `페이지 텍스트·줄 bbox 읽기` → `페이지 본문 연결` → `page_spans·제거 예정 구간` → `청킹·정제`

각 단계 아래에 짧은 설명을 둡니다.

1. **PDF**: 파일 전체를 `LoadedDocument` 하나로 만듦
2. **페이지 읽기**: `get_text("dict", sort=True)`로 텍스트 블록과 줄 좌표를 읽음
3. **본문 연결**: 페이지 사이에 빈 줄을 넣고 한 문자열로 연결
4. **위치 기록**: 페이지별 문자 범위와 반복 여백의 제거 예정 문자 범위를 기록
5. **다음 단계**: 청킹이 페이지 출처를 이어받고 정제가 반복 여백을 제거

흐름 아래 주의 배지:

`줄 bbox는 로드 중 여백 판정에 사용 · 최종 문서에는 page_spans와 removal_spans를 보존`

### 중앙 왼쪽: 실제 핵심 코드

코드 박스 제목은 **현재 구현: PyMuPDF**로 표시합니다.

```python
pages = []
with pymupdf.open(source.path) as pdf:
    for number, page in enumerate(pdf, start=1):
        page_dict = page.get_text("dict", sort=True)
        lines = _page_lines(page_dict)
        pages.append({"number": number, "height": page.rect.height, "lines": lines})
repeated = _repeated_margin_lines(pages, self._policies[source.doc_key])
```

코드 아래 설명:

- `_page_lines()`는 이미지 블록을 건너뛰고 텍스트 줄만 bbox의 위쪽·왼쪽 순으로 정렬함
- 반복 머리말·꼬리말은 여기서 지우지 않고 `removal_spans`로 표시한 뒤 정제 단계에서 제거함
- PDF 전체 텍스트가 비면 “OCR 원천 처리가 필요함” 오류를 내며 자동 OCR은 수행하지 않음

### 중앙 오른쪽: PDF 로드 제품 비교

표 제목에 **제품 선택 후보 — 현재 적용 여부 구분**을 표시합니다.

| 제품 | 잘 맞는 상황 | 현재 적용 |
|---|---|---|
| **PyMuPDF** | 텍스트 계층과 좌표를 직접 읽고 이미지 추출·렌더링도 확장하려는 경우 | 적용 중. `dict` 텍스트만 사용하며 이미지·PyMuPDF4LLM은 미사용 |
| **Docling** | AI 레이아웃 분석, OCR 분기, TableFormer 기반 표 구조가 필요한 문서 | 검토 후보. 우리 로더에는 연결되지 않음 |
| **pdfplumber** | 글자·선 좌표, 규칙 기반 표 추출, 시각 디버깅이 중요한 양식 | 검토 후보. 우리 로더에는 연결되지 않음 |

표 아래 캡션:

`속도·다단 읽기 순서·표 정확도는 문서 표본으로 측정해야 하며 제품명만으로 보장할 수 없음`

### 하단: 설계할 때 정의할 항목

| 설계 항목 | 결정할 질문 |
|---|---|
| 로드 제품 | 텍스트 PDF 중심인가, 레이아웃·표·이미지 이해까지 필요한가? |
| OCR 분기 | 텍스트가 없거나 너무 적을 때 어떤 OCR로 보내고 언제 실패시킬 것인가? |
| 표·읽기 순서 | 다단·표를 행과 열로 복원할 기준과 허용 오류는 무엇인가? |
| 출처 위치 | 페이지, bbox, 문자 범위 중 검색 결과와 답변 근거에 무엇을 남길 것인가? |
| 품질·실패 기준 | 표본 문서로 누락률·순서·표 셀·처리 시간·메모리를 어떻게 합격시킬 것인가? |

### 발표자 말할 내용

“PDF 로드의 목적은 글자를 꺼내는 데서 끝나지 않습니다. 어느 페이지에서 나온 글자인지 다음 청킹 단계가 알 수 있어야
합니다. 우리 코드는 PyMuPDF로 각 페이지의 텍스트 줄과 bbox를 읽고, 페이지 순서대로 한 문서 본문을 만듭니다. 줄 bbox는
반복 머리말과 꼬리말을 찾는 데 사용하고, 최종 문서에는 페이지 문자 범위와 제거 예정 문자 범위를 남깁니다. 정제 단계가
이 범위를 실제로 제거합니다. 현재 로더는 이미지 속 글자를 OCR하지 않으므로 스캔 PDF는 오류로 분기합니다. AI 레이아웃,
OCR, 표 구조가 필요하면 Docling을, 좌표 기반 표 규칙과 시각 검사가 중요하면 pdfplumber를 후보로 비교할 수 있습니다.”

### 발표자 노트

- 현재 구현은 `page.get_text("dict", sort=True)`를 한 번 호출해 본문 구성과 여백 판정에 같은 추출 결과를 사용함.
- `_page_lines()`는 `block.type == 0`인 텍스트 블록만 사용함. PDF에 포함된 이미지를 별도 저장하거나 이미지 설명을 만들지 않음.
- `page_spans`는 연결된 본문에서 각 페이지가 차지하는 문자 시작·끝 범위임. 원래의 줄 bbox 전체를 최종
  `LoadedDocument`에 보존하는 구조는 아님.
- 반복 여백은 페이지 위·아래 7% 안의 줄을 정규화해 설정된 최소 페이지 수 이상 반복되는지 판단함. 로드 단계에서는
  `removal_spans`만 기록하고 실제 제거는 후속 정제 단계가 수행함.
- 텍스트 계층이 일부라도 있으면 현재 코드는 OCR 품질이나 페이지별 텍스트 부족을 따로 판정하지 않음. 전체 본문이 비어
  있을 때만 OCR 필요 오류를 냄. 혼합형 PDF의 OCR 분기 기준은 추가 설계가 필요함.
- `sort=True`와 bbox 정렬을 사용해도 복잡한 다단 문서의 읽기 순서가 항상 맞는다고 보장할 수 없음.
- PyMuPDF4LLM은 Markdown·JSON·페이지 청크와 이미지/OCR 관련 선택지를 제공하지만 현재 프로젝트 코드에서는 사용하지 않음.
- Docling의 OCR·레이아웃 분석·TableFormer와 pdfplumber의 표 추출·시각 디버깅은 제품 기능 설명이며 현재 구현 결과가 아님.
- 이 슬라이드는 소스 분석 결과이며 PDF 로더 전체나 세 제품의 성능 비교를 실행한 결과가 아님.

### 코드 근거

- `hybrid-ai-lab/indexer/vector-bm25/app/infrastructure/loaders.py:122`  
  PyMuPDF 페이지를 연결하고 페이지·반복 여백 범위를 만드는 `_load_pdf()`
- `hybrid-ai-lab/indexer/vector-bm25/app/infrastructure/loaders.py:129`  
  `get_text("dict", sort=True)`로 페이지 텍스트 계층을 읽는 코드
- `hybrid-ai-lab/indexer/vector-bm25/app/infrastructure/loaders.py:150`  
  반복 여백을 즉시 삭제하지 않고 `removal_spans`에 기록하는 코드
- `hybrid-ai-lab/indexer/vector-bm25/app/infrastructure/loaders.py:156`  
  전체 텍스트가 비면 OCR 필요 오류를 내는 코드
- `hybrid-ai-lab/indexer/vector-bm25/app/infrastructure/loaders.py:245`  
  텍스트 블록의 줄과 bbox를 읽기 순서로 정렬하는 `_page_lines()`
- [Docling 공식 CLI 문서](https://docling-project.github.io/docling/reference/cli/)  
  OCR 선택지와 Docling TableFormer 표 구조 엔진
- [PyMuPDF4LLM 공식 API 문서](https://pymupdf.readthedocs.io/en/latest/pymupdf4llm/api.html)  
  Markdown·페이지 청크·이미지·OCR 관련 출력 선택지
- [pdfplumber 공식 저장소 문서](https://github.com/jsvine/pdfplumber/blob/stable/README.md)  
  문자·선 좌표, 표 추출, 시각 디버깅 기능
