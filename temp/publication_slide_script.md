# 게시 원리 슬라이드 스크립트

## 슬라이드 1. 세대 게시: 완성된 검색 묶음으로 한 번에 전환

### 핵심 정의

**세대(generation)**는 한 시점에 함께 검색해야 하는 벡터, BM25, corpus, 카드명 사전, manifest의 한 묶음입니다.

### 화면 구성

- 비율: 16:9, 흰색 배경
- 글꼴: Pretendard
- 제목: 48pt ExtraBold, `#1E2A5C`
- 본문: 16 ~ 18pt, 최소 14pt
- 색상: Deep Navy `#1E2A5C`, Bright Blue `#2E74C6`, Light Blue `#EEF3FA`
- 구성: 상단 세대 전환 그림, 중앙 왼쪽 게시 순서, 중앙 오른쪽 코드, 하단 설계 항목 표

### 상단: 새 세대를 따로 만드는 이유

왼쪽에서 오른쪽으로 흐르는 편집 가능한 도형으로 표현합니다.

`사용 중 G1` → `G2 별도 구축` → `G2 전체 검증` → `active_generation.json → G2`

- G1 카드: `벡터 + BM25 + corpus/사전 + manifest`, 검색 중 배지
- G2 카드: 같은 다섯 구성요소, 준비 중 배지
- 마지막 포인터 카드: `chroma_path`, `search_index_root`, `generation`을 함께 가리킴

그림 아래 한 문장:

> 벡터는 G2인데 BM25는 G1인 섞인 상태를 피하려고, G2를 완성한 뒤 단일 포인터를 마지막에 바꿉니다.

### 중앙 왼쪽: 실제 게시 순서

네 개의 세로 단계 카드로 구성합니다.

1. **전체 검증**
   - Chroma ID·본문·메타데이터·벡터 차원 확인
   - BM25 경로·청크 수·corpus·사전·manifest 해시 확인
2. **게시 잠금**
   - `.publish.lock`으로 포인터 교체 구간 직렬화
3. **기준 세대 확인**
   - 준비를 시작한 기준 세대가 아직 활성인지 확인
   - 다른 실행이 먼저 게시했으면 오래된 결과를 거부
4. **ready 기록 → 포인터 교체**
   - 세대 상태를 `ready`로 저장
   - 임시 JSON을 `fsync`한 뒤 `active_generation.json`으로 교체

### 중앙 오른쪽: 게시 코드 예시

코드 박스 제목에 **실제 코드에서 핵심만 줄인 요약**이라고 표시합니다.

```python
with CrossPlatformFileLock(self.lock_path):
    current = self._active_pointer()
    if current_generation not in {base_generation, generation}:
        raise RuntimeError("오래된 실행 결과는 활성화하지 않습니다.")
    _replace_json(state_path, {
        **generation_state, "status": "ready",
    })
    _replace_json(self.active_pointer_path, pointer)
```

코드 아래 작은 캡션:

`_replace_json()`은 같은 디렉터리에 임시 파일을 쓰고 `os.replace()`로 교체함

### 하단: 설계할 때 정의할 항목

| 설계 항목 | 현재 구현 | 추가로 정할 운영 기준 |
|---|---|---|
| 세대 범위 | Chroma와 BM25·corpus·사전·manifest를 한 세대로 묶음 | 다른 검색 자산도 같은 전환 단위에 넣을지 결정 |
| 게시 합격 기준 | ID·본문·메타데이터·차원, 경로·건수·해시 일치 확인 | 품질 평가와 승인 절차의 통과 기준 결정 |
| 동시 게시 | 짧은 잠금과 기준 세대 비교로 오래된 결과 거부 | 재시도 횟수·대기 시간·운영 알림 결정 |
| 전환 단위 | 전역 JSON 포인터에 두 경로를 기록하고 마지막에 교체 | 새 세대 감지·재로딩 시점과 진행 중 요청 처리 결정 |
| 실패·보관·복구 | 게시 전 실패 시 기존 포인터 유지, 이전 세대 파일 보존 | 자동 롤백, 보관 개수·기간, 정리와 수동 복구 절차 결정 |

표 하단 주의 문구:

`기존 포인터 유지 = 실패한 새 세대를 활성화하지 않음. 자동 롤백 기능을 뜻하지 않음.`

