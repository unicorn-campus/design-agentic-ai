# 정형 데이터 검색기

고객 상담 중 상담사가 이탈 위험 신호를 포착하면, 상담 오케스트레이터는 필요한 고객 현황을 요청합니다.  
이 프로그램은 PostgreSQL의 카드·승인 사용액·연체 자료를 검색해 다음 단계에 전달합니다.  
[유저스토리](../../specs/userstory.md)의 **S-03 / UFR-EVID-010 고객 현황 확보**를 구현합니다.

오케스트레이터는 정형 검색이 필요한지를 결정합니다. 검색기는 고정 조회 목록과 허용 스키마를 소유하고,  
자연어 질문에 맞는 고정 조회를 선택하거나 SQL을 생성합니다. 고정 조회 목록을 오케스트레이터에 복제할 필요가 없습니다.

## 검색 방식과 LLM 호출

| 요청 | 검색 계획과 실행 | 정상 처리 시 LLM 호출 |
|---|---|---|
| `auto` + 질문 | 한 번의 모델 응답에서 고정 `query_id` 또는 SQL 선택·생성 후 실행 | 1회 |
| `fixed` | 지정한 고정 조회 실행; 미지정 시 `customer_snapshot` | 0회 |
| `nl2sql` + 질문 | SQL 생성 → 검증 → 실행 | 1회 |
| 위 요청 + `explain=true` | 검색 후 확인용 결과 설명 생성 | 추가 1회 |

기본 모드는 `auto`이며, **검색 후 설명 생성은 기본 OFF**입니다.  
실제 시스템은 `data`에 들어 있는 검색 결과를 사용합니다. `explanation`은 개발자가 확인할 때만 사용합니다.  
전송 실패에는 SDK 재시도가 최대 1회 있어 네트워크 전송 횟수는 위 논리 호출 횟수보다 늘어날 수 있습니다.  
SQL 검증 실패를 자동 재작성하는 반복 루프는 없습니다.

LLM은 LangChain의 `ChatGroq`를 통해 Groq LPU의 `openai/gpt-oss-120b`를 사용합니다.  
정형 검색기로는 이탈 확률을 예측하거나 최종 상담 제안을 작성하지 않습니다.  
문서·과거 상담 근거 조회와 채택 기록도 별도 유저스토리의 책임입니다.

## 계층 구조

```text
run_sql.py / serve_sql.py
  └─ presentation: CLI 인자·HTTP 요청 수신, 결과·오류 출력
       └─ application: 공통 요청 계약과 검색 흐름
            ├─ domain: 고정 조회 목록, 날짜 규칙, 식별자 제거
            └─ ports ← infrastructure: PostgreSQL, SQL 검증, Groq, 환경 설정

app/bootstrap.py: 인터페이스와 실제 어댑터 조립
```

CLI와 API는 같은 `SearchService.execute()`를 호출합니다.  
응용 계층은 LangChain Runnable로 `검색 계획 → 조회 → 선택적 설명`을 연결하며 인프라 구현을 직접 생성하지 않습니다.  
조회 계획과 실행 SQL의 검증은 구분합니다. 모델이 선택한 계획이더라도 허용 규칙을 통과해야 DB에서 실행합니다.

## 설치와 설정

Python 3.12 이상에서 다음 명령을 실행합니다. 경로는 저장소 루트 기준입니다.

```powershell
cd hybrid-ai-lab/retriever/sql-retriever
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

키는 작업 디렉터리와 관계없이 **`hybrid-ai-lab/.env`**에서 읽습니다.  
서비스 폴더에 키를 복사할 필요는 없습니다. 실제 값은 코드·예제·로그에 포함하지 않습니다.  
같은 이름의 프로세스 환경변수가 있으면 그 값을 우선합니다.

```dotenv
GROQ_API_KEY=발급받은_키
# 아래 DB 설정은 선택입니다.
SQL_RETRIEVER_DB_DSN=host=localhost port=5432 dbname=cardlab user=lab_user
SQL_RETRIEVER_DB_PASSWORD=실습_DB_비밀번호
```

DB 연결 설정이 없으면 기존 공통 RDB의 `localhost:5432/cardlab`, 읽기 전용 `lab_user`를 사용합니다.  
이 로컬 기본 연결에서만 `../../rdb/compose.yml`의 실습 비밀번호를 읽습니다.  
기존 `S22_DB_DSN`, `S22_DB_PASSWORD`도 인식합니다. 예전 SQLite용 `S22_DB_PATH`는 사용하지 않습니다.  
RDB가 꺼져 있다면 [공통 RDB 안내](../../rdb/README.md)에 따라 시작합니다.

선택 설정은 `.env.example`에서 확인할 수 있습니다. DB 쿼리 제한은 기본 5초, 모델 요청 제한은 기본 30초입니다.
`fixed` 검색과 스키마 명세 조회에는 API 키가 필요하지 않습니다.

## CLI

고객 현황 전체를 LLM 없이 조회합니다.

```powershell
.\.venv\Scripts\python.exe run_sql.py --query-mode fixed --member-id M-1042 --base-date 2026-08-31
```

자연어 질문으로 고정 조회 선택 또는 SQL 생성을 맡깁니다.

```powershell
.\.venv\Scripts\python.exe run_sql.py --member-id M-1042 --base-date 2026-08-31 --question "보유 카드 목록을 보여 주세요"
.\.venv\Scripts\python.exe run_sql.py --member-id M-1042 --base-date 2026-08-31 --question "월별 총 승인 사용액을 합산해 주세요"
```

조회 방식을 강제로 지정하거나 확인용 설명을 추가할 수도 있습니다.

```powershell
.\.venv\Scripts\python.exe run_sql.py --query-mode fixed --query-id delinquency `
  --member-id M-1042 --base-date 2026-08-15
.\.venv\Scripts\python.exe run_sql.py --query-mode nl2sql --member-id M-1042 `
  --base-date 2026-08-31 --question "월별 승인 총액은?"
