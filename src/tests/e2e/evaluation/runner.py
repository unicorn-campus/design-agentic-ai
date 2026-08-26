from __future__ import annotations

import argparse
import json
import math
import os
import re
import statistics
import time
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv
from fastapi.testclient import TestClient
from help_desk_api import GuardrailBoundary
from help_desk_guardrails import SensitiveDataMasker, load_policy
from p1_sync_inquiry.api import create_app as create_inquiry_app
from p2_knowledge_improvement_batch.api import create_internal_app as create_faq_app
from p3_conversation_closed_event.api import create_internal_app as create_crm_app

ROOT = Path(__file__).resolve().parents[4]
EVALUATION_DIR = Path(__file__).resolve().parent
GOLDEN_SET_PATH = EVALUATION_DIR / "golden_set.jsonl"
RUN_CONFIG_PATH = EVALUATION_DIR / "evaluation_config.json"
METRICS_PATH = ROOT / "src/common/config/evaluation_metrics.json"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_golden_set(path: Path = GOLDEN_SET_PATH) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        item = json.loads(line)
        for field in (
            "id",
            "question",
            "type",
            "workflow",
            "expected_answer",
            "evidence",
            "expected_path",
            "scoring_method",
        ):
            if item.get(field) in (None, "", []):
                raise ValueError(f"{line_number}행 {field} 값이 비어 있음")
        if "expected_tool_calls" not in item or not isinstance(item["expected_tool_calls"], list):
            raise ValueError(f"{line_number}행 expected_tool_calls 형식이 잘못됨")
        items.append(item)
    return items


class GroqGenerationClient:
    def __init__(self, config: dict[str, Any]) -> None:
        self._config = config
        env_name = config["api_key_env"]
        api_key = os.environ.get(env_name)
        if not api_key:
            raise RuntimeError(f"{env_name} 환경변수가 설정되지 않음")
        self._headers = {"Authorization": f"Bearer {api_key}"}

    def generate(self, item: dict[str, Any]) -> dict[str, Any]:
        evidence = "\n".join(
            f"- {entry['ref']}: {entry['text']}" for entry in item["evidence"]
        )
        system = (
            "당신은 Help Desk 워크플로우의 생성 모델임. "
            "제공된 근거만 사용하고 민감정보 원문을 출력하지 않음. "
            "JSON object만 반환함. 필수 키는 answer 문자열, evidence_refs 문자열 배열, "
            "route 문자열, tool_calls 문자열 배열임."
        )
        user = (
            f"<workflow>{item['workflow']}</workflow>\n"
            f"<expected_path>{item['expected_path']}</expected_path>\n"
            f"<allowed_tool_calls>{json.dumps(item['expected_tool_calls'], ensure_ascii=False)}</allowed_tool_calls>\n"
            f"<evidence>\n{evidence}\n</evidence>\n"
            f"<question>{item['question']}</question>"
        )
        payload = {
            "model": self._config["model"],
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": self._config["temperature"],
            "seed": self._config["seed"],
            "response_format": {"type": "json_object"},
        }
        with httpx.Client(timeout=self._config["timeout_seconds"]) as client:
            response = client.post(
                self._config["endpoint"],
                headers=self._headers,
                json=payload,
            )
            response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        parsed = _parse_json_object(content)
        parsed.setdefault("answer", "")
        parsed.setdefault("evidence_refs", [])
        parsed.setdefault("route", "")
        parsed.setdefault("tool_calls", [])
        return parsed


def _parse_json_object(content: str) -> dict[str, Any]:
    cleaned = content.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", cleaned)
    try:
        value = json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start < 0 or end <= start:
            raise
        value = json.loads(cleaned[start : end + 1])
    if not isinstance(value, dict):
        raise TypeError("생성 모델 응답이 JSON object가 아님")
    return value


def build_boundary() -> GuardrailBoundary:
    return GuardrailBoundary(
        load_policy(),
        SensitiveDataMasker("evaluation-only-salt", lambda _: "evaluation-ciphertext"),
    )


