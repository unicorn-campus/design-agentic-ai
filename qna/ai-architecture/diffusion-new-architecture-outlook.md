# Diffusion 방식 등 새로운 아키텍처 출현에 대한 연구 현황과 미래 전망

- 작성일: 2026-10-15  
- 작성자: 클로니(Agentic AI 아키텍트)  
- 질문: "Diffusion 방식 등 새로운 아키텍처 출현에 대한 연구 현황과 미래 전망"  
- 근거 기준: 논문 원문(arXiv), 제조사 공식 발표, 공개 보고서, 인터뷰 원문을 우선 참조.  
  2차 출처(언론, 블로그)에만 근거한 내용은 본문에 「2차 출처」로 표시.  
  사실(Fact)과 의견(Opinion)은 3장에서 구분 표기

## 한 줄 요약

2026년 10월 현재 "한 토큰씩 순서대로 쓰는" 트랜스포머 자기회귀 방식이 여전히 주류임.  
그러나 「생성 속도」와 「긴 문맥 비용」이라는 두 병목을 깨려는 네 갈래의 새 구조가  
실험실을 넘어 상용 서비스 또는 오픈소스 모델로 나오는 단계에 들어섬.  
확산(Diffusion) 언어 모델과 상태공간(SSM) 하이브리드는 이미 제품 단계이고,  
재귀형 소형 추론 모델과 세계 모델(JEPA)은 아직 연구 단계임.

## 1. 왜 새로운 아키텍처가 나오는가

쉬운 비유: 지금의 LLM은 글을 "한 글자씩 왼쪽에서 오른쪽으로" 씀.  
아무리 빠른 GPU를 써도 앞 글자가 정해져야 다음 글자를 쓸 수 있으므로 속도에 천장이 있음.  
또 글이 길어질수록 "지금까지 쓴 모든 글자"를 매번 다시 훑어야 하므로 비용이 가파르게 늘어남.

| 구조적 비용 | 쉬운 설명 | 에이전트 시스템에 주는 영향 |
|------------|-----------|---------------------------|
| 순차 생성 지연 | 토큰을 하나씩 만들어 GPU 병렬 능력을 다 못 씀 | 도구 호출을 수십 번 반복하면 지연이 누적됨 |
| 메모리(KV 캐시) 증가 | 문맥이 길수록 저장할 중간값이 비례해 늘어남 | 긴 대화, 긴 문서 서빙 비용이 급증함 |
| 문맥 길이의 제곱 비용 | 어텐션 계산량이 문맥 길이의 제곱에 비례함 | 100만 토큰급 문맥은 비용 부담이 큼 |
| 일반화 한계 | 사람보다 훨씬 적게 일반화한다는 지적 | 규모 확장만으로는 한계가 있다는 전문가 발언 |

이 네 가지 중 앞의 셋은 「구조」의 문제라 모델을 키워도 해결되지 않음.  
그래서 2025년부터 "구조를 바꾸는" 연구가 다시 활발해짐.

## 2. 연구 현황: 네 갈래 흐름

### 2.1 확산 언어 모델 (Diffusion Language Model, dLLM)

#### 원리

이미지 생성 모델(Stable Diffusion 등)의 방식을 글에 적용한 것임.  
문장 전체를 "모두 가려진(마스크) 상태"에서 시작해, 여러 번에 걸쳐 동시에 여러 칸을 채우고 다듬음.  
한 번의 계산에서 여러 토큰이 확정되므로 자기회귀 방식보다 생성 속도가 빠름.  
또 앞뒤 문맥을 모두 보므로(양방향) 중간에 끼워 넣기, 고쳐 쓰기 같은 편집 과제에 유리함.

#### 주요 모델 (시간순)

| 모델 | 주체 | 시점 | 규모 | 의미 |
|------|------|------|------|------|
| LLaDA | 중국 인민대, Ant Group | 2025-02 | 8B | 밑바닥부터 학습한 첫 대규모 공개 dLLM |
| Mercury | Inception Labs | 2025-02 ~ 06 | 비공개 | 첫 상용 dLLM, 논문은 2025-06 |
| Gemini Diffusion | Google DeepMind | 2025-05 | 비공개 | 실험 데모, 초당 약 1,479 토큰(오버헤드 제외) |
| LLaDA2.0 | Ant Group(inclusionAI) | 2025-11 ~ 12 | 16B, 100B(MoE) | 첫 100B급 dLLM, Apache-2.0 공개 |
| DiffusionGemma | Google DeepMind | 2026-06 | 약 25B(활성 3.8B) | 구글 첫 오픈 가중치 dLLM(2차 출처) |
| Nemotron-Labs-Diffusion | NVIDIA | 2026-07 | 3B, 8B, 14B | 자기회귀, 확산, 자기추측 3모드 통합 |
| Mercury 2.5 | Inception Labs | 2026-09 ~ 10 | 비공개 | 초당 1,107 토큰(자체 측정), 260K 문맥 |

