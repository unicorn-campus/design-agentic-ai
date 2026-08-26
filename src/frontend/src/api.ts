export type ApiRecord = Record<string, unknown>

export interface InquiryFormValue {
  requestId: string
  authSessionRef: string
  inquiryText: string
  channel: string
}

function apiUrl(path: string): string {
  const base = import.meta.env.VITE_HELP_DESK_API_BASE_URL ?? ''
  return `${base}${path}`
}

export async function submitInquiry(value: InquiryFormValue): Promise<ApiRecord> {
  const response = await fetch(apiUrl('/v1/inquiries'), {
    method: 'POST',
    headers: {
      Accept: 'text/event-stream',
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      request_id: value.requestId,
      auth_session_ref: value.authSessionRef,
      inquiry_text: value.inquiryText,
      channel: value.channel,
    }),
  })
  if (!response.ok) {
    const error = await response.json().catch(() => ({})) as ApiRecord
    throw new Error(typeof error.message === 'string' ? error.message : '요청 처리에 실패함')
  }
  if (!response.body) {
    throw new Error('응답 스트림을 열 수 없음')
  }
  const text = await readStream(response.body)
  return parseFinalEvent(text)
}

async function readStream(stream: ReadableStream<Uint8Array>): Promise<string> {
  const reader = stream.getReader()
  const decoder = new TextDecoder()
  let result = ''
  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    result += decoder.decode(value, { stream: true })
  }
  return result + decoder.decode()
}

export function parseFinalEvent(value: string): ApiRecord {
  const block = value.split('\n\n').find((item) => (
    item.startsWith('event: final') || item.startsWith('event: truncated')
  ))
  const dataLine = block?.split('\n').find((line) => line.startsWith('data: '))
  if (!dataLine) {
    throw new Error('최종 응답을 확인할 수 없음')
  }
  return JSON.parse(dataLine.slice('data: '.length)) as ApiRecord
}
