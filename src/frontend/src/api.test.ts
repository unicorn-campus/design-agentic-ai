import { describe, expect, it } from 'vitest'
import { parseFinalEvent } from './api'

describe('parseFinalEvent', () => {
  it('reads the guarded final response', () => {
    const result = parseFinalEvent(
      'event: final\ndata: {"result_type":"answer","request_status":"completed"}\n\n',
    )
    expect(result).toEqual({ result_type: 'answer', request_status: 'completed' })
  })

  it('accepts the truncated marker contract', () => {
    const result = parseFinalEvent(
      'event: truncated\ndata: {"result_type":"safe_stop","request_status":"failed"}\n\n',
    )
    expect(result.request_status).toBe('failed')
  })

  it('rejects a stream without a final event', () => {
    expect(() => parseFinalEvent('event: progress\ndata: {}\n\n')).toThrow()
  })
})
