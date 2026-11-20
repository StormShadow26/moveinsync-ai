import type { UserScope } from './auth'

export type ThreadScope = 'company' | 'all_companies'

export interface Company { id: number; name: string }
export interface ChatThread { id: number; company_id: number | null; scope: ThreadScope; title: string }
export interface ChatMessage { id: number; thread_id: number; role: 'user' | 'assistant' | 'system'; content: string }

export interface ChatGateway {
  companies(): Promise<Company[]>
  threads(): Promise<ChatThread[]>
  createThread(scope: ThreadScope, companyId: number | null, title?: string): Promise<ChatThread>
  messages(threadId: number): Promise<ChatMessage[]>
  addMessage(threadId: number, content: string): Promise<ChatMessage>
  currentUser(): UserScope | null
}
