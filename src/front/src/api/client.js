// 게이트웨이(I-1) 하나만 부름. I-2·I-3을 직접 부르지 않음(⑦ 3절).
const BASE = '/api'

async function call(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'content-type': 'application/json' },
    ...options,
  })
  const body = await res.json().catch(() => ({}))
  if (!res.ok) {
    const detail = body.detail || body
    throw Object.assign(new Error(detail.reason_code || `HTTP ${res.status}`), { detail })
  }
  return body
}

export const api = {
  members: () => call('/members'),
  member: (ref) => call(`/members/${ref}`),
  setConsent: (ref, patch) =>
    call(`/members/${ref}/consent`, { method: 'POST', body: JSON.stringify(patch) }),

  recommend: (payload) =>
    call('/recommendations', { method: 'POST', body: JSON.stringify(payload) }),
  reject: (payload) =>
    call('/recommendations/reject', { method: 'POST', body: JSON.stringify(payload) }),
  refresh: (payload) =>
    call('/recommendations/refresh', { method: 'POST', body: JSON.stringify(payload) }),

  recordMeal: (payload) => call('/meals', { method: 'POST', body: JSON.stringify(payload) }),
  feedback: (payload) => call('/feedback', { method: 'POST', body: JSON.stringify(payload) }),
  insights: (ref) => call(`/insights/${ref}`),
}
