"""검사 규칙 원본이 1벌뿐이고 ⑥ 행 수와 1:1인지 확인함(11단계 시험 8번)."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from common.guardrail.rules import (
    RuleBookInvalid,
    default_rules_path,
    load_rulebook,
)

SRC_DIRS = (
    Path(__file__).resolve().parent.parent / "guardrail",
    Path(__file__).resolve().parent.parent / "observability",
)


def _source_files() -> list[Path]:
    files: list[Path] = []
    for folder in SRC_DIRS:
        files.extend(sorted(folder.glob("*.py")))
    return files


def _code_lines(path: Path) -> list[tuple[int, str]]:
    """설명글(독스트링)과 주석을 뺀 **코드 줄만** 돌려줌."""
    out: list[tuple[int, str]] = []
    in_doc = False
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        stripped = line.strip()
        if in_doc:
            if stripped.endswith('"""'):
                in_doc = False
            continue
        if stripped.startswith('"""'):
            if not (stripped.endswith('"""') and len(stripped) > 3):
                in_doc = True
            continue
        if stripped.startswith("#") or not stripped:
            continue
        out.append((lineno, line.split("#", 1)[0]))
    return out


def test_rules_file_is_the_only_one() -> None:
    """규칙 원본 파일이 코드 루트에 **1개**뿐임."""
    root = Path(__file__).resolve().parent.parent.parent
    found = sorted(p for p in root.rglob("guardrail_rules.toml") if ".venv" not in p.parts)
    assert found == [default_rules_path()], f"규칙 원본이 여러 곳에 있음: {found}"


def test_row_counts_match_design(rulebook) -> None:
    counts = rulebook.counts
    assert len(rulebook.block_rules) == counts["block_rule"] == 32
    assert len(rulebook.output_checks) == counts["output_check"] == 11
    assert len(rulebook.input_checks) == counts["input_check"] == 14
    assert len(rulebook.mask_rules) == counts["mask_rule"] == 24
    assert len(rulebook.approval_tools) == counts["approval_tool"] == 15
    assert len(rulebook.human_gate_tools()) == counts["human_gate_tool"] == 3
    assert len(rulebook.record_points) == counts["record_point"] == 15
    assert len(rulebook.pattern_steps) == counts["pattern_step"] == 90


def test_block_rule_ids_are_b1_to_b32(rulebook) -> None:
    assert [row["id"] for row in rulebook.block_rules] == [f"B-{i}" for i in range(1, 33)]


def test_no_rule_condition_defined_twice(rulebook) -> None:
    """같은 조건이 두 차단 규칙에 정의된 건수 0건."""
    signals = [row["signal"] for row in rulebook.block_rules]
    dupes = sorted({s for s in signals if signals.count(s) > 1})
    assert dupes == [], f"같은 조건이 두 곳에 정의됨: {dupes}"


def test_no_regex_literal_in_source() -> None:
    """정규식은 설정 파일에만 있음 — 소스에 검사 정규식을 박지 않음."""
    offenders: list[str] = []
    for path in _source_files():
        for lineno, line in _code_lines(path):
            if re.search(r"re\.compile\(\s*[rf]?['\"]", line):
                offenders.append(f"{path.name}:{lineno}")
    assert offenders == [], f"소스에 박힌 정규식: {offenders}"


def test_no_hardcoded_thresholds_in_source() -> None:
    """코드에 박힌 시간 상한·비용 숫자 0건. 4자리 이상 숫자를 소스에서 찾지 않음."""
    offenders: list[str] = []
    for path in _source_files():
        for lineno, line in _code_lines(path):
            for match in re.finditer(r"\b\d{3,}\b", line):
                offenders.append(f"{path.name}:{lineno} → {match.group()}")
    assert offenders == [], f"소스에 박힌 숫자: {offenders}"


