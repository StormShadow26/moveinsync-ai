import type { ReactNode } from 'react'

interface SectionHeadingProps {
  eyebrow: string
  title: string
  children?: ReactNode
  centered?: boolean
}

export function SectionHeading({ eyebrow, title, children, centered = false }: SectionHeadingProps) {
  return <div className={`mb-12 max-w-2xl ${centered ? 'mx-auto text-center' : ''}`}><p className={`mb-3 flex items-center gap-2 text-xs font-extrabold uppercase tracking-[.12em] text-brand-blue ${centered ? 'justify-center' : ''}`}><span className="h-0.5 w-5 bg-gradient-to-r from-brand-blue to-brand-green"/>{eyebrow}</p><h2 className="text-4xl font-bold leading-tight tracking-tight text-brand-ink sm:text-5xl">{title}</h2>{children && <div className="mt-4 text-lg text-slate-500">{children}</div>}</div>
}
