import { useState } from 'react'
import { Footer } from './components/Footer'
import { Hero } from './components/Hero'
import { FinalCta, PlatformSection, PricingSection, ProcessSection, StoriesSection } from './components/LandingSections'
import { LoginDialog } from './components/LoginDialog'
import { Navbar } from './components/Navbar'
import { HttpAuthGateway } from './services/auth-gateway'

const gateway = new HttpAuthGateway()

export default function App() {
  const [loginOpen, setLoginOpen] = useState(false)
  const [dark, setDark] = useState(false)
  const [menuOpen, setMenuOpen] = useState(false)
  const openLogin = () => setLoginOpen(true)

  return <div id="top" className={dark ? 'min-h-screen bg-[#202124] text-slate-100' : 'min-h-screen bg-white text-brand-ink'}>
    <Navbar dark={dark} menuOpen={menuOpen} onToggleTheme={() => setDark(!dark)} onToggleMenu={() => setMenuOpen(!menuOpen)} onSignIn={openLogin}/>
    <main><Hero onSignIn={openLogin}/><PlatformSection/><ProcessSection/><StoriesSection/><PricingSection onSignIn={openLogin}/><FinalCta onSignIn={openLogin}/></main>
    <Footer/>
    {loginOpen && <LoginDialog gateway={gateway} onClose={() => setLoginOpen(false)}/>}
  </div>
}
