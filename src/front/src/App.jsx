import { useCallback, useEffect, useState } from 'react'
import { api } from './api/client'
import { RecommendCard } from './components/RecommendCard'

const REGION_CENTER = {
  'SEOUL-GANGNAM': [37.4979, 127.0276],
  'SEOUL-YEOUIDO': [37.5219, 126.9245],
  'SEOUL-JONGNO': [37.5729, 126.9794],
  'SEONGNAM-PANGYO': [37.3947, 127.1112],
}

// 서비스 구간은 점심 11 ~ 13시임(① 4절 Q-1 · `BM:1-Problem#P1`).
// 그 밖의 시각에는 영업 시간 필터가 반경 내 식당을 전부 걸러 내며 이것은
// **설계대로 도는 것**임. 로컬에서 아무 때나 확인할 수 있도록 요청 시각을
// 고를 수 있게 하되, 왜 그런지를 화면에 밝힘.
const LUNCH_SLOTS = [
  ['2026-08-06T11:30:00+09:00', '11:30 (EARLY_LUNCH)'],
  ['2026-08-06T12:10:00+09:00', '12:10 (PEAK_LUNCH)'],
  ['2026-08-06T13:20:00+09:00', '13:20 (LATE_LUNCH)'],
  ['', '지금 시각 그대로'],
]