def test_no_observability_product_name_in_source() -> None:
    """코드에 박힌 관측 제품 이름 0건."""
    banned = (
        "jaeger", "zipkin", "datadog", "newrelic", "new relic", "grafana", "tempo",
        "honeycomb", "lightstep", "signoz", "elastic", "splunk", "dynatrace",
        "cloudwatch", "stackdriver", "xray", "sentry", "prometheus", "loki",
    )
    offenders: list[str] = []
    for path in _source_files():
        lowered = path.read_text(encoding="utf-8").lower()
        offenders.extend(f"{path.name} → {name}" for name in banned if name in lowered)
    assert offenders == [], f"제품 이름이 코드에 박혔음: {offenders}"


def test_no_secret_literal_in_rules_file() -> None:
    """규칙 원본에 실제 열쇠·토큰·비밀번호가 없음. 자리표시 이름만 씀."""
    text = default_rules_path().read_text(encoding="utf-8")
    for banned in ("sk-", "Bearer ", "password =", "secret ="):
        assert banned not in text, f"규칙 원본에 비밀값 같은 글이 있음: {banned}"


def test_boot_fails_when_counts_disagree(tmp_path: Path) -> None:
    """규칙을 못 읽으면 뜨는 시점에 실패함 — 검사 없이 도는 상태를 만들지 않음."""
    text = default_rules_path().read_text(encoding="utf-8")
    broken = text.replace("block_rule = 32", "block_rule = 99", 1)
    target = tmp_path / "broken.toml"
    target.write_text(broken, encoding="utf-8")
    with pytest.raises(RuleBookInvalid, match="1:1 대응이 깨졌"):
        load_rulebook(target)


def test_boot_fails_when_file_missing(tmp_path: Path) -> None:
    with pytest.raises(RuleBookInvalid, match="찾지 못했음"):
        load_rulebook(tmp_path / "없는파일.toml")


def test_every_masking_row_has_all_four_record_paths(rulebook) -> None:
    """마스킹 24행 전건이 기록 4경로를 하나도 빼지 않고 다룸."""
    from common.guardrail.masking import RECORD_PATHS

    missing: list[str] = []
    for row in rulebook.mask_rules:
        declared = set(row.get("paths", ())) | set((row.get("path_overrides") or {}).keys())
        for path in RECORD_PATHS:
            if path.value not in declared:
                missing.append(f"{row['id']}:{path.value}")
    assert missing == [], f"기록 경로가 빠진 마스킹 행: {missing}"


def test_unconfirmed_rows_are_counted(rulebook) -> None:
    """`[확인필요]` 행이 실제로 있고 세어짐 — README 목록과 대조할 근거."""
    rows = rulebook.unconfirmed_rows()
    assert rows, "`[확인필요]` 행을 하나도 세지 못했음"


def test_readme_unconfirmed_table_matches_config(rulebook) -> None:
    """`[확인필요]` 건수를 숫자로 적었고 **README 목록의 행 수와 같음**(자가 점검 10번)."""
    canonical = rulebook.raw["unconfirmed"]
    readme = Path(__file__).resolve().parent.parent / "guardrail" / "README.md"
    text = readme.read_text(encoding="utf-8")

    section = text.split("## 7. `[확인필요]` 목록")[1].split("\n## ")[0]
    numbered = re.findall(r"^\|\s*(\d+)\s*\|", section, flags=re.MULTILINE)
    assert len(numbered) == len(canonical), (
        f"README 목록 {len(numbered)}행 ≠ 설정 `[[unconfirmed]]` {len(canonical)}행"
    )
    assert numbered == [str(i) for i in range(1, len(canonical) + 1)]
    assert f"**{len(canonical)}건**" in section, "README 머리에 건수를 숫자로 적지 않았음"

    # 태그 글이 설정과 README 양쪽에 같은 순서로 있음
    for index, row in enumerate(canonical, 1):
        head = str(row["tag"]).split(" —")[0].split("(")[0].strip()
        assert head in section, f"{index}번 태그 `{head}`가 README 목록에 없음"


def test_readme_declares_unverified_state(rulebook) -> None:
    """실제 측정을 안 했으므로 산출물 머리에 `미검증 설계`라고 적었음."""
    readme = Path(__file__).resolve().parent.parent / "guardrail" / "README.md"
    first_line = readme.read_text(encoding="utf-8").splitlines()[0]
    assert "미검증 설계" in first_line
    assert rulebook.verification_state == "미검증 설계"
