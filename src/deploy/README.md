# 미검증 설계: Help Desk 패키징과 로컬 실행

실제 운영 배포 미수행 상태임. Docker 이미지 빌드와 로컬 Compose 실행 정의만 제공함.  
D-09 배포 대상 런타임 확정 전까지 전용 배포 매니페스트는 생성하지 않음.

## 개요

⑦ 물리 배치도의 실행환경 묶음 3개를 이미지 3개로 그대로 묶음.  
② 내부 관계도 구성요소 15개를 모두 대응했으며 미대응 0건임.

| 덩어리 | 포함 구성요소 | 배포 형태 | 바깥 포트 | 안쪽 포트 | 자원 최소·최대 | 어디서 정했나 |
|---|---|---|---|---|---|---|
| P-1 고객 문의 동기 처리 | Help Desk API, 동기 런타임, LLM Adapter, 규칙 처리기, 상담 위험 예측 API | 런타임 이미지 | 8080 | 8080 | 1~2개, 요청 250m·256Mi, 상한 1CPU·512Mi | ⑦ 배치도, 07 API·UI, 개발 판단(되묻기) |
| P-2 상담 지식 개선 배치 | 02:00 Scheduler, 배치 런타임, LLM Adapter, 규칙 처리기, 우선순위 예측 API | 예약 실행 가능한 이미지, 내부 API 포함 | 열지 않음 | 8081 | 1~2개, 요청 250m·256Mi, 상한 1CPU·512Mi | ⑦ 배치도, 07 API·UI, 개발 판단(되묻기) |
| P-3 상담 종료 이벤트 처리 | Event Consumer, 이벤트 런타임, LLM Adapter, 규칙 처리기, 사후 위험 예측 API | 이벤트 구독 이미지, 내부 API 포함 | 열지 않음 | 8082 | 1~2개, 요청 250m·256Mi, 상한 1CPU·512Mi | ⑦ 배치도, 07 API·UI, 개발 판단(되묻기) |

이미지를 만들지 않는 실행환경 묶음 0개임.  
이미지 3개와 이미지 없는 형태 0개의 합은 ⑦의 3개와 같음.

P-1만 호스트에 공개함. P-2와 P-3 내부 승인 API는 Compose 네트워크에서만 접근 가능함.
연결 수와 동시 실행 상한은 순서 6에서 확정한 워크플로우별 1건을  
운영 설정 기준으로 사용함.

## 이미지와 판 표시

| 이미지 | 정의 | 기본 실행 |
|---|---|---|
| `help-desk-p1` | `services/p1-sync-inquiry/Dockerfile` | P-1 API |
| `help-desk-p2` | `services/p2-knowledge-improvement-batch/Dockerfile` | P-2 내부 승인 API |
| `help-desk-p3` | `services/p3-conversation-closed-event/Dockerfile` | P-3 내부 승인 API |

판 표시는 `{커밋식별자}-{UTC빌드시각}` 형식임. `latest` 태그 사용 금지임.  
로컬 기본 태그 `local-unverified`는 운영 배포에 사용하지 않음.

Python 기반 이미지는 `python:3.12-slim`의 다중 아키텍처 다이제스트를 고정함.  
실행 사용자는 UID 10001 비관리자이며 `/var/lib/help-desk`와 `/tmp`만 쓰기 가능함.  
비밀값은 빌드 인자나 이미지 층에 넣지 않고 실행 시 환경변수로만 주입함.

## 로컬에서 띄우는 법

먼저 `common/.env.example`, `tools/.env.example`, `deploy/secrets/*/.env.example`을 같은 위치의
`.env` 파일로 복사하고 필수 값을 비밀 보관소에서 주입함.  
실제 값은 문서나 저장소에 기록하지 않음.

### Windows Git Bash

