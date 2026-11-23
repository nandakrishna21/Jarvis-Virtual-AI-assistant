import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'
import { useEffect, useState } from 'react'
import { api, type SystemStatus, type Proposal } from '../services/api'
import { useAppDispatch, useAppSelector } from '../store/hooks'
import { LayoutDashboard, Bot, Search, Briefcase, FileUser, FolderKanban, CalendarClock, Workflow, BarChart3, Settings, Bell, Mic, Cpu, HardDrive, ShieldCheck, Menu, X, FileText, Mail, Wand2, Radio, Download, Smartphone, Moon, Sun } from 'lucide-react'

let installPrompt: any = null

const nav = [
  { to: '/', label: 'Command Center', short: 'Home', icon: LayoutDashboard, end: true },
  { to: '/assistant', label: 'AI Assistant', short: 'Ask', icon: Bot },
  { to: '/voice', label: 'Voice Agent', short: 'Voice', icon: Radio },
  { to: '/jobs', label: 'Job Discovery', short: 'Discover', icon: Search },
  { to: '/matched', label: 'Matched Jobs', short: 'Matches', icon: Briefcase },
  { to: '/resume', label: 'Resume Intelligence', short: 'Resume', icon: FileUser },
  { to: '/resume-generator', label: 'Resume Generator', short: 'Generate', icon: Wand2 },
  { to: '/emails', label: 'Email Access', short: 'Mail', icon: Mail },
  { to: '/documents', label: 'Document Studio', short: 'Docs', icon: FileText },
  { to: '/applications', label: 'Application Manager', short: 'Apps', icon: FolderKanban },
  { to: '/interviews', label: 'Interview Tracker', short: 'Interviews', icon: CalendarClock },
  { to: '/automation', label: 'Automation Center', short: 'Automation', icon: Workflow },
  { to: '/analytics', label: 'Analytics', short: 'Stats', icon: BarChart3 },
  { to: '/settings', label: 'Settings', short: 'Settings', icon: Settings },
]

const bottomNav = nav.filter(item => ['/', '/assistant', '/voice', '/matched', '/resume-generator'].includes(item.to))

