"""상담 원문(D3) v4: 상담마다 상담사 발화 한 줄에 회원의 보유 카드 이름을 끼워 넣음(사용자 지시, 2026-10-23).

왜: 문서 스키마 v2의 X2(상담에서 말한 카드의 혜택과 조건) 경로를 시험하려 했으나 v3 원문 48건에 한빛 카드 이름이 한 번도 없었음.
원칙(v3 변경과 같음)
- 카드는 실습 DB(rdb/init/02_seed.sql)의 그 회원 보유 카드(card → product)에서만 고름
- 평가셋(ragas/eval-set.json, indexer/vector-bm25/evaluation/group2_questions.json)이 인용하는 줄, 개인정보 줄, DB 집계 줄은 고치지 않음
- 줄 수와 순서는 그대로 둠. 기존 글자는 지우거나 바꾸지 않고 카드 이름 구만 끼워 넣음(difflib로 삽입만 있는지 검사)
- 혜택 크기나 자격을 약속하는 말은 넣지 않음(카드 이름만 넣음)
- 함께 고침: [기록정보] 버전 v3 → v4, 강사용 상담근거_대조표.jsonl의 같은 발화 인용, 생성검증.json 발화 통계와 source_version
원문과 강사용 파일은 CRLF라 bytes로 읽고 써서 줄끝을 지킴.
실행: python add_card_names.py --plan  → output/card_name_plan.json(바꾸지 않음)
      python add_card_names.py --apply → 계획대로 원문과 강사용 파일을 고침
"""

from __future__ import annotations

import difflib
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
LAB = HERE.parents[2]
sys.path.insert(0, str(LAB / "indexer" / "graphrag" / "v0"))
from common import make_llm  # noqa: E402

DOCS = LAB / "docs"
INSTR = DOCS / "_instructor" / "D3"
PLAN = HERE.parent / "output" / "card_name_plan.json"
CRLF = "\r\n"


def copy_table(name: str) -> list[list[str]]:
    rows, on = [], False
    for line in (LAB / "rdb" / "init" / "02_seed.sql").read_text(encoding="utf-8").splitlines():
        if line.startswith(f"COPY {name} "):
            on = True
            continue
        if on and line.startswith("\\."):
            break
        if on:
            rows.append(line.split("\t"))
    return rows


def held_cards() -> dict[str, list[str]]:
    names = {r[0]: r[1] for r in copy_table("product")}
    out: dict[str, list[str]] = {}
    for r in copy_table("card"):  # card_id, member_id, product_id, brand, issue_date, status
        if r[5] == "ACTIVE":
            out.setdefault(r[1], [])
            if names[r[2]] not in out[r[1]]:
                out[r[1]].append(names[r[2]])
    return out


def eval_cited() -> set[str]:
    found: set[str] = set()

    def walk(x):
        if isinstance(x, str) and len(x) >= 6:
            found.add(x)
        elif isinstance(x, dict):
            for v in x.values():
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)

    walk(json.loads((LAB / "ragas" / "eval-set.json").read_text(encoding="utf-8")))
    walk(json.loads((LAB / "indexer" / "vector-bm25" / "evaluation" / "group2_questions.json").read_text(encoding="utf-8")))
    return found


def records() -> list[dict]:
    out = []
    for f in sorted(DOCS.glob("D3_S0*.txt")):
        lines = f.read_bytes().decode("utf-8").split(CRLF)
        cur = None
        for i, line in enumerate(lines):
            m = re.match(r"\[상담ID\] (C-\d+-\d+) .*회원번호: (M-\d+)", line)
            if m:
                cur = {"file": f.name, "record_id": m.group(1), "member": m.group(2), "topic": "", "lines": []}
                out.append(cur)
            elif cur and line.startswith("[상담주제]"):
                cur["topic"] = line.split("]", 1)[1].strip()
            elif cur and line.startswith(("고객:", "상담사:")):
                cur["lines"].append((i, line))
    return out


def only_inserted(old: str, new: str) -> str | None:
    """new가 old에 글자를 끼워 넣기만 했으면 넣은 글을, 아니면 None을 돌려줌."""

    ops = difflib.SequenceMatcher(a=old, b=new, autojunk=False).get_opcodes()
    if any(tag not in ("equal", "insert") for tag, *_ in ops):
        return None
    return "".join(new[j1:j2] for tag, _, _, j1, j2 in ops if tag == "insert")


