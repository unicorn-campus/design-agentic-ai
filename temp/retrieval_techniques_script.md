# 검색 테크닉 — PPT 스크립트 (v2: 도형 시각화판)

> 4장 구성. 개념은 **편집 가능한 도형**(박스·화살표·칩·막대·점)으로 그리고, 글은 도형 라벨 수준으로 줄임.  
> 모든 수치는 교재·프로젝트 파일·논문에서 확인한 값만 사용함. 예시 그림은 「예시」로 표기함.  
> 내용 원안: 지식니(`jisikni`) v1 스크립트 / 시각화 재구성: 클로니

---

## 슬라이드 1. 검색 방식 4종 한눈에

- breadcrumb: RAG › 4. Techniques › 4.2 Retrieval
- 리드문: 같은 질문도 "낱말로 찾기"와 "뜻으로 찾기"는 서로 다른 문서를 데려옴
- 시각화: 4열 카드. 카드마다 헤더 바 + 미니 도식 + 강점/약점 2줄

| 카드 | 미니 도식(도형) | 강점 | 약점 |
|---|---|---|---|
| Sparse (BM25) | 질문 칩 [연회비][면제] → 문서 안 칩 중 같은 낱말만 파랗게 표시 | 조항 번호·상품 코드 같은 정확한 용어 | 다른 말로 물으면 못 찾음 |
| Dense (임베딩) | 원점에서 뻗은 화살표 3개, 질문 화살표와 각도가 가까운 문서가 선택됨 | 구어체·돌려 말한 질문 | 드문 고유명사·숫자 코드 |
| Hybrid | [BM25 점수]·[Vector 점수] 박스 2개 → 화살표 → [합친 점수] | 용어+자연어가 섞인 질문 | 검색기 2개 관리·비중 조정 |
| GraphRAG | 원 노드 3개(회원·카드·혜택)를 선으로 연결 | "A와 이어진 B" 관계 추적 | 그래프 구축 비용 |

- 하단 띠: 「이 프로젝트(hybrid-ai-lab)」 배지 + 필 4개  
  Sparse = BM25S + Kiwi / Dense = KURE-v2 + ChromaDB / Hybrid = Vector 0.6 + BM25 0.4 / GraphRAG = 미적용
- 발표 노트: Sparse는 벡터 대부분이 0이라 "드문(sparse)", Dense는 모든 칸에 숫자가 차 있어 "빽빽한(dense)"임.  
  우리 프로젝트는 약관 조항 번호와 상담 대화체 질문이 함께 들어오므로 Hybrid를 기본으로 둠
- 출처: 교재 10.RAG.md §4.2 · vector-retriever README.md

---

## 슬라이드 2. Sparse Retrieval — BM25

- breadcrumb: RAG › 4.2 Retrieval › 4.2.1 Sparse
- 리드문: BM25는 "질문 낱말이 이 문서에 얼마나 자주, 전체 문서에서 얼마나 드물게 나오나"로 점수를 매김
- 시각화 ① 상단 흐름도(박스 5개 + 화살표)  
  [질문 "연회비 면제 조건은?"] → [정규화: NFKC·소문자·숫자 쉼표] → [Kiwi 형태소 분석] →  
  [칩: 연회비 · 면제 · 조건 / 회색 취소선 칩 "은?"] → [BM25S 점수 계산]  
  흐름도 아래 콜아웃: 색인과 질문에 **같은 토크나이저** 사용, 서명이 다르면 검색 거부
- 시각화 ② 점수 요소 3칸(번호 배지 + 미니 그래프)
  - ① TF 포화: 막대 5개(1·2·3·5·10회). 높이는 BM25 TF 항 `tf×(k1+1)/(tf+k1)`, k1=1.5로 계산  
    → 1.00 · 1.43 · 1.67 · 1.92 · 2.17, 점선 한계선 2.5(=k1+1)
  - ② IDF: 「카드」 5개 문서 모두 등장 → 가중치 막대 짧음 / 「연회비」 1개 문서만 등장 → 막대 김 (예시)
  - ③ 길이 보정 b: 같은 "연회비 2회"라도 짧은 문서(평균의 0.5배) 1.70 vs 긴 문서(평균의 2배) 1.08  
    (k1=1.5, b=0.75로 TF 항 계산)
- 하단 필: 프로젝트 설정 k1 1.5 · b 0.75 · BM25S lucene 방식
- 발표 노트: 한국어는 "연회비는/연회비가/연회비를"이 서로 다른 글자라 그대로 비교하면 못 맞춤.  
  Kiwi로 조사를 떼고 뜻 있는 낱말만 남김. 토큰 예시는 프로젝트 가상환경에서 실제 실행 결과임(지식니 확인)
- 출처: 교재 §4.2.1 · Robertson & Zaragoza(2009) · Kiwi · BM25S · lexical_index.py · korean_tokenizer.py

---

## 슬라이드 3. Dense Retrieval — 임베딩과 코사인 유사도

