import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'
import { useEffect, useState } from 'react'
import { api, type SystemStatus, type Proposal } from '../services/api'
import { LayoutDashboard, Bot, Search, Briefcase, FileUser, FolderKanban, CalendarClock, Workflow, BarChart3, Settings, Bell, Mic, Cpu, HardDrive, ShieldCheck, Menu, X, FileText, Mail, Wand2, Radio } from 'lucide-react'

const nav = [
  { to: '/', label: 'Command Center', icon: LayoutDashboard, end: true },
  { to: '/assistant', label: 'AI Assistant', icon: Bot },
  { to: '/voice', label: 'Voice Agent', icon: Radio },
  { to: '/jobs', label: 'Job Discovery', icon: Search },
  { to: '/matched', label: 'Matched Jobs', icon: Briefcase },
  { to: '/resume', label: 'Resume Intelligence', icon: FileUser },
  { to: '/resume-generator', label: 'Resume Generator', icon: Wand2 },
  { to: '/emails', label: 'Email Access', icon: Mail },
  { to: '/documents', label: 'Document Studio', icon: FileText },
  { to: '/applications', label: 'Application Manager', icon: FolderKanban },
  { to: '/interviews', label: 'Interview Tracker', icon: CalendarClock },
  { to: '/automation', label: 'Automation Center', icon: Workflow },
  { to: '/analytics', label: 'Analytics', icon: BarChart3 },
  { to: '/settings', label: 'Settings', icon: Settings },
]

export default function Layout() {
  const [status, setStatus] = useState<SystemStatus | null>(null)
  const [pending, setPending] = useState(0)
  const [open, setOpen] = useState(false)
  const [q, setQ] = useState('')
  const navigate = useNavigate()
  const location = useLocation()

  useEffect(() => {
    let alive = true
    const load = async () => {
      try { const s = await api.get<SystemStatus>('/system/status'); if (alive) setStatus(s) } catch {}
      try {
        const a = await api.get<{ pending?: number; actions?: Proposal[] }>('/actions?status=pending')
        if (alive) setPending(a?.pending ?? (a?.actions?.length ?? 0))
      } catch {}
    }
    load()
    const t = setInterval(load, 12000)
    return () => { alive = false; clearInterval(t) }
  }, [location.pathname])

  const ollamaOk = !!status?.ollama?.ok

  function onSearch(e: React.FormEvent) {
    e.preventDefault()
    if (!q.trim()) return
    navigate('/assistant', { state: { prefill: q.trim() } })
    setQ('')
  }

  return (
    <div className="min-h-screen text-[var(--text)]">
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
              <button className="lg:hidden text-[var(--muted)]" onClick={() => setOpen(false)}><X size={18}/></button>
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

        <div className="flex-1 min-w-0 flex flex-col">
          <header className="sticky top-0 z-30 glass border-b border-[var(--border-soft)]">
            <div className="px-4 lg:px-6 py-3 flex items-center gap-3">
              <button className="lg:hidden text-[var(--muted)]" onClick={() => setOpen(true)}><Menu size={18}/></button>
              <form onSubmit={onSearch} className="flex-1 max-w-xl">
                <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search or command JARVIS..." className="w-full px-3 py-2 rounded-lg text-sm bg-black/20" />
              </form>
              <div className="hidden md:flex items-center gap-3 text-xs text-[var(--muted)]">
                <div className="flex items-center gap-1.5"><Cpu size={14}/><span className={status && status.cpu_percent>85?'text-amber-300':''}>{status ? `${Math.round(status.cpu_percent)}%` : '--'}</span></div>
                <div className="flex items-center gap-1.5"><HardDrive size={14}/><span className={status && status.ram_percent>85?'text-amber-300':''}>{status ? `${Math.round(status.ram_percent)}%` : '--'}</span></div>
                <div className={`flex items-center gap-1.5 ${ollamaOk?'text-emerald-300':'text-amber-300'}`}><Bot size={14}/><span>{ollamaOk ? 'AI Ready' : 'AI Offline'}</span></div>
              </div>
              <button onClick={() => navigate('/applications')} className="relative p-2 rounded-lg hover:bg-white/5 text-[var(--muted)]" title="Pending approvals">
                <Bell size={16}/>
                {pending > 0 && <span className="absolute -top-0.5 -right-0.5 min-w-[16px] h-4 px-1 rounded-full bg-amber-400 text-black text-[10px] flex items-center justify-center font-semibold">{pending}</span>}
              </button>
              <button onClick={() => navigate('/assistant')} className="p-2 rounded-lg hover:bg-white/5 text-cyan-300" title="Voice assistant"><Mic size={16}/></button>
              <button onClick={() => navigate('/settings')} className="hidden sm:flex items-center gap-2 px-2 py-1.5 rounded-lg hover:bg-white/5 text-xs text-[var(--muted)]"><ShieldCheck size={14}/><span>Profile</span></button>
            </div>
          </header>
          <main className="flex-1 p-4 lg:p-6"><Outlet context={{ status, pending }} /></main>
        </div>
      </div>
    </div>
  )
}
