import type { ReactNode } from 'react'

interface ButtonProps {
  children: ReactNode
  onClick?: () => void
  outline?: boolean
}

export function Button({ children, onClick, outline = false }: ButtonProps) {
  return <button onClick={onClick} className={`rounded-lg px-5 py-3 text-sm font-bold transition hover:-translate-y-0.5 hover:shadow-material ${outline ? 'border border-brand-blue/35 bg-white text-brand-blue' : 'bg-gradient-to-r from-brand-blue to-brand-green text-white'}`}>{children}</button>
}
