# K8 커뮤니티 요약 장표 스크립트 (별도 덱, 교재 반영 전 검토용)

## 장표 5장

| 쪽 | 제목 | 내용 |
|------|------|------|
| 1 | K8. 커뮤니티 요약 (선택) | 사실 질문과 거시 질문, 5단계 흐름, 규칙 4개, 선택 단계 |
| 2 | Leiden으로 커뮤니티 찾기 (원리) | 모듈성, 옮기기, 다듬기, 합치기 그림, 씨앗 고정 |
| 3 | GDS로 커뮤니티 찾기 (코드) | `community.py` detect 발췌(투영, gds.leiden.stream, 투영 삭제), 전체 재색인 수치 |
| 4 | 묶음마다 보고서 쓰기 (원리와 코드) | 실제 LLM 입력 글, 출력 형식, 적재 코드, 실제 보고서 예 |
| 5 | 커뮤니티 보고서로 거시 검색하기 | Q23 흐름, 상위 보고서, Q23 ~ Q25 결과 |

## 근거

| 항목 | 근거 |
|------|------|
| 코드 | `hybrid-ai-lab/indexer/graphrag/v0/community.py` |
| 수치 | v0 전체 재색인 `full-001`(세대 gen-full-001-807ef9e6): 청크 218, 엔티티 1,663, 관계 1,527, 묶음 144, 요약 78, K8 토큰 228,427, ④ 통과 |
| 보고서 예, 프롬프트 입력 | 같은 세대의 「연회비 대비 가치」 묶음(엔티티 23개). `make_data.py`가 뽑음 |
| 거시 검색 결과 | `hybrid-ai-lab/verify/k8-community/full/macro_eval.json` |

## 빌드

`make_data.py`(v0 가상환경) → `node build.js` → `python post.py K8커뮤니티요약.pptx` →  
`python scripts/render-pptx.py temp/k8-community/K8커뮤니티요약.pptx --out temp/k8-community/preview`

- 5장의 「찾기는 되지만 답이 약함」 문장은 사람이 결과를 읽고 `data.json`의 `finding`에 씀(`make_data.py`가 덮어쓰지 않음)
- 보고서 본문의 가운뎃점은 LLM이 쓴 원문이라 그대로 둠
