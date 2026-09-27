# S3.1 청킹 설계와 직접 구현

교재 슬라이드 17 ~ 30의 청킹 함수 2종과 첫 실행을 위한 완성 코드임.  
S2.3에서 만든 자료를 읽어 조·항 또는 상담 턴으로 나누고 S3.2용 JSONL을 저장함.  
Python 3.10 이상 사용. 외부 AI API·API 키·DB 연결 없이 실행 가능함.

## (1) 바로 실행

Windows PowerShell에서 아래 명령 실행. Python 환경에 PyYAML이 이미 있으면 설치 생략 가능함.

```powershell
cd C:\Users\hiond\class\design-agentic-ai\hybrid-ai-lab
python -m pip install -r s3.1/requirements.txt
python s3.1/run_chunking.py
```

기본 명령은 교재의 첫 실행처럼 D1만 처리함. 결과는 `s3.1/data/chunked/`에 저장됨.  
입력·출력 기본 경로는 스크립트 위치 기준이므로 어느 폴더에서 실행해도 같음.  
`--input`, `--output`으로 지정한 상대 경로는 현재 터미널 위치 기준임.

S2.3 결과가 없으면 아래 명령으로 준비한 뒤 실행함. 기존 정제 결과가 있으면 재실행 불필요함.

```powershell
python -m pip install -r s2.3/requirements.txt
python s2.3/parse_docs.py --report --split-by header --pseudonymize --validate
```

교재의 `w2-4/data/parsed`는 현재 프로젝트에서 `s2.3/data/parsed`에 해당함.  
다른 위치의 결과는 `--input 경로`로 지정 가능함. 폴더 입력은 개별 `pages/*.md`, `records/*.md`를 읽음.  
따라서 S2.3 실습에서 편집한 메타데이터도 반영됨. JSONL 파일 경로를 직접 지정하는 방식도 지원함.

## (2) 교재 순서대로 실습

| 교재 활동 | 코드·실행 | 확인 내용 |
|---|---|---|
| 슬라이드 22 ~ 23 규칙 결정 | `templates/worksheet.md`를 온라인 조별 문서에 복사 | 문서별 값과 이유 기록 |
| 슬라이드 24 ~ 26 함수 구현 | `src/chunking.py` | 경계 → 분할 → 중첩 → 꼬리표 주석 확인 |
| 슬라이드 27 직접 작성 | 아래 함수 호출 또는 함수 본문 수정 후 테스트 | 한 줄씩 설명 가능한지 확인 |
| 슬라이드 28 첫 실행 | `python s3.1/run_chunking.py` | 조각 수·평균 길이·최대 길이 확인 |
| 슬라이드 29 역할별 판정 | `data/chunked/chunks.md`와 원문 대조 | 조항 예외·꼬리표·질문 3건 판정 |
| 슬라이드 30 다음 시간 전달 | `chunks.jsonl`, 실행 기록, 온라인 문서 링크 보관 | S3.2 입력 준비 |

사용자 요청에 따라 함수 본문까지 구현한 완성본임. 교재의 빈 골격 배포본과는 구분됨.  
직접 작성 연습에는 사본에서 두 함수의 본문을 다시 작성하고 제공 테스트로 결과를 비교하는 방식 사용 가능함.

`s3.1` 폴더에서 Python 실행 시 아래처럼 함수만 직접 호출 가능함.

```python
from src.chunking import chunk_by_clause, chunk_by_turn

meta = {"doc_key": "D1", "source": "D1_example.md"}
chunks = chunk_by_clause("제1조(목적)\n(1) 교육용 예시임.", meta)
print(len(chunks))
print(sum(len(c.text) for c in chunks) / len(chunks) if chunks else 0)
print(max((len(c.text) for c in chunks), default=0))
```

위 최소 메타데이터는 함수 동작 설명용임. 파일 실행에는 S2.3 공통 꼬리표와 문서별 필수 키가 필요함.

## (3) 실행값 변경·전략 비교

아래 명령은 `hybrid-ai-lab` 위치 기준임.

