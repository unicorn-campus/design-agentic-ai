"""⑥ 6절 관측 기록 지점 표 O-1 ~ O-11.

이름 규칙 출처는 **OpenTelemetry GenAI 시맨틱 컨벤션**이며 문서 상태가
`Development`(표준 후보)임. `gen_ai.*` 속성에 `Stable` 단계가 0건이므로
이름이 예고 없이 바뀔 수 있음 — **2026-08-05 조회 기준**으로 인용함(⑥ 6절).

적재 위치는 ② DB6 관측 기록 저장소이며, O-9 개인정보 접근 로그는
일반 관측 기록과 **분리 저장**함(⑦ 5-3 문제 3 해결 · S-8a).
"""

from __future__ import annotations

import json
import logging
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any

from . import db
from .masking import mask_record

log = logging.getLogger("lp.obs")

# O-1 ~ O-11 기록 지점 이름(표준 후보 스팬 이름 규칙)
SPAN_NAMES = {
    "O-1": "chat {model}",  # gen_ai.operation.name + gen_ai.request.model
    "O-2": "execute_tool {tool}",  # gen_ai.tool.name
    "O-3": "invoke_agent {agent}",  # gen_ai.agent.name
}


@dataclass
class SpanRecord:
    """관측 기록 1행. O-1 ~ O-11 중 하나에 해당함."""

    point: str  # O-1 ~ O-11
    span_name: str
    step: str  # S-R1 ~ S-E6
    trace_id: str
    member_ref: str | None = None
    latency_ms: int = 0
    is_error: bool = False
    reason_code: str | None = None
    attributes: dict[str, Any] = field(default_factory=dict)


async def write_span(record: SpanRecord) -> None:
    """DB6 직적재. **적재 직전에 마스킹함**(⑤ F-8 변환 지점 · ⑥ M-1 ~ M-3)."""
    masked = mask_record(record.attributes)
    try:
        await db.execute(
            "obs",
            """
            INSERT INTO obs_span
              (point, span_name, step, trace_id, member_ref, latency_ms,
               is_error, reason_code, attributes)
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9::jsonb)
            """,
            record.point,
            record.span_name,
            record.step,
            record.trace_id,
            mask_record({"member_ref": record.member_ref})["member_ref"]
            if record.member_ref
            else None,
            record.latency_ms,
            record.is_error,
            record.reason_code,
            json.dumps(masked, ensure_ascii=False, default=str),
        )
    except Exception as exc:  # 관측 실패가 서비스를 무너뜨리지 않게 함
        log.warning("관측 기록 적재 실패 point=%s err=%s", record.point, type(exc).__name__)


async def write_access_log(
    *,
    actor: str,
    member_ref: str,
    field_ids: list[str],
    decrypt_called: bool,
    trace_id: str,
) -> None:
    """O-9 개인정보 접근 로그 — **값은 남기지 않고** 주체·시각·항목 종류만.

    6개월 보관 대상이며(`US:NFR-SYS-030#체크리스트`) 일반 관측 기록과
    분리 저장함(⑦ 5-2 S-8a · ⑥ M-4).
    """
    try:
        await db.execute(
            "obs",
            """
            INSERT INTO obs_access_log
              (actor, member_ref, field_ids, allergen_key_decrypt, trace_id)
            VALUES ($1,$2,$3,$4,$5)
            """,
            actor,
            mask_record({"member_ref": member_ref})["member_ref"],
            field_ids,
            decrypt_called,
            trace_id,
        )
    except Exception as exc:
        log.warning("접근 로그 적재 실패 err=%s", type(exc).__name__)


@asynccontextmanager
async def span(
    point: str,
    step: str,
    trace_id: str,
    *,
    span_name: str | None = None,
    member_ref: str | None = None,
    attributes: dict[str, Any] | None = None,
):
    """단계 하나를 감싸 지연시간·실패 사유를 기록함.

    `yield`로 넘기는 dict에 속성을 더 담으면 그대로 적재됨.
    """
    attrs: dict[str, Any] = dict(attributes or {})
    started = time.perf_counter()
    error: BaseException | None = None
    try:
        yield attrs
    except BaseException as exc:  # noqa: BLE001 — 기록 후 다시 던짐
        error = exc
        raise
    finally:
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        reason = getattr(error, "code", None) if error else None
        await write_span(
            SpanRecord(
                point=point,
                span_name=span_name or step,
                step=step,
                trace_id=trace_id,
                member_ref=member_ref,
                latency_ms=elapsed_ms,
                is_error=error is not None,
                reason_code=reason if isinstance(reason, str) else None,
                attributes=attrs
                | ({"error_type": type(error).__name__} if error else {}),
            )
        )


def setup_logging(service: str) -> None:
    logging.basicConfig(
        level=logging.INFO,
        format=f"%(asctime)s [{service}] %(levelname)s %(name)s :: %(message)s",
    )