```bash
cd src
export HELP_DESK_IMAGE_TAG="$(git rev-parse --short HEAD)-$(date -u +%Y%m%d%H%M%S)"
export HELP_DESK_COMMON_ENV_FILE=./common/.env
export HELP_DESK_TOOLS_ENV_FILE=./tools/.env
export HELP_DESK_P2_CONFIG_FILE=./services/p2-knowledge-improvement-batch/.env
export HELP_DESK_P1_SECRET_FILE=./deploy/secrets/p1/.env
export HELP_DESK_P2_SECRET_FILE=./deploy/secrets/p2/.env
export HELP_DESK_P3_SECRET_FILE=./deploy/secrets/p3/.env
docker compose config --quiet
docker compose up --build
```

### Windows PowerShell

```powershell
Set-Location src
$env:HELP_DESK_IMAGE_TAG="$(git rev-parse --short HEAD)-$((Get-Date).ToUniversalTime().ToString('yyyyMMddHHmmss'))"
$env:HELP_DESK_COMMON_ENV_FILE='./common/.env'
$env:HELP_DESK_TOOLS_ENV_FILE='./tools/.env'
$env:HELP_DESK_P2_CONFIG_FILE='./services/p2-knowledge-improvement-batch/.env'
$env:HELP_DESK_P1_SECRET_FILE='./deploy/secrets/p1/.env'
$env:HELP_DESK_P2_SECRET_FILE='./deploy/secrets/p2/.env'
$env:HELP_DESK_P3_SECRET_FILE='./deploy/secrets/p3/.env'
docker compose config --quiet
docker compose up --build
```

### Linux 또는 macOS

```bash
cd src
export HELP_DESK_IMAGE_TAG="$(git rev-parse --short HEAD)-$(date -u +%Y%m%d%H%M%S)"
export HELP_DESK_COMMON_ENV_FILE=./common/.env
export HELP_DESK_TOOLS_ENV_FILE=./tools/.env
export HELP_DESK_P2_CONFIG_FILE=./services/p2-knowledge-improvement-batch/.env
export HELP_DESK_P1_SECRET_FILE=./deploy/secrets/p1/.env
export HELP_DESK_P2_SECRET_FILE=./deploy/secrets/p2/.env
export HELP_DESK_P3_SECRET_FILE=./deploy/secrets/p3/.env
docker compose config --quiet
docker compose up --build
```

상태 확인 경로는 전 서비스 공통 `GET /health/live`와 `GET /health/ready`임.  
Compose Health Check는 프로세스 생존 확인을 사용함.  
트래픽 개방 전 준비 확인을 별도로 호출함.

## 비밀값

| 키 이름 | 어디서 어디로 들어가나 | 필수 | 쓰는 덩어리 | 어디서 뽑았나 |
|---|---|:---:|---|---|
| `HELP_DESK_LLM_API_KEY` | 비밀 보관소에서 환경변수 | 예 | P-1, P-2, P-3 | 모델 설정 |
| `HELP_DESK_CHECKPOINT_URI` | 비밀 보관소에서 환경변수 | 예 | P-1, P-2, P-3 | 상태 저장 설정 |
| `HELP_DESK_CHECKPOINT_ENCRYPTION_KEY` | 비밀 보관소에서 환경변수 | 예 | P-1, P-2, P-3 | 상태 저장 설정 |
| `HELP_DESK_MASKING_SALT` | 비밀 보관소에서 환경변수 | 예 | P-1, P-2, P-3 | 가드레일 설정 |
| `HELP_DESK_C_A1_CREDENTIAL` | 비밀 보관소에서 환경변수 | 조건부 | P-1, P-2, P-3 | C-A1 커넥터 |
| `HELP_DESK_C_A2_CREDENTIAL` | 비밀 보관소에서 환경변수 | 조건부 | P-1, P-2 | C-A2 커넥터 |
| `HELP_DESK_C_A3_CREDENTIAL` | 비밀 보관소에서 환경변수 | 조건부 | P-1, P-2 | C-A3 커넥터 |
| `HELP_DESK_C_A4_CREDENTIAL` | 비밀 보관소에서 환경변수 | 조건부 | P-3 | C-A4 커넥터 |
| `HELP_DESK_C_A5_CREDENTIAL` | 비밀 보관소에서 환경변수 | 조건부 | P-3 | C-A5 커넥터 |
| `HELP_DESK_GLOSSARY_POSTGRES_DSN` | 비밀 보관소에서 환경변수 | 조건부 | P-2 | 용어사전 저장소 설정 |
| `HELP_DESK_KNOWLEDGE_RAG_DSN` | 비밀 보관소에서 환경변수 | 조건부 | P-2 | RAG 저장소 설정 |
| `HELP_DESK_KNOWLEDGE_GRAPH_PASSWORD` | 비밀 보관소에서 환경변수 | 조건부 | P-2 | GraphRAG 저장소 설정 |
| `HELP_DESK_KNOWLEDGE_GRAPH_ADMIN_USER` | 운영 비밀 보관소에서 일회성 작업 | 예 | 운영 작업 | Neo4j role 스크립트 |
| `HELP_DESK_KNOWLEDGE_GRAPH_ADMIN_PASSWORD` | 운영 비밀 보관소에서 일회성 작업 | 예 | 운영 작업 | Neo4j role 스크립트 |

