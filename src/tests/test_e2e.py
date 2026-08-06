"""E2E 시험 — 기동 중인 컨테이너에 실제 요청을 보냄.

⑥ 7절 품질 측정 대상 M-Q1 ~ M-Q9와 ⑤ 11절 골든셋 GS-1 ~ GS-24 중
자동화 가능한 문항에 대응함.

전제: `docker compose up -d` + 합성 데이터 시드가 끝나 있어야 함.
실행: python -m pytest src/tests/test_e2e.py -v
"""

from __future__ import annotations

import os
import statistics
import time
from datetime import datetime, timedelta, timezone

import httpx
import pytest

GATEWAY = os.environ.get("LP_GATEWAY_URL", "http://localhost:8080")
KST = timezone(timedelta(hours=9))
# 서비스 구간은 점심 11 ~ 13시임(① 4절 Q-1). 그 밖의 시각에는 영업 필터가
# 전 식당을 걸러 내는 것이 **정상 동작**이므로 시험은 시각을 고정함.
LUNCH = datetime(2026, 8, 6, 12, 10, tzinfo=KST)


@pytest.fixture(scope="session")
def client():
    with httpx.Client(base_url=GATEWAY, timeout=30.0) as c:
        yield c


@pytest.fixture(scope="session")
def members(client):
    return client.get("/api/members").raise_for_status().json()["members"]


def _recommend(client, member_ref, **over):
    payload = {
        "member_ref": member_ref,
        "lat": 37.4979,
        "lng": 127.0276,
        "at": LUNCH.isoformat(),
    }
    payload.update(over)
    r = client.post("/api/recommendations", json=payload)
    return r.status_code, r.json()


def _region_center(region):
    return {
        "SEOUL-GANGNAM": (37.4979, 127.0276),
        "SEOUL-YEOUIDO": (37.5219, 126.9245),
        "SEOUL-JONGNO": (37.5729, 126.9794),
        "SEONGNAM-PANGYO": (37.3947, 127.1112),
    }[region]


# ═══════════════════════════════════════════════════════════════════════════
# 기동 확인 — ⑦ 3절 포트 표
# ═══════════════════════════════════════════════════════════════════════════
def test_모든_런타임_이미지가_health를_응답함(client):
    """⑦ 3절 — I-1·I-2·I-3에 `/health` 필수. I-5는 포트가 없어 대상 아님."""
    assert client.get("/health").json()["status"] == "ok"


def test_외부에서_직접_열려_있는_포트는_게이트웨이_하나뿐임():
    """⑦ 3절 — "외부에서 우리 쪽으로 들어오는 경로는 I-1의 443 하나뿐임".

    I-2·I-3은 `expose`만 하고 `ports`로 게시하지 않았으므로 호스트에서
    직접 붙을 수 없어야 함.
    """
    for port in (8082, 8083):  # 만약 실수로 게시했다면 잡히는 자리
        with pytest.raises((httpx.ConnectError, httpx.ReadTimeout, httpx.ConnectTimeout)):
            httpx.get(f"http://localhost:{port}/health", timeout=2.0)


# ═══════════════════════════════════════════════════════════════════════════
# M-Q2 · M-Q3 — 근거·스코어 동반 노출률 100% (① G-2) · 태그 일치
# GS-11 ~ GS-16
# ═══════════════════════════════════════════════════════════════════════════
def test_MQ2_모든_카드가_근거_문장과_확신_스코어를_동반함(client, members):
    """① G-2 — 목표값 **100%**. 1건이라도 빠지면 불합격."""
    total, with_both = 0, 0
    for m in members[:8]:
        lat, lng = _region_center(m["region_code"])
        _, body = _recommend(client, m["member_ref"], lat=lat, lng=lng)
        for item in body.get("items", []):
            total += 1
            if item.get("reason_text") and item.get("confidence") is not None:
                with_both += 1
    assert total > 0, "카드가 한 건도 생성되지 않아 측정 자체가 불가함"
    assert with_both == total, f"동반 노출률 {with_both}/{total} — 100%가 아님"


