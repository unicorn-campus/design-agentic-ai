# 미검증 설계: 배포와 되돌리기 절차서

## 배포 전 준비

1. `DEPLOYMENT_INPUTS.md`의 필수 입력 확보 여부 확인함.
2. 이미지 태그를 `{커밋식별자}-{UTC빌드시각}` 형식으로 정하고 직전 정상 태그 기록함.
3. Neo4j 운영자가 `config/neo4j/roles.cypher`를 배포 전 1회 실행함.
4. 릴리스 관리자가 아래 상태 스키마 준비 명령을 배포 전 1회 실행함.

```bash
cd src
docker compose run --rm --entrypoint python p1-sync-inquiry \
  /opt/help-desk-deploy/scripts/prepare_checkpoint.py
```

5. 추가형 스키마 변경만 먼저 반영함. 열과 색인 삭제는 다음 판으로 미룸.
6. 직전 승인 문서, 그래프, 용어사전 세대를 읽기 전용으로 1세대 보관함.
7. `docker compose config --quiet`와 배포 시험 전건 통과 여부 확인함.
8. P-1, P-2, P-3 순서로 이미지를 올리고 각 단위의 상태 확인 완료 후 다음 단위 진행함.

## 로컬 배포

```bash
cd src
export HELP_DESK_IMAGE_TAG="$(git rev-parse --short HEAD)-$(date -u +%Y%m%d%H%M%S)"
docker compose build
docker compose up -d
```

P-1만 바깥 포트 8080으로 공개함. P-2와 P-3 포트는 Compose 내부 네트워크에서만 접근 가능함.

## 단위별 되돌리기

아래 명령의 `{직전정상태그}`는 배포 전 기록한 값으로 교체함.

| 덩어리 | 되돌리기 명령 | 되돌린 뒤 확인할 것 |
|---|---|---|
| P-1 고객 문의 동기 처리 | `HELP_DESK_IMAGE_TAG={직전정상태그} docker compose up -d --no-build p1-sync-inquiry` | `/health/live`, `/health/ready`, 고객 문의 1건 |
| P-2 상담 지식 개선 배치 | `HELP_DESK_IMAGE_TAG={직전정상태그} docker compose up -d --no-build p2-knowledge-improvement-batch` | 두 상태 경로, 배치 예행 1건, 승인 대기열 |
| P-3 상담 종료 이벤트 처리 | `HELP_DESK_IMAGE_TAG={직전정상태그} docker compose up -d --no-build p3-conversation-closed-event` | 두 상태 경로, 격리된 시험 이벤트 1건 |

상태 확인이 실패하면 해당 단위 트래픽을 열지 않고 직전 태그로 다시 실행함.

## 되돌아오지 않는 변경

| 변경 | 무엇이 되돌아오지 않나 | 직전 값 1세대 보관 | 배포 전 준비 |
|---|---|:---:|---|
| 설문 발송 | 이미 외부 수신자에게 전달된 발송 | 예 | 대상 목록과 동의 참조 스냅샷 보관 |
| 승인 문서 색인 교체 | 삭제된 이전 검색 결과 | 예 | 직전 색인 세대를 읽기 전용 보관 |
| 업무 관계 그래프 적재 | 덮어쓴 이전 관계 경로 | 예 | 직전 그래프 세대 스냅샷 보관 |
| 용어사전 세대 교체 | 삭제된 이전 정규화 결과 | 예 | 직전 승인 세대 최대 7일 보관 |

CRM 쓰기는 되돌림 가능 등급임.  
승인 기록을 근거로 이전 값 복원 후 감사 로그에 복원 사실만 기록함.
삭제 대상 원문과 실제 비밀값은 감사 로그에 기록하지 않음.
