import { useEffect, useMemo, useState } from "react";
import { fetchRecommendations, recordMeal } from "../api";
import { rejectReasons, sampleRecommendations, type MealFeedback, type MealHistoryEntry, type Recommendation, type Route } from "../data";
import { BottomNav, Header, Modal, Page } from "../components/Chrome";

type Navigate = (route: Route) => void;

export function HomeScreen({ navigate, selectRecommendation }: { navigate: Navigate; selectRecommendation: (item: Recommendation) => void }) {
  const [recommendations, setRecommendations] = useState(sampleRecommendations);
  const [detail, setDetail] = useState<Recommendation | null>(null);
  const [rejecting, setRejecting] = useState<Recommendation | null>(null);
  const [loading, setLoading] = useState(false);
  const load = async () => {
    setLoading(true);
    try { setRecommendations(await fetchRecommendations()); } finally { setLoading(false); }
  };
  useEffect(() => { void load(); }, []);
  const accept = (item: Recommendation) => { selectRecommendation(item); navigate("navigation"); };

  return (
    <>
      <Header location navigate={navigate} />
      <Page>
        <section className="home-hero">
          <div><p>좋은 점심이에요, 준혁님 👋</p><h1>오늘 뭐 먹을까요?</h1></div>
          <button className={`refresh-button ${loading ? "is-loading" : ""}`} aria-label="전체 새로고침" onClick={() => void load()}>↻</button>
        </section>
        <div className="context-row"><span className="tag tag--info">🌧️ 비 18°C</span><span className="tag">📅 금요일</span><span className="tag tag--success">⏰ 점심 42분</span></div>
        <p className="section-eyebrow">취향과 오늘 상황을 반영한 추천 3곳</p>
        <section aria-live="polite" aria-busy={loading}>
          {recommendations.map((item) => (
            <article className="card rec-card" key={item.recommendationId}>
              <div className="rec-card__rank">{item.rank}. 오늘의 선택</div>
              <div className="rec-card__header"><span className="rec-card__name">{item.restaurantName} <span className="caption">({item.category})</span></span><span className="rec-card__score">⭐ {item.confidenceScore}%</span></div>
              <div className="rec-card__menu">대표: {item.menuName} · {item.price.toLocaleString("ko-KR")}원</div>
              <div className="rec-card__meta">📍 도보 {item.walkMinutes}분 · {item.distanceM}m</div>
              <div className="rec-card__reason">“{item.reasonLine}”</div>
              <div className="rec-card__actions">
                <button className="btn-text" onClick={() => setDetail(item)}>왜?</button>
                <button className="btn-text muted" onClick={() => setRejecting(item)}>거절</button>
                <button className="btn btn-primary" onClick={() => accept(item)}>여기 갈래요 →</button>
              </div>
            </article>
          ))}
        </section>
      </Page>
      <BottomNav active="home" navigate={navigate} />
      {detail && <Modal title={`${detail.restaurantName}을 추천한 이유`} onClose={() => setDetail(null)}>
        <p className="modal__body">{detail.reasonDetail}</p>
        <div className="context-row">{detail.contextTags.map((tag) => <span className="tag" key={tag}>{tag}</span>)}</div>
        <button className="btn btn-primary btn-full" onClick={() => accept(detail)}>여기 갈래요 →</button>
      </Modal>}
      {rejecting && <Modal title="거절 사유를 알려주세요" onClose={() => setRejecting(null)}>
        <p className="modal__body">다음 추천을 더 잘 맞추는 데 사용해요.</p>
        <div className="chip-group">{rejectReasons.map((reason) => <button className="chip" key={reason} onClick={() => { setRecommendations((current) => current.filter((item) => item.recommendationId !== rejecting.recommendationId)); setRejecting(null); }}>{reason}</button>)}</div>
      </Modal>}
    </>
  );
}