- breadcrumb: RAG › 4.2 Retrieval › 4.2.2 Dense
- 리드문: 문장을 숫자 목록(벡터)으로 바꾼 뒤, 질문과 "방향"이 가장 비슷한 문서를 고름
- 시각화 ① 상단 흐름도  
  [질문 "연회비 안 내도 되는 경우"] → [KURE-v2 임베딩] → [칩 0.12 · -0.34 · 0.56 · … / 숫자 768개] →  
  [ChromaDB 코사인 비교] → [Top-K / 후보는 최종 건수×4 먼저 수집]
- 시각화 ② 좌하 벡터 공간(예시): 원점에서 화살표 4개  
  질문(파랑, 굵게) / "연회비 면제 조건"(네이비, 각도 가까움 → 선택) / "포인트 적립"·"해외 결제"(회색, 각도 멂)  
  라벨: 각도가 작을수록 유사 · 길이는 무시 · 점수 = 1 − 거리
- 시각화 ③ 우하 MMR 패널  
  similarity(기본): 색 블록 5개 [A][A][A][A][B] → 같은 내용 반복  
  mmr: [A][B][C][A][D] → 관련성 + 다양성  
  λ 눈금 막대 0(다양성 우선) ~ 1(관련성 우선), 표시점 0.5 / 주석: 기본은 꺼짐, 점수는 원래 코사인 값 유지
- 발표 노트: 문서에 없는 표현으로 물어도 찾는 게 장점, "D1 제10조" 같은 코드에는 흐릿함 → 다음 장 Hybrid.  
  768차원은 모델 페이지가 아니라 우리 색인 `/health` 실측값임(모델 페이지 설명이 바뀌었음 — 지식니 확인)
- 출처: 교재 §4.2.2 · Carbonell & Goldstein(1998) · KURE-v2 모델 페이지 · settings.py · chroma_store.py

---

## 슬라이드 4. Hybrid Search — 두 점수를 합치는 두 가지 방법

- breadcrumb: RAG › 4.2 Retrieval › 4.2.3 Hybrid
- 리드문: BM25 점수와 코사인 점수는 단위가 달라 그냥 더할 수 없음 — 교재는 "순위"로, 프로젝트는 "0 ~ 1 점수"로 합침
- 시각화 ① 좌 패널 「교재 — RRF(순위로 합치기)」 (교재 §4.2.3 예시, k=60)  
  문서 A: BM25 1위 · Dense 3위 → 1/61 + 1/63 = 0.0323  
  문서 B: BM25 5위 · Dense 1위 → 1/65 + 1/61 = 0.0318  
  가로 막대 2개(A가 약간 김) → 「A 최종 상위」 / 주석: 몇 점인지 버리고 몇 등인지만 봄
- 시각화 ② 우 패널 「이 프로젝트 — 정규화 가중합」  
  1단계 최소-최대 정규화: 원점수 막대 2·5·8 → 화살표 → 0.0·0.5·1.0 (scoring.py 주석 예시)  
  2단계 가중합: 누적 막대 Vector 60% + BM25 40% / 주석: 점수 차 크기까지 반영
- 시각화 ③ 하단 실측 띠 (2026-09-20 · 질문 10건 · Top-5 · 질문 변환 off)  
  점 10개 2줄: vector 8/10(q04·q10 빈 점) · hybrid 9/10(q10 빈 점)  
  응답 시간 중앙값 막대: vector 186ms · hybrid 195ms → 차이 거의 없음
- 발표 노트: 평균값은 첫 질문의 모델 적재 시간이 섞여 비교에 부적합하므로 중앙값 사용(실측 JSON 원시값에서 재계산)
- 출처: 교재 §4.2.3 · Cormack et al.(2009, SIGIR) · scoring.py · settings.py · retriever_10q_4mode_results.json

---

## 근거 출처 목록

- 교재: https://github.com/cna-bootcamp/aistudy/blob/main/agentic-ai/textbook/10.RAG.md#42-retrieval
- Robertson & Zaragoza(2009) "The Probabilistic Relevance Framework: BM25 and Beyond"
- Cormack, Clarke & Büttcher(2009, SIGIR) "Reciprocal Rank Fusion outperforms Condorcet and individual Rank Learning Methods"
- Carbonell & Goldstein(1998) "The Use of MMR, Diversity-Based Reranking for Reordering Documents and Producing Summaries"
- https://github.com/bab2min/Kiwi · https://github.com/xhluca/bm25s · https://huggingface.co/nlpai-lab/KURE-v2
- 프로젝트(`hybrid-ai-lab/`): `retriever/vector-retriever/README.md`, `app/application/scoring.py`,  
  `app/infrastructure/settings.py`, `app/infrastructure/chroma_store.py`, `app/infrastructure/korean_tokenizer.py`,  
  `indexer/vector-bm25/app/infrastructure/lexical_index.py`, `retriever/vector-retriever/data/retriever_10q_4mode_results.json`
