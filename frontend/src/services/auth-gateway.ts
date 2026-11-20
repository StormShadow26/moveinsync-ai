import type { AuthGateway, UserScope } from '../contracts/auth'

interface TokenResponse { access_token: string }

export class HttpAuthGateway implements AuthGateway {
  async requestOtp(email: string): Promise<void> {
    await this.request('/auth/otp/request', { method: 'POST', body: JSON.stringify({ email }) })
  }

  async verifyOtp(email: string, code: string): Promise<UserScope> {
    const token = await this.request<TokenResponse>('/auth/otp/verify', { method: 'POST', body: JSON.stringify({ email, code }) })
    sessionStorage.setItem('moveinsync_access_token', token.access_token)
    const user = await this.request<UserScope>('/auth/me', { headers: { Authorization: `Bearer ${token.access_token}` } })
    sessionStorage.setItem('moveinsync_user', JSON.stringify(user))
    return user
  }

  private async request<T = void>(path: string, options: RequestInit): Promise<T> {
    const response = await fetch(path, { ...options, headers: { 'Content-Type': 'application/json', ...options.headers } })
    const payload = await response.json()
    if (!response.ok) throw new Error(payload.detail ?? 'Something went wrong.')
    return payload as T
  }
}
