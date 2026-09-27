# SQL · NL2SQL Layered Architecture 예제

자연어 질문에 답하려면 모델이 참고할 정형 데이터를 안전하게 조회하고, 각 값의 출처를 함께 전달해야 합니다.  
이 예제는 PostgreSQL 조회 결과를 근거가 포함된 Context로 조립하고, 필요할 때 Claude에 전달합니다.

`vector-retriever`와 같은 최상위 구조를 사용합니다. 루트의 `run_sql.py`가 CLI 요청을 받고, 실제 구현은  
`app/`의 네 계층에 들어 있습니다.

## 구조

```text
hybrid-ai-lab/sql-retriever/
├─ run_sql.py                         # 얇은 CLI 진입점
├─ requirements.txt
├─ README.md
├─ app/
│  ├─ domain/                         # 날짜·월 보충·Context 순수 규칙
│  ├─ application/                    # 포트·요청/응답·조회 유스케이스
│  ├─ infrastructure/                 # PostgreSQL·Claude·읽기 전용 SQL
│  ├─ presentation/
│  │  └─ cli.py                       # CLI 입력 파싱·결과 출력
│  ├─ prompts/
│  │  └─ answer_with_context.md
│  └─ bootstrap.py                    # 포트와 어댑터 조립
└─ tests/
```

의존 방향은 `presentation → application ← infrastructure`이며, 응용 계층은 `domain`의 순수 규칙을 사용합니다.  
응용 계층은 포트 계약만 알기 때문에 PostgreSQL이나 LLM 클라이언트가 바뀌어도 조회 흐름을 유지할 수 있습니다.  
`app/bootstrap.py`는 실행 시점에 포트와 실제 어댑터를 연결합니다.

## 설치

Python 3.11 이상을 권장합니다. 다음 명령은 모두 `hybrid-ai-lab/sql-retriever/`에서 실행합니다.

### Windows PowerShell

```powershell
cd "$HOME/class/design-agentic-ai/hybrid-ai-lab/sql-retriever"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

### macOS·Linux·WSL

```bash
cd ~/class/design-agentic-ai/hybrid-ai-lab/sql-retriever
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

예제 루트의 `.env`가 없으면 상위 `hybrid-ai-lab/.env`를 읽습니다.

```dotenv
CLAUDE_API_KEY=발급받은_API_키
S22_DB_DSN=host=localhost port=5432 dbname=cardlab user=lab_user
S22_DB_PASSWORD=공통_RDB_실습계정_비밀번호
```

`S22_DB_DSN`을 생략하면 `localhost:5432/cardlab`과 읽기 전용 `lab_user`를 사용합니다.  
로컬 기본 연결에서는 `../rdb/compose.yml`의 비밀번호를 읽습니다.

## 실행

DB를 사용하는 모드보다 먼저 공통 PostgreSQL을 기동합니다.

```text
docker compose -f ../rdb/compose.yml up -d
docker compose -f ../rdb/compose.yml ps
```

`--mode`로 실행할 예제를 선택합니다.

| 모드 | 확인할 내용 | PostgreSQL | LLM |
|------|-------------|------------|-----|
| `schema` | 8개 테이블의 컬럼과 행 수 | 사용 | 미사용 |
| `products` | 활성 카드의 상품명·연회비·발급일·상태 | 사용 | 미사용 |
| `usage` | 최근 6개월 승인 사용액과 빈 월 보충 | 사용 | 미사용 |
| `delinquency` | 기준월 이하의 최신 연체 지표 | 사용 | 미사용 |
| `context` | 세 조회 결과로 만든 근거 Context | 사용 | 미사용 |
| `first` | 기본 Claude 요청과 응답 메타데이터 | 미사용 | 사용 |
| `nl2sql` | 자연어 질문으로 만든 검토용 SELECT | 미사용 | 사용 |
| `ask` | 조회·Context 조립·답변 요청의 전체 흐름 | 사용 | 사용 |

스키마와 고정 SQL 조회는 API 키 없이 실행할 수 있습니다.

```text
python run_sql.py --mode schema
python run_sql.py --mode products --segment 2
python run_sql.py --mode usage --segment 2
python run_sql.py --mode delinquency --segment 2
python run_sql.py --mode context --segment 2
```

`first`, `nl2sql`, `ask`에 `--offline`을 붙이면 LLM 요청 내용을 만들되 API는 호출하지 않습니다.

```text
python run_sql.py --mode first --offline
python run_sql.py --mode nl2sql --offline
python run_sql.py --mode ask --offline --segment 2
```

`.env`에 `CLAUDE_API_KEY`가 있으면 `--offline`을 제거하여 실제 LLM을 호출할 수 있습니다.

```text
python run_sql.py --mode ask --segment 2
```

`nl2sql` 모드가 생성한 SQL은 검토를 위해 화면에만 출력합니다.  
DB에서는 `app/infrastructure/queries.py`의 읽기 전용 SELECT 세 개만 실행합니다.

## 입력 변경

| 조 | 세그먼트 | 대표 고객 |
|----|----------|-----------|
| 1 | 신규 가입 | M-1001 |
| 2 | 장기 보유 | M-1042 |
| 3 | VIP | M-3001 |
| 4 | 휴면 직전 | M-4001 |
| 5 | 다중 카드 | M-5001 |
| 6 | 연회비 부담 | M-6001 |

```text
python run_sql.py --mode ask --offline --segment 6
python run_sql.py --mode usage --member-id M-1042 --base-date 2026-08-31
python run_sql.py --mode ask --offline --question "보유 상품과 연회비를 요약해 주세요"
python run_sql.py --help
```

`--segment` 기본값은 2입니다. `--member-id`를 지정하면 대표 고객보다 우선합니다.  
기준일 기본값은 `2026-08-31`이며, 허용 범위는 `2026-03-01` ~ `2026-08-31`입니다.

## 테스트와 확인 기준

```text
python -m unittest discover -s tests -v
```

`schema` 모드에서 8개 테이블과 행 수가 출력되면 DB 연결·권한·스키마가 정상입니다.  
`ask --offline`에서 상품·사용액·연체 Context가 출력되면 통합 조회도 정상입니다.  
실제 LLM 호출은 API 키와 네트워크가 있는 환경에서 별도로 확인해야 합니다.

## 관련 자료

- [공통 RDB와 데이터 설명](../rdb/README.md)
- [답변 프롬프트](app/prompts/answer_with_context.md)
- [프롬프트 작성 가이드](../../references/prompt-guide.md)