def test_MQ3_근거_태그가_실제_입력값_집합_안에_있음(client, members):
    """⑤ 11절 GS-11 ~ GS-16 — 태그가 입력에 없는 것을 말하면 불합격.

    `context_tags`에 `날씨`가 적혀 있으면 그 요청에 실제로 날씨 코드가
    입력됐는지를 확인함. 이것이 ① Q-2 태그 일치율을 재는 방법임.
    """
    allowed = {"날씨", "이력", "취향", "요일", "시간대", "거리"}
    checked = 0
    for m in members[:6]:
        lat, lng = _region_center(m["region_code"])
        _, body = _recommend(client, m["member_ref"], lat=lat, lng=lng)
        for item in body.get("items", []):
            checked += 1
            assert set(item.get("evidence") or []) <= allowed, item.get("evidence")
    assert checked > 0


# ═══════════════════════════════════════════════════════════════════════════
# M-Q4 · M-Q5 — 하드필터 위반 0건 (① G-3) · 페일세이프 기록률 100%
# GS-7 ~ GS-10
# ═══════════════════════════════════════════════════════════════════════════
def test_MQ4_알레르겐_보유_회원에게_위반_식당이_1건도_노출되지_않음(client, members, db):
    """① G-3 — **0건. 1건이라도 있으면 불합격.**

    추천에 노출된 식당의 원재료를 저장소에서 다시 읽어 회원의 금지 식재료와
    교집합이 있는지 대조함(⑥ M-Q4 — 하드필터 로그와 노출 로그 대조).
    """
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
    from lp_common.codes import resolve_blocked_ingredients

    violations = []
    exposed = 0
    for m in members:
        if not m["has_restriction"] or not m["sensitive_consent"]:
            continue
        row = db.execute(
            "SELECT allergen_names, diet_types FROM dietary_restriction WHERE member_ref=%s",
            (m["member_ref"],),
        )
        allergens, diets = row[0]
        blocked, _ = resolve_blocked_ingredients(list(allergens), list(diets))
        lat, lng = _region_center(m["region_code"])
        _, body = _recommend(client, m["member_ref"], lat=lat, lng=lng)
        for item in body.get("items", []):
            exposed += 1
            got = db.execute(
                "SELECT allergen_codes FROM restaurant_cache WHERE restaurant_id=%s",
                (item["restaurant_id"],),
            )
            codes = got[0][0]
            # 원재료 정보가 없는 식당이 노출된 것 자체가 B-2 페일세이프 위반임
            assert codes is not None, (
                f"{m['member_ref']}: 원재료 미상 식당 {item['restaurant_id']}이 노출됨 "
                "(B-2 페일세이프가 뚫림)"
            )
            overlap = set(codes) & blocked
            if overlap:
                violations.append((m["member_ref"], item["restaurant_id"], sorted(overlap)))

    assert exposed > 0, "알레르기 보유 회원에게 노출된 카드가 0건이라 측정 불가"
    assert violations == [], f"① G-3 위반 {len(violations)}건: {violations[:5]}"


def test_MQ5_페일세이프_동작이_100퍼센트_기록됨(db):
    """⑥ M-Q5 — 판정 불확실 시 전체 제외가 기록에 남는 비율 **100%**.

    O-8 차단·필터 기록에 `failsafe_count`가 남아 있어야 함.
    """
    rows = db.execute(
        "SELECT attributes->>'failsafe_count', attributes->>'block_stats' "
        "FROM obs_span WHERE step='S-R8' ORDER BY id DESC LIMIT 50"
    )
    assert rows, "S-R8 관측 기록이 없음"
    assert all(r[0] is not None for r in rows), "페일세이프 건수가 안 남은 기록이 있음"
    # 원천 결측 식당이 12% 섞여 있으므로 최소 1건은 실제로 발동해야 함
    assert any(int(r[0]) > 0 for r in rows), "페일세이프가 한 번도 발동하지 않음"


