import { Github } from 'lucide-react'
import { footerGroups } from '../data/content'
import { Brand } from './Brand'

export function Footer() {
  return <footer className="border-t border-slate-200 py-14"><div className="mx-auto grid w-[min(1280px,calc(100%-2rem))] gap-8 sm:grid-cols-2 lg:grid-cols-4"><div><Brand/><p className="mt-4 max-w-xs text-sm text-slate-500">AI-first operational intelligence for employee transport teams.</p><a className="mt-4 inline-flex text-brand-ink" href="https://github.com/StormShadow26/moveinsync-ai" aria-label="GitHub"><Github size={22}/></a></div>{footerGroups.map(([heading, ...links]) => <div key={heading} className="grid content-start gap-2 text-sm"><b>{heading}</b>{links.map((link) => <a key={link} href="#top" className="text-slate-500 hover:text-brand-blue">{link}</a>)}</div>)}</div><div className="mx-auto mt-12 flex w-[min(1280px,calc(100%-2rem))] flex-col justify-between gap-3 border-t border-slate-200 pt-5 text-xs text-slate-500 sm:flex-row"><span>© 2026 MoveInSync AI. All rights reserved.</span><div className="flex gap-4"><a href="#top">Privacy policy</a><a href="#top">Terms of use</a><a href="#top">Accessibility</a></div></div></footer>
}
