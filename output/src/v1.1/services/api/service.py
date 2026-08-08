"""화면용 데모 포트. 실제 LangGraph 연결은 동일 시그니처 구현체로 교체 가능함."""

from __future__ import annotations

import time
import uuid
from datetime import UTC, date, datetime

from .schemas import (
    InsightResponse,
    MealRecordRequest,
    MealRecordResponse,
    ProfileResponse,
    ProfileUpdateRequest,
    RecommendationCard,
    RecommendationRequest,
    RecommendationResponse,
    SubscriptionRequest,
    SubscriptionResponse,
)


class ApprovalRequired(RuntimeError):
    """결제·해지처럼 되돌리기 어려운 쓰기에 명시적 승인이 빠짐."""


class DemoLunchPickService:
    """외부 API 없이 프로토타입과 계약을 검증하는 결정론 구현체."""

    def __init__(self) -> None:
        self.nickname = "준혁"
        self._idempotent_subscriptions: dict[str, SubscriptionResponse] = {}

    async def recommend(self, request: RecommendationRequest, correlation_id: str) -> RecommendationResponse:
        del request
        rows = (
            ("rec-001", "된장찌개 정식", "미소된장", 350, 5, 87.0, 8_500, "비 오는 날 따뜻한 국물 추천", "서울 강남구 테헤란로 123"),
            ("rec-002", "크림 파스타", "봉주르 파스타", 550, 8, 72.0, 11_000, "이번 주 한식이 많았으니 양식", "서울 강남구 역삼로 45"),
            ("rec-003", "짬뽕", "홍콩반점", 200, 3, 65.0, 9_000, "가까운 곳에서 빠르게", "서울 강남구 테헤란로 88"),
        )
        cards = [
            RecommendationCard(
                recommendation_id=row[0], menu_name=row[1], signature_menu=row[1], place_name=row[2],
                distance_m=row[3], walk_minutes=row[4], confidence_score=row[5], price=row[6],
                reason_line=row[7], reason_detail=f"{row[7]} — 날씨·최근 이력·취향을 함께 반영했어요.",
                context_tags=["🌧️ 날씨", "❤️ 취향"], address=row[8],
            )
            for row in rows
        ]
        return RecommendationResponse(cards=cards, card_count=len(cards), correlation_id=correlation_id)

    async def record_meal(self, request: MealRecordRequest) -> MealRecordResponse:
        del request
        return MealRecordResponse(
            meal_record_id=f"meal-{uuid.uuid4().hex[:12]}",
            recorded_on=date.today(),
            undo_until_epoch_ms=int(time.time() * 1000) + 30_000,
        )

    async def profile(self) -> ProfileResponse:
        return ProfileResponse(member_id="demo-member", nickname=self.nickname, email_masked="ju***@example.com", plan="free", meal_count=12)

    async def update_profile(self, request: ProfileUpdateRequest) -> ProfileResponse:
        self.nickname = request.nickname
        return await self.profile()

    async def insights(self) -> InsightResponse:
        return InsightResponse(
            top_categories=[{"name": "한식", "percent": 62}, {"name": "양식", "percent": 25}, {"name": "중식", "percent": 8}],
            weekly_pattern_summary="한식을 가장 좋아하시네요! 이번 주 4일 연속 국물 메뉴였어요.",
            satisfaction_average=4.2,
            accuracy_gain_rate=42.0,
        )

    async def subscribe(self, request: SubscriptionRequest, *, cancel: bool = False) -> SubscriptionResponse:
        if not request.approved:
            raise ApprovalRequired("결제·해지는 사용자 승인 후에만 실행 가능함")
        cached = self._idempotent_subscriptions.get(request.idempotency_key)
        if cached is not None:
            return cached
        action = "cancel_scheduled" if cancel else "active"
        plan = "free_pending" if cancel else "premium"
        response = SubscriptionResponse(
            status=action,
            plan=plan,
            message=("현재 결제 주기 종료일에 무료 플랜으로 전환됨" if cancel else "프리미엄 7일 체험이 시작됨"),
        )
        self._idempotent_subscriptions[request.idempotency_key] = response
        return response

    @staticmethod
    def now_iso() -> str:
        return datetime.now(UTC).isoformat()
