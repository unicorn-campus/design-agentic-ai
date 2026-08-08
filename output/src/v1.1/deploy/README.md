# 미검증 설계 — Docker 로컬 패키징·배포

실제 운영 배포는 수행하지 않았으며 Docker Compose 문법·로컬 이미지 빌드·예행 작업만 검증 대상임.  
오케스트레이션 제품과 관측 백엔드 제품은 미확정 상태로 유지함.

## 배포 단위

| 단위 | 포함 구성요소 | 형태 | 내부 포트 | 로컬 노출 | 이미지 |
|------|-------------|------|----------:|----------:|--------|
| D-1 회원 서비스 | 인증·프로파일·식이제한·구독 상태 | 런타임 이미지 | 8090 | 8090 | `lunchpick/member-service` |
| D-2 추천·이력 서비스 | 추천·기록·피드백·인사이트 | 런타임 이미지 | 8091 | 8091 | `lunchpick/recommendation-history-service` |
| D-3 결제 서비스 | 구독 결제·정기 결제·해지 | 런타임 이미지 | 8092 | 8092 | `lunchpick/payment-service` |
| D-4 프론트엔드 | 모바일 웹·정적 자원 | 운영 정적 호스팅·로컬 정적 이미지 | 해당 없음 | 8080 | `lunchpick/frontend` |
| D-5 일일 학습 배치 | 03:00 학습·보존 대상 예행 | 런타임 이미지 | 8093 예약 | 노출 없음 | `lunchpick/daily-learning-batch` |

백엔드 공통 Dockerfile을 `APP_PORT`별로 4회 빌드하므로 이미지 판은 4개로 분리됨.  
프론트엔드는 `pnpm build` 결과 `dist/`만 최종 정적 이미지에 포함함. 운영에서는 CDN 정적 호스팅으로 교체 필요.

## 로컬 실행

`.env.example`을 `.env`로 복사한 뒤 로컬 PostgreSQL 비밀번호만 안전하게 주입함.  
실물 API 키는 Mock 판에 넣지 않음.

### Windows PowerShell

```powershell
Set-Location output\src\v1.1
Copy-Item .env.example .env
# .env의 LUNCHPICK_POSTGRES_PASSWORD를 로컬 비밀값으로 채움
docker compose config --quiet
docker compose build
docker compose up -d
docker compose ps
```

### Windows GitBash

```bash
cd output/src/v1.1
cp .env.example .env
# .env의 LUNCHPICK_POSTGRES_PASSWORD를 로컬 비밀값으로 채움
docker compose config --quiet
docker compose build
docker compose up -d
docker compose ps
```

### Linux/macOS

```bash
cd output/src/v1.1
cp .env.example .env
# .env의 LUNCHPICK_POSTGRES_PASSWORD를 로컬 비밀값으로 채움
docker compose config --quiet
docker compose build
docker compose up -d
docker compose ps
```

배치 예행은 `docker compose --profile jobs run --rm daily-learning-batch`로 별도 실행함.  
기본 Compose 기동에서 배치가 자동 실행되지 않으며 실제 삭제는 코드에서 기본 거부됨.

## 비밀값 주입

`.env.example`의 첫 15개 `LUNCHPICK_*` 키가 설계서 K-01 ~ K-15와 순서대로 대응함.  
예시 파일의 값은 모두 비어 있으며 이미지 빌드 인자에 비밀값을 넣지 않음.

| 범주 | 경로 | 원칙 |
|------|------|------|
| 로컬 | `.env` → Compose 환경변수 | `.env` 저장소 제외 |
| 운영 | 플랫폼 비밀 객체 → 컨테이너 실행 환경 | 제품 확정 전 인터페이스만 유지 |
| 파일형 자격 | 비밀 파일 마운트 | 이미지 층·매니페스트 평문 금지 |
| OTLP | 주소·인증 헤더 환경변수 | 제품 이름 비고정 |

## 저장소·보존