#### 확인된 사실

- 속도: Inception Labs는 Mercury 2.5가 범용 NVIDIA GPU에서 초당 1,107 토큰을 낸다고 발표함.  
  다만 이는 제조사 자체 측정이며, OpenRouter 실트래픽 기준으로는 초당 약 477 토큰이 관측됨(2차 출처).  
  조건이 달라 직접 비교는 어렵지만, 자기회귀 모델보다 수 배 빠르다는 방향은 일관됨
- 품질: Google 공식 페이지의 Gemini Diffusion 수치는 Gemini 2.0 Flash-Lite와 비교해  
  코드(LiveCodeBench, MBPP)와 수학(AIME 2025)은 비슷하거나 약간 높고,  
  지식과 추론(GPQA Diamond 40.4% 대 56.5%, Global MMLU Lite 69.1% 대 79.0%)은 뚜렷이 낮음.  
  Mercury 2.5 역시 "비용 최적화 모델(GPT-5.6 Luna Low, Gemini 3.5 Flash-Lite, Claude Haiku 4.5)과  
  비슷한 수준"이라고 밝힘. 즉 현재 dLLM의 자리는 "최상위 품질"이 아니라 "빠르고 싼 등급"임
- 학습 방법의 전환: LLaDA2.0은 밑바닥부터 학습하지 않고, 이미 학습된 자기회귀 모델을  
  3단계(블록 크기 확대 → 전체 확산 → 블록 축소) 과정으로 확산 모델로 변환함.  
  "AR 모델의 지식을 물려받으면서 병렬 생성 장점을 얻는" 방식이 100B 규모에서 가능함을 보임
- 두 방식의 결합: NVIDIA의 Nemotron-Labs-Diffusion은 한 모델이 자기회귀, 확산, 자기추측(확산이 초안을  
  쓰고 자기회귀가 검증) 세 가지 방식으로 동작함. 8B 모델이 Qwen3-8B 대비 비슷한 정확도에서  
  한 번의 계산당 6배 많은 토큰을 내고, GB200 GPU에서 4배 높은 처리량을 보고함
- 연구 규모: 공개 논문 목록(Awesome-Diffusion-LLM)은 2026년 6 ~ 8월 석 달간 논문 169편이 추가되었다고 밝힘.  
  대표 서베이(arXiv 2508.10875)는 2026-06에 3판으로 갱신됨.  
  2026-05에는 LLaDA 계열 전용 오픈소스 서빙 엔진(dlmserve)도 나옴

#### 아직 풀리지 않은 문제

| 문제 | 내용 | 대응 연구 |
|------|------|-----------|
| 병렬 디코딩 품질 저하 | 여러 토큰을 동시에 확정할 때 "토큰끼리 독립"이라 가정하므로 서로 의존이 강한 과제에서 품질이 급락함 | ParallelBench(ICLR 2026)가 벤치마크로 입증, 신뢰도 기반 선택 디코딩(Fast-dLLM) |
| KV 캐시 적용 어려움 | 양방향 어텐션이라 자기회귀식 캐시를 그대로 못 씀 | 블록 단위 근사 캐시(Fast-dLLM), IO 인식 캐시(Flash-dLLM) |
| 출력 길이 고정 | 완전 병렬 확산은 생성 길이를 미리 정해야 함 | 블록 확산(블록 안은 병렬, 블록 간은 순차) |
| 환각 양상이 다름 | 자기회귀와 다른 실패 패턴이 보고됨(arXiv 2604.10556) | 전용 평가셋 연구 진행 중 |
| 독립 검증 부족 | 속도 수치 대부분이 제조사 자체 측정임 | 서드파티 측정이 늘고 있으나 조건이 제각각임 |

### 2.2 상태공간 모델(SSM)과 선형 어텐션 하이브리드

#### 원리

