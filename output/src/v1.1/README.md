# 런치픽 v1.1

`prompts/develop` 9종을 기준으로 만든 Python 3.12 · LangGraph · FastAPI · React/TypeScript 구현임.  
화면은 런치픽 UI/UX 프로토타입 10종의 구조·디자인 토큰·상호작용을 React로 이전함.

## 구성

| 경로 | 책임 |
|------|------|
| `common/` | 상태·설정·PostgreSQL 체크포인터·데이터·지식·가드레일·관측 |
| `services/flow/` | LangGraph 90노드·분기·반복 상한·중단·재개 |
| `services/api/` | FastAPI REST·SSE·OpenAPI·승인 경계 |
| `toolkit/` | 외부 커넥터·최소 권한·재시도·멱등성·승인 게이트 |
| `frontend/` | React + TypeScript + Vite 모바일 웹 10화면 |
| `tests/eval/` | 골든셋 34문항·대역/실물 분리 평가 실행기 |
| `deploy/` | Docker 이미지·Compose·보존 예행·되돌리기 절차 |

## 빠른 실행

### 로컬 개발

```powershell
Set-Location output\src\v1.1\services
uv sync --extra dev
uv run uvicorn api.main:app --host 127.0.0.1 --port 8000
```

새 터미널에서 프론트엔드 실행 필요함.

```powershell
Set-Location output\src\v1.1\frontend
pnpm install --frozen-lockfile
pnpm dev
```

- 화면: `http://127.0.0.1:5173/#login`
- API 문서: `http://127.0.0.1:8000/docs`
- 상태 확인: `http://127.0.0.1:8000/health`

### Docker Compose

```powershell
Set-Location output\src\v1.1
Copy-Item .env.example .env
# .env의 LUNCHPICK_POSTGRES_PASSWORD에 로컬 전용 비밀값 입력 필요함
docker compose config --quiet
docker compose build
docker compose up -d
```

Docker 프론트엔드는 `http://127.0.0.1:8080`이며 `/api/` 요청을 추천·이력 서비스로 전달함.

## 시험

```powershell
uv run --project common pytest common -q
uv run --project services pytest services -q
uv run --project toolkit pytest toolkit -q
uv run --project common pytest tests\eval -q -m "not live_call"
uv run --project services pytest deploy\tests -q
Set-Location frontend; pnpm test; pnpm build
```

실물 PostgreSQL·외부 API·실물 평가 호출은 `live_call`로 분리됨. 기본 시험에서는 실행되지 않음.

## 의사결정·보류

- FastAPI REST + SSE 채택, 자동 OpenAPI 사용
- `AsyncPostgresSaver` 채택, 운영 실패 시 기본 중단, 개발 명시 설정에서만 메모리 대체
- 정형 조회·속성 필터·벡터 유사도·용어사전 채택
- 문서 RAG·GraphRAG·NL2SQL·MCP·A2A는 설계 판정에 따라 현재 범위에서 제외
- 운영 오케스트레이터·관측 백엔드·일부 데이터 원천·보존 기간은 각 README의 `[확인필요]` 유지

세부 실행 계약은 [API README](services/api/README.md), [화면 README](frontend/README.md),  
[워크플로우 README](services/flow/README.md), [배포 README](deploy/README.md)를 참고함.