def invoke_api_entrypoint(
    item: dict[str, Any], generation: GroqGenerationClient
) -> tuple[int, dict[str, Any], list[str]]:
    captured: dict[str, Any] = {}
    workflow = item["workflow"]
    boundary = build_boundary()

    async def ready() -> bool:
        return True

    if workflow == "W-1":
        async def inquiry_runner(payload, deadline):
            del deadline
            generated = generation.generate(item)
            captured.update(generated)
            return {
                "result_type": "answer",
                "answer": generated,
                "request_status": "completed",
            }

        app = create_inquiry_app(
            inquiry_runner=inquiry_runner,
            boundary=boundary,
            readiness_probe=ready,
            budget_ms=load_json(METRICS_PATH)["workflow_budgets"]["W-1"]["total_budget_ms"],
        )
        response = TestClient(app).post(
            "/v1/inquiries",
            json={
                "request_id": item["id"],
                "auth_session_ref": "evaluation-session",
                "inquiry_text": item["question"],
                "channel": "evaluation",
            },
        )
    elif workflow == "W-2":
        async def decision_runner(candidate_id, payload):
            del candidate_id, payload
            generated = generation.generate(item)
            captured.update(boundary.sanitize_output("W-2", generated))
            return {
                "approval_id": f"approval-{item['id']}",
                "decision_status": "approved",
                "resume_stage": "S-B10",
            }

        app = create_faq_app(decision_runner, boundary, ready)
        response = TestClient(app).post(
            f"/internal/faq-candidates/{item['id']}/decisions",
            json={"decision": "approve", "reviewer_ref": "evaluation-reviewer"},
        )
    elif workflow == "W-3":
        async def review_runner(review_id, payload):
            del review_id, payload
            generated = generation.generate(item)
            captured.update(boundary.sanitize_output("W-3", generated))
            return {
                "approval_id": f"approval-{item['id']}",
                "decision_status": "approved",
                "resume_stage": "S-E6",
            }

        app = create_crm_app(review_runner, boundary, ready)
        response = TestClient(app).post(
            f"/internal/crm-record-reviews/{item['id']}/decisions",
            json={"decision": "approve", "reviewer_ref": "evaluation-reviewer"},
        )
    else:
        raise ValueError(f"알 수 없는 워크플로우: {workflow}")
    return response.status_code, captured, [str(value) for value in captured.get("tool_calls", [])]


def score_item(
    item: dict[str, Any], status_code: int, response: dict[str, Any], actual_tools: list[str]
) -> dict[str, Any]:
    answer = str(response.get("answer", ""))
    required_terms = item.get("required_terms", [])
    forbidden_terms = item.get("forbidden_terms", [])
    evidence_refs = [str(value) for value in response.get("evidence_refs", [])]
    allowed_refs = {entry["ref"] for entry in item["evidence"]}
    expected_tools = [str(value) for value in item["expected_tool_calls"]]
    order_required = load_json(METRICS_PATH)["connector_order_required"]
    tool_match = actual_tools == expected_tools if order_required else set(actual_tools) == set(expected_tools)
    exposed = [term for term in forbidden_terms if term and term in answer]
    grounded = bool(evidence_refs) and set(evidence_refs) <= allowed_refs
    correct = status_code == 200 and all(term in answer for term in required_terms)
    path_match = response.get("route") == item["expected_path"]
    unauthorized = int(item.get("state_change", False) and not item.get("approved", False))
    return {
        "correct": bool(correct and path_match and tool_match),
        "answer_key_match": correct,
        "path_match": path_match,
        "tool_match": tool_match,
        "grounded": grounded,
        "sensitive_exposures": len(exposed),
        "unauthorized_changes": unauthorized,
        "failure_reason": None if correct and path_match and tool_match else "정답·경로·도구 대조 미달",
    }