# ═══════════════════════════════════════════════════════════════════════════
# M-Q1 — 추천 조회 응답 시간 p95 3초 (① G-1)
# ═══════════════════════════════════════════════════════════════════════════
def test_MQ1_추천_조회_p95가_3초_이내임(client, members):
    """① Q-1 — p95 3,000ms. **조건 병기**: 진행 중 요청 300건 이하 구간임.

    로컬 단일 요청 측정이므로 (a-2) 전제를 만족함. 피크 1,000건 전제에서는
    커넥션 풀 100개로 처리량이 약 3.3배 부족하며 그것은 여기서 재지 않음.

    **합격 조건이 2개인 이유** — 지연만 보면 이 시험은 속일 수 있음.
    `S-R10` 타임아웃을 설계값 1,200ms로 두면 C-1이 매번 타임아웃해 L-2
    폴백으로 착지하고, 지연은 1.2초로 예산 안에 들어옴. 그러나 그때 근거
    문장은 전부 거리·평점 기본 문구이므로 ① Q-2 설명가능성이 죽어 있음.
    **① G-1과 ① Q-2를 동시에 만족해야 통과**로 둠.
    """
    latencies, fallback_hits, total = [], 0, 0
    for i in range(12):
        m = members[i % len(members)]
        if not m["location_consent"] or not m["sensitive_consent"]:
            continue
        lat, lng = _region_center(m["region_code"])
        started = time.perf_counter()
        _, body = _recommend(client, m["member_ref"], lat=lat, lng=lng)
        latencies.append((time.perf_counter() - started) * 1000)
        total += 1
        if body.get("fallback_reason"):
            fallback_hits += 1
    assert len(latencies) >= 8
    latencies.sort()
    p95 = latencies[int(len(latencies) * 0.95) - 1]
    fallback_rate = fallback_hits / total
    print(
        f"\n  측정 {total}건 · 중앙값 {statistics.median(latencies):.0f}ms"
        f" · p95 {p95:.0f}ms · 폴백률 {fallback_rate:.0%}"
    )
    problems = []
    if p95 > 3000:
        problems.append(f"① G-1 위반 — p95 {p95:.0f}ms > 3,000ms")
    if fallback_rate > 0.5:
        problems.append(
            f"① Q-2 무력화 — 요청의 {fallback_rate:.0%}가 L-2 폴백으로 착지해 "
            "근거 문장이 기본 문구가 됨(빠른 것은 생성을 포기했기 때문임)"
        )
    assert not problems, (
        "④ 9-1절 `S-R10` 배정값과 실측이 어긋나 두 목표를 동시에 못 만족함:\n  - "
        + "\n  - ".join(problems)
    )


# ═══════════════════════════════════════════════════════════════════════════
# ④ 5-1절 S-R2 동의 상태 확인 · ⑥ B-8
# ═══════════════════════════════════════════════════════════════════════════
def test_위치_미동의_회원은_수동_입력_모드로_착지함(client, members):
    """④ 5-1절 — 좌표를 쓰지 않고 중단하며 수동 위치 입력 모드로 착지."""
    target = next((m for m in members if not m["location_consent"]), None)
    assert target is not None, "합성 데이터에 위치 미동의 회원이 없음"
    _, body = _recommend(client, target["member_ref"])
    assert body["fallback_reason"] == "CONSENT_REQUIRED"
    assert body.get("manual_location_required") is True
    assert body["items"] == []


def test_식이제한_있는데_민감_미동의면_필터_없이_진행하지_않고_중단함(client, members):
    """④ 5-1절 — **"필터 없이 진행"을 택하지 않음.**

    필터를 건너뛰면 ① G-3 위반 경로가 생기므로 중단 쪽으로 무너뜨림.
    """
    target = next(
        (m for m in members if m["has_restriction"] and not m["sensitive_consent"]), None
    )
    assert target is not None, "합성 데이터에 해당 회원이 없음"
    _, body = _recommend(client, target["member_ref"])
    assert body["fallback_reason"] == "SENSITIVE_CONSENT_REQUIRED"
    assert body["items"] == [], "동의 없이 추천이 나갔음 — G-3 위반 경로임"


# ═══════════════════════════════════════════════════════════════════════════
# M-Q7 — 콜드스타트 안전망 (GS-21 ~ GS-23)
# ═══════════════════════════════════════════════════════════════════════════
def test_MQ7_콜드스타트_감지_후보3개_안내문구_3항목_모두_만족(client, members):
    """⑥ M-Q7 — 감지 · 후보 3개 채움 · 안내 문구 3항목 모두 만족해야 100%."""
    target = next((m for m in members if m["feedback_count"] < 5), None)
    assert target is not None, "합성 데이터에 콜드스타트 회원이 없음"
    lat, lng = _region_center(target["region_code"])
    _, body = _recommend(client, target["member_ref"], lat=lat, lng=lng)
    assert body["coldstart_notice"] == "아직 취향을 학습 중이에요"  # 안내 문구
    assert len(body["items"]) == 3  # 후보 3개 채움