export function NavigationScreen({ navigate, recommendation }: { navigate: Navigate; recommendation: Recommendation }) {
  return (
    <>
      <Header title="길찾기" back="home" navigate={navigate} />
      <Page>
        <section className="nav-destination"><span className="rank-pin">1</span><div><h1>{recommendation.restaurantName}</h1><p>{recommendation.address}</p></div></section>
        <div className="map-panel" role="img" aria-label="도보 경로 지도">
          <div className="map-grid" /><div className="route-line" /><span className="map-start">현재 위치</span><span className="map-end">🍽️</span>
        </div>
        <section className="walk-summary"><div className="walk-icon">🚶</div><div><strong>도보 {recommendation.walkMinutes}분</strong><p>{recommendation.distanceM}m · 횡단보도 2회</p></div></section>
        <div className="external-map-row"><button className="btn btn-secondary" onClick={() => alert("카카오맵 딥링크는 모바일에서 열립니다.")}>🟨 카카오맵</button><button className="btn btn-secondary" onClick={() => alert("네이버지도 딥링크는 모바일에서 열립니다.")}>🟩 네이버지도</button></div>
        <div className="return-note">⏱️ 지금 출발하면 12:42 도착 · 13:28 복귀 예상</div>
        <button className="btn btn-primary btn-full" onClick={() => navigate("meal")}>도착했어요 · 식사 기록하기</button>
      </Page>
    </>
  );
}

export function MealScreen({ navigate, recommendation, onMealCompleted }: { navigate: Navigate; recommendation: Recommendation; onMealCompleted: (feedback: MealFeedback) => void }) {
  const [recorded, setRecorded] = useState(false);
  const [feedback, setFeedback] = useState<"good" | "bad" | null>(null);
  const [message, setMessage] = useState("");
  const save = async () => {
    try { await recordMeal(recommendation.recommendationId); setMessage("식사 기록을 저장했어요."); }
    catch { setMessage("데모 모드로 기록했어요. API 연결 후 서버에 저장됩니다."); }
    setRecorded(true);
  };
  return (
    <>
      <Header title="식사 기록" back="navigation" navigate={navigate} />
      <Page>
        {!recorded ? <section className="record-hero"><div className="meal-emoji">🍲</div><p>{recommendation.restaurantName}</p><h1>{recommendation.menuName},<br />맛있게 드셨나요?</h1><button className="record-main-button" onClick={() => void save()}>✓<span>식사 기록하기</span></button></section>
          : <section className="feedback-panel"><div className="success-mark">✓</div><h1>오늘 점심 어땠어요?</h1><p>{message}</p><div className="emoji-feedback"><button className={feedback === "good" ? "selected" : ""} onClick={() => setFeedback("good")}>👍<span>좋았어요</span></button><button className={feedback === "bad" ? "selected" : ""} onClick={() => setFeedback("bad")}>👎<span>별로였어요</span></button></div><div className="chip-group feedback-keywords"><button className="chip">맛있었어요</button><button className="chip">양 적당</button><button className="chip">빨리 나왔어요</button></div><button className="btn btn-primary btn-full" disabled={!feedback} onClick={() => { if (feedback) onMealCompleted(feedback); navigate("home"); }}>피드백 완료</button><button className="btn-text btn-full" onClick={() => { onMealCompleted("neutral"); navigate("home"); }}>건너뛰기</button></section>}
      </Page>
      {recorded && <div className="undo-bar"><span>식사 기록 완료</span><button onClick={() => setRecorded(false)}>실행 취소</button></div>}
    </>
  );
}

