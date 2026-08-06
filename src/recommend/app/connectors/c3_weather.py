"""C-3 날씨 조회 커넥터 — E-3 (E)날씨 API. ⑤ 7절.

**사용 주체: 추천 경로에서 직접 부름.** 행정구역 단위라 호출량이 작아
J-6 예외로 남긴 유일한 외부 호출임(⑤ 7절 · ② 4절).

입력은 `region_code`(행정구역 코드)뿐임 — 정확 좌표는 여기로 넘기지 않음.
TB-3으로 좌표가 넘어가는 것은 C-2뿐임(⑤ 8절 F-2).

반복 호출을 줄이는 캐시가 필요하나 **값은 ④가 타임아웃 표에서 소유**하므로
⑤는 적지 않음. 여기서는 행정구역+시각 단위 메모리 캐시로 구현함.
"""

from __future__ import annotations

import logging
import time

import httpx

from lp_common.codes import WEATHER_CODES

log = logging.getLogger("lp.c3")

# 행정구역 코드 → 대표 좌표(외부 API 조회용). 회원 좌표를 쓰지 않음
_REGION_CENTER = {
    "SEOUL-GANGNAM": (37.4979, 127.0276),
    "SEOUL-YEOUIDO": (37.5219, 126.9245),
    "SEOUL-JONGNO": (37.5729, 126.9794),
    "SEONGNAM-PANGYO": (37.3947, 127.1112),
}


class WeatherConnector:
    def __init__(self, *, mode: str, api_key: str, cache_ttl_sec: int = 600) -> None:
        self.mode = mode
        self.api_key = api_key
        self.cache_ttl_sec = cache_ttl_sec
        self._cache: dict[str, tuple[float, str]] = {}

    async def fetch(self, region_code: str, *, timeout_sec: float) -> str:
        cached = self._cache.get(region_code)
        if cached and time.monotonic() - cached[0] < self.cache_ttl_sec:
            return cached[1]

        if self.mode == "mock" or not self.api_key:
            code = self._mock(region_code)
        else:
            code = await self._real(region_code, timeout_sec=timeout_sec)

        self._cache[region_code] = (time.monotonic(), code)
        return code

    async def _real(self, region_code: str, *, timeout_sec: float) -> str:
        lat, lng = _REGION_CENTER.get(region_code, _REGION_CENTER["SEOUL-GANGNAM"])
        async with httpx.AsyncClient(timeout=timeout_sec) as client:
            resp = await client.get(
                "https://api.openweathermap.org/data/2.5/weather",
                params={"lat": lat, "lon": lng, "appid": self.api_key, "units": "metric"},
            )
            resp.raise_for_status()
            body = resp.json()
        main = (body.get("weather") or [{}])[0].get("main", "Clear")
        temp = (body.get("main") or {}).get("temp", 20)
        return _to_code(main, temp)

    def _mock(self, region_code: str) -> str:
        # 결정론 Mock — 지역 코드 해시로 고정함(테스트 재현성)
        return WEATHER_CODES[sum(map(ord, region_code)) % len(WEATHER_CODES)]


def _to_code(main: str, temp: float) -> str:
    if main in ("Rain", "Drizzle", "Thunderstorm"):
        return "RAIN"
    if main == "Snow":
        return "SNOW"
    if temp >= 30:
        return "HOT"
    if temp <= 3:
        return "COLD"
    if main == "Clouds":
        return "CLOUD"
    return "CLEAR"