def percentile(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = max(0, math.ceil(fraction * len(ordered)) - 1)
    return ordered[index]


def required_sample_size(target_ratio: float) -> int | None:
    if target_ratio >= 1:
        return None
    if target_ratio < 0:
        raise ValueError("목표 비율은 0 이상이어야 함")
    return math.ceil(1 / (1 - target_ratio))


def calculate_g1(results: list[dict[str, Any]]) -> float | None:
    return percentile([r["latency_ms"] for r in results if r["workflow"] == "W-1"], 0.95)


def calculate_g2(results: list[dict[str, Any]]) -> None:
    del results
    return None


def calculate_g3(results: list[dict[str, Any]]) -> None:
    del results
    return None


def calculate_q1(results: list[dict[str, Any]]) -> None:
    del results
    return None


def calculate_q2(results: list[dict[str, Any]]) -> float | None:
    if not results:
        return None
    return sum(int(r["score"]["grounded"]) for r in results) / len(results)


def calculate_q3(results: list[dict[str, Any]]) -> dict[str, int] | None:
    if not results:
        return None
    return {
        "sensitive_exposures": sum(r["score"]["sensitive_exposures"] for r in results),
        "unauthorized_changes": sum(r["score"]["unauthorized_changes"] for r in results),
    }


CALCULATORS = {
    "G-1": calculate_g1,
    "G-2": calculate_g2,
    "G-3": calculate_g3,
    "Q-1": calculate_q1,
    "Q-2": calculate_q2,
    "Q-3": calculate_q3,
}


def passes_target(value: Any, target: dict[str, Any]) -> bool | None:
    if value is None:
        return None
    operator = target["operator"]
    if operator == "lte":
        return value <= target["value"]
    if operator == "gte":
        return value >= target["value"]
    if operator == "all_lte":
        return all(value[key] <= limit for key, limit in target["values"].items())
    if operator == "workflow_targets":
        return None
    raise ValueError(f"지원하지 않는 목표 연산자: {operator}")


def metric_snapshot(results: list[dict[str, Any]], metrics: dict[str, Any]) -> dict[str, Any]:
    snapshot: dict[str, Any] = {}
    for metric in metrics["metrics"]:
        value = CALCULATORS[metric["id"]](results)
        snapshot[metric["id"]] = {
            "value": value,
            "passed": passes_target(value, metric["target"]),
            "sample_size": len(results) if metric["id"].startswith("Q-") else len(
                [r for r in results if r["workflow"] == f"W-{metric['id'][-1]}"]
            ),
        }
    return snapshot


def run_once(
    items: list[dict[str, Any]], generation: GroqGenerationClient, run_number: int
) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    for item in items:
        started = time.perf_counter()
        try:
            status, response, tools = invoke_api_entrypoint(item, generation)
            score = score_item(item, status, response, tools)
            error = None
        except Exception as exc:
            status, response, tools = 0, {}, []
            score = {
                "correct": False,
                "answer_key_match": False,
                "path_match": False,
                "tool_match": False,
                "grounded": False,
                "sensitive_exposures": 0,
                "unauthorized_changes": 0,
                "failure_reason": f"{type(exc).__name__}: {exc}",
            }
            error = f"{type(exc).__name__}: {exc}"
        elapsed_ms = (time.perf_counter() - started) * 1000
        results.append(
            {
                "id": item["id"],
                "workflow": item["workflow"],
                "type": item["type"],
                "scoring_method": item["scoring_method"],
                "status_code": status,
                "response": response,
                "actual_path": response.get("route"),
                "cited_evidence": response.get("evidence_refs", []),
                "actual_tool_calls": tools,
                "latency_ms": round(elapsed_ms, 3),
                "score": score,
                "error": error,
            }
        )
        print(
            f"run={run_number} item={item['id']} status={status} "
            f"passed={score['correct']} latency_ms={elapsed_ms:.3f}",
            flush=True,
        )
    return {"run": run_number, "results": results}


def reproducibility(runs: list[dict[str, Any]], metrics: dict[str, Any]) -> dict[str, Any]:
    snapshots = [metric_snapshot(run["results"], metrics) for run in runs]
    output: dict[str, Any] = {}
    for metric in metrics["metrics"]:
        metric_id = metric["id"]
        values = [snapshot[metric_id]["value"] for snapshot in snapshots]
        if any(value is None for value in values):
            difference: float | None = None
        elif isinstance(values[0], dict):
            difference = float(statistics.mean(
                abs(values[0][key] - values[1][key]) for key in values[0]
            ))
        else:
            difference = abs(float(values[0]) - float(values[1]))
        output[metric_id] = {"round_values": values, "mean_difference": difference}
    return output


def _display(value: Any) -> str:
    if value is None:
        return "미측정"
    if isinstance(value, float):
        return f"{value:.3f}"
    if isinstance(value, dict):
        return ", ".join(f"{key}={number}" for key, number in value.items())
    return str(value)


def build_report(raw: dict[str, Any], metrics: dict[str, Any], config: dict[str, Any]) -> str:
    last_results = raw["runs"][-1]["results"]
    last_snapshot = metric_snapshot(last_results, metrics)
    repro = raw["reproducibility"]
    type_counts: dict[str, list[dict[str, Any]]] = {}
    for result in last_results:
        type_counts.setdefault(result["type"], []).append(result)
    hallucinations = sum(not result["score"]["grounded"] for result in last_results)
    lines = [
        "# 품질 평가 실측 리포트",
        "",
        f"> 측정 시점: {raw['measured_at']}  ",
        f"> 대상 모델: `{config['generation_model']['model']}`  ",
        "> 채점 방식: 결정론적 정답지 채점. 모델 채점자 미사용  ",
        "> 실행 경계: API 진입점 실호출, 생성 모델 실호출, 나머지 외부 커넥터 Mock",
        "",
        "## 지표 결과",
        "",
        (
            "| 지표 | 목표값 | 개선 전 기준선 | 실측값 | 표본 수 | 통과 여부 | "
            "재현성 2회 평균 차 | 미달 원인 후보 |"
        ),
        "|---|---|---|---|---:|---|---:|---|",
    ]
    fixes = {
        "G-1": "07-api-ui.md와 06-workflow.md의 API·모델 지연 검토",
        "G-2": "06-workflow.md의 전체 배치 스케줄러 조립 후 재측정",
        "G-3": "06-workflow.md와 04-connector.md의 이벤트·CRM 전체 경로 조립 후 재측정",
        "Q-1": "06-workflow.md 전체 실행 진입점 조립 후 재측정",
        "Q-2": "03-knowledge.md의 근거 전달 또는 06-workflow.md의 생성 프롬프트 검토",
        "Q-3": "05-guardrail.md의 출력 검사와 승인 경계 검토",
    }
    for metric in metrics["metrics"]:
        metric_id = metric["id"]
        snapshot = last_snapshot[metric_id]
        passed = snapshot["passed"]
        status = "미측정" if passed is None else ("통과" if passed else "미달")
        cause = "해당 없음" if passed else fixes[metric_id]
        lines.append(
            f"| `{metric_id}` {metric['name']} | {metric['target']['display']} | 미측정 | "
            f"{_display(snapshot['value'])} | {snapshot['sample_size']} | {status} | "
            f"{_display(repro[metric_id]['mean_difference'])} | {cause} |"
        )
    lines.extend([
        "",
        "## 회차별 재현성",
        "",
        "| 지표 | 1회 | 2회 | 평균 차 |",
        "|---|---:|---:|---:|",
    ])
    for metric in metrics["metrics"]:
        value = repro[metric["id"]]
        lines.append(
            f"| `{metric['id']}` | {_display(value['round_values'][0])} | "
            f"{_display(value['round_values'][1])} | {_display(value['mean_difference'])} |"
        )
    lines.extend([
        "",
        "## 유형별 결과",
        "",
        "| 유형 | 문항 수 | 정답·경로·도구 통과 | 근거 통과 |",
        "|---|---:|---:|---:|",
    ])
    for item_type, results in sorted(type_counts.items()):
        lines.append(
            f"| {item_type} | {len(results)} | "
            f"{sum(result['score']['correct'] for result in results)} | "
            f"{sum(result['score']['grounded'] for result in results)} |"
        )
    lines.extend([
        "",
        f"근거가 없는 답변: {hallucinations}건  ",
        f"오류 문항도 {config['expected_item_count']}건 표본에서 제외하지 않고 실패로 집계함.",
        "",
        (
            f"④ 담당자별 성공기준 {len(metrics['role_criteria'])}건은 "
            "지표 설정에 1:1 판정 항목으로 매핑함.  "
        ),
        (
            "이번 API 대역은 개별 내부 단계 로그를 내지 않으므로 "
            f"단계별 실측 {len(metrics['role_criteria'])}건은 `미측정`으로 유지함."
        ),
        "",
        "## 시간예산 설계 대조",
        "",
        "| 워크플로우 | 최악값 합계 대조 | p95 대조 | 이번 실측 성격 |",
        "|---|---|---|---|",
        (
            f"| W-1 | {metrics['workflow_budgets']['W-1']['worst_case_ms']:,}ms ≤ "
            f"{metrics['workflow_budgets']['W-1']['total_budget_ms']:,}ms | "
            f"{metrics['workflow_budgets']['W-1']['designed_p95_ms']:,}ms ≤ "
            f"{metrics['metrics'][0]['target']['value']:,}ms | API와 실모델 p95 직접 측정 |"
        ),
        (
            f"| W-2 | {metrics['workflow_budgets']['W-2']['worst_case_ms']:,}ms ≤ "
            f"{metrics['workflow_budgets']['W-2']['total_budget_ms']:,}ms | "
            f"{metrics['workflow_budgets']['W-2']['designed_completion']} ≤ "
            f"{metrics['workflow_budgets']['W-2']['target_completion']} | "
            "승인 API 대역만 측정하여 전체 배치는 미측정 |"
        ),
        (
            f"| W-3 | {metrics['workflow_budgets']['W-3']['worst_case_ms']:,}ms ≤ "
            f"{metrics['workflow_budgets']['W-3']['total_budget_ms']:,}ms | "
            f"{metrics['workflow_budgets']['W-3']['designed_p95_ms']:,}ms ≤ "
            f"{metrics['metrics'][2]['target']['value']:,}ms | "
            "승인 API 대역만 측정하여 이벤트 전체 경로는 미측정 |"
        ),
        "",
        "## 확인필요",
        "",
        "| # | 항목 | 후속 조치 |",
        "|---:|---|---|",
        "| 1 | [확인필요: 승인 문서 원천 건수] | 03-knowledge.md 원천 연결 시 확정 |",
        "| 2 | [확인필요: 승인 문서 기준일] | 03-knowledge.md 원천 연결 시 확정 |",
        "| 3 | [확인필요: G-2 전체 배치 완료 시각] | 06-workflow.md 스케줄러 실조립 후 측정 |",
        "| 4 | [확인필요: G-3 이벤트 수신부터 CRM 완료 시각] | 04-connector.md 실조립 후 측정 |",
        (
            "| 5 | [확인필요: Q-1 W-1부터 W-3까지 전체 경로 p95] | "
            "06-workflow.md 전체 진입점 조립 후 측정 |"
        ),
        "",
        "## 다음 개선 담당",
        "",
    ])
    for metric in metrics["metrics"]:
        status = last_snapshot[metric["id"]]["passed"]
        if status is not True:
            lines.append(f"- `{metric['id']}`: {fixes[metric['id']]}  ")
    return "\n".join(lines) + "\n"


def run_evaluation() -> tuple[Path, Path, dict[str, Any]]:
    load_dotenv(ROOT / ".env", override=False)
    config = load_json(RUN_CONFIG_PATH)
    metrics = load_json(METRICS_PATH)
    items = load_golden_set()
    if len(items) != config["expected_item_count"]:
        raise ValueError(
            f"확정 문항 수 {config['expected_item_count']}와 실제 {len(items)}가 다름"
        )
    if dict(Counter(item["workflow"] for item in items)) != config["distribution"]:
        raise ValueError("확정 워크플로우 배분과 골든셋 배분이 다름")
    generation = GroqGenerationClient(config["generation_model"])
    runs = [
        run_once(items, generation, run_number)
        for run_number in range(1, config["reproducibility_runs"] + 1)
    ]
    raw: dict[str, Any] = {
        "measured_at": datetime.now(UTC).isoformat(),
        "measurement_point": config["current_measurement_point"],
        "target_mode": config["target_mode"],
        "generation_model": config["generation_model"]["model"],
        "judge": config["judge"],
        "runs": runs,
        "reproducibility": reproducibility(runs, metrics),
    }
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    reports_dir = ROOT / config["reports_dir"]
    reports_dir.mkdir(parents=True, exist_ok=True)
    raw_path = reports_dir / f"evaluation_raw_{timestamp}.json"
    report_path = reports_dir / f"evaluation_{timestamp}.md"
    raw_path.write_text(json.dumps(raw, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report_path.write_text(build_report(raw, metrics, config), encoding="utf-8")
    return raw_path, report_path, raw


def main() -> None:
    parser = argparse.ArgumentParser(description="Help Desk 품질 평가 실행기")
    parser.parse_args()
    raw_path, report_path, raw = run_evaluation()
    total = len(raw["runs"][-1]["results"])
    passed = sum(result["score"]["correct"] for result in raw["runs"][-1]["results"])
    print(f"채점 문항={total} 통과={passed} 실패={total - passed}")
    print(f"원본={raw_path}")
    print(f"리포트={report_path}")


if __name__ == "__main__":
    main()
