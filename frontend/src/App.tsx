import { useState } from 'react'
import { Footer } from './components/Footer'
import { Hero } from './components/Hero'
import { FinalCta, PlatformSection, PricingSection, ProcessSection, StoriesSection } from './components/LandingSections'
import { LoginDialog } from './components/LoginDialog'
import { Navbar } from './components/Navbar'
import { ChatWorkspace } from './components/ChatWorkspace'
import type { UserScope } from './contracts/auth'
import { HttpAuthGateway } from './services/auth-gateway'
import { HttpChatGateway } from './services/chat-gateway'

const gateway = new HttpAuthGateway()
const chatGateway = new HttpChatGateway()

export default function App() {
  const [loginOpen, setLoginOpen] = useState(false)
  const [dark, setDark] = useState(false)
  const [menuOpen, setMenuOpen] = useState(false)
  const [user, setUser] = useState<UserScope | null>(() => chatGateway.currentUser())
  const openLogin = () => setLoginOpen(true)

  if (user) return <ChatWorkspace gateway={chatGateway} user={user} onSignOut={() => { sessionStorage.clear(); setUser(null) }}/>

  return <div id="top" className={dark ? 'min-h-screen bg-[#202124] text-slate-100' : 'min-h-screen bg-white text-brand-ink'}>
    <Navbar dark={dark} menuOpen={menuOpen} onToggleTheme={() => setDark(!dark)} onToggleMenu={() => setMenuOpen(!menuOpen)} onSignIn={openLogin}/>
    <main><Hero onSignIn={openLogin}/><PlatformSection/><ProcessSection/><StoriesSection/><PricingSection onSignIn={openLogin}/><FinalCta onSignIn={openLogin}/></main>
    <Footer/>
    {loginOpen && <LoginDialog gateway={gateway} onClose={() => setLoginOpen(false)} onAuthenticated={user => { setUser(user); setLoginOpen(false) }}/>}
  </div>
}