관측·알림 코드에서 전송 자격 환경변수는 0개 확인함.  
D-11 대상 확정 뒤 별도 항목 추가 필요함.

## 저장소

| 저장소 | 안·밖 | 보존 기간 | 파기 주기 | 어디서 정했나 |
|---|---|---|---|---|
| S-1 승인 문서 저장소 | 런타임 밖 | 원천 승인 만료 후 최대 1일 | 일 1회 | ⑤ 보존·삭제, 개발 판단(되묻기) |
| S-2 업무 관계 그래프 | 런타임 밖 | 원천 삭제 후 최대 1일 | 일 1회 | ⑤ 보존·삭제, 개발 판단(되묻기) |
| S-3 용어사전·온톨로지 | 런타임 밖 | 현재 승인 세대와 직전 1세대, 최대 7일 | 주 1회 | ⑤ 보존·삭제, 개발 판단(되묻기) |
| S-4 체크포인트 저장소 | 런타임 밖 영속 볼륨 | W-1 600000ms, W-2 3600000ms, W-3 60000ms | 기간 경과 즉시 | D-08, ⑤ 보존·삭제, 개발 판단(되묻기) |
| S-5 이벤트 버스·격리 큐 | 런타임 밖 | 처리 완료 이벤트 7일 | 일 1회 | ⑤ 보존·삭제, 개발 판단(되묻기) |
| S-6 지식 개선 대기열 | 런타임 밖 | 승인·반려 완료 후보 30일 | 일 1회 | ⑤ 보존·삭제, 개발 판단(되묻기) |
| S-7 관측·감사 저장소 | 런타임 밖 | 감사 정책 소유 | 감사 정책 소유 | ⑥ 관측 적재처, 개발 판단(되묻기) |

⑥ 관측 적재처 3종은 모두 사내 저장소이며 국외 외부 전송 0건임.

## 보존과 파기

기본 명령은 예행만 수행하며 실제 삭제 수 0건임.

```bash
python src/deploy/jobs/retention_cleanup.py
```

미완 승인, 재개 대기, 진행 중 체크포인트는 만료 대상에서 제외함.  
회원 단위 삭제는 `subject_ref`로 체크포인트까지 함께 선별하는 인터페이스를 제공함.  
실제 삭제는 `HELP_DESK_RETENTION_DELETE_ENABLED=true`와 사람 승인 참조가 모두 있을 때만 허용함.  
01 저장 계층의 삭제 어댑터가 아직 없으므로 명령행 실제 삭제는 기본 거부함.

## 되돌리기와 배포 입력

- [되돌리기 절차서](ROLLBACK.md)
- [배포 실행 입력값](DEPLOYMENT_INPUTS.md)
- [비밀값 항목 목록](secret_inventory.json)

