"""소스 파일에서 행 범위를 그대로 잘라 snippets.json으로 만듦 — 슬라이드 발췌가 소스와 글자까지 같게 하려는 것.

python extract.py  → snippets.json (+ 화면에 발췌별 줄 수 · 가장 긴 줄)
docstring 블록은 빼고, 이어지지 않는 구간 사이에는 '# …(생략)' 줄을 넣음.
"""

import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2] / "hybrid-ai-lab"
RAGAS = "ragas/"
RET = "retriever/vector-retriever/"

# 이름: (파일, [(시작행, 끝행), ...], docstring 빼기)
SPECS = {
    "ports": (RAGAS + "app/application/ports.py", [(85, 98), (128, 134)], False),
    "bootstrap": (RAGAS + "app/bootstrap.py", [(48, 55), (63, 76)], True),
    "fake_indexer": (RAGAS + "tests/fakes.py", [(92, 112)], True),
    "test_restore": (RAGAS + "tests/test_runner.py", [(60, 71)], True),
    "cli_main": (RAGAS + "app/presentation/cli.py", [(76, 82), (108, 114), (119, 126)], True),
    "settings": (RAGAS + "app/infrastructure/settings.py", [(51, 62), (93, 98)], True),
    "atomic": (RAGAS + "app/infrastructure/files.py", [(25, 38), (182, 192)], True),
    "parse_md": (RAGAS + "app/domain/eval_set.py", [(42, 42), (53, 61), (64, 73), (80, 81)], True),
    "check_index": (RAGAS + "app/domain/verification.py", [(110, 110), (118, 120), (128, 144)], True),
    "check_plan": (RAGAS + "app/domain/plan.py", [(62, 62), (72, 86), (97, 102)], True),
    "run": (RAGAS + "app/application/runner_service.py", [(180, 190), (195, 198), (204, 208)], True),
    "run_version": (RAGAS + "app/application/runner_service.py", [(268, 282), (311, 318)], True),
    "restore": (RAGAS + "app/application/runner_service.py", [(221, 243)], True),
    "apply": (RAGAS + "app/application/runner_service.py", [(361, 381)], True),
    "subprocess": (RAGAS + "app/infrastructure/processes.py", [(19, 20), (28, 44)], True),
    "score_hits": (RET + "evaluate_retriever.py", [(84, 106)], True),
    "split_rows": (RAGAS + "app/domain/scoring.py", [(13, 19), (36, 58)], True),
    "score_rows": (RAGAS + "app/application/ragas_service.py", [(27, 28), (36, 52)], True),
    "judge": (RAGAS + "app/infrastructure/ragas_judge.py", [(52, 52), (63, 80)], True),
    "anthropic": (RAGAS + "app/infrastructure/anthropic_llm.py", [(30, 52)], True),
    "kappa": (RAGAS + "app/domain/scoring.py", [(104, 132)], True),
    "compare": (RAGAS + "app/application/compare_service.py", [(124, 130), (137, 148)], True),
    "plan_yaml": (RAGAS + "plans/top_k.yaml", [(1, 27)], False),
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


def extract(path: str, ranges: list[tuple[int, int]], no_doc: bool) -> dict:
    """행 범위를 잘라 발췌 글과 머리말을 만듦."""

    source = (ROOT / path).read_text(encoding="utf-8").splitlines()
    picked: list[tuple[int, str]] = []
    ranges = [(start, min(end, len(source))) for start, end in ranges]  # 파일 끝을 넘는 범위는 끝까지로 자름
    for index, (start, end) in enumerate(ranges):
        block = [(no, source[no - 1]) for no in range(start, end + 1)]
        if no_doc:
            block = strip_docstrings(block)
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
    label = ", ".join(f"{a}-{b}" for a, b in ranges)
    omitted = len(ranges) > 1 or no_doc
    return {"path": path, "ranges": ranges, "header": f"{path.replace(RAGAS, '').replace('retriever/', 'retriever/')}:{label}"
            + (" (docstring · 일부 생략)" if omitted else ""), "lines": lines}


def main() -> None:
    result = {name: extract(*spec) for name, spec in SPECS.items()}
    Path(__file__).with_name("snippets.json").write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    for name, item in result.items():
        width = max(len(line) for line in item["lines"])
        print(f"{name:14} {len(item['lines']):3}줄  최장 {width:3}자  {item['header']}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