| 저장소 | 배치 | 보존·파기 상태 |
|--------|------|----------------|
| S-1 회원 | 컨테이너 밖 | 기간 미확정·컬럼 파기 보류 |
| S-2 위치 | 컨테이너 밖 | 6개월 만료 대상 예행 가능 |
| S-3 이력 | 컨테이너 밖 | 무료 30일·프리미엄 무기한 구분 |
| S-4 취향 벡터 | 컨테이너 밖 | 기간 미확정·직전 1세대 보관 필요 |
| S-5 추천 캐시 | 컨테이너 밖 | TTL 미확정 |
| S-6 감사 로그 | 컨테이너 밖·분리 | 6개월·보호 대상은 실행 주체 삭제 금지 |
| S-7 결제 | 컨테이너 밖 | 실패 이력 7일·본체 기간 미확정 |

핸들 보관 위치는 해당 없음. MCP 서버와 A2A가 현재 범위에서 제외되었기 때문임.

## Context7 확인 결과

- Docker 다단계 빌드에서 명명된 스테이지와 `COPY --from` 사용 확인
- 비밀값의 `ARG`·`ENV` 빌드 주입 금지와 실행 시 주입 확인
- Compose의 환경변수·파일 기반 비밀 주입 방식 확인
- `HEALTHCHECK` 간격·타임아웃·시작 유예·재시도 문법 확인

## 실제 로컬 검증 결과

2026-08-08 기준 아래 결과를 실제 명령으로 확인함.

| 검증 | 결과 |
|------|------|
| `docker compose --profile jobs build` | 애플리케이션 이미지 5개 빌드 성공 |
| 컨테이너 사용자 | 백엔드 4개 `10001:10001` · 프론트 `nginx` |
| PostgreSQL | `postgres:18-alpine` 상태 `healthy` |
| 프론트 정적 응답 | `http://127.0.0.1:8080/index.html` 200 |
| 프론트 API 프록시 | `http://127.0.0.1:8080/api/v1/profile` 200 |
| 백엔드 상태 확인 | 8090·8091·8092의 `/health` 모두 200 |
| 보존 작업 예행 | 검사 4건 · 만료 1건 · 보호 1건 · 실제 삭제 0건 |
| 비밀값 검사 | 이미지 층 0건 · 매니페스트 원문 0건 · 실행 로그 0건 |

검증에는 일회성 로컬 비밀번호를 프로세스 환경으로만 주입했으며 파일·이미지·로그에 저장하지 않음.

## 되돌리기·실행 입력

- [되돌리기 절차](ROLLBACK.md)
- [배포 실행 입력값](DEPLOY_INPUTS.md)

## `[확인필요]` 목록 — 11건

| # | 항목 | 막히는 것 |
|:-:|------|----------|
| 1 | 운영 컨테이너 오케스트레이션 제품 | 제품별 매니페스트·오토스케일 배포 |
| 2 | 관측 백엔드 제품 | 실제 OTLP 전송 검증 |
| 3 | 벡터 인덱스 제품 | S-4 연결·풀 상한 검증 |
| 4 | 비밀 저장소·이미지 저장소 | 운영 비밀 주입·이미지 푸시 |
| 5 | 푸시·알림톡 제공자 | 발송 자격 K-13 구체화 |
| 6 | S-1·S-4·S-5·S-7 보존 기간 | 실제 파기 조건 |
| 7 | 위치정보 보호 책임자 | 위치 파기 승인·감사 확인 |
| 8 | 배치 실행 창·슬롯 잠금 수단 | 두 배치 순차 실행 보장 |
| 9 | 감사 로그 일 발생량·레코드 크기 | 6개월 저장 용량 산정 |
| 10 | 서비스별 FastAPI 라우트 격리 | 공통 앱 이미지의 최소 노출 검증 |
| 11 | `/health/live`·`/health/ready` 분리 | 현재 단일 `/health`만 있어 준비 전 트래픽 차단 검증 불가 |