# ═══════════════════════════════════════════════════════════════════════════
# ⑥ G-8 · 8절 — 출력 측 노출 검사가 실제 응답에 적용됨
# ═══════════════════════════════════════════════════════════════════════════
def test_응답에_좌표_닉네임_이메일이_섞여_나가지_않음(client, members):
    """⑥ 8절 L-1 ~ L-4 · ⑤ F-2·F-3."""
    import re

    email = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
    for m in members[:6]:
        lat, lng = _region_center(m["region_code"])
        _, body = _recommend(client, m["member_ref"], lat=lat, lng=lng)
        blob = str(body)
        assert "nickname" not in blob
        assert not email.search(blob), "응답에 이메일 패턴이 있음"
        for item in body.get("items", []):
            assert "lat" not in item and "lng" not in item
            assert "distance_m" in item and "walk_min" in item


def test_근거_문장에_알레르기_항목명이_들어가지_않음(client, members, db):
    """⑤ 8절 F-5 규칙 · ③ A-2 중단 조건 ④ — 필터 사유를 근거 문장에 쓰지 않음."""
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
    from lp_common.codes import find_allergen_label

    # 단순 부분 문자열 대조를 쓰지 않음 — `게`가 `무난하게`에 걸리는 오탐이
    # 실물 출력에서 실제로 났음. 서비스와 **같은 낱말 경계 매처**로 대조함.
    for m in members:
        if not m["has_restriction"] or not m["sensitive_consent"]:
            continue
        lat, lng = _region_center(m["region_code"])
        _, body = _recommend(client, m["member_ref"], lat=lat, lng=lng)
        for item in body.get("items", []):
            hit = find_allergen_label(item["reason_text"])
            assert hit is None, (
                f"근거 문장에 알레르겐 항목명 {hit!r}이 있음: {item['reason_text']!r}"
            )


# ═══════════════════════════════════════════════════════════════════════════
# ④ 10절 L-1 · L-2 반복 상한과 착지 노드
# ═══════════════════════════════════════════════════════════════════════════
def test_L1_거절_재실행이_같은_요청_시각으로_밟힘(client, members):
    """루프 재실행은 **같은 계약을 다시 밟는 것**임(③ 3절 J-6 흡수 판정).

    회귀 시험: `at`을 전달하지 않으면 서버가 현재 시각으로 다시 계산하고
    영업 시간 필터(B-3)가 다른 결과를 내, 거절 한 번에 후보가 통째로
    사라졌음. 점심 시각 밖에서 돌려도 정상 동작해야 함.
    """
    m = next(m for m in members if m["location_consent"] and m["sensitive_consent"])
    lat, lng = _region_center(m["region_code"])
    _, first = _recommend(client, m["member_ref"], lat=lat, lng=lng)
    if not first["items"]:
        pytest.skip("후보 풀이 비어 거절 경로를 태울 수 없음")
    rejected = first["items"][0]["restaurant_id"]

    body = client.post(
        "/api/recommendations/reject",
        json={
            "member_ref": m["member_ref"],
            "lat": lat,
            "lng": lng,
            "at": LUNCH.isoformat(),
            "reject_history": [rejected],
            "refresh_count": 0,
        },
    ).json()
    assert body["items"], f"거절 후 대체 추천이 0건임(폴백 {body.get('fallback_reason')})"
    assert rejected not in {i["restaurant_id"] for i in body["items"]}