export function InsightsScreen({ navigate, view, records }: { navigate: Navigate; view: "history" | "insight"; records: MealHistoryEntry[] }) {
  const now = new Date();
  const daysInMonth = new Date(now.getFullYear(), now.getMonth() + 1, 0).getDate();
  const monthLabel = `${now.getFullYear()}년 ${now.getMonth() + 1}월`;
  const mealByDay = useMemo(() => new Map(records.map((item) => [item.day, item])), [records]);
  return (
    <>
      <Header title="나의 점심" navigate={navigate} />
      <Page>
        <div className="segmented-tabs" role="tablist"><button className={view === "history" ? "active" : ""} aria-selected={view === "history"} onClick={() => navigate("history")} role="tab">이력</button><button className={view === "insight" ? "active" : ""} aria-selected={view === "insight"} onClick={() => navigate("insights")} role="tab">인사이트</button></div>
        {view === "history" ? <>
          <div className="calendar-header"><button className="btn-icon">←</button><strong>{monthLabel}</strong><button className="btn-icon">→</button></div>
          <div className="calendar-grid">{["일","월","화","수","목","금","토"].map((day) => <span className="calendar-label" key={day}>{day}</span>)}{Array.from({ length: daysInMonth }, (_, index) => index + 1).map((day) => { const meal = mealByDay.get(day); return <div className={`calendar-day ${meal ? "has-meal" : ""}`} data-testid={`meal-day-${day}`} key={day}><span>{day}</span>{meal && <small title={meal.restaurant}>{meal.feedback === "good" ? "😊" : meal.feedback === "bad" ? "😕" : "🍽️"}</small>}</div>; })}</div>
          <section className="premium-callout"><div><strong>30일 이전 이력도 계속 보관하세요</strong><p>프리미엄은 식사 이력을 제한 없이 기억해요.</p></div><button className="btn-text" onClick={() => navigate("subscription")}>체험하기</button></section>
        </> : <section className="insight-stack">
          <article className="card insight-card highlight-card"><span>이번 주 당신의 점심 패턴</span><h2>한식을 가장 좋아하시네요!</h2><p>이번 주 4일 연속 국물 메뉴였어요 🍲</p></article>
          <article className="card insight-card"><h3>선호 카테고리 Top 5</h3>{[["한식",62],["양식",25],["중식",8],["일식",3],["기타",2]].map(([label, value]) => <div className="bar-row" key={label}><span>{label}</span><div><i style={{ width: `${value}%` }} /></div><strong>{value}%</strong></div>)}</article>
          <article className="card insight-card"><h3>만족도 변화</h3><div className="satisfaction"><strong>4.2</strong><span>/ 5.0</span><b>↗ 0.4</b></div><p>추천 정확도가 첫 주보다 42% 좋아졌어요.</p></article>
        </section>}
      </Page>
      <BottomNav active={view === "history" ? "history" : "insights"} navigate={navigate} />
    </>
  );
}

export function ProfileScreen({ navigate, dietaryConfigured, locationEnabled, onLocationChange }: { navigate: Navigate; dietaryConfigured: boolean; locationEnabled: boolean; onLocationChange: (enabled: boolean) => void }) {
  const [name, setName] = useState("준혁");
  const [draft, setDraft] = useState(name);
  const [editing, setEditing] = useState(false);
  const [recommendAlert, setRecommendAlert] = useState(true);
  return (
    <>
      <Header title="프로필" navigate={navigate} />
      <Page>
        <section className="profile-hero"><div className="profile-avatar">준</div><div><h1>{name}님</h1><p>준혁님과 12번의 점심을 함께했어요.</p></div><button className="btn-text" onClick={() => setEditing(true)}>수정</button></section>
        <Settings title="계정"><SettingRow label="이메일" value="junhyuk@example.com" /><SettingRow label="닉네임" value={name} /></Settings>
        <Settings title="식이제한"><SettingRow label="알레르기·식이 유형" value={dietaryConfigured ? "설정됨" : "미설정"} onClick={() => navigate("dietary")} /></Settings>
        <Settings title="알림"><ToggleRow label="점심 추천 알림" value={recommendAlert} onChange={setRecommendAlert} /><ToggleRow label="피드백 리마인더" value onChange={() => undefined} /></Settings>
        <Settings title="구독"><SettingRow label="현재 플랜" value="무료" onClick={() => navigate("subscription")} /></Settings>
        <Settings title="위치"><ToggleRow label="위치 정보 제공" value={locationEnabled} onChange={onLocationChange} /></Settings>
        <button className="btn-text muted profile-logout" onClick={() => navigate("login")}>로그아웃</button>
      </Page>
      <BottomNav active="profile" navigate={navigate} />
      {editing && <Modal title="닉네임 수정" onClose={() => setEditing(false)}><label className="input-group">닉네임<input className="input-field" value={draft} maxLength={20} onChange={(event) => setDraft(event.target.value)} /></label><div className="modal-actions"><button className="btn btn-secondary" onClick={() => setEditing(false)}>취소</button><button className="btn btn-primary" disabled={draft.trim().length < 2} onClick={() => { setName(draft.trim()); setEditing(false); }}>저장</button></div></Modal>}
    </>
  );
}

