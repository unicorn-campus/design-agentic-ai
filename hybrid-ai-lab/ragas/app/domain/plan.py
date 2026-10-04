"""버전 정의(계획 파일)의 실행 전 검사 규칙 · 대상 키 해석 · 실행 ID 규칙."""

from __future__ import annotations

import copy
from dataclasses import dataclass
import re
from typing import Any

APPLY_KINDS = ("config_file", "env", "code_arg")
TOOLS = ("indexer", "retriever")  # 이번 실행기가 값을 바꿀 수 있는 도구(ragas · review는 채점 쪽이라 바꿀 값이 없음)
EMBED_MAX_TOKENS = 800  # 인덱서 임베딩 입력 상한 — 청크 크기가 이보다 크면 인덱서가 ValueError로 멈춤

# 대상 키별 허용 범위(인덱서 · 리트리버 소스의 검사 값을 옮김). 범위 밖은 색인 전에 거부함
RANGES: dict[str, tuple[float, float]] = {
    "defaults.chunk_size": (1, EMBED_MAX_TOKENS),
    "--top-k": (1, 10),  # 후보 수 = top_k × 2 × 4, 리트리버 요청 검사가 1 ~ 10
    "GRADE_UPPER": (0.0, 1.0),
    "GRADE_LOWER": (0.0, 1.0),
    "GRADE_MIN_GAP": (0.0, 1.0),
    "GRADE_OVERLAP_WAIVER": (0.0, 1.0),
    "HYBRID_VECTOR_WEIGHT": (0.0, 1.0),
    "HYBRID_BM25_WEIGHT": (0.0, 1.0),
    "MAX_TURNS": (1, 50),
    "MAX_LLM_CALLS": (1, 200),
    "MAX_REWRITES": (0, 10),
}
_TARGET = re.compile(r"^(?P<tool>[a-z_]+):(?P<kind>config|env|arg|code):(?P<rest>.+)$")
_KIND_OF_APPLY = {"config_file": "config", "env": "env", "code_arg": "arg"}


@dataclass(frozen=True)
class Target:
    """한 줄 주소 '{도구}:{종류}:{대상}'을 나눈 값."""

    tool: str
    kind: str  # config · env · arg · code(아직 못 꺼낸 코드 값)
    path: str  # config면 파일 경로, 나머지는 빈 값
    key: str  # config면 JSON 경로, env면 환경변수 이름, arg면 인자 이름


def parse_target(text: str) -> Target:
    """대상 키 주소를 나눔.

    예시: "indexer:config:config/document_policies.json#defaults.chunk_size"
          → Target("indexer", "config", "config/document_policies.json", "defaults.chunk_size")
    예외: 꼴이 맞지 않으면 ValueError.
    """

    match = _TARGET.match(text.strip())
    if not match:
        raise ValueError(f"대상 키 꼴이 '{{도구}}:{{종류}}:{{대상}}'이 아닙니다: {text}")
    tool, kind, rest = match.group("tool"), match.group("kind"), match.group("rest")
    if kind in {"config", "code"}:
        if "#" not in rest:
            raise ValueError(f"config · code 대상은 '파일#키' 꼴이어야 합니다: {text}")
        path, key = rest.split("#", 1)
        return Target(tool, kind, path, key)
    return Target(tool, kind, "", rest)


