import type { AuthGateway, UserScope } from '../contracts/auth'

interface TokenResponse { access_token: string }

export class HttpAuthGateway implements AuthGateway {
  async login(email: string, password: string): Promise<UserScope> {
    const body = new URLSearchParams({ username: email, password })
    const token = await this.request<TokenResponse>('/auth/login', { method: 'POST', body })
    sessionStorage.setItem('moveinsync_access_token', token.access_token)
    return this.request<UserScope>('/auth/me', { headers: { Authorization: `Bearer ${token.access_token}` } })
  }

  private async request<T>(path: string, options: RequestInit): Promise<T> {
    const response = await fetch(path, options)
    const payload = await response.json()
    if (!response.ok) throw new Error(payload.detail ?? 'Something went wrong.')
    return payload as T
  }
}