쉬운 비유: 어텐션은 "지금까지 읽은 모든 문장을 책상에 펼쳐 놓고 매번 다시 훑는" 방식임.  
SSM과 선형 어텐션은 "크기가 정해진 수첩에 요약을 갱신해 가며 읽는" 방식임.  
수첩 크기가 늘지 않으므로 문맥이 길어져도 비용이 일정하지만, 세세한 기억은 약해짐.  
그래서 대부분의 층을 수첩 방식으로 바꾸고, 일부 층만 어텐션을 남기는 「하이브리드」가 표준이 됨.

#### 주요 모델

| 모델 | 주체 | 시점 | 구조 |
|------|------|------|------|
| Qwen3-Next 80B-A3B | Alibaba Qwen | 2025-09 | Gated DeltaNet 3층 : 어텐션 1층 반복(48층 중 36 : 12) |
| Kimi Linear | Moonshot AI | 2025-10 | Kimi Delta Attention 20층 : MLA 7층 |
| Nemotron 3 Nano | NVIDIA | 2025-12 | 52층 중 Mamba-2 23, MoE 23, 어텐션 6 |
| Mamba-3 | CMU, Princeton, Together AI 등 | 2026-03 | ICLR 2026 채택, Mamba-2의 절반 상태 크기로 같은 성능 |
| Nemotron 3 Super | NVIDIA | 2026-04 | 120B(활성 12B) Mamba-어텐션-MoE 하이브리드, 최대 1M 문맥 |
| Qwen3.5 | Alibaba Qwen | 2026 | Qwen3-Next의 3 : 1 패턴 계승(2차 출처) |

#### 확인된 사실

- 비율의 수렴: 서로 다른 회사의 모델이 모두 "값싼 층 3개에 어텐션 1개" 근처로 수렴함.  
  어텐션을 완전히 없애면 긴 범위의 정확한 되찾기(바늘 찾기)가 약해지기 때문임
- 상태공간 모델 자체의 발전: Mamba-3는 새로운 이산화 방식, 복소수 상태, 다입력 다출력(MIMO) 구조로  
  1.5B 규모에서 Gated DeltaNet 대비 평균 0.6 ~ 1.8점 높은 정확도를 보고함
- 운영 단계 진입: NVIDIA Nemotron 3는 Nano(30B-A3B), Super(100B급), Ultra(500B급) 세 크기로  
  하이브리드 구조를 상용 수준 모델 계열 전체에 적용함
- 변환 연구: 이미 학습된 어텐션 모델을 Mamba 계열이나 선형 어텐션으로 바꾸는 "증류" 연구가  
  2026년에 활발함(Taylor-Calibrate, 하이브리드 서빙용 상태 압축 등)

### 2.3 재귀형 소형 추론 모델 (HRM, TRM)

#### 원리

쉬운 비유: 큰 모델이 "한 번에 긴 답을 쓰는" 대신, 아주 작은 모델이 "같은 답안을 여러 번 고쳐 쓰는" 방식임.  
매개변수(지식의 양)보다 "반복해서 다듬는 계산 구조"가 퍼즐형 추론에 효과가 있다는 것을 보임.

#### 확인된 사실

- HRM(Hierarchical Reasoning Model, 2025년 상반기): 서로 다른 속도로 도는 두 개의 작은 신경망으로 구성.  
  2,700만 매개변수로 ARC-AGI-1 40.3%
- TRM(Tiny Recursive Model, 2025-10): 2층짜리 신경망 하나(약 700만 매개변수)로 ARC-AGI-1 45%,  
  ARC-AGI-2 8%. 저자는 DeepSeek R1, o3-mini, Gemini 2.5 Pro보다 높은 점수를 0.01% 미만의  
  매개변수로 냈다고 밝힘. 단, 논문 저자는 1명이며 LLM 비교 실험의 세부가 부족하다는 비판이 있음
- ARC Prize 2025 기술 보고서(2026-01): 참가 1,455팀, ARC-AGI-2 비공개 평가 최고점 24%.  
  2025년의 핵심 주제를 "정제 루프(refinement loop)의 등장"으로 규정함.  
  사전학습 없는 약 700만 매개변수 신경망이 경쟁력 있는 성능을 냈다고 명시함.  
  다만 TRM 계열은 대회 계산량 제한을 훨씬 넘겨 공개 평가에서 약 7.8%에 그쳤다는 지적도 있음