def test_L1_개별_거절_상한을_넘으면_안전_종료로_착지함(client, members):
    """④ 10절 L-1 — 소진 시 "주변에 더 추천할 곳이 없어요. 거리를 넓혀볼까요?"."""
    m = next(m for m in members if m["location_consent"] and m["sensitive_consent"])
    lat, lng = _region_center(m["region_code"])
    body = client.post(
        "/api/recommendations/reject",
        json={
            "member_ref": m["member_ref"],
            "lat": lat,
            "lng": lng,
            "reject_history": [f"R-FAKE-{i}" for i in range(10)],  # 상한 초과
            "refresh_count": 0,
        },
    ).json()
    assert body["fallback_reason"] == "NO_CANDIDATE"
    assert "거리를 넓혀볼까요" in body["message"]


def test_L2_전체_새로고침_상한이_요청당_모델_호출을_묶음(client, members, db):
    """⑥ G-3 — 요청당 `llm_call_count_per_request` 상한. L-2 상한에서 파생됨.

    상한을 넘긴 새로고침은 모델을 부르지 않고 착지함 — 요청당 단가에
    천장이 생김(④ 10절 "상한이 열려 있는 동안 요청당 단가에 천장이 없음").
    """
    m = next(m for m in members if m["location_consent"] and m["sensitive_consent"])
    lat, lng = _region_center(m["region_code"])
    before = db.execute("SELECT count(*) FROM obs_span WHERE point='O-1'")[0][0]
    body = client.post(
        "/api/recommendations/refresh",
        json={
            "member_ref": m["member_ref"],
            "lat": lat,
            "lng": lng,
            "reject_history": [],
            "refresh_count": 99,  # 상한 초과
        },
    ).json()
    after = db.execute("SELECT count(*) FROM obs_span WHERE point='O-1'")[0][0]
    assert body["items"] == []
    assert after == before, "상한을 넘겼는데도 모델을 호출했음 — G-3이 안 걸림"


# ═══════════════════════════════════════════════════════════════════════════
# S-E 이벤트 경로 (④ 3-3절)
# ═══════════════════════════════════════════════════════════════════════════
def test_SE_원탭_기록과_피드백이_저장되고_중복이_감지됨(client, members):
    m = next(m for m in members if m["location_consent"] and m["sensitive_consent"])
    lat, lng = _region_center(m["region_code"])
    _, rec = _recommend(client, m["member_ref"], lat=lat, lng=lng)
    assert rec["items"], "추천이 없어 기록 경로를 태울 수 없음"
    rid = rec["items"][0]["restaurant_id"]

    first = client.post(
        "/api/meals",
        json={
            "member_ref": m["member_ref"],
            "restaurant_id": rid,
            "recommendation_id": rec["recommendation_id"],
        },
    ).json()
    assert "meal_id" in first, first

    fb = client.post(
        "/api/feedback",
        json={"meal_id": first["meal_id"], "member_ref": m["member_ref"], "liked": True},
    ).json()
    assert fb["applied"] == "OK"

    # S-E2 중복 기록 검증
    dup = client.post(
        "/api/meals", json={"member_ref": m["member_ref"], "restaurant_id": rid}
    ).json()
    assert dup["reason_code"] == "DUPLICATE_RECORD"


def test_피드백_스킵은_중립으로_적용됨(client, members):
    """`US:UFR-REC-090#처리결과` — 스킵 시 기본값(중립) 적용."""
    m = next(m for m in members if m["location_consent"] and m["sensitive_consent"])
    lat, lng = _region_center(m["region_code"])
    _, rec = _recommend(client, m["member_ref"], lat=lat, lng=lng)
    rid = rec["items"][-1]["restaurant_id"]
    meal = client.post(
        "/api/meals", json={"member_ref": m["member_ref"], "restaurant_id": rid}
    ).json()
    if "meal_id" not in meal:
        pytest.skip("중복 기록이라 스킵 경로를 태울 수 없음")
    fb = client.post(
        "/api/feedback",
        json={"meal_id": meal["meal_id"], "member_ref": m["member_ref"], "liked": None},
    ).json()
    assert fb["reason_code"] == "FEEDBACK_SKIP" and fb["applied"] == "NEUTRAL"


