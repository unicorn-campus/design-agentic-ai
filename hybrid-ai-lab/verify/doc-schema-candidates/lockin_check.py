"""examples 방식이 글에 없는 이름까지 따라 쓰는지(굳어짐) 대략 살핌.

이름마다 그 뜻을 나타내는 한국어 낱말을 정하고, 그 이름을 낸 청크 글에 낱말이 하나도 없으면 '근거 없음'으로 셈.
낱말 사전은 사람이 정한 대략값이라 정밀한 측정이 아니라 두 방식의 차이를 보는 용도임.
실행: ../neo4j-vector-search/.venv/Scripts/python lockin_check.py
"""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CHUNKS = ROOT.parent.parent / "indexer/vector-bm25/data/artifacts/ch2-20261003-001/prepared-chunks.json"
WORDS = {
    "card": ["카드"], "fee": ["연회비", "수수료", "요금"], "limit": ["한도", "최대", "월 "], "channel": ["앱", "온라인", "오프라인",
    "콜센터", "채널", "홈페이지", "모바일"], "transaction": ["결제", "이용", "거래", "승인", "금액"], "refund": ["환불", "취소", "반환"],
    "dispute": ["분쟁", "이의", "민원", "항변"], "familymember": ["가족"], "contactpreference": ["연락", "문자", "전화", "알림", "선호"],
    "company": ["회사", "카드사", "제휴", "가맹"], "bank": ["은행", "계좌"], "service": ["서비스"],
}
key = lambda s: re.sub(r"[^0-9a-z가-힣]", "", s.lower())

data = json.loads(CHUNKS.read_text(encoding="utf-8"))
rows = data if isinstance(data, list) else next(v for v in data.values() if isinstance(v, list))
text = {r["chunk_id"]: r["text"] for r in rows}
print("이름: 낸 청크 수 / 근거 없음 (A 따로 | B examples)")
for name, words in WORDS.items():
    out = []
    for folder in ("output", "output-examples"):
        calls = [json.loads(l) for l in (ROOT / folder / "calls.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
        hit = [c for c in calls if "error" not in c and name in {key(n) for n in c["nodes"]}]
        bad = [c for c in hit if not any(w in text[c["chunk_id"]] for w in words)]
        out.append(f"{len(hit)} / {len(bad)}")
    print(f"- {name}: {out[0]} | {out[1]}")