export default function App() {
  const [members, setMembers] = useState([])
  const [atOverride, setAtOverride] = useState(LUNCH_SLOTS[1][0])
  const [memberRef, setMemberRef] = useState('')
  const [detail, setDetail] = useState(null)
  const [result, setResult] = useState(null)
  const [rejects, setRejects] = useState([])
  const [refreshCount, setRefreshCount] = useState(0)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)
  const [log, setLog] = useState([])
  const [insight, setInsight] = useState(null)

  const push = (line) =>
    setLog((prev) => [`${new Date().toLocaleTimeString('ko-KR')} ${line}`, ...prev].slice(0, 30))

  useEffect(() => {
    api
      .members()
      .then((r) => {
        setMembers(r.members)
        if (r.members.length) setMemberRef(r.members[0].member_ref)
      })
      .catch((e) => setError(`회원 목록을 못 불러왔습니다: ${e.message}`))
  }, [])

  useEffect(() => {
    if (!memberRef) return
    setResult(null)
    setRejects([])
    setRefreshCount(0)
    setInsight(null)
    api.member(memberRef).then(setDetail).catch(() => setDetail(null))
  }, [memberRef])

  const geoOf = () => {
    const m = members.find((x) => x.member_ref === memberRef)
    const center = REGION_CENTER[m?.region_code] || REGION_CENTER['SEOUL-GANGNAM']
    return { lat: center[0], lng: center[1] }
  }

  const run = useCallback(
    async (kind) => {
      setBusy(true)
      setError(null)
      const { lat, lng } = geoOf()
      const payload = {
        member_ref: memberRef,
        lat,
        lng,
        reject_history: rejects,
        refresh_count: refreshCount,
        ...(atOverride ? { at: atOverride } : {}),
      }
      try {
        const fn = kind === 'refresh' ? api.refresh : kind === 'reject' ? api.reject : api.recommend
        const r = await fn(payload)
        setResult(r)
        if (kind === 'refresh') setRefreshCount((c) => c + 1)
        push(
          `${kind} → 카드 ${r.items?.length ?? 0}건 · ${r.latency_ms ?? '?'}ms` +
            (r.fallback_reason ? ` · 폴백 ${r.fallback_reason}` : '') +
            (r.output_violations?.length ? ` · 출력검사 위반 ${r.output_violations.join(',')}` : '')
        )
      } catch (e) {
        setError(`${e.message} — ${e.detail?.message || ''}`)
        push(`실패: ${e.message}`)
      } finally {
        setBusy(false)
      }
    },
    [memberRef, rejects, refreshCount, members, atOverride]
  )

  const onAccept = async (item) => {
    try {
      const r = await api.recordMeal({
        member_ref: memberRef,
        restaurant_id: item.restaurant_id,
        recommendation_id: result?.recommendation_id,
      })
      if (r.reason_code === 'DUPLICATE_RECORD') {
        push(`S-E2 중복 기록 감지 — ${r.message}`)
        return
      }
      push(`S-E1 원탭 기록 완료 meal=${r.meal_id}`)
      await api.feedback({ meal_id: r.meal_id, member_ref: memberRef, liked: true })
      push('S-E4 피드백(좋아요) 제출 — A-3을 깨우지 않고 저장소에만 적재됨(J-9)')
    } catch (e) {
      push(`기록 실패: ${e.message}`)
    }
  }

  const onReject = async (item) => {
    const next = [...rejects, item.restaurant_id]
    setRejects(next)
    setBusy(true)
    setError(null)
    const { lat, lng } = geoOf()
    try {
      const r = await api.reject({
        member_ref: memberRef,
        lat,
        lng,
        reject_history: next,
        refresh_count: refreshCount,
        ...(atOverride ? { at: atOverride } : {}),
      })
      setResult(r)
      push(`L-1 개별 거절 ${next.length}회 → ${r.items?.length ?? 0}건 재제시`)
    } catch (e) {
      setError(e.message)
    } finally {
      setBusy(false)
    }
  }

  const loadInsight = async () => {
    try {
      setInsight(await api.insights(memberRef))
    } catch (e) {
      push(`인사이트 실패: ${e.message}`)
    }
  }

  const selected = members.find((m) => m.member_ref === memberRef)

  return (
    <div className="app">
      <header>
        <h1>런치픽</h1>
        <p className="tagline">
          최적 선택지를 <strong>제시</strong>합니다 — 시스템이 식사를 확정하지 않습니다
          <span className="src">① 성격 선언</span>
        </p>
      </header>

      <section className="panel">
        <label>
          회원
          <select value={memberRef} onChange={(e) => setMemberRef(e.target.value)}>
            {members.map((m) => (
              <option key={m.member_ref} value={m.member_ref}>
                {m.member_ref} · {m.region_code} · 피드백 {m.feedback_count}
                {m.has_restriction ? ' · 식이제한' : ''}
                {!m.location_consent ? ' · 위치 미동의' : ''}
                {!m.sensitive_consent ? ' · 민감 미동의' : ''}
              </option>
            ))}
          </select>
        </label>
        <label>
          요청 시각
          <select value={atOverride} onChange={(e) => setAtOverride(e.target.value)}>
            {LUNCH_SLOTS.map(([value, label]) => (
              <option key={label} value={value}>
                {label}
              </option>
            ))}
          </select>
        </label>
        {!atOverride && (
          <p className="notice">
            점심 11 ~ 13시 밖에서는 영업 시간 필터가 반경 내 식당을 전부 걸러 내
            <strong> 후보 0건</strong>으로 착지합니다. 고장이 아니라 설계대로 도는 것입니다.
            <span className="src">① 4절 Q-1 · ⑥ B-3</span>
          </p>
        )}
        {detail && (
          <div className="badges">
            <span className={detail.coldstart ? 'badge warn' : 'badge'}>
              {detail.coldstart ? '콜드스타트' : `취향 학습됨(${detail.feedback_count}건)`}
            </span>
            <span className="badge">{detail.plan_type}</span>
            {detail.restriction_count > 0 && (
              <span className="badge danger">식이제한 {detail.restriction_count}건</span>
            )}
            <span className={detail.location_consent ? 'badge ok' : 'badge danger'}>
              위치동의 {detail.location_consent ? 'O' : 'X'}
            </span>
            <span className={detail.sensitive_consent ? 'badge ok' : 'badge danger'}>
              민감동의 {detail.sensitive_consent ? 'O' : 'X'}
            </span>
          </div>
        )}
        <div className="actions">
          <button disabled={busy || !memberRef} onClick={() => run('recommend')}>
            오늘의 추천 받기
          </button>
          <button disabled={busy || !result?.items?.length} className="ghost" onClick={() => run('refresh')}>
            전부 새로고침 (L-2)
          </button>
          <button disabled={!memberRef} className="ghost" onClick={loadInsight}>
            취향 인사이트
          </button>
        </div>
      </section>

      {error && <div className="alert">{error}</div>}

      {result && (
        <section>
          <div className="resultbar">
            <span>추천 ID {result.recommendation_id || '—'}</span>
            <span>{result.latency_ms}ms / 예산 3000ms</span>
            {result.fallback_reason && <span className="warn">폴백 {result.fallback_reason}</span>}
            {result.output_violations?.length > 0 && (
              <span className="danger">출력검사 위반 {result.output_violations.join(', ')}</span>
            )}
          </div>

          {result.coldstart_notice && <p className="notice">{result.coldstart_notice}</p>}
          {result.learning_notice && <p className="notice">{result.learning_notice}</p>}
          {!result.items?.length && (
            <p className="notice">{result.message || '표시할 추천이 없습니다'}</p>
          )}

          <div className="cards">
            {(result.items || []).map((item, i) => (
              <RecommendCard
                key={item.restaurant_id}
                item={item}
                rank={i}
                busy={busy}
                onAccept={onAccept}
                onReject={onReject}
              />
            ))}
          </div>
        </section>
      )}

      {insight && (
        <section className="panel">
          <h2>취향 인사이트</h2>
          {!insight.available ? (
            <p className="notice">
              {insight.message} (기록 {insight.recorded}건)
              <span className="src">⑤ 10절 — 추측한 인사이트를 만들지 않음</span>
            </p>
          ) : (
            <ul className="insight">
              <li>조회 범위 {insight.window_days}일 ({insight.plan_type})</li>
              <li>총 기록 {insight.recorded}끼</li>
              <li>
                만족률{' '}
                {insight.satisfy_rate === null ? '—' : `${Math.round(insight.satisfy_rate * 100)}%`}
                <span className="src">5점 척도가 아닌 만족률 — ① 10절 발견 2번</span>
              </li>
              <li>
                자주 먹은 종류:{' '}
                {insight.top_categories.map((c) => `${c.category_code}(${c.count})`).join(', ')}
              </li>
            </ul>
          )}
        </section>
      )}

      <section className="panel">
        <h2>실행 기록</h2>
        <pre className="log">{log.join('\n') || '— 아직 없음 —'}</pre>
      </section>
    </div>
  )
}