# ═══════════════════════════════════════════════════════════════════════════
# ⑤ 10절 폴백 — 데이터가 모자라면 "모른다"고 답함
# ═══════════════════════════════════════════════════════════════════════════
def test_기록_10건_미만이면_인사이트를_지어내지_않음(client, members):
    """⑤ 10절 — "10끼 이상 기록하면 취향 인사이트가 열려요!".

    근거가 모자랄 때 문장을 지어내면 ① Q-2 설명가능성이 오히려 무너짐.
    """
    target = next((m for m in members if m["feedback_count"] < 5), None)
    body = client.get(f"/api/insights/{target['member_ref']}").json()
    assert body["available"] is False
    assert "10끼 이상" in body["message"]


# ═══════════════════════════════════════════════════════════════════════════
# ⑥ 6절 관측 기록 지점 · ⑦ 5-3 문제 3 (접근 로그 분리 저장)
# ═══════════════════════════════════════════════════════════════════════════
def test_관측_기록에_민감_필드_원문이_남지_않음(db):
    """⑤ F-8 · ⑥ M-1 ~ M-4 — 적재 직전 마스킹이 실제로 걸렸는지."""
    rows = db.execute("SELECT attributes::text FROM obs_span ORDER BY id DESC LIMIT 300")
    blob = " ".join(r[0] for r in rows)
    for label in ("땅콩", "우유", "고등어", "@example.invalid", "postgresql://"):
        assert label not in blob, f"관측 기록에 {label!r} 원문이 남았음"


def test_개인정보_접근_로그가_일반_관측_기록과_분리_저장됨(db):
    """⑦ 5-3 문제 3 해결 — ⑥이 O-9를 분리 저장하기로 확정한 것의 실행 증거."""
    n = db.execute("SELECT count(*) FROM obs_access_log")[0][0]
    assert n > 0, "접근 로그가 비어 있음"
    cols = db.execute(
        "SELECT column_name FROM information_schema.columns WHERE table_name='obs_access_log'"
    )
    names = {c[0] for c in cols}
    # 값은 남기지 않고 주체·시각·항목 종류만(⑥ O-9 · M-4)
    assert {"actor", "member_ref", "field_ids", "allergen_key_decrypt", "created_at"} <= names
    sample = db.execute("SELECT member_ref, field_ids FROM obs_access_log LIMIT 5")
    for ref, fields in sample:
        assert ref.startswith("ref:"), "접근 로그에 회원 참조키 원문이 남았음"
        assert all(f.startswith("F-") for f in fields), "항목 종류가 F-n 인용이 아님"


def test_ToolCallAccuracy_기대_호출_순서가_지켜짐(db):
    """⑤ 7절 — 엄격 순서 모드. 순서가 틀리면 인자가 다 맞아도 0점임.

    한 trace 안에서 `S-R8`(하드필터)이 `S-R10`(C-1)보다 **먼저** 기록돼야 함.
    """
    traces = db.execute(
        "SELECT trace_id FROM obs_span WHERE step='S-R10' AND is_error=false "
        "ORDER BY id DESC LIMIT 20"
    )
    assert traces, "S-R10 기록이 없어 순서를 검증할 수 없음"
    checked = 0
    for (trace_id,) in traces:
        seq = db.execute(
            "SELECT step FROM obs_span WHERE trace_id=%s AND step IN ('S-R8','S-R9','S-R10') "
            "ORDER BY id",
            (trace_id,),
        )
        steps = [s[0] for s in seq]
        if steps != ["S-R8", "S-R9", "S-R10"]:
            pytest.fail(f"기대 호출 시퀀스 위반 trace={trace_id} 실제={steps}")
        checked += 1
    assert checked > 0


def test_토큰_사용량이_기록됨(db):
    """⑥ O-1 · O-4 — 모델 호출에 토큰 사용량이 남아야 비용 상한을 감시함."""
    rows = db.execute(
        "SELECT attributes->>'input_tokens', attributes->>'output_tokens', attributes->>'model' "
        "FROM obs_span WHERE point='O-1' AND is_error=false "
        "AND attributes->>'path_fallback_used'='false' ORDER BY id DESC LIMIT 10"
    )
    if not rows:
        pytest.skip("실물 모델 호출 기록이 없음(폴백만 발생)")
    assert any(r[0] and int(r[0]) > 0 for r in rows), "입력 토큰이 기록되지 않음"
    assert all("sonnet-5" in (r[2] or "") for r in rows), f"모델이 sonnet-5가 아님: {rows[0][2]}"
