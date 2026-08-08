"""프로그램이 뜰 때 한 번 부르는 준비 작업.

확인 결과(2026-08-08 · 실제 실행): Windows 기본 이벤트 루프로는 비동기 데이터베이스
드라이버가 돌지 않음 — `psycopg.InterfaceError: Psycopg cannot use the
'ProactorEventLoop' to run in async mode`. 중간 저장 장치를 데이터베이스로 쓰는
프로세스는 루프를 바꾼 뒤에 시작해야 함.
"""

from __future__ import annotations

import asyncio
import sys

__all__ = ["needs_selector_event_loop", "configure_event_loop_for_async_db"]


def needs_selector_event_loop() -> bool:
    return sys.platform == "win32"


def configure_event_loop_for_async_db() -> bool:
    """비동기 데이터베이스가 돌 수 있는 이벤트 루프로 맞춤. 바꿨으면 참을 돌려줌.

    루프를 만들기 **전에** 부름. 이미 돌고 있는 루프는 바꿀 수 없음.
    """
    if not needs_selector_event_loop():
        return False
    policy_type = getattr(asyncio, "WindowsSelectorEventLoopPolicy", None)
    if policy_type is None:
        return False
    if isinstance(asyncio.get_event_loop_policy(), policy_type):
        return False
    asyncio.set_event_loop_policy(policy_type())
    return True