- 후속 연구: TRM에 Mamba-2를 결합한 변형(2026-02), 확률적 TRM(2026-05), HRM의 동역학 분석(2026-03)이 나옴

#### 한계

- 퍼즐(격자 변환)에 특화된 결과이며, 자연어 과제로 넓어진 증거는 아직 없음
- 과제마다 따로 학습하는 방식이라 "범용 모델"과는 성격이 다름

### 2.4 세계 모델과 JEPA

#### 원리

쉬운 비유: LLM은 "다음 단어"를 맞히도록 배우지만, JEPA(Joint Embedding Predictive Architecture)는  
"다음 장면의 핵심 특징"을 맞히도록 배움. 바닥 무늬 같은 사소한 세부를 그려내는 데 힘을 쓰지 않고,  
"공이 어디로 갈지" 같은 요약된 표현 공간에서 예측함.

#### 확인된 사실

- Yann LeCun은 2025-11 Meta를 떠나며 "LLM에만 집중하면 막다른 길에 이른다"고 밝힘
- 2025-12 파리에 AMI Labs(Advanced Machine Intelligence)를 설립, 2026-03 시드 라운드로 10억 3천만 달러를  
  조달함(Bezos Expeditions, Nvidia, 삼성전자 등 참여). 약 5년간은 판매 제품 없이 연구 조직으로 운영 예정
- 2026-03 LeWorldModel(약 1,500만 매개변수 JEPA) 논문, 2026-05 LeJEPA의 "선형 식별 가능성" 증명 논문 발표.  
  단, 증명은 잠재 변수가 가우시안이고 전이가 정상 가산 잡음일 때로 한정됨(2차 출처)
- 2026-10 현재 배포된 제품은 없음

#### 위치

- 텍스트 에이전트를 대체하려는 흐름이 아니라, 로봇과 물리 세계 이해를 겨냥한 흐름임
- "스케일링만으로 안 된다"는 문제의식은 공유하지만, 해법의 방향은 dLLM, SSM과 다름

### 2.5 트랜스포머 자체의 진화 (대체가 아닌 보강)

새 구조와 별개로 트랜스포머 안에서도 비용을 줄이는 기술이 표준이 됨.

- 전문가 혼합(MoE): 전체 매개변수 중 일부만 활성화. 위 표의 대부분 모델이 채택
- 다중 토큰 예측(MTP)과 추측 디코딩: 한 번에 여러 토큰 후보를 내고 검증. Nemotron 3 Super와 Ultra가 채택
- 저정밀 학습(NVFP4): Nemotron 3 Super와 Ultra가 4비트 부동소수점으로 학습
- 데이터 품질: Stanford AI Index 2026은 OLMo 3.1 Think 32B가 Grok 4 대비 약 90배 적은 매개변수로  
  여러 벤치마크에서 비슷한 결과를 냈다고 밝힘. 구조가 아니라 데이터 정제의 힘임
- 투명성 저하: 같은 보고서는 최상위 모델일수록 학습 코드, 데이터 규모, 매개변수 수를 숨긴다고 지적함.  
  즉 "프런티어 모델이 어떤 구조인지"는 외부에서 확인할 수 없음

## 3. 미래 전망

### 3.1 전문가 발언 (사실)

| 인물 | 시점 | 요지 |
|------|------|------|
| Ilya Sutskever | 2025-11-25 Dwarkesh 인터뷰 | 2012 ~ 2020은 연구의 시대, 2020 ~ 2025는 스케일링의 시대, 이제 "큰 컴퓨터를 가진 연구의 시대"로 돌아감 |
| Ilya Sutskever | 같은 인터뷰 | 모델은 사람보다 "극적으로 나쁘게 일반화"함. 특정 구조를 지목하지 않고 "빠진 학습 원리"가 있다고 봄. 사람처럼 배우는 시스템까지 5 ~ 20년 |
| Yann LeCun | 2025-11 Meta 퇴사 시 | LLM 집중은 막다른 길. 세계 모델은 제품까지 약 5년 |
| ARC Prize 재단 | 2026-01 기술 보고서 | 2025년의 주제는 정제 루프. 프런티어 추론은 "지식 범위"에 크게 묶여 있음. ARC-AGI-3는 탐색, 계획, 기억을 요구하는 상호작용 과제로 전환 |

### 3.2 클로니의 전망 (의견)

#### 단기: 2026년 하반기 ~ 2027년

