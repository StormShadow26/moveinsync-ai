import type { AskResponse, ChatGateway, ChatMessage, ChatThread, Company, ThreadScope } from '../contracts/chat'
import type { UserScope } from '../contracts/auth'
import { readResponse } from './http'

export class HttpChatGateway implements ChatGateway {
  currentUser(): UserScope | null {
    const value = sessionStorage.getItem('moveinsync_user')
    return value ? JSON.parse(value) as UserScope : null
  }

  companies(): Promise<Company[]> { return this.request('/query/companies') }
  threads(): Promise<ChatThread[]> { return this.request('/query/threads') }
  createThread(scope: ThreadScope, companyId: number | null, title = 'New conversation'): Promise<ChatThread> {
    return this.request('/query/threads', { method: 'POST', body: JSON.stringify({ scope, company_id: companyId, title }) })
  }
  messages(threadId: number): Promise<ChatMessage[]> { return this.request(`/query/threads/${threadId}/messages`) }
  ask(threadId: number, content: string): Promise<AskResponse> {
    return this.request(`/query/threads/${threadId}/ask`, { method: 'POST', body: JSON.stringify({ content }) })
  }

  private async request<T>(path: string, options: RequestInit = {}): Promise<T> {
    const token = sessionStorage.getItem('moveinsync_access_token')
    const response = await fetch(path, { ...options, headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json', ...options.headers } })
    return readResponse<T>(response)
  }
}
