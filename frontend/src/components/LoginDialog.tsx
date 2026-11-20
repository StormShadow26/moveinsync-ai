import { X } from 'lucide-react'
import { FormEvent, useState } from 'react'
import type { AuthGateway, UserScope } from '../contracts/auth'

interface LoginDialogProps {
  gateway: AuthGateway
  onClose: () => void
}

export function LoginDialog({ gateway, onClose }: LoginDialogProps) {
  const [scope, setScope] = useState<UserScope>()
  const [email, setEmail] = useState('')
  const [otpSent, setOtpSent] = useState(false)
  const [error, setError] = useState('')

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setError('')
    setScope(undefined)
    const form = new FormData(event.currentTarget)
    const suppliedEmail = String(form.get('email'))
    try {
      if (!otpSent) {
        await gateway.requestOtp(suppliedEmail)
        setEmail(suppliedEmail)
        setOtpSent(true)
        return
      }
      setScope(await gateway.verifyOtp(email, String(form.get('code'))))
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Sign in failed.')
    }
  }

  return <div className="fixed inset-0 z-50 grid place-items-center bg-brand-ink/45 p-4 backdrop-blur-sm">
    <div className="relative w-full max-w-md rounded-2xl bg-white p-8 shadow-2xl">
      <button onClick={onClose} className="absolute right-4 top-4 rounded-full p-2 text-slate-600 transition hover:bg-slate-100"><X size={18}/></button>
      <p className="mb-3 text-xs font-extrabold uppercase tracking-[.12em] text-brand-blue">Workspace access</p>
      <h2 className="text-3xl font-bold tracking-tight text-brand-ink">Sign in to your workspace</h2>
      <p className="mt-2 text-slate-500">Enter your provisioned email, then use the one-time code sent to it.</p>
      <form onSubmit={submit} className="mt-6 grid gap-4">
        <label className="grid gap-1 text-sm font-semibold text-brand-ink">Email
          <input required disabled={otpSent} defaultValue={email} name="email" type="email" placeholder="name@company.com" className="rounded-lg border border-slate-300 px-3 py-3 outline-none transition focus:border-brand-blue focus:ring-4 focus:ring-brand-blue/15 disabled:bg-slate-100"/>
        </label>
        {otpSent && <label className="grid gap-1 text-sm font-semibold text-brand-ink">Verification code
          <input required name="code" inputMode="numeric" pattern="[0-9]{6}" maxLength={6} placeholder="6-digit code" className="rounded-lg border border-slate-300 px-3 py-3 outline-none transition focus:border-brand-blue focus:ring-4 focus:ring-brand-blue/15"/>
        </label>}
        <button className="rounded-lg bg-gradient-to-r from-brand-blue to-brand-green px-4 py-3 font-bold text-white transition hover:-translate-y-0.5 hover:shadow-material">
          {otpSent ? 'Verify and sign in' : 'Send verification code'}
        </button>
        {error && <p className="text-sm text-brand-red">{error}</p>}
      </form>
      {scope && <div className="mt-5 rounded-lg bg-green-50 p-4 text-sm text-green-900">
        <b className="block capitalize">{scope.user_type.replace(/_/g, ' ')}</b>
        <span>{scope.access_scope === 'all_companies' ? 'Access: all companies' : `Access: company ID ${scope.company_id}`}</span>
      </div>}
    </div>
  </div>
}