- dLLM은 "속도가 곧 돈인 자리"부터 들어옴. 코드 자동완성, 에이전트의 도구 호출 루프, 대량 분류와 추출이 그 자리임.  
  품질은 비용 최적화 등급(Flash-Lite, Haiku급)과 겨루는 수준에 머물고, 최상위 추론 모델을 대체하지는 못함
- "자기회귀 대 확산"의 이분법은 사라짐. AR 모델을 확산으로 변환(LLaDA2.0), 블록 확산, 3모드(Nemotron)처럼  
  두 방식을 한 모델 안에서 섞어 쓰는 것이 표준 레시피가 됨
- 하이브리드(값싼 층 3 : 어텐션 1)는 오픈 가중치 모델의 기본값이 됨. 1M 토큰급 문맥 서빙 단가가 내려감

#### 중기: 2028년 ~ 2030년

- 프런티어 모델의 내부 구조는 비공개가 유지되어, "트랜스포머가 대체되었는가"는 외부에서 확인하기 어려움.  
  오픈 모델에서 하이브리드와 혼합 디코딩이 표준이 되었는지로 간접 판단하게 됨
- 재귀형 추론 구조는 범용 모델을 대체하기보다, 계획과 퍼즐형 과제를 맡는 "모듈"로 큰 모델 옆에 붙을 가능성이 큼
- 세계 모델은 로봇과 물리 시뮬레이션에서 먼저 성과를 내고, 텍스트 에이전트 영역에는 늦게 들어옴
- Ilya가 말한 "빠진 일반화 원리"가 발견된다면 그것이 가장 큰 변수이지만, 현재 어떤 후보도 입증되지 않음

#### 불확실 요소

- dLLM 속도 수치는 대부분 제조사 측정이며, 독립 측정은 조건이 제각각임
- 병렬 디코딩은 토큰 사이 의존이 강한 과제(순서가 중요한 리스트 조작, 긴 논증)에서 품질이 급락함
- 하이브리드 모델은 긴 범위의 정확한 되찾기(바늘 찾기)에서 어텐션 모델보다 약하다는 보고가 있음
- 확산 모델의 환각 패턴이 자기회귀와 달라 기존 가드레일 평가셋이 그대로 통하지 않을 수 있음

### 3.3 Agentic AI 설계에 주는 시사점

- 모델 선택 축에 「구조」를 추가함. 같은 품질 등급이면 지연과 단가 기준으로 dLLM과 하이브리드를 후보에 넣음
- 평가셋에 병렬 디코딩 취약 과제를 넣음. ParallelBench가 보인 대로 일반 코드와 수학 벤치마크는 이 결함을 놓침
- 서빙 계층을 포트와 어댑터로 격리함. 프롬프트 캐시, 추측 디코딩처럼 KV 캐시를 전제한 코드는  
  dLLM과 하이브리드에서 전제가 깨질 수 있음. 모델 교체가 응용 계층에 번지지 않게 함
- 모델 교체는 되돌릴 수 있게 함. 새 구조 모델은 환각 양상이 달라 운영 중 롤백 경로가 필요함
- "빠른 모델로 초안, 강한 모델로 검증" 구조는 Nemotron의 자기추측 방식이 모델 안에서 하는 일을  
  에이전트 워크플로우 수준에서 하는 것임. 두 층에서 같은 아이디어가 쓰이므로 역할 중복을 설계 시 점검함

## 4. 결론

- 연구 현황: 확산 언어 모델은 100B 규모 오픈소스(LLaDA2.0)와 초당 1,000 토큰급 상용(Mercury 2.5)에 도달했고,  
  SSM 하이브리드는 NVIDIA, Alibaba, Moonshot의 주력 오픈 모델 구조가 됨. 재귀형 소형 모델과 세계 모델은 연구 단계임
- 공통 흐름: "트랜스포머를 버린다"가 아니라 "트랜스포머와 섞는다"로 수렴함.  
  AR→확산 변환, 3모드 디코딩, 3 : 1 하이브리드가 모두 그 예임
- 전망: 1 ~ 2년 안에 비용 최적화 등급에서 새 구조가 보편화되고, 최상위 품질 등급은 여전히 자기회귀 계열이 지킬 가능성이 큼.  
  근본적 전환은 "일반화 원리"의 발견에 달려 있으며, 이는 아직 아무도 입증하지 못함

## 출처

### 확산 언어 모델

