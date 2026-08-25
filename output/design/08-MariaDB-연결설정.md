# MariaDB 로컬 연결 설정

## 1. 구성

| 항목 | 값 |
|---|---|
| 실행 방식 | Docker Compose |
| 이미지 | `mariadb:11.4` |
| 컨테이너 | `design-agentic-ai-mariadb` |
| 호스트 | `127.0.0.1` |
| 포트 | `3307` |
| 데이터베이스 | `agentic_ai` |
| 사용자 | `agentic` |
| 문자 집합 | `utf8mb4` |
| 데이터 볼륨 | `design-agentic-ai-mariadb-data` |

비밀번호는 Git 추적 대상이 아닌 프로젝트 루트의 `.env.mariadb`에 저장함.  
공유용 기본 형식은 `.env.mariadb.example`에서 확인 가능함.

## 2. 실행

프로젝트 루트에서 아래 명령 실행함.

```bash
docker compose \
  --env-file .env.mariadb \
  -f infra/mariadb/compose.yaml \
  up -d
```

상태 확인 명령임.

```bash
docker compose \
  --env-file .env.mariadb \
  -f infra/mariadb/compose.yaml \
  ps
```

## 3. VS Code Database Client 연결

Database Client에서 다음 값으로 새 연결 생성함.

| 입력 항목 | 값 |
|---|---|
| 연결 유형 | MariaDB |
| 이름 | `Local MariaDB` |
| 호스트 | `127.0.0.1` |
| 포트 | `3307` |
| 사용자 | `agentic` |
| 비밀번호 | `.env.mariadb`의 `MARIADB_PASSWORD` 값 |
| 데이터베이스 | `agentic_ai` |
| SSL | 사용 안 함 |

연결은 VS Code Database Client의 전역 로컬 설정으로 저장함.  
비밀번호 원본은 Git 추적 대상이 아닌 `.env.mariadb`에서 관리함.

## 4. 연결 검증

컨테이너 내부 검증 명령임.

```bash
docker exec design-agentic-ai-mariadb \
  mariadb -uagentic -p agentic_ai
```

접속 후 아래 SQL로 서버와 현재 데이터베이스 확인함.

```sql
SELECT VERSION() AS version, DATABASE() AS database_name;
```

VS Code에서는 `Local MariaDB` 연결을 연 뒤 동일 SQL 실행함.

### 실제 검증 결과

검증일은 2026-08-25임.

| 검증 항목 | 결과 |
|---|---|
| 컨테이너 상태 | `healthy` |
| 서버 버전 | `11.4.13-MariaDB-ubu2404` |
| 현재 데이터베이스 | `agentic_ai` |
| 데이터베이스 문자 집합 | `utf8mb4` |
| VS Code 연결 이름 | `Local MariaDB` |
| VS Code 연결 상태 | 연결 트리 확장 및 서버 메타데이터 조회 성공 |

## 5. 중지와 재시작

중지 명령임. 데이터 볼륨은 유지됨.

```bash
docker compose \
  --env-file .env.mariadb \
  -f infra/mariadb/compose.yaml \
  down
```

재시작은 2절의 `up -d` 명령 사용함.

볼륨까지 삭제하는 `down -v`는 데이터가 제거되므로 사용 전 별도 확인 필요함.
