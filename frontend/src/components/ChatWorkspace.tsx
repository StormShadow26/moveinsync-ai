import { LogOut, MessageSquarePlus, Send } from 'lucide-react'
import { FormEvent, useEffect, useState } from 'react'
import type { UserScope } from '../contracts/auth'
import type { ChatGateway, ChatMessage, ChatThread, Company, ThreadScope } from '../contracts/chat'

interface ChatWorkspaceProps { gateway: ChatGateway; user: UserScope; onSignOut: () => void }

function friendlyQueryNotice(reason: unknown) {
  const message = reason instanceof Error ? reason.message : ''
  return /^(I can help|What should|The query|The data query|Please enter)/.test(message)
    ? message
    : "I couldn't answer that just now. Please try a transport-data question again."
}

export function ChatWorkspace({ gateway, user, onSignOut }: ChatWorkspaceProps) {
  const [companies, setCompanies] = useState<Company[]>([])
  const [threads, setThreads] = useState<ChatThread[]>([])
  const [selected, setSelected] = useState<ChatThread>()
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [scope, setScope] = useState<ThreadScope>(user.user_type === 'client_transport_admin' ? 'company' : 'all_companies')
  const [companyId, setCompanyId] = useState<number | null>(user.company_id)
  const [draft, setDraft] = useState('')
  const [notice, setNotice] = useState('')

  const loadThreads = async () => {
    try { setThreads(await gateway.threads()) } catch { setNotice("I couldn't load your conversations. Please refresh and try again.") }
  }

  useEffect(() => {
    void loadThreads()
    if (user.user_type === 'internal_ops_manager') gateway.companies().then(setCompanies).catch(() => setNotice("I couldn't load companies. Please refresh and try again."))
  }, [])
  useEffect(() => {
    if (selected) gateway.messages(selected.id).then(setMessages).catch(() => setNotice("I couldn't load this conversation. Please try again."))
    else setMessages([])
  }, [selected])

  const newChat = async () => {
    try {
      const thread = await gateway.createThread(scope, scope === 'company' ? companyId : null)
      setThreads(current => [thread, ...current]); setSelected(thread); setNotice('')
    } catch { setNotice("I couldn't create a conversation. Please check the selected data scope and try again.") }
  }

  const send = async (event: FormEvent) => {
    event.preventDefault()
    if (!selected || !draft.trim()) return
    const question = draft.trim()
    setDraft('')
    try {
      const answer = await gateway.ask(selected.id, question)
      const history = await gateway.messages(selected.id)
      setMessages(history.map(message => message.id === answer.id ? answer : message)); setNotice('')
    }
    catch (reason) { setNotice(friendlyQueryNotice(reason)) }
  }

  const scopeName = selected?.scope === 'all_companies'
    ? 'All assigned companies'
    : companies.find(company => company.id === selected?.company_id)?.name ?? `Company ${selected?.company_id ?? companyId}`

  return <div className="min-h-screen bg-slate-50 text-brand-ink">
    <header className="flex h-16 items-center justify-between border-b bg-white px-5">
      <b className="text-lg">moveinsync<span className="text-brand-blue">.ai</span></b>
      <div className="flex items-center gap-4 text-sm"><span>{user.email}</span><button onClick={onSignOut} className="flex items-center gap-1 font-bold text-slate-500 hover:text-brand-blue"><LogOut size={16}/>Sign out</button></div>
    </header>
    <div className="mx-auto grid min-h-[calc(100vh-4rem)] max-w-7xl lg:grid-cols-[300px_1fr]">
      <aside className="border-r bg-white p-4">
        <button onClick={() => void newChat()} className="flex w-full items-center justify-center gap-2 rounded-lg bg-brand-blue px-4 py-3 text-sm font-bold text-white"><MessageSquarePlus size={17}/>New chat</button>
        <div className="mt-4 grid gap-2">
          {user.user_type === 'internal_ops_manager' && <><label className="text-xs font-bold text-slate-500">Data scope</label><select value={scope} onChange={event => setScope(event.target.value as ThreadScope)} className="rounded-lg border p-2 text-sm"><option value="all_companies">All assigned companies</option><option value="company">One company</option></select>{scope === 'company' && <select value={companyId ?? ''} onChange={event => setCompanyId(Number(event.target.value))} className="rounded-lg border p-2 text-sm"><option value="">Select a company</option>{companies.map(company => <option key={company.id} value={company.id}>{company.name}</option>)}</select>}</>}
          {user.user_type === 'client_transport_admin' && <p className="rounded-lg bg-blue-50 p-3 text-xs text-brand-blue">Scope: your company only</p>}
        </div>
        <div className="mt-6 grid gap-1">{threads.map(thread => <button key={thread.id} onClick={() => { setSelected(thread); setNotice('') }} className={`rounded-lg px-3 py-3 text-left text-sm ${selected?.id === thread.id ? 'bg-blue-50 text-brand-blue' : 'hover:bg-slate-50'}`}><b className="block truncate">{thread.title}</b><span className="text-xs text-slate-500">{thread.scope === 'all_companies' ? 'All assigned companies' : `Company ${thread.company_id}`}</span></button>)}</div>
      </aside>
      <main className="flex min-h-0 flex-col">
        <div className="border-b bg-white px-6 py-4"><p className="text-xs font-bold uppercase tracking-widest text-brand-blue">{selected ? scopeName : 'New conversation'}</p><h1 className="text-xl font-bold">{selected?.title ?? 'Start a transport data conversation'}</h1></div>
        <div className="flex-1 space-y-4 overflow-y-auto p-6">
          {messages.length ? messages.map(message => <div key={message.id} className={`max-w-2xl rounded-2xl p-4 ${message.role === 'user' ? 'ml-auto bg-brand-blue text-white' : 'bg-white shadow-material'}`}><p>{message.content}</p>{message.generated_sql && <details className="mt-3 text-sm"><summary>View SQL</summary><pre className="mt-2 overflow-auto whitespace-pre-wrap">{message.generated_sql}</pre></details>}{message.columns && <div className="mt-3 overflow-auto"><table className="text-left text-sm"><thead><tr>{message.columns.map(column => <th className="border p-2" key={column}>{column}</th>)}</tr></thead><tbody>{message.rows?.map((row, index) => <tr key={index}>{message.columns?.map(column => <td className="border p-2" key={column}>{String(row[column] ?? '—')}</td>)}</tr>)}</tbody></table></div>}</div>) : <div className="mx-auto max-w-lg pt-20 text-center text-slate-500"><h2 className="text-2xl font-bold text-brand-ink">Ask about transport operations</h2><p className="mt-3">Create a chat, then ask about no-shows, occupancy, routes, or costs.</p></div>}
          {notice && <div className="max-w-2xl rounded-2xl border border-blue-100 bg-blue-50 p-4 text-sm text-slate-600"><p className="font-bold text-brand-blue">How can I help?</p><p className="mt-1">{notice}</p></div>}
        </div>
        <form onSubmit={send} className="border-t bg-white p-4"><div className="mx-auto flex max-w-3xl gap-2"><input value={draft} onChange={event => setDraft(event.target.value)} disabled={!selected} placeholder={selected ? 'Ask about no-shows, occupancy, routes, or costs…' : 'Create a new chat first'} className="min-w-0 flex-1 rounded-xl border px-4 py-3 outline-none focus:border-brand-blue"/><button disabled={!selected} className="rounded-xl bg-brand-blue px-4 text-white disabled:bg-slate-300"><Send size={18}/></button></div></form>
      </main>
    </div>
  </div>
}