되돌릴 수 없는 변경은 설문 발송, 문서 색인 교체, 그래프 적재,  
용어사전 세대 교체 4종임.  
4종 모두 배포 전 직전 값 1세대 보관을 필수로 둠.

## 설계 범위 밖 값 목록

| 값 | 정한 값 | 어디서 정했나 | 왜 설계서에 없나 |
|---|---|---|---|
| 배포 형태 | P-1 런타임, P-2 예약 실행 이미지, P-3 이벤트 구독 이미지 | 개발 판단(되묻기) | ⑦ 최소화로 설계 범위 밖 |
| 런타임 규모 상한 | 최소 1, 최대 2, 요청 250m·256Mi, 상한 1CPU·512Mi | 개발 판단(되묻기) | ⑦ 최소화로 설계 범위 밖 |
| 비밀값 항목 | 14개 | 코드 환경변수와 운영 role 스크립트 | ⑦ 비밀값 주입 경로 없음 |
| 저장소 배치 | 7개 전부 런타임 밖 | 개발 판단(되묻기) | ⑦ 최소화로 설계 범위 밖 |
| 이미지 판 표시 | 커밋 식별자와 UTC 빌드 시각 | 개발 판단(되묻기) | ⑦ 최소화로 설계 범위 밖 |
| 되돌릴 수 없는 변경 | 4종, 직전 값 1세대 보관 | 개발 판단(되묻기) | ⑦ 최소화로 설계 범위 밖 |
| 중복 방지 키 | D-08 SQLite, 24시간 | 순서 4 확정값 인용 | ⑦ 최소화로 설계 범위 밖 |
| 상태 확인 경로 | `/health/live`, `/health/ready` | 07 API·UI 코드 | 포트와 경로는 07 소유 |
| 만료 삭제 시점 | ⑤ 보존·삭제 9행의 주기 | ⑤ 보존·삭제 | 보존 정책은 ⑤ 소유 |
| 상태 스키마 준비 | 릴리스 관리자 선행 1회 | 순서 1 확정값 인용 | ⑦ 최소화로 설계 범위 밖 |
| 매니페스트 파일 | `src/docker-compose.yml` | 개발 판단(되묻기) | ⑦ 최소화로 설계 범위 밖 |
| 배포 절차 | P-1, P-2, P-3 순차 확인 | 개발 판단(되묻기) | ⑦ 최소화로 설계 범위 밖 |

## 되묻기로 정한 값 목록

위 「설계 범위 밖 값 목록」 중 개발 판단 8행은 사용자 승인 기본값임.  
설계서에 되돌려 적을 자리가 없으므로 이 README를 유일한 기록으로 사용함.

## 확인필요 목록

| 확인필요 | 영향 | 확정 주체 |
|---|---|---|
| `[확인필요: 배포 대상 런타임]` | 런타임 전용 매니페스트와 비밀 객체 참조 형식 미생성 | 프로젝트 운영자 |
| `[확인필요: 관측 내보내기 대상]` | 제품별 exporter와 전송 자격 키 미생성 | 관측 운영자 |
| `[확인필요: 프론트엔드 배치 단위]` | D-04 화면이 ⑦ 실행환경 묶음에 없어 정적 호스팅 정의 미생성 | 아키텍트 |
| `[확인필요: P-2 예약 트리거 연결]` | 이미지에 Scheduler 코드는 있으나 런타임 예약 규칙 미생성 | 배포 런타임 담당자 |
| `[확인필요: P-3 이벤트 구독 연결]` | 이미지에 Consumer 코드는 있으나 메시지 브로커 구독 규칙 미생성 | 배포 런타임 담당자 |
| `[확인필요: 준비 상태 의존성 연결]` | 상태 경로는 있으나 기본 앱의 준비 Probe 주입 전 503 응답 | 07 API·UI 담당자 |
| `[확인필요: 체크포인트 삭제 어댑터]` | 예행 가능, 실제 저장소 삭제는 기본 거부 | 01 런타임 담당자 |

확인필요 7건임.
