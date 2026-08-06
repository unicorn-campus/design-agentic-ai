"""I-3 `lp-member` — ② 4절 MBR 회원 서비스(인증·취향 프로파일·식이제한).

⑦ 2절 I-3 쪼갠 이유: 부하 시점이 추천과 다르고(로그인·온보딩),
**알레르기 전용 암호화 키(K-5)를 갖는 이미지를 최소 개수로 묶어 두려고**
결제와도 분리함. K-5가 주입되는 이미지는 I-2·I-3 **2개뿐**임(⑦ 4-4절).

⑦ 3절 포트: 8080(클러스터 내부 서비스 포트만) · 외부 인터넷 노출 **안 함** —
알레르기 전용 키를 갖는 이미지를 인터넷에 직접 열지 않음.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from lp_common import db
from lp_common.codes import ALLERGEN_NAME_TO_CODES, DIET_TYPE_TO_CODES
from lp_common.config import get_settings
from lp_common.observability import setup_logging, write_access_log

log = logging.getLogger("lp.member")
settings = get_settings("lp-member")


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging("lp-member")
    if not settings.allergen_key:
        # ⑦ 4-4절 — K-5는 이미지에 굽지 않고 뜨는 순간 전용 보관소에서 받아 메모리에만 둠
        log.warning("K-5 알레르기 전용 키가 주입되지 않았음 — 식이제한 경로가 막힘")
    await db.init_pools(settings, roles=("ro", "rw", "obs"))
    yield
    await db.close_pools()


app = FastAPI(title="런치픽 회원 서비스 (I-3)", lifespan=lifespan)


@app.get("/health")
async def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "service": "lp-member",
        # 값이 아니라 **주입 여부만** 밝힘(⑦ 4-2 · 4-3 위반 3번 회피)
        "allergen_key_injected": bool(settings.allergen_key),
        "pii_key_injected": bool(settings.pii_key),
        "kakao_mode": settings.kakao_mode,
    }


@app.get("/v1/members")
async def list_members() -> dict[str, Any]:
    """로컬 확인용 회원 목록. **이메일·닉네임 원문은 내보내지 않음**(F-3)."""
    rows = await db.fetch(
        "ro",
        """
        SELECT m.member_ref, m.plan_type, m.region_code, m.job_cluster_code,
               p.feedback_count,
               (d.allergen_names <> '{}' OR d.diet_types <> '{}') AS has_restriction,
               c.location_consent, c.sensitive_consent
        FROM member m
        JOIN preference_profile p USING (member_ref)
        JOIN dietary_restriction d USING (member_ref)
        JOIN consent c USING (member_ref)
        ORDER BY m.member_ref
        """,
        limit_guard=200,
    )
    return {"members": [dict(r) for r in rows]}


@app.get("/v1/members/{member_ref}")
async def member_detail(member_ref: str) -> dict[str, Any]:
    """회원 상세. F-1은 **보유 여부와 항목 수**만 내보내고 항목명은 내보내지 않음.

    항목명을 읽는 것은 A-1의 필터 단계 내부로 한정됨(⑤ 3절 접근 금지 항목).
    """
    row = await db.fetchrow(
        "ro",
        """
        SELECT m.member_ref, m.plan_type, m.region_code, m.job_cluster_code,
               p.category_scores, p.feedback_count,
               d.allergen_names, d.diet_types,
               c.location_consent, c.sensitive_consent
        FROM member m
        JOIN preference_profile p USING (member_ref)
        JOIN dietary_restriction d USING (member_ref)
        JOIN consent c USING (member_ref)
        WHERE m.member_ref = $1
        """,
        member_ref,
    )
    if row is None:
        raise HTTPException(status_code=404, detail={"reason_code": "AUTH_FAIL"})
    await write_access_log(
        actor="lp-member",
        member_ref=member_ref,
        field_ids=["F-1", "F-9", "F-10"],
        decrypt_called=bool(row["allergen_names"] or row["diet_types"]),
        trace_id="member-detail",
    )
    scores = row["category_scores"]
    if isinstance(scores, str):
        import json

        scores = json.loads(scores)
    return {
        "member_ref": row["member_ref"],
        "plan_type": row["plan_type"],
        "region_code": row["region_code"],
        "job_cluster_code": row["job_cluster_code"],
        "feedback_count": row["feedback_count"],
        "coldstart": int(row["feedback_count"]) < 5,
        "top_categories": sorted(scores or {}, key=(scores or {}).get, reverse=True)[:5],
        # F-1 — 항목명이 아니라 개수만 나감
        "restriction_count": len(row["allergen_names"]) + len(row["diet_types"]),
        "location_consent": row["location_consent"],
        "sensitive_consent": row["sensitive_consent"],
    }


class ConsentPatch(BaseModel):
    location_consent: bool | None = None
    sensitive_consent: bool | None = None


@app.post("/v1/members/{member_ref}/consent")
async def update_consent(member_ref: str, patch: ConsentPatch) -> dict[str, Any]:
    """동의 상태 변경. `US:UFR-MBR-030#검증요구사항`은 철회 방법 안내를 요구함.

    철회가 가능하다는 것이 ④ `S-R2`(요청 시점 동의 확인)를 신설한 근거임.
    """
    row = await db.fetchrow(
        "ro", "SELECT location_consent, sensitive_consent FROM consent WHERE member_ref=$1",
        member_ref,
    )
    if row is None:
        raise HTTPException(status_code=404, detail={"reason_code": "AUTH_FAIL"})
    loc = row["location_consent"] if patch.location_consent is None else patch.location_consent
    sen = row["sensitive_consent"] if patch.sensitive_consent is None else patch.sensitive_consent
    await db.execute(
        "rw",
        "UPDATE consent SET location_consent=$2, sensitive_consent=$3, updated_at=now() "
        "WHERE member_ref=$1",
        member_ref,
        loc,
        sen,
    )
    return {"member_ref": member_ref, "location_consent": loc, "sensitive_consent": sen}


@app.get("/v1/lexicon")
async def lexicon() -> dict[str, Any]:
    """K-5 용어사전 노출 — 프런트가 항목명 후보를 고를 때 씀."""
    return {
        "allergen_names": sorted(ALLERGEN_NAME_TO_CODES),
        "diet_types": sorted(DIET_TYPE_TO_CODES),
    }