SYSTEM = ("너는 교육용 합성 상담 기록을 고치는 편집자다. 상담사 발화 한 줄에 고객의 보유 카드 이름을 자연스럽게 끼워 넣는다. "
          "규칙: 고를 줄 하나와 카드 하나를 정한다. 원래 글자는 하나도 지우거나 바꾸지 않고 '고객님의 한빛 ○○ 카드', "
          "'한빛 ○○ 카드' 같은 짧은 구만 끼워 넣는다. 혜택 크기, 자격, 승인 여부를 약속하는 말은 넣지 않는다. "
          "상담 주제와 맞는 카드를 고르고, 맞는 것이 없으면 첫 카드를 쓴다. "
          'JSON 하나로만 답한다: {"line_no": <후보 번호>, "card": "<카드 이름>", "new_line": "<고친 줄 전체>"}')


def plan() -> None:
    cards, cited = held_cards(), eval_cited()
    llm = make_llm()
    out = []
    for r in records():
        cands = [(i, l) for i, l in r["lines"] if l.startswith("상담사:")
                 and not any(c in l or l.split(":", 1)[1].strip() in c for c in cited)
                 and not re.search(r"승인 거래|합계|\d{3,}|가상", l)]
        held = cards.get(r["member"], [])
        rec = {"record_id": r["record_id"], "file": r["file"], "member": r["member"], "topic": r["topic"],
               "held": held, "candidates": len(cands)}
        for attempt in range(3):
            if not cands or not held:
                rec["error"] = "후보 줄 또는 보유 카드 없음"
                break
            prompt = (f"상담 주제: {r['topic']}\n보유 카드: {', '.join(held)}\n후보 상담사 발화:\n"
                      + "\n".join(f"{k}. {l}" for k, (_, l) in enumerate(cands)))
            try:
                ans = json.loads(llm.chat_json(prompt, system_instruction=SYSTEM))
                k, card, new = int(ans["line_no"]), ans["card"], ans["new_line"].strip()
                idx, old = cands[k]
                ins = only_inserted(old, new)
                ok = card in held and ins is not None and card in ins and len(ins) <= 25
                if ok:
                    rec.update(line_index=idx, old=old, new=new, card=card, inserted=ins, attempts=attempt + 1)
                    rec.pop("error", None)
                    break
                rec["error"] = f"검사 실패: card_ok={card in held}, inserted={ins!r}"
            except Exception as e:  # 응답 꼴 오류는 다시 물음
                rec["error"] = f"{type(e).__name__}: {str(e)[:120]}"
        out.append(rec)
        print(rec["record_id"], rec.get("card"), "|", rec.get("inserted") or rec.get("error"), flush=True)
    PLAN.parent.mkdir(parents=True, exist_ok=True)
    PLAN.write_text(json.dumps({"edits": out, "llm_usage": dict(llm.usage)}, ensure_ascii=False, indent=2), encoding="utf-8")
    print("계획", sum("new" in e for e in out), "/", len(out))


SUMMARY = [  # 상담마다 있는 상담사 마무리 발화와 카드 이름 구를 끼워 넣을 자리(앞, 뒤)
    (re.compile(r"^상담사: 이번 요청에 대해 ‘.*’ 내용을 기록하겠습니다\.$"), "내용을 ", "기록하겠습니다.", " 카드 상담으로 "),
    (re.compile(r"^상담사: 앞선 기록과 연결하고, 이번에는 ‘.*’ 내용으로 정리하겠습니다\.$"), "내용으로 ", "정리하겠습니다.",
     " 카드 상담 기록에 "),
]
DUPLICATE = ["한빛 하늘여정", "한빛 자유여행"]  # 카드 중복 상담: 고객이 "같은 역할을 하는 두 장"이라 한 여행 카드 두 장