def check_plan(plan: dict[str, Any]) -> tuple[list[str], list[str]]:
    """계획 파일을 실행 전에 검사해 (거부 사유, 미지원 사유)를 돌려줌.

    거부(V1 ~ V4 · V10 · V11): 하나라도 있으면 아무것도 실행하지 않음.
    미지원(V7-1): 그 계획의 버전을 모두 건너뜀 — 실패가 아니라 '아직 바꾸는 방법이 없음'임.
    V5 · V6(평가셋) · V8 · V9(도구 지원) · V12 ~ V14(포인터 · 잠금 · 서버)는 파일 · 프로세스를 봐야 해서 서비스가 검사함.
    """

    rejects: list[str] = []
    unsupported: list[str] = []
    apply = plan.get("apply")
    if apply not in APPLY_KINDS:
        rejects.append(f"V4 apply는 {APPLY_KINDS} 중 하나여야 합니다: {apply}")
    try:
        target = parse_target(str(plan.get("target", "")))
    except ValueError as error:
        return [*rejects, f"V4 {error}"], unsupported
    if target.tool not in TOOLS:
        rejects.append(f"V4 바꿀 수 있는 도구는 {TOOLS}뿐입니다: {target.tool}")
    if target.kind == "code":
        unsupported.append(f"V9 코드에 박힌 값은 아직 인자로 꺼내지 않았습니다: {target.key}")
    elif apply in _KIND_OF_APPLY and _KIND_OF_APPLY[apply] != target.kind:
        rejects.append(f"V4 apply({apply})와 대상 종류({target.kind})가 맞지 않습니다")
    if target.kind == "config" and not target.key.startswith("defaults."):
        unsupported.append(f"V7-1 인덱서는 defaults만 읽습니다(유형별 값은 코드 수정 필요): {target.key}")

    versions = plan.get("versions") or []
    ids = [str(v.get("id")) for v in versions]
    baseline = plan.get("baseline")
    if len(set(ids)) != len(ids):
        rejects.append("V3 versions의 id가 겹칩니다(버전 폴더가 덮어써짐)")
    if baseline not in [v.get("value") for v in versions]:
        rejects.append(f"V2 기준 값 {baseline}이 versions에 없습니다")
    if not plan.get("hyperparameter"):
        rejects.append("V1 hyperparameter 이름이 없습니다")
    low_high = RANGES.get(target.key)
    for version in versions:
        value = version.get("value")
        if low_high and not (isinstance(value, (int, float)) and low_high[0] <= value <= low_high[1]):
            rejects.append(f"V10 · V11 {target.key} 값 {value}이 허용 범위 {low_high[0]} ~ {low_high[1]} 밖입니다")
    return rejects, unsupported


def ordered_versions(plan: dict[str, Any], only: list[str] | None = None) -> list[dict[str, Any]]:
    """기준 버전을 맨 앞에 두고 나머지는 계획 파일 순서대로 줄 세움.

    목적: 기준이 없으면 Δ를 못 내므로 기준을 먼저 돌림. only가 있으면 그 id만 남김(기준은 항상 포함).
    """

    baseline = plan["baseline"]
    versions = [v for v in plan["versions"] if only is None or str(v["id"]) in only or v["value"] == baseline]
    return sorted(versions, key=lambda v: (v["value"] != baseline,))


def thread_id(hyperparameter: str, version_id: str, run_date: str) -> str:
    """버전마다 다른 색인 실행 ID를 만듦 — 세대가 'gen-{thread-id}-{해시8}'로 나뉨(설계 가정 형식)."""

    return f"exp-{hyperparameter}-{version_id}-{run_date}"


def leaf_differences(left: Any, right: Any, prefix: str = "") -> list[str]:
    """두 JSON 값의 끝 값이 다른 경로 목록을 돌려줌.

    목적: 설정 복사본이 원본과 '대상 키 1개만' 다른지 확인함(V1 — 한 번에 하나만 바꿈).
    """

    if isinstance(left, dict) and isinstance(right, dict):
        keys = sorted(set(left) | set(right))
        return [d for k in keys for d in leaf_differences(left.get(k), right.get(k), f"{prefix}{k}.")]
    return [] if left == right else [prefix.rstrip(".")]


def set_json_path(document: dict[str, Any], dotted: str, value: Any) -> dict[str, Any]:
    """점 표기 경로의 값을 바꾼 새 dict를 돌려줌(원본은 그대로 둠).

    예외: 경로 중간이나 마지막 키가 원본에 없으면 KeyError — 없는 키를 새로 만들면 인덱서가 읽지 않는 값이 됨.
    """

    result = copy.deepcopy(document)
    node = result
    parts = dotted.split(".")
    for part in parts[:-1]:
        node = node[part]
    if parts[-1] not in node:
        raise KeyError(dotted)
    node[parts[-1]] = value
    return result