function Settings({ title, children }: { title: string; children: React.ReactNode }) { return <section className="settings-section"><h2>{title}</h2>{children}</section>; }
function SettingRow({ label, value, onClick }: { label: string; value: string; onClick?: () => void }) { return <button className="setting-row" onClick={onClick} disabled={!onClick}><span>{label}</span><span>{value} {onClick && "›"}</span></button>; }
function ToggleRow({ label, value, onChange }: { label: string; value: boolean; onChange: (value: boolean) => void }) { return <label className="setting-row"><span>{label}</span><input type="checkbox" role="switch" checked={value} onChange={(event) => onChange(event.target.checked)} /></label>; }

export function SubscriptionScreen({ navigate }: { navigate: Navigate }) {
  const [payment, setPayment] = useState(false);
  const [active, setActive] = useState(false);
  const [cancel, setCancel] = useState(false);
  return (
    <>
      <Header title="구독 관리" back="profile" navigate={navigate} />
      <Page>
        <section className="subscription-hero"><span>🧠</span><h1>30일간 쌓인 취향 데이터가<br />내일 사라져요. 유지하시겠어요?</h1><p>프리미엄은 시간이 지날수록 더 정확해져요.</p></section>
        <div className="plan-grid"><article className="plan-card"><h2>무료</h2><strong>0원</strong><ul><li>추천 3개/일</li><li>이력 30일</li><li>기본 인사이트</li></ul><button className="btn btn-secondary btn-full" disabled={!active}>{active ? "무료로 전환" : "현재 플랜"}</button></article><article className="plan-card plan-card--premium"><span className="popular-badge">가장 인기</span><h2>⭐ 프리미엄</h2><strong>월 4,900원</strong><ul><li>추천 3개/일</li><li>이력 무제한 ✓</li><li>고급 인사이트 ✓</li><li>우선 학습 ✓</li></ul><button className="btn btn-primary btn-full" onClick={() => setPayment(true)}>{active ? "사용 중" : "7일 무료 체험 시작"}</button></article></div>
        {active && <button className="btn btn-secondary btn-full cancel-trigger" onClick={() => setCancel(true)}>구독 해지하기</button>}
        <p className="billing-note">체험 종료 전 알림 · 언제든 해지 가능 · 결제 전 최종 확인</p>
      </Page>
      {payment && <Modal title="결제 방식 선택" onClose={() => setPayment(false)}><form onSubmit={(event) => { event.preventDefault(); setActive(true); setPayment(false); }}><label className="input-group">카드 번호<input className="input-field" required inputMode="numeric" placeholder="0000 0000 0000 0000" /></label><div className="split-fields"><label className="input-group">유효기간<input className="input-field" required placeholder="MM/YY" /></label><label className="input-group">CVC<input className="input-field" required inputMode="numeric" placeholder="000" /></label></div><p className="approval-notice">결제하기를 누르면 월 4,900원 정기 결제에 승인합니다.</p><button className="btn btn-primary btn-full" type="submit">결제 승인하기</button></form></Modal>}
      {cancel && <Modal title="정말 해지하시겠어요?" onClose={() => setCancel(false)}><p className="modal__body">현재 결제 주기까지 프리미엄을 이용한 뒤 무료 플랜으로 전환됩니다.</p><div className="modal-actions"><button className="btn btn-secondary" onClick={() => setCancel(false)}>유지하기</button><button className="btn btn-primary danger" onClick={() => { setActive(false); setCancel(false); }}>해지 예약 승인</button></div></Modal>}
    </>
  );
}
