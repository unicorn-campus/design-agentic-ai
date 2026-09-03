[목표]
현재 디렉토리의 스킬과 에이젼트를 이용한 플러그인 개발
[역할]
당신은 Claude 스킬,에이젼트,플러그인에 능통한 AI 개발자임
[맥락]
기존 개발된 스킬과 에이젼트를 회사 전체에 공유하기 위해 플러그인으로 패키징 필요
[입력]
스킬/에이젼트: .claude/skills, .claude/agents
[처리]
- 현재 스킬과 에이젼트 분석 및 이해
- marketplace와 plugin 이름을 사용자에게 입력 받음: AskUserQuestion 사용하고 추천 이름 제공
- 플러그인 개발: 단일 플러그인 구조로 개발
   - `.claude-plugin` 디렉토리 하위에 marketplace.json, plugin.json 생성
   - 스킬/에이젼트 디렉토리를 루트 디렉토리 하위로 이동
   - `/{plugin}:{skill}` 형식의 슬래시 명령 지원
- README.md에 플러그인 기능, 플러그인 설치/조회/업그레이드/삭제 방법 작성
[출력]
개발된 플러그인
[제약조건]
- MUST: 
  - Claude 공식문서를 검색하여 규칙에 맞게 marketplace.json과 plugin.json 생성
  - `/{plugin}:{skill}` 형식의 슬래시 명령 지원
  - 추가 정보나 내 의사결정이 필요하면 반드시 문의
- MUST NOT:
  - 멀티 플러그인 구조로 개발하지 말 것
  - 추가 정보가 필요하면 추측하지 말고 사용자에게 요청
