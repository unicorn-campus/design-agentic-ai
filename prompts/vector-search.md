[목표]
기존 개발된 RAG Indexer와 Retriever를 LangChain과 LangGraph를 사용하여 재개발

[역할]
클로니가 팀원들과 협업하여 수행

[맥락]
- 내 상황: 강사로서 LangChain 기반의 RAG 예제를 제공하고자 함
- 독자: 교육생
[입력]
기존 LangChain을 사용하지 않고 개발한 소스: hybrid-ai-lab/s2.3, hybrid-ai-lab/s3.1~s3.3

[처리]
- 기존 개발한 소스를 분석 및 이해 
- 개발 계획 수립 및 사용자 승인
  - 워크플로우를 Mermaid Script로 작성 및 사용자 승인 요청
  - 각 노드별 개발 계획서 작성
  - 개발 계획서 사용자 승인 받기
- Indexer 개발 
  - 앱 개발
  - 테스트 및 버그 픽스
  - README.md 작성: 개요, 디렉토리 구조, 가상환경 설정, 실행 방법
- Retriever 개발
  - 앱 개발
  - 테스트 및 버그 픽스
  - README.md 작성: 개요, 디렉토리 구조, 가상환경 설정, 실행 방법
  
[출력]
- Indexer: hybrid-ai-lab/vector/indexer/{소스, requirements.txt, README.md}
- Retriever: hybrid-ai-lab/vector/retriever/{소스, requirements.txt, README.md}

[제약조건]
- MUST: 
  - 추가 정보나 내 의사결정이 필요하면 반드시 나에게 요청
  - Layered Architecture로 개발
  - LangChain 공통 
    - 프롬프트는 시스템 프롬프트와 유저 프롬프트 명확히 분리
    - LangGraph로 단일 MAS 워크플로우 구현  
    - 노드 간 데이터 공유는 StateGraph의 State(Reducer)로 구현
    - 세션 체크포인트(중단 복구·재개)로 SqliteSaver(로컬파일) 사용
    - Output Parser 대신 Structured Output 사용
    - LCEL 체인 실행 방식 선택
      - UI 스트리밍 + 병렬 도구 호출 → 비동기 스트리밍(astream)
      - UI 스트리밍만 필요 → 동기 스트리밍(stream)
      - 배치·백그라운드 처리 → 비동기(ainvoke)
      - 단발 검증·스크립트 → 동기(invoke)
  - LLM 인터페이스 
    - Model: Config에 사용할 모델 제공자를 지정하고 모델 제공자별 모델은 아래 사용
      - Claude: Opus 5 사용
      - OpenAI: GPT 5.6-Sol 사용
      - Groq LPU: OpenAI gpt-oss-120b
    - 기본 파라미터: timeout 30초, 429 응답 시 지수 백오프 재시도 2회
- MUST NOT
  - 추측하지 말고 입력 소스에 기반하여 개발
- 완료조건
  - 모든 출력물 정상 생성
  - 테스트 통과 및 정상 작동 확인
