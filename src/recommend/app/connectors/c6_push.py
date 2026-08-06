"""C-6 푸시 발송 커넥터 — E-6 (E)푸시 알림. ⑤ 7절.

`S-E6` 리마인더 발송 주체가 식사기록·피드백이고 그 실행 단위가 I-2이므로
K-14 자격증명은 I-2에 주입됨(⑦ 4-2 K-14).

**재시도 0회** — 원문이 "리마인더 1회만(강제 아님)"을 못 박았고 재시도를
넣으면 알림이 2회 이상 가서 원문 값을 강화하는 것이 됨(④ 9-2절).

⑥ 11절 A-8 판정: 보낸 알림은 회수 불가하나 사람 승인을 붙이면 1시간 후
리마인더가 성립하지 않으므로 **제한 장치(발송 1건 · 재시도 0회)로 대체**함.
발송 직전 문구에 ⑥ 8절 L-2·L-3 검사를 적용함.
"""

from __future__ import annotations

import logging

from lp_common.output_check import check_push_message

log = logging.getLogger("lp.c6")


class PushConnector:
    def __init__(self, *, mode: str) -> None:
        self.mode = mode
        self.sent: list[tuple[str, str]] = []  # Mock 검증용

    async def send(self, device_token: str, message: str) -> tuple[str, list[str]]:
        """Returns: (send_result, 출력검사 위반 목록)"""
        safe_message, violations = check_push_message(message)
        if self.mode == "mock":
            self.sent.append((device_token, safe_message))
            log.info("푸시 발송(mock) token=%s… len=%d", device_token[:6], len(safe_message))
            return "SENT", violations
        # 실물 벤더 SDK 연동 자리. 로컬 테스트 범위에서는 Mock만 씀
        raise NotImplementedError("푸시 실물 경로는 로컬 테스트 범위 밖임")
