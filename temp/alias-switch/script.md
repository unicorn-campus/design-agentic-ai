# 검색 갈래 ④ 별칭 전환 — PPT 스크립트

- 산출물: `temp/alias-switch/별칭전환.pptx` (1장)
- 작성: 클로니, 2026-10-19
- 위치: 「2. 인덱싱: 1-b 분리형(검색 엔진)의 인덱싱 파이프라인」 검색 갈래 ④ 「별칭 전환(세대)」 설명.
  검색 엔진에 쓰기 장표(`temp/search-engine-write/검색엔진쓰기.pptx`) 다음에 둠
- 스타일: `references/pptx-guide.md` — `내용_단쪽`, Pretendard, 14pt 이상, 편집 가능 도형, 출처 줄 없음(근거는 이 파일에만)

## 근거(스크립트에만 기록)

| 내용 | 근거 |
|------|------|
| `step4_switch_alias`, `verify_generation`, `resolve_alias` | `hybrid-ai-lab/verify/search-branch-example/search_branch.py` |
| `update_aliases` 한 요청에 remove와 add를 넣으면 별칭이 빈 순간 없이 옮겨짐 | OpenSearch `POST /_aliases` 문서(context7 `/opensearch-project/documentation-website`, 지식니 확인) |
| 시험: 없음 → 1세대(a-2), 1세대 → 2세대(c-1), 1세대 인덱스 유지(c-2), 2세대 → 1세대 되돌리기(d-1), 건수 23(d-2), 검색 동작(d-3) | `run.log` 15, 17, 41 ~ 43, 98 ~ 101행 |
| 그래프(Neo4j) 세대도 같은 순간에 바꿔야 함 | 1-b 파이프라인 장표 「세대 전환을 함께」. 예제는 검색 엔진 쪽만 구현(README 한계) |

- 코드 발췌는 실제 소스에서 `new_index`가 이미 별칭에 있을 때 건너뛰는 처리와 반환값을 줄인 것임.
  remove와 add를 한 `update_aliases` 요청에 넣는 핵심은 소스와 같음

---

## 장표 1. 검색 갈래 ④ 별칭 전환

- 제목: 검색 갈래 ④ 별칭 전환
- 리드문: 새 세대 인덱스를 다 채우고 건수를 확인한 뒤, 검색이 보는 이름표(별칭)만 한 번에 옮김

**도형 구성**

1. 위쪽 세 칸(y 1.9 ~ 4.35), 칸 사이 화살표
   - 「전환 전」: 별칭 `card_chunks` 필 → 1세대 인덱스(네이비, 사용 중). 2세대 인덱스(점선, 채우는 중)
   - 「건수 확인」: 별칭은 아직 1세대. 2세대 인덱스(블루 테두리, 건수 23 = 입력 23). 옆 글: refresh 뒤 건수 확인, 다르면 전환 중단
   - 「전환 후」: 별칭 → 2세대 인덱스(네이비, 사용 중). 1세대 인덱스(회색, 남겨 둠)
2. 가운데(y 4.5 ~ 5.95): 「왜 한 요청인가」 두 줄 비교
   - 두 번 나눠 부르면: [remove 1세대] → [별칭이 비어 검색 0건](다크) → [add 2세대]
   - update_aliases 한 요청: [remove 1세대 + add 2세대를 한 번에] → [빈 순간 없음](블루)
3. 아래 왼쪽(y 6.1 ~ 7.95): 코드 상자 「search_branch.py 발췌」
   ```python
   previous = resolve_alias(client, alias)   # 지금 별칭이 가리키는 세대
   actions = [{"remove": {"index": name, "alias": alias}}
              for name in previous]
   actions.append({"add": {"index": new_index, "alias": alias}})
   client.indices.update_aliases(body={"actions": actions})  # 한 요청
   ```
4. 아래 오른쪽
   - 블루 카드: 되돌리기는 같은 함수에 1세대 인덱스를 넘기면 됨
   - 틴트 카드(시험): 없음 → 1세대, 1세대 → 2세대, 2세대 → 1세대 모두 통과. 되돌린 뒤 건수 23, 검색 동작
   - 콜아웃: 그래프(Neo4j) 세대도 같은 순간에 바꿔야 함. 예제는 검색 엔진 쪽만 구현

**발표자 노트**

검색은 실제 인덱스 이름을 모르고 card_chunks라는 별칭에만 질의합니다. 전체 재색인 때는 새 세대 인덱스를 따로 다 채우고,
refresh 뒤 건수가 기대와 같은지 확인합니다. 건수가 다르면 덜 만들어진 세대이므로 전환하지 않습니다.
확인이 끝나면 별칭을 새 세대로 옮기는데, 이때 옛 세대에서 빼는 일과 새 세대에 붙이는 일을 update_aliases 한 요청에 함께 넣습니다.
두 번에 나눠 부르면 그 사이에 별칭이 아무것도 가리키지 않아 검색 결과가 비는 순간이 생깁니다.
옛 세대 인덱스는 지우지 않고 남겨 두므로, 문제가 생기면 같은 함수에 옛 인덱스를 넘겨 바로 되돌릴 수 있습니다.
그래프 쪽 Neo4j 세대도 같은 순간에 맞춰 바꿔야 검색 결과의 chunk_id가 그래프에서 끊기지 않습니다. 예제는 검색 엔진 쪽만 구현했습니다.
