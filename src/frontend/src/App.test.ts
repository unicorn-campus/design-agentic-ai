import { render, screen } from '@testing-library/vue'
import { describe, expect, it } from 'vitest'
import App from './App.vue'

describe('App', () => {
  it('renders only the inquiry workflow screen', () => {
    render(App)
    expect(screen.getByRole('heading', { name: 'Help Desk Copilot' })).toBeTruthy()
    expect(screen.getByLabelText('문의 내용')).toBeTruthy()
    expect(screen.queryByText('관리자')).toBeNull()
    expect(screen.queryByText('통계')).toBeNull()
  })
})
