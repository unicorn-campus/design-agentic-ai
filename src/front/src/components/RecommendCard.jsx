// ④ 11절 최종 출력 형식을 그대로 화면에 옮긴 카드.
//
// `reason_text`와 `confidence`는 **선택이 될 수 없음** — ① G-2가 동반 노출
// 100%를 요구하므로 둘 중 하나라도 없으면 카드를 그리지 않고 경고를 띄움.
// ⑥ G-9: 확신 스코어를 모든 카드에 노출해 과신을 막고, "제시이며 확정이
// 아님"이라는 성격을 화면에 유지함(① 성격 선언).

export function RecommendCard({ item, rank, onAccept, onReject, busy }) {
  const missing = !item.reason_text || item.confidence === null || item.confidence === undefined

  if (missing) {
    return (
      <div className="card card--broken">
        <strong>① G-2 위반 — 근거·확신 스코어가 빠진 카드</strong>
        <p>동반 노출률 100%가 깨졌습니다. 이 카드는 노출되면 안 됩니다.</p>
      </div>
    )
  }

  const pct = Math.round(item.confidence * 100)
  const level = pct >= 60 ? 'high' : pct >= 40 ? 'mid' : 'low'

  return (
    <div className="card">
      <div className="card__head">
        <span className="card__rank">{rank + 1}</span>
        <div>
          <h3>{item.restaurant_name || '(표시명 없음)'}</h3>
          <p className="card__menu">{item.signature_menu}</p>
        </div>
        <div className={`conf conf--${level}`} title="확신 스코어(① G-2 동반 노출 필수)">
          {pct}%
        </div>
      </div>

      <p className="card__reason">{item.reason_text}</p>
      {item.reason_replaced && (
        <p className="card__replaced">
          ⑥ L-2 출력검사에 걸려 근거 문장이 기본 추천 이유로 교체됨
        </p>
      )}

      <div className="card__meta">
        <span>도보 {item.walk_min}분</span>
        <span>{item.distance_m}m</span>
        <span className="tags">
          {(item.evidence || []).map((tag) => (
            <em key={tag}>#{tag}</em>
          ))}
        </span>
      </div>

      <div className="card__actions">
        <button disabled={busy} onClick={() => onAccept(item)}>
          여기로 갈래요
        </button>
        <button disabled={busy} className="ghost" onClick={() => onReject(item)}>
          다른 곳 볼래요
        </button>
      </div>
    </div>
  )
}