```powershell
# D1·D2·D3 전체 처리
python s3.1/run_chunking.py --doc all

# 2조 상담 8건 처리
python s3.1/run_chunking.py --doc D3 --segment 2 --output s3.1/data/group2

# D1 중첩 없는 결과와 기본값 비교
python s3.1/run_chunking.py --doc D1 --max-chars 600 --overlap 0 --output s3.1/data/no_overlap

# 작은 크기로 분할과 제목 반복을 관찰
python s3.1/run_chunking.py --doc D1 --max-chars 300 --overlap 40 --output s3.1/data/small

# 짧은 대화에 6턴 적용
python s3.1/run_chunking.py --doc D3 --turns-per-chunk 6 --overlap-turns 1 --output s3.1/data/turn6
```

기본값은 D1 600자/80자 중첩, D2 600자/0자 중첩, D3 4턴/1턴 중첩임.  
D2 중첩은 `--d2-overlap`으로 변경함. 표는 글자 중첩 대신 제목·머리글·조건을 반복함.  
같은 출력 폴더로 재실행하면 결과 파일을 갱신하므로 비교 실험은 `--output`을 다르게 지정함.

## (4) 코드 구조와 규칙

| 파일 | 역할 |
|---|---|
| `src/chunking.py` | `Chunk`, `make_chunk`, 청킹 함수 2종 구현 |
| `lab_io.py` | 정제 결과 읽기·기본 검사·페이지 연결·D2 표 정규화 |
| `run_chunking.py` | 실행값 처리·전역 ID 부여·통계·결과 저장 |
| `token_budget.py` | 선택한 임베딩 모델의 실제 토큰 수 계산 |
| `tests/` | 경계·원문 보존·중첩·메타데이터·입력 연결 검증 |
| `templates/worksheet.md` | 온라인 조별 문서에 복사할 규칙·판정 양식 |

고정 함수 규약은 아래와 같음.

```python
chunk_by_clause(doc_text: str, meta: dict,
                max_chars: int = 600, overlap: int = 80) -> list[Chunk]
chunk_by_turn(record_text: str, meta: dict,
              turns_per_chunk: int = 4, overlap_turns: int = 1) -> list[Chunk]
```

- D1: `제N조`, `제N조의N`, `(N)`과 원문의 원형 항 번호 지원. 조 제목 반복 포함 최종 길이 검사함.
- D2: 배포 자료의 카드·혜택 ID를 제목으로 연결하고 테두리 없는 표를 Markdown 표로 정규화함.
- 표: 600자 초과 시 행 묶음 분할, 카드명·제목·열 머리글·관련 조건·각주 반복함.
- 속성표: 한 혜택의 실적·한도·제외 조건은 관련 조건으로 함께 반복하여 조건 누락을 방지함.
- 예외: 단일 행과 필수 문맥만으로 600자 초과 시 길이·사유를 기록하고 토큰 검사 대상으로 생성함.
- D3: 같은 화자의 연속 발화를 합친 뒤 두 마디를 1턴으로 계산함. 고객부터 시작해도 처리 가능함.
- 꼬리: 남은 새 턴 2개 이하는 앞 조각에 합침. 12턴·4/1 설정은 `1-4`, `4-7`, `7-12`임.
- 출처: `page`는 입력 단위의 시작 쪽, 여러 쪽에 걸치면 `page_end` 추가. 각주 쪽은 `footnote_page`임.
- 메타데이터: 입력을 복사해 `chunk_index`, `char_len`, `clause_no` 또는 `turn_range` 추가함.
- ID: 실행 전체에서 D1/D2 순번을 연속 부여함. D3는 `D3_{record_id}_{index:04d}`임.

교재의 `^[(1)-(20)]`는 항 번호를 뜻하는 올바른 정규식이 아니므로 `^\([1-9]\d*\)` 계열로 수정함.  
표지·목차·참고 목록은 제외 사유를 기록함. D1의 참조 각주는 해당 조항에 연결함.  
D2 페이지 끝에서 다음 쪽으로 넘어간 조건도 직전 혜택에 연결함. 원문 파일은 수정하지 않음.

## (5) 결과와 검증

| 결과 파일 | 내용 |
|---|---|
| `chunks.jsonl` | 한 줄에 `text`, `chunk_id`, `metadata`를 가진 조각 1개 |
| `chunks.md` | 조각 본문과 꼬리표를 읽고 대조하는 확인본 |
| `chunking_run1.txt` | 실제 사용 인자·조각 수·평균·최대 길이 |
| `report.json` | 입력 단위 수·문서별 통계·제외 내역·입력 내용 해시 |
| `review.jsonl` | 보류 사유와 해당 입력 전문·메타데이터 |
| `exceptions.jsonl` | 단일 행+필수 문맥의 길이 예외 후보, 길이·초과 사유 |

