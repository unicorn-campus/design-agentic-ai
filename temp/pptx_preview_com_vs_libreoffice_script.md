# PPT 스크립트: PowerPoint 크래시 원인과 LibreOffice 미리보기 전환

- 형식: 16:9, 4장, 모든 그림은 편집 가능한 도형(사각형·화살표·표)으로 구성  
- 경로 표기(breadcrumb): `PPT 작성 › 미리보기 렌더링`

---

## 01. PowerPoint는 컴퓨터에 하나만 뜸 (패턴 A 변형: 구조도 + 문제 카드)

- 리드문: 미리보기 스크립트가 사용자가 쓰던 PowerPoint와 같은 프로세스를 함께 썼음
- 좌측 구조도
  - 사용자 박스 → POWERPNT.EXE(1개) 안의 "사용자 창"
  - COM 스크립트 박스(render.ps1, 에이전트가 즉석 생성) → POWERPNT.EXE 안의 "숨은 미리보기 창"
- 우측 문제 카드 3개
  1. 같은 프로세스에 붙음 → 사용자 작업과 섞여 멈춤
  2. 끝날 때 `Quit()` → 사용자 창까지 함께 닫힘
  3. 시간 초과로 중간에 끊김 → 숨은 PowerPoint가 남아 다음 실행이 먹통
- 하단 강조: 최근 14일 강제 종료 기록(이벤트 1000) 0건 → 스스로 죽기보다 스크립트가 닫았을 가능성이 큼

## 02. 창이 갑자기 닫히는 순서 (시퀀스 다이어그램)

- 리드문: 스크립트는 처음에 한 번만 확인하고, 마지막에 PowerPoint 전체를 닫음
- 가로 3줄(스크립트 / POWERPNT.EXE / 사용자) × 세로 4단계
  1. 스크립트: "PowerPoint 켜져 있나?" → 아니오
  2. 스크립트: 숨은 PowerPoint 실행 → POWERPNT.EXE 시작
  3. 사용자: 결과 PPT 열기 → 같은 프로세스에 창 추가
  4. 스크립트: `Quit()` → 프로세스 종료 → 사용자 창이 갑자기 닫힘
- 하단 강조: 1단계 확인 결과를 4단계까지 믿어서 생긴 문제

## 03. 바뀐 방식: LibreOffice 미리보기 (패턴 D 변형: 흐름도 + 비교표)

- 리드문: PowerPoint를 띄우지 않고, 별도 프로그램으로 PDF를 거쳐 그림을 만듦
- 흐름도: 덱.pptx → LibreOffice(headless) → 덱.pdf → PyMuPDF → slide-N.png
  - LibreOffice 아래 메모: 전용 임시 프로필, 180초 상한
- 비교표(이전 COM / 이후 LibreOffice)
  - 사용자 창과의 관계: 같은 프로세스 공유 / 따로 실행
  - 끝낼 때: `Quit()`가 전부 닫음 / 변환 프로세스만 끝남
  - 멈췄을 때: 숨은 프로세스가 남음 / 180초 뒤 실패로 끝냄
- 실행 명령: `python scripts/render-pptx.py 덱.pptx --out 출력폴더`

## 04. 바꾼 것과 확인한 것 (패턴 D: 표 + 검증 카드)

- 좌측 표: 파일 / 바꾼 내용
  - `scripts/render-pptx.py`: 새 미리보기 스크립트
  - `references/pptx-guide.md`: 미리보기 절 추가, COM 금지
  - `AGENTS.md`: 사용 규칙 + 교훈 [HIGH]
- 우측 검증 카드 4개
  - 실제 덱 2개 변환 성공(3장·1장, exit 0)
  - 열려 있던 사용자 PowerPoint 창 그대로 유지
  - 변환 뒤 남은 soffice 프로세스 0개
  - 한글(Pretendard)·표·도형 정상 표시
- 하단 메모: LibreOffice 미리보기는 PowerPoint와 줄바꿈이 조금 다를 수 있음