.\.venv\Scripts\python.exe run_sql.py --query-mode fixed --member-id M-1042 --base-date 2026-08-31 --explain
.\.venv\Scripts\python.exe run_sql.py --schema
```

JSON 결과는 stdout으로, 오류는 stderr로 출력합니다. 스키마 명세는 키·DB 접속 없이 확인할 수 있습니다.  
PowerShell에서 결과를 다른 프로그램으로 전달할 때는 UTF-8 인코딩을 사용합니다.

## HTTP API

```powershell
.\.venv\Scripts\python.exe serve_sql.py --port 8012
```

기본 바인딩은 `127.0.0.1`, 로컬 기본 포트는 `8012`입니다. `/docs`에서 요청 계약을 확인할 수 있습니다.

| 메서드·경로 | 용도 |
|---|---|
| `POST /search` | CLI와 동일한 검색 서비스 호출 |
| `GET /schema` | 고정 조회 목록과 허용 논리 테이블·컬럼 명세 |
| `GET /health` | 프로세스 생존 확인; DB·Groq 연결 검증 결과가 아님 |

`auto` 요청 예시입니다.

```json
{
  "query_mode": "auto",
  "member_id": "M-1042",
  "base_date": "2026-08-31",
  "question": "월별 총 승인 사용액을 합산해 주세요",
  "explain": false
}
```

`fixed` 요청은 `question`을 생략할 수 있습니다. `query_id`는 `fixed`에서만 직접 지정합니다.

```json
{
  "query_mode": "fixed",
  "query_id": "customer_snapshot",
  "member_id": "M-1042",
  "base_date": "2026-08-31"
}
```

응답의 `requested_query_mode`는 요청 방식이고 `query_mode`는 실제 선택한 `fixed` 또는 `nl2sql`입니다.
`query_id`, `routing_reason`, `data`, `warnings`, `explanation_status`로 선택 이유와 결과를 확인합니다.  
설명을 요청하지 않으면 `explanation=null`, `explanation_status=not_requested`입니다.  
설명 생성에 실패해도 성공한 검색 결과는 유지하고 `explanation_status=failed`로 반환합니다.

입력 오류와 거부된 SQL은 실행하지 않습니다. DB 또는 Groq 실패 시 SQL·접속 문자열·키를 오류 본문에 노출하지 않습니다.  
이 API는 신뢰된 내부 호출용이며, 상담사 인증과 해당 회원 조회 권한 확인은 호출 측에서 수행해야 합니다.  
현재 실습 서비스에는 사내 인증·권한 시스템 연동이 없습니다.

## 고정 조회와 논리 스키마

| query_id | 반환할 내용 |
|---|---|
| `customer_snapshot` | S-03용 고객 현황 전체, 원본 카드ID·상품ID, 승인 사용액, 연체액, 출처·기준시점 |
| `cards` | 보유 카드·상품·브랜드·발급일·현재 상태·상품 시행일·연회비 |
| `monthly_usage` | 최근 6개월 카드별 월 승인액·승인 건수·조회 기간 |
| `delinquency` | 기준일 이전 완료된 월 중 최신 연체 지표 |

NL2SQL은 원본 테이블을 직접 검색하지 않습니다. 코드가 요청 회원·기준일로 제한한 논리 테이블을 구성합니다.  
이 논리 테이블은 SQL의 CTE이며, DB에 테이블이나 뷰를 생성하지 않습니다.

| 논리 테이블 | 내용 |
|---|---|
| `customer_profile` | 해당 회원의 가입일·연령대 |
| `customer_cards` | 해당 회원의 기준일 이전 발급 카드와 연결 상품 |
| `monthly_usage` | 해당 회원 카드의 최근 6개월 월별 승인 거래 집계 |
| `customer_delinquency` | 기준일 이전 완료된 월의 최신 회원 단위 연체 지표 |

전체 컬럼은 `--schema` 또는 `/schema`에서 확인합니다. 명세의 원본은 코드 한곳에 있습니다.  
카드 연결에는 요청 내 대체 식별자 `card_ref`를 사용합니다.  
검색 결과에 원본 카드ID가 필요한 S-03 호출은 `customer_snapshot`을 사용합니다.

## 데이터 해석과 검증 경계

- 공통 RDB는 교육용 합성 데이터입니다. 요청 기준일과 `lab_metadata`의 데이터 기준일을 구분합니다.
- 데이터 기준일 이후 또는 회원 가입 전을 조회하면 거부합니다. 예제 기준일은 `2026-08-31`입니다.
- 거래 제공 기간은 메타데이터 `txn_period`에서 확인합니다. 현재 실습 데이터는 `2025-08`부터 있습니다.
- 제공 기간 이전 요청은 거부하며, 초기 월 조회에서는 가용 월만 반환하고 없는 과거 월을 0원으로 채우지 않습니다.
- 승인 사용액은 `APPROVED` 거래만 합산합니다. 취소 거래·기준일 이후 거래를 포함하지 않습니다.
- 연체 자료는 월말을 실제 기준시점으로 사용합니다. `2026-08-15` 요청에 8월 말 자료를 사용하지 않습니다.
- 카드 상태 이력이 없어 `current_status`는 현재 스냅샷으로 표시합니다.
- 기준일 이전 발급 카드를 현재 상태와 함께 반환합니다. 현재 `ACTIVE` 상태로 과거 거래를 일괄 제외하지 않습니다.
- 상품 시행일이 미래이면 조회 당시 유효한 연회비로 단정하지 않도록 경고합니다.
- 월 집계는 건별 거래가 아닙니다. 건수는 `SUM(transaction_count)`이며 `COUNT(*)`는 집계 행 수입니다.
- 데이터가 없는 연체 상태와 실제 연체액 0을 구분합니다.
- 정수 금액·합계는 JSON 숫자로, 소수 결과는 정밀도를 보존하는 문자열로 반환합니다.

SQL 검증기는 허용 논리 테이블과 컬럼을 대상으로 한 SELECT 한 개만 허용합니다.  
쓰기, 원본·private 스키마 접근, 서브쿼리, WITH, UNION, 잠금, 임의 함수 등은 실행 전에 차단합니다.  
일부 JOIN·GROUP BY·정렬·집계는 지원하며 최대 100행과 DB 실행시간 제한을 적용합니다.  
입력 회원·기준일은 SQL 파라미터로 바인딩하고 PostgreSQL 읽기 전용 트랜잭션에서 실행합니다.

모델의 검색 계획 입력에는 질문·허용 스키마·고정 조회 설명만 보냅니다. 실제 고객 행은 보내지 않습니다.  
확인용 설명을 켜면 조회 결과에서 원본 식별자 필드를 제거하고 대체 카드 참조를 사용합니다.  
질문에도 식별자·연락처·이메일 등 알려진 패턴을 제거합니다. 자유문장의 모든 개인정보를 판별하는 기능은 아닙니다.  
호출 측에서도 질문의 민감정보를 제거해야 합니다. 실행 중 LangSmith 외부 tracing은 비활성화합니다.

## 검증

```powershell
.\.venv\Scripts\python.exe -m pytest tests -q
```

단위 검증은 모델·저장소를 대역으로 바꿔 외부 호출 없이 수행합니다.  
실제 PostgreSQL 통합 테스트는 `SQL_RETRIEVER_TEST_DSN`을 지정한 경우에만 실행합니다.  
실제 Groq 검증은 CLI의 `auto`·`nl2sql`·`--explain` 요청으로 구분해서 확인할 수 있습니다.  
모델은 지원하지 않는 질문을 거절하도록 요청받지만, 자연어의 의미를 항상 정확히 해석한다고 보장하지는 않습니다.  
반환 SQL과 검색 결과를 확인할 수 있도록 유지하고, 데이터 접근 경계는 모델 판단과 별도로 코드가 강제합니다.

2026-09-27 구현 시점의 실제 확인 결과입니다.

| 검증 | 결과 |
|---|---|
| 단위·프레젠테이션·실제 PostgreSQL 통합 시험 | 87개 통과 |
| API 키를 비운 고정 검색 | 카드 2개와 고객 현황 조회 성공, 설명 미호출 |
| Groq 자동 고정 조회 선택 | 보유 카드 질문을 `cards`로 선택하고 2행 반환 |
| Groq 자동 NL2SQL | 고객 전체 월별 승인 총액 질문에 집계 SQL을 생성하고 6개월 반환 |
| 강제 NL2SQL | 승인 총액 상위 2개월 조회 성공 |
| 선택적 Groq 설명 | 연체 조회 결과의 확인용 설명 생성 성공 |
| 실제 HTTP | `/health`·`/schema`·고정/자동 `/search` 200, 잘못된 입력 422 |

검증용 API 서버는 테스트 후 종료했습니다. 프로그램을 사용하려면 위 실행 명령으로 시작합니다.

참고한 공식 문서:  
[LangChain ChatGroq](https://docs.langchain.com/oss/python/integrations/chat/groq),  
[Groq GPT-OSS 120B](https://console.groq.com/docs/model/openai/gpt-oss-120b).