def plan_rule() -> None:
    """LLM 없이 규칙으로 계획함. LLM은 원래 글자를 자주 바꿔 48건 중 15건만 검사를 통과했음(2026-10-23 실측)."""

    cards, cited = held_cards(), eval_cited()
    products = {r[1]: r[0] for r in copy_table("product")}
    out = []
    for r in records():
        held = sorted(cards.get(r["member"], []), key=lambda n: products[n])
        chosen = DUPLICATE if r["topic"] == "카드 중복" and all(c in held for c in DUPLICATE) else held[:1]
        rec = {"record_id": r["record_id"], "file": r["file"], "member": r["member"], "topic": r["topic"], "held": held}
        for idx, line in r["lines"]:
            hit = next(((a, b, tail) for pat, a, b, tail in SUMMARY if pat.match(line)), None)
            if not hit or any(c in line or line.split(":", 1)[1].strip() in c for c in cited):
                continue
            a, b, tail = hit
            new = line.replace(a + b, a + " 카드와 ".join(chosen) + tail + b, 1)
            ins = only_inserted(line, new)
            if ins and all(c in ins for c in chosen):
                rec.update(line_index=idx, old=line, new=new, card=", ".join(chosen), inserted=ins)
                break
        if "new" not in rec:
            rec["error"] = "마무리 발화를 찾지 못함"
        out.append(rec)
        print(rec["record_id"], rec.get("card"), "|", rec.get("new", rec.get("error")), flush=True)
    PLAN.parent.mkdir(parents=True, exist_ok=True)
    PLAN.write_text(json.dumps({"method": "규칙(마무리 발화에 카드 이름 구 삽입)", "edits": out}, ensure_ascii=False, indent=2),
                    encoding="utf-8")
    print("계획", sum("new" in e for e in out), "/", len(out))


def apply() -> None:
    edits = [e for e in json.loads(PLAN.read_text(encoding="utf-8"))["edits"]]
    if any("new" not in e for e in edits):
        raise SystemExit("계획에 실패한 상담이 있어 적용하지 않음")
    by_file: dict[str, list[dict]] = {}
    for e in edits:
        by_file.setdefault(e["file"], []).append(e)
    for name, es in by_file.items():
        path = DOCS / name
        lines = path.read_bytes().decode("utf-8").split(CRLF)
        for e in es:
            assert lines[e["line_index"]] == e["old"], (name, e["record_id"])
            lines[e["line_index"]] = e["new"]
        text = CRLF.join(lines)
        text = re.sub(r"(\[기록정보\][^\r\n]*버전: )v3", r"\1v4", text)
        path.write_bytes(text.encode("utf-8"))
    # 강사용 대조표: 같은 발화 인용을 새 글로 바꿈
    tpath = INSTR / "상담근거_대조표.jsonl"
    raw = tpath.read_bytes().decode("utf-8")
    nl = CRLF if CRLF in raw else "\n"
    rows = [json.loads(x) for x in raw.split(nl) if x.strip()]
    olds = {e["record_id"]: (e["old"].split(":", 1)[1].strip(), e["new"].split(":", 1)[1].strip()) for e in edits}
    changed = 0
    for row in rows:
        o, n = olds[row["record_id"]]
        for k, v in row.items():
            if isinstance(v, str) and o in v:
                row[k] = v.replace(o, n)
                changed += 1
            elif isinstance(v, list):
                new_v = [x.replace(o, n) if isinstance(x, str) and o in x else x for x in v]
                changed += sum(a != b for a, b in zip(v, new_v))
                row[k] = new_v
        row["source_version"] = "v4"
    tpath.write_bytes((nl.join(json.dumps(r, ensure_ascii=False) for r in rows) + nl).encode("utf-8"))
    # 생성검증: 발화 통계 다시 셈
    utts = [l.split(":", 1)[1].strip() for r in records() for _, l in r["lines"]]
    gpath = INSTR / "생성검증.json"
    graw = gpath.read_bytes().decode("utf-8")
    g = json.loads(graw)
    g.update(utterances=len(utts), unique_utterances=len(set(utts)), source_version="v4")
    gnl = CRLF if CRLF in graw else "\n"
    gpath.write_bytes(json.dumps(g, ensure_ascii=False, indent=2).replace("\n", gnl).encode("utf-8") + (gnl.encode() if graw.endswith(gnl) else b""))
    print("원문", len(edits), "줄 고침, 대조표 인용", changed, "곳 고침, 발화", len(utts), "개 중 서로 다른 발화", len(set(utts)))


if __name__ == "__main__":
    {"--plan": plan_rule, "--plan-llm": plan, "--apply": apply}[sys.argv[1]]()