export default function Layout() {
  const dispatch = useAppDispatch()
  const status = useAppSelector((s) => s.app.status) as SystemStatus | null
  const pending = useAppSelector((s) => s.app.pending)
  const installAvailable = useAppSelector((s) => s.ui.installAvailable)
  const installed = useAppSelector((s) => s.ui.installed)
  const open = useAppSelector((s) => s.ui.sidebarOpen)
  const setOpen = (value: boolean) => dispatch({ type: 'ui/sidebar', payload: value })
  const [q, setQ] = useState('')
  const [resting, setResting] = useState(false)
  const navigate = useNavigate()
  const location = useLocation()

  useEffect(() => {
    let alive = true
    let timer: any = null
    const load = async () => {
      try {
        const s = await api.get<SystemStatus>('/system/status')
        if (alive) dispatch({ type: 'app/status', payload: s })
      } catch { }
      try {
        const a = await api.get<{ pending?: number; actions?: Proposal[] }>('/actions?status=pending')
        if (alive) dispatch({ type: 'app/pending', payload: a?.pending ?? (a?.actions?.length ?? 0) })
      } catch { }
      try {
        const p = await api.get<any>('/system/power')
        if (alive) setResting(!!p?.resting)
      } catch { }
    }
    const start = () => {
      if (timer) clearInterval(timer)
      timer = setInterval(() => { if (!document.hidden) load() }, 30000)
    }
    const onVisible = () => { if (!document.hidden) load() }
    load()
    start()
    document.addEventListener('visibilitychange', onVisible)
    return () => {
      alive = false
      if (timer) clearInterval(timer)
      document.removeEventListener('visibilitychange', onVisible)
    }
  }, [dispatch, location.pathname])

  useEffect(() => {
    const onInstallPrompt = (event: any) => {
      event.preventDefault()
      installPrompt = event
      dispatch({ type: 'ui/installAvailable', payload: true })
    }
    const onInstalled = () => { installPrompt = null; dispatch({ type: 'ui/installed', payload: true }) }
    window.addEventListener('beforeinstallprompt', onInstallPrompt)
    window.addEventListener('appinstalled', onInstalled)
    if (window.matchMedia('(display-mode: standalone)').matches) {
      dispatch({ type: 'ui/installed', payload: true })
    }
    return () => {
      window.removeEventListener('beforeinstallprompt', onInstallPrompt)
      window.removeEventListener('appinstalled', onInstalled)
    }
  }, [dispatch])

  const ollamaOk = status?.ai_ok ?? !!status?.ollama?.ok

  async function installApp() {
    if (installPrompt) {
      installPrompt.prompt()
      const choice = await installPrompt.userChoice
      if (choice?.outcome === 'accepted') dispatch({ type: 'ui/installed', payload: true })
      installPrompt = null
      dispatch({ type: 'ui/installAvailable', payload: false })
      return
    }
    const ios = /iphone|ipad|ipod/i.test(navigator.userAgent)
    dispatch({
      type: 'ui/toast',
      payload: {
        id: Date.now(),
        kind: 'info',
        text: ios
          ? 'On iPhone: tap the Share button, then "Add to Home Screen".'
          : 'Open your browser menu and choose "Install app" / "Add to Home screen".',
      },
    })
  }

  async function toggleRest() {
    try {
      const r = await api.post<any>(resting ? '/system/power/wake' : '/system/power/rest')
      setResting(!!r?.resting)
    } catch { }
  }

  function onSearch(e: React.FormEvent) {
    e.preventDefault()
    if (!q.trim()) return
    navigate('/assistant', { state: { prefill: q.trim() } })
    setQ('')
  }

  return (
    <div className="min-h-screen text-[var(--text)] pb-16 lg:pb-0">
      <div className="flex min-h-screen">
        <aside className={`fixed lg:static inset-y-0 left-0 z-40 w-72 transform transition-transform duration-200 ${open ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}`}>
          <div className="h-full glass-strong border-r border-[var(--border-soft)] flex flex-col">
            <div className="px-5 py-4 border-b border-[var(--border-soft)] flex items-center justify-between">
              <div>
                <div className="text-xl font-semibold tracking-[0.18em] glow-text text-[var(--cyan)]">JARVIS</div>
                <div className="text-[11px] text-[var(--muted)] mt-0.5 flex items-center gap-2">
                  <span className={`inline-block w-2 h-2 rounded-full ${ollamaOk ? 'bg-emerald-400 shadow-[0_0_8px_#22c55e]' : 'bg-amber-400 shadow-[0_0_8px_#f59e0b]'}`} />
                  {ollamaOk ? 'Systems Online' : 'Limited Mode'}
                </div>
              </div>
              <button className="lg:hidden text-[var(--muted)]" onClick={() => setOpen(false)} aria-label="Close menu"><X size={18}/></button>
            </div>
            <nav className="flex-1 overflow-y-auto p-3 space-y-1">
              {nav.map((item) => {
                const Icon = item.icon
                return (
                  <NavLink key={item.to} to={item.to} end={item.end} onClick={() => setOpen(false)}
                    className={({ isActive }) => `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition border ${isActive ? 'bg-cyan-500/10 text-cyan-200 border-cyan-400/25 shadow-[0_0_18px_rgba(0,229,255,0.08)]' : 'text-slate-300/85 border-transparent hover:bg-white/5 hover:text-white'}`}>
                    <Icon size={16} className="opacity-90" />
                    <span>{item.label}</span>
                  </NavLink>
                )
              })}
            </nav>
            <div className="p-3 border-t border-[var(--border-soft)] text-[11px] text-[var(--muted)] space-y-1">
              <div className="flex items-center justify-between"><span>AI</span><span className={ollamaOk ? 'text-emerald-300' : 'text-amber-300'}>{status?.model || 'local'}</span></div>
              <div className="flex items-center justify-between"><span>Approvals</span><span className={pending ? 'text-amber-300' : 'text-slate-400'}>{pending} pending</span></div>
            </div>
          </div>
        </aside>

        {open && <div className="lg:hidden fixed inset-0 z-30 bg-black/60" onClick={() => setOpen(false)} />}

        <div className="flex-1 min-w-0 flex flex-col">
          <header className="sticky top-0 z-20 glass border-b border-[var(--border-soft)]" style={{ paddingTop: 'env(safe-area-inset-top)' }}>
            <div className="px-3 sm:px-4 lg:px-6 py-3 flex items-center gap-2 sm:gap-3">
              <button className="lg:hidden text-[var(--muted)] p-1" onClick={() => setOpen(true)} aria-label="Open menu"><Menu size={20}/></button>
              <form onSubmit={onSearch} className="flex-1 max-w-xl">
                <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search or command JARVIS..." className="w-full px-3 py-2 rounded-lg text-sm bg-black/20" />
              </form>
              <div className="hidden md:flex items-center gap-3 text-xs text-[var(--muted)]">
                <div className="flex items-center gap-1.5"><Cpu size={14}/><span className={status && status.cpu_percent>85?'text-amber-300':''}>{status ? `${Math.round(status.cpu_percent)}%` : '--'}</span></div>
                <div className="flex items-center gap-1.5"><HardDrive size={14}/><span className={status && status.ram_percent>85?'text-amber-300':''}>{status ? `${Math.round(status.ram_percent)}%` : '--'}</span></div>
                <div className={`flex items-center gap-1.5 ${ollamaOk?'text-emerald-300':'text-amber-300'}`}><Bot size={14}/><span>{ollamaOk ? 'AI Ready' : 'AI Offline'}</span></div>
              </div>
              {installAvailable && !installed && (
                <button onClick={installApp} className="hidden sm:inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border border-cyan-400/30 bg-cyan-500/10 text-cyan-200 text-xs">
                  <Download size={14}/><span>Install</span>
                </button>
              )}
              <button onClick={toggleRest} className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border text-xs ${resting ? 'bg-indigo-500/20 border-indigo-400/40 text-indigo-200' : 'bg-emerald-500/10 border-emerald-400/30 text-emerald-200'}`} title={resting ? 'Wake JARVIS' : 'Rest mode - pause automations'}>
                {resting ? <Moon size={14}/> : <Sun size={14}/>}<span className="hidden sm:inline">{resting ? 'Resting' : 'Active'}</span>
              </button>
              <button onClick={() => navigate('/applications')} className="relative p-2 rounded-lg hover:bg-white/5 text-[var(--muted)]" title="Pending approvals">
                <Bell size={16}/>
                {pending > 0 && <span className="absolute -top-0.5 -right-0.5 min-w-[16px] h-4 px-1 rounded-full bg-amber-400 text-black text-[10px] flex items-center justify-center font-semibold">{pending}</span>}
              </button>
              <button onClick={() => navigate('/voice')} className="p-2 rounded-lg hover:bg-white/5 text-cyan-300" title="Voice agent"><Mic size={16}/></button>
              <button onClick={() => navigate('/settings')} className="hidden sm:flex items-center gap-2 px-2 py-1.5 rounded-lg hover:bg-white/5 text-xs text-[var(--muted)]"><ShieldCheck size={14}/><span>Profile</span></button>
            </div>
          </header>
          {status?.demo && (
            <div className="border-b border-amber-400/20 bg-amber-500/10 px-3 py-1.5 text-[11px] text-amber-200">
              Public demo: chat, voice and read-only pages are enabled. Email, files, uploads and automations are disabled.
            </div>
          )}
          <main className="flex-1 p-3 sm:p-4 lg:p-6"><Outlet context={{ status, pending }} /></main>
        </div>
      </div>

      <nav className="lg:hidden fixed bottom-0 inset-x-0 z-30 glass-strong border-t border-[var(--border-soft)]" style={{ paddingBottom: 'env(safe-area-inset-bottom)' }}>
        <div className="grid grid-cols-6">
          {bottomNav.map((item) => {
            const Icon = item.icon
            return (
              <NavLink key={item.to} to={item.to} end={item.end}
                className={({ isActive }) => `flex flex-col items-center justify-center gap-0.5 py-2 text-[10px] ${isActive ? 'text-cyan-300' : 'text-[var(--muted)]'}`}>
                <Icon size={19}/>
                <span>{item.short}</span>
              </NavLink>
            )
          })}
          <button onClick={() => setOpen(true)} className="flex flex-col items-center justify-center gap-0.5 py-2 text-[10px] text-[var(--muted)]" aria-label="Open all pages">
            <Menu size={19}/>
            <span>More</span>
          </button>
        </div>
      </nav>

      {!installed && (
        <button onClick={installApp}
          className="sm:hidden fixed right-3 z-30 flex items-center gap-1.5 rounded-full border border-cyan-400/40 bg-[#0b1b2e]/90 px-3 py-2 text-[11px] text-cyan-200 shadow-lg"
          style={{ bottom: 'calc(4.5rem + env(safe-area-inset-bottom))' }}>
          <Smartphone size={14}/><span>Install app</span>
        </button>
      )}
    </div>
  )
}