- [A Survey on Diffusion Language Models (arXiv 2508.10875, v3 2026-06)](https://arxiv.org/abs/2508.10875)
- [Awesome-Diffusion-LLM 논문 목록 (GitHub)](https://github.com/AIDASLab/Awesome-Diffusion-LLM)
- [LLaDA: Large Language Diffusion Models (arXiv 2502.09992)](https://arxiv.org/abs/2502.09992)
- [LLaDA2.0: Scaling Up Diffusion Language Models to 100B (arXiv 2512.15745)](https://arxiv.org/abs/2512.15745)
- [LLaDA2.X 저장소 (inclusionAI, GitHub)](https://github.com/inclusionAI/LLaDA2.X)
- [Mercury: Ultra-Fast Language Models Based on Diffusion (arXiv 2506.17298)](https://arxiv.org/abs/2506.17298)
- [Introducing Mercury 2.5 (Inception Labs 공식 블로그)](https://www.inceptionlabs.ai/blog/introducing-mercury-2-5)
- [Gemini Diffusion (Google DeepMind 공식 페이지)](https://deepmind.google/models/gemini-diffusion/)
- [DiffusionGemma 보도 (The Decoder, 2차 출처)](https://the-decoder.com/googles-new-open-model-diffusiongemma-generates-text-from-noise-instead-of-word-by-word/)
- [Nemotron-Labs-Diffusion: Tri-Mode Language Model (arXiv 2607.05722)](https://arxiv.org/abs/2607.05722)
- [ParallelBench: Trade-offs of Parallel Decoding in Diffusion LLMs (arXiv 2510.04767, ICLR 2026)](https://arxiv.org/abs/2510.04767)
- [Fast-dLLM: KV Cache and Parallel Decoding (arXiv 2505.22618)](https://arxiv.org/abs/2505.22618)
- [Flash-dLLM: IO-Aware KV Caching (arXiv 2609.26796)](https://arxiv.org/abs/2609.26796)
- [Lost in Diffusion: Hallucination Patterns in dLLMs (arXiv 2604.10556)](https://arxiv.org/pdf/2604.10556)
- [Mercury 2.5 실측 논평 (BenchLM, 2차 출처)](https://benchlm.ai/blog/posts/mercury-2-5-calls-you-dont-see)

### 상태공간 모델과 하이브리드

- [Mamba-3: Improved Sequence Modeling using State Space Principles (arXiv 2603.15569, ICLR 2026)](https://arxiv.org/abs/2603.15569)
- [NVIDIA Nemotron 3: Efficient and Open Intelligence (arXiv 2512.20856)](https://arxiv.org/abs/2512.20856)
- [Nemotron 3 Super Technical Report (NVIDIA Research, 2026-04)](https://research.nvidia.com/labs/nemotron/files/NVIDIA-Nemotron-3-Super-Technical-Report.pdf)
- [Hybrid Attention 구조 비교 (Sebastian Raschka, LLM Architecture Gallery)](https://sebastianraschka.com/llm-architecture-gallery/hybrid-attention/)
- [LLM Research Papers: The 2026 List (Sebastian Raschka)](https://magazine.sebastianraschka.com/p/llm-research-papers-2026-part1)

### 재귀형 소형 추론 모델

- [Less is More: Recursive Reasoning with Tiny Networks (arXiv 2510.04871)](https://arxiv.org/abs/2510.04871)
- [ARC Prize 2025: Technical Report (arXiv 2601.10904)](https://arxiv.org/abs/2601.10904)
- [Tiny Recursive Reasoning with Mamba-2 Attention Hybrid (arXiv 2602.12078)](https://arxiv.org/pdf/2602.12078)
- [Probabilistic Tiny Recursive Model (arXiv 2605.19943)](https://arxiv.org/html/2605.19943v1)

### 세계 모델과 전문가 전망

- [Advanced Machine Intelligence Labs (Wikipedia)](https://en.wikipedia.org/wiki/Advanced_Machine_Intelligence_Labs)
- [Ilya Sutskever: 스케일링의 시대에서 연구의 시대로 (Dwarkesh Podcast, 2025-11-25)](https://www.dwarkesh.com/p/ilya-sutskever-2)
- [AI Index Report 2026, Chapter 1 Research and Development (Stanford HAI)](https://hai.stanford.edu/assets/files/ai_index_report_2026_chapter_1_research_development.pdf)
- [Stanford's AI Index for 2026 (IEEE Spectrum)](https://spectrum.ieee.org/state-of-ai-index-2026)
