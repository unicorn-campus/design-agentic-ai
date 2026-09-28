"""Groq와 로컬 Qwen·Gemma 모델의 검색 계획 품질·지연시간을 같은 입력으로 비교합니다."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import random
import statistics
import subprocess
import time
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path

import sqlglot
from sqlglot import exp

from app.bootstrap import create_language_model
from app.domain.catalog import query_catalog
from app.infrastructure.ollama_gateway import OllamaGateway
from app.infrastructure.settings import LLM_PROVIDERS, load_settings
from app.infrastructure.sql_guard import LOGICAL_SCHEMA, validate_sql
from app.infrastructure.vllm_gateway import VllmGateway


@dataclass(frozen=True)
class Case:
    case_id: str
    question: str
    expected_mode: str
    expected_query_id: str | None = None
    base_date: date = date(2026, 8, 31)


CASES = (
    Case("F1", "보유 카드 목록을 보여 주세요", "fixed", "cards"),
    Case("F2", "고객 현황을 종합 조회해 주세요", "fixed", "customer_snapshot"),
    Case("F3", "최근 6개월 카드별 월별 승인 금액과 승인 건수를 보여 주세요",
         "fixed", "monthly_usage"),
    Case("F4", "최신 연체액과 연체 일수를 보여 주세요", "fixed", "delinquency"),
    Case("N1", "고객 전체의 월별 총 승인 사용액을 보여 주세요", "nl2sql"),
    Case("N2", "최근 6개월 전체 승인 건수를 월별로 보여 주세요", "nl2sql"),
    Case("N3", "전체 기간의 거래당 평균 승인 금액을 계산해 주세요", "nl2sql"),
    Case("N4", "연회비가 가장 높은 카드 3개를 보여 주세요", "nl2sql"),
    Case("N5", "현재 ACTIVE 카드 수를 브랜드별로 보여 주세요", "nl2sql"),
    Case("U1", "카드별 연체액의 월별 추이를 보여 주세요", "unsupported"),
    Case("U2", "7개월 전 카드 사용액을 보여 주세요", "unsupported"),
    Case("U3", "이 고객의 이탈 확률은 몇 퍼센트인가요", "unsupported"),
)

QWEN_COMPARISON_MODEL = "hf.co/unsloth/Qwen3.5-9B-GGUF:Q4_K_M"


def _has_aggregate(statement: exp.Expression, kind, column: str) -> bool:
    return any(
        any(item.name.lower() == column for item in node.find_all(exp.Column))
        for node in statement.find_all(kind)
    )


def _grouped_by(statement: exp.Expression, column: str) -> bool:
    group = statement.args.get("group")
    return group is not None and any(
        item.name.lower() == column for item in group.find_all(exp.Column)
    )


def _semantic_match(case_id: str, sql: str | None) -> bool:
    if not sql:
        return False
    try:
        statement = sqlglot.parse_one(sql, read="postgres")
    except Exception:
        return False
    tables = {item.name.lower() for item in statement.find_all(exp.Table)}
    columns = {item.name.lower() for item in statement.find_all(exp.Column)}

    if case_id == "N1":
        return ("monthly_usage" in tables and _has_aggregate(statement, exp.Sum, "approved_amount")
                and _grouped_by(statement, "month"))
    if case_id == "N2":
        return ("monthly_usage" in tables and _has_aggregate(statement, exp.Sum, "transaction_count")
                and _grouped_by(statement, "month"))
    if case_id == "N3":
        return ("monthly_usage" in tables and {"approved_amount", "transaction_count"} <= columns
                and statement.find(exp.Div) is not None and statement.find(exp.Nullif) is not None)
    if case_id == "N4":
        limit = statement.args.get("limit")
        limit_value = limit.expression.name if limit is not None and limit.expression is not None else ""
        ordered = list(statement.find_all(exp.Ordered))
        return ("customer_cards" in tables and {"card_ref", "annual_fee"} <= columns
                and limit_value == "3"
                and any(item.args.get("desc") is True
                        and any(column.name.lower() == "annual_fee"
                                for column in item.find_all(exp.Column)) for item in ordered))
    if case_id == "N5":
        text = statement.sql(dialect="postgres").upper()
        return ("customer_cards" in tables and "brand" in columns
                and statement.find(exp.Count) is not None and _grouped_by(statement, "brand")
                and "CURRENT_STATUS" in text and "ACTIVE" in text)
    return True


def _assess(case: Case, plan) -> dict:
    route_match = plan.query_mode == case.expected_mode
    fixed_id_match = case.expected_mode != "fixed" or plan.query_id == case.expected_query_id
    sql_guard_pass = None
    semantic_match = None
    if case.expected_mode == "nl2sql":
        try:
            validate_sql(plan.sql or "")
            sql_guard_pass = True
        except ValueError:
            sql_guard_pass = False
        semantic_match = _semantic_match(case.case_id, plan.sql)
    elif case.expected_mode == "unsupported":
        semantic_match = plan.sql is None and plan.query_id is None
    plan_match = route_match and fixed_id_match and sql_guard_pass is not False and semantic_match is not False
    return {
        "route_match": route_match,
        "fixed_id_match": fixed_id_match,
        "sql_guard_pass": sql_guard_pass,
        "semantic_match": semantic_match,
        "plan_match": plan_match,
    }


def _percentile(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * fraction
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    weight = position - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def _rate(records: list[dict], key: str, applicable=None, *, failures_as_false: bool = False) -> float | None:
    selected = [item for item in records if applicable is None or applicable(item)]
    if failures_as_false:
        values = [bool(item.get(key, False)) for item in selected]
    else:
        values = [item[key] for item in selected if item.get(key) is not None]
    return sum(bool(value) for value in values) / len(values) if values else None


def _latency_summary(records: list[dict]) -> dict:
    latencies = [item["latency_ms"] for item in records]
    return {
        "samples": len(latencies),
        "p50_ms": round(statistics.median(latencies), 3) if latencies else None,
        "p95_ms": round(_percentile(latencies, 0.95), 3) if latencies else None,
    }


def _command_version(command: list[str]) -> str | None:
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=10, check=False)
    except (OSError, subprocess.SubprocessError):
        return None
    output = (result.stdout or result.stderr).strip()
    return output or None


def _select_gateway(provider: str, settings):
    if provider == "groq":
        model_name = settings.model
        gateway = create_language_model(settings, provider)
    elif provider == "google_local":
        model_name = settings.gemma_model
        gateway = create_language_model(settings, provider)
    elif provider == "google_local-vllm":
        model_name = settings.vllm_model
        gateway = create_language_model(settings, "google_local", "vllm")
    else:
        model_name = QWEN_COMPARISON_MODEL
        gateway = OllamaGateway(
            settings.ollama_base_url,
            model_name,
            settings.llm_timeout_seconds,
            settings.max_tokens,
        )
    return model_name, gateway


def _run_provider(provider: str, repeat: int, seed: int) -> tuple[dict, list[dict]]:
    settings = load_settings()
    model_name, gateway = _select_gateway(provider, settings)
    if provider == "groq" and not settings.api_key:
        return {"provider": provider, "model": model_name, "status": "skipped",
                "reason": "GROQ_API_KEY가 설정되지 않았습니다."}, []
    if provider == "google_local-vllm" and not settings.vllm_api_key:
        return {"provider": provider, "model": model_name, "status": "skipped",
                "reason": "SQL_RETRIEVER_VLLM_API_KEY가 설정되지 않았습니다."}, []
    catalog = query_catalog()
    records: list[dict] = []

    started = time.perf_counter_ns()
    try:
        first = gateway.plan(CASES[0].question, LOGICAL_SCHEMA, catalog, "auto",
                             base_date=CASES[0].base_date)
        first_call_ms = (time.perf_counter_ns() - started) / 1_000_000
        first_status = "ok"
        first_error = None
    except Exception as error:
        first_call_ms = (time.perf_counter_ns() - started) / 1_000_000
        first_status = "error"
        first_error = type(error).__name__
        first = None
    records.append({
        "provider": provider,
        "case_id": CASES[0].case_id,
        "repeat": 0,
        "phase": "first_call",
        "latency_ms": round(first_call_ms, 3),
        "status": first_status,
        "plan": first.model_dump(mode="json") if first is not None else None,
        "error_type": first_error,
        **(_assess(CASES[0], first) if first is not None else {}),
    })

    work = [(case, index + 1) for index in range(repeat) for case in CASES]
    random.Random(seed).shuffle(work)
    for case, iteration in work:
        started = time.perf_counter_ns()
        try:
            plan = gateway.plan(case.question, LOGICAL_SCHEMA, catalog, "auto",
                                base_date=case.base_date)
            latency_ms = (time.perf_counter_ns() - started) / 1_000_000
            record = {
                "provider": provider,
                "case_id": case.case_id,
                "repeat": iteration,
                "phase": "warm",
                "latency_ms": round(latency_ms, 3),
                "status": "ok",
                "plan": plan.model_dump(mode="json"),
                "error_type": None,
                **_assess(case, plan),
            }
        except Exception as error:
            latency_ms = (time.perf_counter_ns() - started) / 1_000_000
            record = {
                "provider": provider,
                "case_id": case.case_id,
                "repeat": iteration,
                "phase": "warm",
                "latency_ms": round(latency_ms, 3),
                "status": "error",
                "plan": None,
                "error_type": type(error).__name__,
            }
        records.append(record)

    warm = [item for item in records if item["phase"] == "warm"]
    successful = [item for item in warm if item["status"] == "ok"]
    is_ollama = isinstance(gateway, OllamaGateway)
    is_vllm = isinstance(gateway, VllmGateway)
    summary = {
        "provider": provider,
        "runtime": "vllm" if is_vllm else "ollama" if is_ollama else "groq",
        "model": model_name,
        "status": "completed" if successful else "failed",
        "session_first_call_ms": round(first_call_ms, 3),
        "session_first_call_status": first_status,
        "warm": _latency_summary(warm),
        "warm_successful": _latency_summary(successful),
        "structured_output_method": getattr(gateway, "_structured_method", None),
        "structured_output_attempts": getattr(gateway, "structured_output_attempts", None),
        "structured_output_fallback_calls": getattr(
            gateway, "structured_output_fallback_calls", None),
        "ollama_ps": _command_version(["ollama", "ps"]) if is_ollama else None,
        "vllm_container": _command_version([
            "docker", "ps", "--filter", "name=vllm-gemma4-12b",
            "--format", "{{.Names}}|{{.Status}}|{{.Ports}}",
        ]) if is_vllm else None,
        "ollama_gpu_process": _command_version([
            "nvidia-smi",
            "--query-compute-apps=process_name,used_memory",
            "--format=csv,noheader",
        ]) if is_ollama or is_vllm else None,
        "gpu_state_after": _command_version([
            "nvidia-smi",
            "--query-gpu=utilization.gpu,memory.used",
            "--format=csv,noheader",
        ]) if is_ollama or is_vllm else None,
        "quality": {
            "successful_calls": len(successful),
            "plan_matches": sum(bool(item.get("plan_match")) for item in warm),
            "call_success_rate": len(successful) / len(warm) if warm else None,
            "route_accuracy": _rate(warm, "route_match", failures_as_false=True),
            "fixed_id_accuracy": _rate(
                warm, "fixed_id_match", lambda item: item["case_id"].startswith("F"),
                failures_as_false=True),
            "sql_guard_pass_rate": _rate(
                warm, "sql_guard_pass", lambda item: item["case_id"].startswith("N"),
                failures_as_false=True),
            "semantic_accuracy": _rate(
                warm, "semantic_match", lambda item: not item["case_id"].startswith("F"),
                failures_as_false=True),
            "plan_match_rate": _rate(warm, "plan_match", failures_as_false=True),
            "fixed_plan_accuracy": _rate(
                warm, "plan_match", lambda item: item["case_id"].startswith("F"),
                failures_as_false=True),
            "nl2sql_plan_accuracy": _rate(
                warm, "plan_match", lambda item: item["case_id"].startswith("N"),
                failures_as_false=True),
            "unsupported_plan_accuracy": _rate(
                warm, "plan_match", lambda item: item["case_id"].startswith("U"),
                failures_as_false=True),
        },
    }
    return summary, records


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Groq와 Qwen·Gemma 계열 검색 계획 벤치마크")
    parser.add_argument(
        "--providers",
        nargs="+",
        choices=(*LLM_PROVIDERS, "google_local-vllm", "qwen"),
        default=(*LLM_PROVIDERS, "google_local-vllm", "qwen"),
    )
    parser.add_argument("--repeat", type=int, default=1)
    parser.add_argument("--seed", type=int, default=20260927)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    if not 1 <= args.repeat <= 20:
        parser.error("--repeat는 1~20 범위여야 합니다.")

    prompt = (Path(__file__).parent / "app" / "prompts" / "search_plan.md").read_bytes()
    result = {
        "run": {
            "started_at": datetime.now(timezone.utc).isoformat(),
            "repeat": args.repeat,
            "seed": args.seed,
            "prompt_sha256": hashlib.sha256(prompt).hexdigest(),
            "scope": "LLM plan() only; DB retrieval and explanation excluded",
            "environment": {
                "platform": platform.platform(),
                "python": platform.python_version(),
                "ollama": _command_version(["ollama", "--version"]),
                "gpu": _command_version([
                    "nvidia-smi",
                    "--query-gpu=name,memory.total",
                    "--format=csv,noheader",
                ]),
                "ollama_ps_before": _command_version(["ollama", "ps"]),
                "vllm_container_before": _command_version([
                    "docker", "ps", "--filter", "name=vllm-gemma4-12b",
                    "--format", "{{.Names}}|{{.Status}}|{{.Ports}}",
                ]),
                "gpu_state_before": _command_version([
                    "nvidia-smi",
                    "--query-gpu=utilization.gpu,memory.used",
                    "--format=csv,noheader",
                ]),
            },
        },
        "providers": [],
        "records": [],
    }
    for provider in args.providers:
        summary, records = _run_provider(provider, args.repeat, args.seed)
        result["providers"].append(summary)
        result["records"].extend(records)

    rendered = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0 if all(item["status"] in {"completed", "skipped"}
                    for item in result["providers"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
