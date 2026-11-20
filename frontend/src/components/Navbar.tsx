import { Menu, Moon, Sun } from 'lucide-react'
import { Brand } from './Brand'
import { Button } from './Button'

interface NavbarProps {
  dark: boolean
  menuOpen: boolean
  onToggleTheme: () => void
  onToggleMenu: () => void
  onSignIn: () => void
}

export function Navbar({ dark, menuOpen, onToggleTheme, onToggleMenu, onSignIn }: NavbarProps) {
  return <header className="sticky top-0 z-40 border-b border-slate-200/70 bg-white/90 backdrop-blur dark:border-slate-700 dark:bg-[#202124]/90">
    <nav className="mx-auto flex h-19 w-[min(1280px,calc(100%-2rem))] items-center justify-between">
      <Brand/>
      <div className="hidden gap-8 text-sm font-semibold md:flex"><a href="#platform">Platform</a><a href="#stories">Stories</a><a href="#pricing">Pricing</a></div>
      <div className="flex items-center gap-2">
        <button onClick={onToggleTheme} aria-label="Switch theme" className="rounded-full p-2 transition hover:bg-slate-100 dark:hover:bg-slate-800">{dark ? <Sun size={19}/> : <Moon size={19}/>}</button>
        <button onClick={onSignIn} className="hidden px-3 py-2 text-sm font-bold md:block">Sign in</button>
        <Button onClick={onSignIn}>Try the demo</Button>
        <button onClick={onToggleMenu} className="p-2 md:hidden"><Menu size={22}/></button>
      </div>
    </nav>
    {menuOpen && <div className="border-t border-slate-200 bg-white p-4 md:hidden"><div className="mx-auto flex w-[min(1280px,calc(100%-2rem))] flex-col gap-3 font-semibold"><a href="#platform">Platform</a><a href="#stories">Stories</a><a href="#pricing">Pricing</a></div></div>}
  </header>
}
