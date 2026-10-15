"""소스 파일에서 행 범위를 그대로 잘라 snippets.json으로 만듦 — 슬라이드 발췌가 소스와 글자까지 같게 하려는 것.

python extract.py  → snippets.json (+ 화면에 발췌별 줄 수와 가장 긴 줄)
docstring 블록은 빼고(no_doc), 한 줄 전체가 주석인 줄도 뺄 수 있음(no_comment).
이어지지 않는 구간 사이에는 '# …(생략)' 줄을 넣음.
"""

import json
from pathlib import Path
import re
import sys

ROOT = Path.home() / "workspace" / "crc" / "sql-retriever"
A, D, I, P = "app/application/", "app/domain/", "app/infrastructure/", "app/presentation/"

# 이름: (파일, [(시작행, 끝행), ...], docstring 빼기, 주석 줄 빼기)
SPECS = {
    "ports": (A + "ports.py", [(20, 31), (74, 84)], False, False),
    "bootstrap": ("app/bootstrap.py", [(20, 29), (37, 55)], True, False),
    "cli": (P + "cli.py", [(35, 45)], False, False),
    "api": (P + "api.py", [(53, 62)], True, False),
    "service": (A + "services.py", [(25, 25), (31, 51)], True, False),
    "graph": (I + "graph.py", [(24, 44), (46, 48)], True, False),
    "state": (A + "models.py", [(157, 171), (192, 195)], True, False),
    "budget": (D + "time_budget.py", [(8, 12), (38, 49), (52, 65)], True, False),
    "settings": (I + "settings.py", [(46, 50), (52, 57), (64, 74)], True, False),
    "r1_check": (A + "steps.py", [(135, 148)], True, False),
    "masking": (D + "masking.py", [(11, 21)], False, True),
    "r1_member": (I + "postgres_repository.py", [(24, 28), (31, 33), (73, 84)], True, True),
    "r2": (A + "steps.py", [(190, 192), (202, 215), (218, 220)], True, False),
    "groq": (I + "groq_planner.py", [(26, 31), (82, 98)], False, False),
    "schema": (I + "groq_planner.py", [(35, 59)], False, False),
    "user_prompt": (I + "prompts/c01_user_prompt.md", [(1, 6)], False, False),
    "groq_fail": (I + "groq_planner.py", [(107, 124), (126, 132)], True, False),
    "judge": (A + "steps.py", [(253, 276)], True, False),
    "period": (D + "periods.py", [(25, 25), (32, 51)], True, False),
    "validate": (I + "sql_validator.py", [(80, 95), (104, 107)], True, True),
    "tables": (I + "sql_validator.py", [(139, 155), (180, 186)], True, False),
    "tx": (I + "postgres_repository.py", [(135, 146), (160, 163), (177, 181)], True, False),
    "execute": (I + "postgres_repository.py", [(105, 114)], True, False),
    "r5": (A + "steps.py", [(349, 361)], True, False),
    "r6": (A + "steps.py", [(386, 398)], True, False),
    "message": (D + "messages.py", [(19, 24)], True, False),
}


def strip_docstrings(lines: list[tuple[int, str]]) -> list[tuple[int, str]]:
    """세 따옴표 docstring 블록을 뺌(한 줄짜리 포함). 바로 뒤 빈 줄 하나도 뺌."""

    out, inside, skip_blank = [], False, False
    for no, text in lines:
        stripped = text.strip()
        if not inside and stripped.startswith('"""'):
            if stripped.count('"""') >= 2 and len(stripped) > 3:
                skip_blank = True
                continue
            inside = True
            continue
        if inside:
            if '"""' in stripped:
                inside, skip_blank = False, True
            continue
        if skip_blank and not stripped:
            skip_blank = False
            continue
        skip_blank = False
        out.append((no, text))
    return out


def extract(path: str, ranges: list[tuple[int, int]], no_doc: bool, no_comment: bool) -> dict:
    """행 범위를 잘라 발췌 글과 머리말을 만듦."""

    source = (ROOT / path).read_text(encoding="utf-8").splitlines()
    picked: list[tuple[int, str]] = []
    for index, (start, end) in enumerate(ranges):
        if end > len(source):
            raise ValueError(f"{path}: 파일 끝({len(source)}행)을 넘는 범위 {start}-{end}")
        block = [(no, source[no - 1]) for no in range(start, end + 1)]
        if no_doc:
            block = strip_docstrings(block)
        if no_comment:
            block = [(no, text) for no, text in block if not text.strip().startswith("#")]
        while block and not block[-1][1].strip():
            block.pop()
        if index > 0 and block:
            indent = re.match(r"\s*", block[0][1]).group(0)
            picked.append((0, f"{indent}# …(생략)"))
        picked.extend(block)
    # 공통 들여쓰기는 걷어 내 화면 폭을 아낌(상대 들여쓰기는 그대로)
    indents = [len(t) - len(t.lstrip()) for _, t in picked if t.strip()]
    cut = min(indents) if indents else 0
    lines = [t[cut:] if len(t) >= cut else t for _, t in picked]
    label = ", ".join(f"{a}-{b}" if a != b else f"{a}" for a, b in ranges)
    omitted = [name for name, on in (("docstring", no_doc), ("주석", no_comment), ("구간", len(ranges) > 1)) if on]
    notes = [", ".join(omitted) + " 생략"] if omitted else []
    if cut:
        notes.append("들여쓰기 축소")
    header = f"{path}:{label}" + (f"  ({' / '.join(notes)})" if notes else "")
    return {"path": path, "ranges": ranges, "header": header, "lines": lines}


def main() -> None:
    result = {name: extract(*spec) for name, spec in SPECS.items()}
    Path(__file__).with_name("snippets.json").write_text(json.dumps(result, ensure_ascii=False, indent=1),
                                                         encoding="utf-8")
    for name, item in result.items():
        width = max(len(line) for line in item["lines"])
        print(f"{name:12} {len(item['lines']):3}줄  최장 {width:3}자  {item['header']}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