### 발표자 말할 내용

“세대는 같은 시점에 검색해야 하는 벡터와 BM25, corpus, 카드명 사전, manifest를 묶은 단위입니다. G1을 검색에 쓰는
동안 G2를 별도 경로에 만들고, 두 색인의 내용과 해시를 모두 확인합니다. 게시할 때는 잠금을 잡고 G2가 준비를 시작했던
기준 세대가 아직 활성인지 확인합니다. 검증을 통과하면 G2 상태를 ready로 기록하고, 마지막에 active_generation.json만
G2 경로로 바꿉니다. 이 구조는 실패한 새 세대가 활성화되는 일을 막지만, 서비스의 새 경로 재로딩과 자동 롤백·보관 기간은
별도 운영 기준으로 정해야 합니다.”

### 발표자 노트

- `publish()`는 빈 세대와 중복 청크 ID를 거부한 뒤 Chroma 컬렉션과 BM25 산출물을 다시 검증함.
- Chroma 검증은 발행 대상과 저장된 ID 집합, 본문, 메타데이터, 벡터 수와 차원을 비교함. BM25 검증은 경로 범위,
  세대, 청크 수, corpus와 카드명 사전 해시를 확인함.
- 잠금 안에서 현재 세대가 `base_generation` 또는 이미 같은 `generation`일 때만 게시함. 다른 세대가 먼저 활성화되었으면
  `RuntimeError`를 내고 포인터를 바꾸지 않음.
- `_replace_json()`은 임시 파일의 내용을 `fsync`한 뒤 `os.replace()`함. 한 JSON 파일 교체의 원자성을 높이는 구현이며,
  저장 장치·프로세스 장애 전반의 무중단을 보장한다는 뜻은 아님.
- 게시 실패 시 이전 활성 포인터를 유지하는 시험이 있음. 실패 후 새 세대를 자동 폐기하거나 이전 세대로 자동 되돌리는
  로직은 `publish()`에 없음.
- 이전 세대 디렉터리를 지우는 보관 정책도 `publish()`에 없음. 보관 개수·기간과 정리 작업은 운영 설계 항목임.
- 전역 `active_generation.json`은 Chroma와 검색 색인 루트를 함께 가리킴. Retriever 앱이 이 전역 포인터를 읽는 코드는
  확인되지 않았으며, Chroma와 검색 색인 루트를 별도 설정으로 받음. `VersionedCorpusStore`는 설정된 검색 색인 루트 안의
  `active_index.json`만 읽음. 새 세대 감지·두 경로 재로딩·진행 중 요청 처리 방식은 별도 구성·운영 항목임.
- 이 슬라이드는 코드 구조를 설명한 것이며 실제 게시나 장애 전환을 실행한 결과가 아님.

### 코드 근거

- `hybrid-ai-lab/indexer/vector-bm25/app/infrastructure/index_repository.py:53`  
  임시 파일을 `fsync`한 뒤 JSON을 교체하는 `_replace_json()`
- `hybrid-ai-lab/indexer/vector-bm25/app/infrastructure/index_repository.py:155`  
  활성 세대를 건드리지 않고 새 세대를 `building` 상태로 준비하는 `begin()`
- `hybrid-ai-lab/indexer/vector-bm25/app/infrastructure/index_repository.py:299`  
  Chroma의 ID·본문·메타데이터·벡터 차원을 확인하는 `_verify_collection()`
- `hybrid-ai-lab/indexer/vector-bm25/app/infrastructure/index_repository.py:427`  
  검증 → 잠금 → 기준 세대 검사 → ready → 전역 포인터 교체를 수행하는 `publish()`
- `hybrid-ai-lab/indexer/vector-bm25/app/infrastructure/lexical_index.py:397`  
  BM25 경로·건수·corpus·사전 해시를 검증하는 `verify()`
- `hybrid-ai-lab/retriever/vector-retriever/app/infrastructure/corpus_store.py:30`  
  설정된 검색 색인 루트의 `active_index.json`에서 활성 세대를 읽는 코드
- `hybrid-ai-lab/indexer/vector-bm25/tests/test_service.py:491`  
  게시 실패 시 이전 활성 세대가 유지되는지 확인하는 시험
