"""경과 시간과 기준일을 주는 ClockPort의 시스템 시계 구현임."""

from __future__ import annotations

import time
from datetime import date

from app.application.ports import ClockPort


class SystemClock(ClockPort):
    """운영용 시계. 파이썬 표준 시계만 쓰고 상태를 갖지 않음.

    시험에서는 이 클래스를 쓰지 않고 가짜 시계를 주입해 시간 예산 분기를 재현함.
    """

    def now(self) -> float:
        """단조 증가 시각(초)을 반환함.

        방법: 시스템 시각 변경(NTP 보정·시간대 변경)에 흔들리지 않는 monotonic 시계를 씀.
        반환값: 두 값의 차가 경과 초인 실수. 벽시계 시각이 아님.
        """

        return time.monotonic()

    def today(self) -> date:
        """C-01의 상대 날짜 해석에 쓸 기준일(서버 지역 날짜)을 반환함."""

        return date.today()