종료 코드 0은 처리 완료, 1은 입력·실행 오류, 2는 검토 보류가 존재함을 뜻함.  
보류된 입력은 `chunks.jsonl`에 포함되지 않으며 `review.jsonl`에 전문을 보존함.  
표 전체가 600자를 넘는다는 이유만으로 보류하지 않음. 먼저 행 묶음 분할을 시도함.  
단일 행과 필수 문맥만으로도 넘는 예외는 `char_len`, `exception_reason`을 실행 기록에 남김.  
토큰 한도 이내 예외만 최종 조각으로 승인하며, 한도 초과 시 긴 셀을 문장 단위로 나누고 재검사함.  
필수 조건을 유지하며 재분할할 수 없거나 실제 모델의 토큰 검사가 미설정이면 검토 대상으로 보류함.

### 표 예외의 토큰 검사

실제 임베딩 모델과 같은 `tokenizer.json` 및 해당 모델의 입력 토큰 한도 사용 필요함.  
모델이 정해지지 않았다면 기본 실행으로 행 분할 결과와 예외 후보를 확인한 뒤 S3.2에서 검사함.  
600자 기준을 임의로 늘려 예외를 없애는 방식은 사용하지 않음.

```powershell
python -m pip install -r s3.1/requirements-token.txt
# 경로와 한도는 선정한 모델의 실제 값으로 치환 필요
python s3.1/run_chunking.py --doc all --tokenizer-json MODEL/tokenizer.json --max-input-tokens LIMIT
```

접두사가 필요한 모델은 `--token-prefix "passage: "`처럼 지정함.  
접두사·특수 토큰을 포함하여 계산하며 자동 잘라내기와 패딩은 해제함.  
이는 [Tokenizers 공식 API](https://huggingface.co/docs/tokenizers/main/api/tokenizer)의 동작에 따름.  
지정한 파일이 실제 모델과 일치하는지와 `LIMIT` 값은 사용자가 확인해야 함.  
임베딩 API 호출 자체는 수행하지 않음.

```powershell
cd C:\Users\hiond\class\design-agentic-ai\hybrid-ai-lab\s3.1
python -m unittest discover -s tests -v
```

실제 배포 자료의 규모는 교재 설명용 합성 숫자와 다름. D1은 40개 조항임.  
검증된 최신 실행 수치는 `data/chunked/chunking_run1.txt` 참조.  
`Chunk(**json.loads(line))`으로 JSONL을 다시 읽어 S3.2 입력 객체로 복원 가능함.

2026-09-10 D1 v1.2와 실제 모델 토크나이저를 적용한 전체 실행 결과: 485개 생성됨.  
D1 53개, D2 336개, D3 96개이며 검토 보류는 0개임.  
600자를 넘는 D2 예외 후보 56개는 `nlpai-lab/KURE-v1`의 8,192토큰 한도를 통과하여 포함됨.  
전체 청크의 최대 토큰 수와 예외 후보의 최대 토큰 수는 모두 371토큰임. 접두어는 사용하지 않음.  
이는 표 전체 크기만 보고 허용한 결과가 아니라 행별 필수 문맥을 반복한 뒤 실제 토큰 수를 검사한 결과임.  
36개 자동 테스트 통과: 행 분할·조건 반복·예외 기록·토큰 검사·문장 재분할·보류 경로 포함함.  
토큰 검사 테스트에는 검사 전용 토크나이저와 계수 함수를 사용했으며 실제 운영 모델 검증 결과는 아님.

기본 검사는 글자 수·경계·데이터 구조 검사임. 토큰 옵션을 지정한 경우에만 실제 토큰 수를 검사함.  
글자 수를 토큰 수로 간주하지 않으며 검색·응답 품질 평가는 S3.2 이후에 수행함.  
자동 실행 성공만으로 각 조각이 질문에 답하기에 충분하다는 뜻은 아니므로 조건과 예외를 원문 대조함.  
입력 연결 규칙은 현재 배포 자료 형식에 맞춤. 새 문서 형식은 경계·표·제외 규칙 재검토 필요함.  
청크 ID는 한 문서 버전 기준임. 크기·중첩·버전 변경 후 재적재 시 이전 조각 정리는 S3.2에서 수행함.
