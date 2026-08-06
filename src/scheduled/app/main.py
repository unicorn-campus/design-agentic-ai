"""I-5 `lp-scheduled` — ⑦ 2절 예약 작업 이미지.

**묶음** — BAT(일일 취향 학습)과 SYNC(식당 데이터 동기화)는 둘 다 상주하지
않고 스케줄로 도는 성격이 같음. DevOps 0.5명 제약상 이미지를 2개로 늘리지
않음. **권한은 실행 프로파일 2개로 나눔**(잡 이름 허용 목록 2개 고정).

⑦ 3절 포트: **해당 없음(예약 실행 · HTTP 수신 없음)** — 요청을 받지 않고
스케줄로만 돎. 살아 있는지는 **종료 코드와 실행 기록**으로 판정함.

오토스케일링 대상 아님 · 동시 실행 1로 제한 · BAT 매일 03:00 1회.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from datetime import datetime, timedelta, timezone

from lp_common import db
from lp_common.config import get_settings
from lp_common.observability import setup_logging

from . import a3_daily_learning, sync_worker

log = logging.getLogger("lp.scheduled")
KST = timezone(timedelta(hours=9))

# 실행 프로파일 2개 — 잡 이름 허용 목록을 고정함(⑦ 2절 I-5)
ALLOWED_JOBS = ("bat", "sync")

# 프로파일별 저장소 역할 — BAT은 취향 벡터 쓰기(K-7)만, SYNC는 캐시 쓰기(K-10)만
JOB_DB_ROLES = {
    "bat": ("ro", "rw", "obs"),
    "sync": ("ro", "rw", "obs"),
}


async def _run(job: str, region: str | None) -> int:
    settings = get_settings("lp-scheduled")
    await db.init_pools(settings, roles=JOB_DB_ROLES[job])
    try:
        if job == "bat":
            out = await a3_daily_learning.run()
            print("=== S-B1 ~ S-B8 일일 취향 학습 완료 보고 ===")
            print(f"  갱신 회원 수          {out.updated_count}")
            print(f"  콜드스타트 유지       {out.skipped_coldstart_count}")
            print(f"  실패 회원 수          {out.failed_count}")
            print(f"  전일 수락률           {out.prev_accept_rate:.1%}")
            print(f"  전일 만족률           {out.prev_satisfy_rate:.1%}")
            print(f"  외부 모델 호출        0건 (J-7 — 배치 경로에 LLM 없음)")
            print(f"  학습 반영 메시지      {out.learning_message}")
            return 1 if out.aborted else 0

        state = await sync_worker.run(settings, region_code=region)
        print("=== S-B9 ~ S-B15 식당 데이터 동기화 완료 보고 ===")
        print(f"  조회 식당 수          {len(state['fetched_restaurants'])}")
        print(f"  S-B11 차단 건수       {state['blocked_string_count']}  ← ⑥ G-1/G-2 근본 차단")
        print(f"  S-B12 폐업 제외       {state['closed_filtered_count']}")
        print(f"  S-B13 적재 건수       {state['loaded_count']}")
        print(f"  S-B14 만료 건수       {state['expired_count']}")
        return 0
    finally:
        await db.close_pools()


def main() -> None:
    parser = argparse.ArgumentParser(description="런치픽 예약 작업 이미지(I-5)")
    parser.add_argument("job", choices=ALLOWED_JOBS, help="실행 프로파일: bat | sync")
    parser.add_argument("--region", default=None, help="SYNC 대상 지역 코드")
    parser.add_argument(
        "--loop-sec",
        type=int,
        default=0,
        help="0이면 1회 실행 후 종료(스케줄러가 부름). >0이면 주기 반복",
    )
    args = parser.parse_args()
    setup_logging(f"lp-scheduled/{args.job}")

    if args.loop_sec <= 0:
        sys.exit(asyncio.run(_run(args.job, args.region)))

    async def loop() -> None:
        while True:
            try:
                await _run(args.job, args.region)
            except Exception:  # noqa: BLE001
                log.exception("예약 작업 실패 job=%s", args.job)
            await asyncio.sleep(args.loop_sec)

    asyncio.run(loop())


if __name__ == "__main__":
    main()
