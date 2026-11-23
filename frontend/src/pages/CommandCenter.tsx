import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api, type Greeting, type ChatResponse, type Proposal } from '../services/api'
import Orb, { type OrbState } from '../components/jarvis/Orb'
import ApprovalCard from '../components/jarvis/ApprovalCard'
import { Send, Mic, Activity, Sparkles, ShieldAlert, Bell, Briefcase, Mail, ListTodo, Cpu, RefreshCw, ChevronRight, CheckCircle2, AlertTriangle, Moon, Sun, ExternalLink, CloudSun } from 'lucide-react'

type Msg = { role: 'user' | 'assistant'; text: string; proposal?: Proposal; openUrl?: string; openLabel?: string; weather?: any }

type Briefing = {
  greeting: Greeting | null
  pending: Proposal[]
  notifications: any[]
  activity: any[]
  topMatches: any[]
  gmail: any
  tasks: any
  system: any
}

const empty: Briefing = { greeting: null, pending: [], notifications: [], activity: [], topMatches: [], gmail: null, tasks: null, system: null }

export default function CommandCenter() {
  const [b, setB] = useState<Briefing>(empty)
  const [state, setState] = useState<OrbState>('idle')
  const [input, setInput] = useState('')
  const [messages, setMessages] = useState<Msg[]>([])
  const [busy, setBusy] = useState(false)
  const [listening, setListening] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [resting, setResting] = useState(false)
  const [powerBusy, setPowerBusy] = useState(false)
  const recognitionRef = useRef<any>(null)
  const navigate = useNavigate()

  const refresh = useCallback(async () => {
    const [g, p, n, a, j, gm, t, s, pw] = await Promise.allSettled([
      api.get<Greeting>('/assistant/greeting'),
      api.get<any>('/actions?status=pending'),
      api.get<any>('/notifications?limit=8'),
      api.get<any>('/assistant/history?limit=10'),
      api.get<any>('/jobs/top-matches'),
      api.get<any>('/gmail/account'),
      api.get<any>('/productivity'),
      api.get<any>('/system/status'),
      api.get<any>('/system/power'),
    ])
    const val = <T,>(r: PromiseSettledResult<T>, fallback: T): T => r.status === 'fulfilled' ? r.value : fallback
    const greeting = val(g, null)
    const pendingRes = val(p, { actions: [] })
    const power = val(pw, null) as any
    if (power && typeof power.resting === 'boolean') setResting(!!power.resting)
    setB({
      greeting,
      pending: (pendingRes?.actions || []).filter((x: Proposal) => x.status === 'pending'),
      notifications: val(n, { notifications: [] })?.notifications || [],
      activity: val(a, { history: [] })?.history || [],
      topMatches: (val(j, []) as any[])?.slice?.(0, 5) || [],
      gmail: val(gm, null),
      tasks: val(t, null),
      system: val(s, null),
    })
    setMessages(prev => prev.length ? prev : [{ role: 'assistant', text: greeting?.message || 'Good day. I am JARVIS. Systems are initializing.' }])
    setLoading(false)
  }, [])

  useEffect(() => {
    let timer: any = null
    const tick = () => { if (!document.hidden) refresh() }
    refresh()
    timer = setInterval(tick, 30000)
    const onVisible = () => { if (!document.hidden) refresh() }
    document.addEventListener('visibilitychange', onVisible)
    return () => {
      if (timer) clearInterval(timer)
      document.removeEventListener('visibilitychange', onVisible)
    }
  }, [refresh])

  async function send(text?: string) {
    const msg = (text ?? input).trim()
    if (!msg || busy) return
    setInput(''); setError(null)
    setMessages((m) => [...m, { role: 'user', text: msg }])
    setBusy(true); setState('thinking')
    try {
      setState('executing')
      const res = await api.post<ChatResponse>('/assistant/chat', { message: msg })
      const reply = res?.response || res?.error || 'No response.'
      setMessages((m) => [...m, { role: 'assistant', text: reply, proposal: res?.proposal, openUrl: res?.open_url, openLabel: res?.open_label, weather: res?.weather }])
      setState(res?.ok === false ? 'error' : 'success')
      await refresh()
      setTimeout(() => setState('idle'), 1500)
    } catch (e: any) {
      const msg2 = e?.message || 'Request failed.'
      setError(msg2)
      setMessages((m) => [...m, { role: 'assistant', text: msg2 }])
      setState('error'); setTimeout(() => setState('idle'), 2000)
    } finally { setBusy(false) }
  }

  async function togglePower() {
    setPowerBusy(true)
    try {
      const r = await api.post<any>(resting ? '/system/power/wake' : '/system/power/rest')
      setResting(!!r?.resting)
    } catch (e: any) {
      setError(e?.message || 'Failed to toggle JARVIS power mode.')
    } finally { setPowerBusy(false) }
  }

  function toggleMic() {
    const SR: any = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition
    if (!SR) { setError('Voice input is not supported in this browser. Use Chrome/Edge or type.'); return }
    if (listening) { recognitionRef.current?.stop(); setListening(false); setState('idle'); return }
    const rec = new SR(); rec.lang = 'en-US'; rec.interimResults = false; rec.continuous = false
    rec.onstart = () => { setListening(true); setState('listening'); setError(null) }
    rec.onend = () => { setListening(false); setState((s) => s === 'listening' ? 'idle' : s) }
    rec.onerror = () => { setListening(false); setState('error'); setTimeout(() => setState('idle'), 1500) }
    rec.onresult = (ev: any) => { const t = ev?.results?.[0]?.[0]?.transcript; if (t) { setInput(t); send(t) } }
    recognitionRef.current = rec; rec.start()
  }

  const stats = b.greeting?.stats
  const pendingCount = b.pending.length
  const briefing = useMemo(() => {
    const name = b.greeting?.name?.split(' ')[0] || 'there'
    const bits = [
      `${pendingCount} approval${pendingCount === 1 ? '' : 's'} waiting`,
      `${stats?.high_match ?? 0} high-match jobs`,
      b.gmail?.connected ? `Gmail connected${b.gmail?.email ? ` (${b.gmail.email})` : ''}` : 'Gmail not connected',
      `${b.tasks?.overdue ?? 0} overdue task${(b.tasks?.overdue ?? 0) === 1 ? '' : 's'}`,
    ]
    return `Good ${new Date().getHours() < 12 ? 'morning' : new Date().getHours() < 17 ? 'afternoon' : 'evening'}, ${name}. ${bits.join(' · ')}.`
  }, [b.greeting, b.gmail, b.tasks, pendingCount, stats])

  const quick = b.greeting?.quick_commands?.length ? b.greeting.quick_commands : [
    { label: 'Scan jobs', command: 'Find Python backend jobs in India' },
    { label: 'Top matches', command: 'Show my top job matches' },
    { label: 'Check inbox', command: 'Check my Gmail for recruiter emails' },
    { label: 'Daily report', command: "Generate today's report" },
  ]

  return (
    <div className="space-y-4">
      <section className="glass-strong rounded-2xl p-4 sm:p-5 relative overflow-hidden">
        <div className="absolute inset-0 scanline opacity-[0.07] pointer-events-none" />
        <div className="flex flex-col xl:flex-row gap-5 items-start">
          <div className="flex-shrink-0 self-center xl:self-start"><Orb state={state} size={210} /></div>
          <div className="flex-1 min-w-0 w-full">
            <div className="flex items-center justify-between gap-3">
              <div>
                <div className="text-xs uppercase tracking-[0.2em] text-cyan-300/80">Mission Briefing</div>
                <h1 className="text-xl sm:text-2xl font-semibold mt-1 glow-text">{b.greeting?.greeting || 'JARVIS Command Center'}</h1>
              </div>
              <div className="flex items-center gap-2">
                <button onClick={togglePower} disabled={powerBusy} className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-xs font-medium transition ${resting ? 'bg-indigo-500/20 border-indigo-400/40 text-indigo-200' : 'bg-emerald-500/15 border-emerald-400/35 text-emerald-200 hover:bg-emerald-500/25'}`} title={resting ? 'Wake JARVIS' : 'Put JARVIS in rest mode'}>
                  {resting ? <Moon size={14}/> : <Sun size={14}/>}<span>{powerBusy ? '...' : resting ? 'OFF' : 'ON'}</span>
                </button>
                <button onClick={refresh} className="p-2 rounded-lg border border-[var(--border-soft)] text-[var(--muted)] hover:text-cyan-200" title="Refresh"><RefreshCw size={15}/></button>
              </div>
            </div>
            <p className="text-sm text-slate-300/85 mt-2">{loading ? 'Loading systems...' : briefing}</p>
            {error && <div className="mt-2 text-xs text-red-300 flex items-center gap-1.5"><AlertTriangle size={13}/>{error}</div>}
            <div className="mt-4 grid grid-cols-2 md:grid-cols-4 gap-2">
              <Stat label="Approvals" value={pendingCount} accent={pendingCount > 0} onClick={() => document.getElementById('approval-queue')?.scrollIntoView({ behavior: 'smooth' })} />
              <Stat label="High Matches" value={stats?.high_match ?? '--'} onClick={() => navigate('/matched')} />
              <Stat label="Overdue Tasks" value={b.tasks?.overdue ?? '--'} accent={(b.tasks?.overdue ?? 0) > 0} onClick={() => navigate('/tasks')} />
              <Stat label="Gmail" value={b.gmail?.connected ? 'Connected' : 'Offline'} accent={!b.gmail?.connected} onClick={() => navigate('/emails')} />
            </div>
            <div className="mt-4 flex gap-2">
              <input value={input} onChange={(e) => setInput(e.target.value)} onKeyDown={(e) => e.key==='Enter' && send()} placeholder='Command JARVIS: "Find Python backend jobs in Hyderabad"' className="flex-1 px-3 py-2.5 rounded-lg text-sm bg-black/20" />
              <button onClick={() => send()} disabled={busy} className="px-3 py-2 rounded-lg bg-cyan-500/20 border border-cyan-400/30 text-cyan-200 hover:bg-cyan-500/30 disabled:opacity-50"><Send size={16}/></button>
              <button onClick={toggleMic} className={`px-3 py-2 rounded-lg border ${listening ? 'bg-emerald-500/20 border-emerald-400/40 text-emerald-200' : 'bg-white/5 border-[var(--border-soft)] text-[var(--muted)] hover:text-cyan-200'}`} title="Voice command"><Mic size={16}/></button>
            </div>
            <div className="mt-3 flex flex-wrap gap-2">
              {quick.map((q) => (
                <button key={q.label} onClick={() => send(q.command)} className="text-xs px-2.5 py-1.5 rounded-full border border-cyan-400/20 text-cyan-100/90 bg-cyan-500/5 hover:bg-cyan-500/10">{q.label}</button>
              ))}
            </div>
          </div>
        </div>
      </section>

      <div className="grid grid-cols-1 xl:grid-cols-[1.15fr_.85fr] gap-4">
        <section className="space-y-4">
          <div id="approval-queue" className="glass rounded-2xl p-4">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2 text-sm text-cyan-200"><ShieldAlert size={16}/> Approval Queue {pendingCount > 0 && <span className="text-[11px] px-1.5 py-0.5 rounded-full bg-amber-400/20 text-amber-300 border border-amber-400/30">{pendingCount}</span>}</div>
              <button onClick={() => navigate('/applications')} className="text-xs text-[var(--muted)] hover:text-cyan-200 inline-flex items-center gap-1">All approvals <ChevronRight size={13}/></button>
            </div>
            {b.pending.length === 0 ? (
              <div className="text-sm text-[var(--muted)] flex items-center gap-2"><CheckCircle2 size={15} className="text-emerald-400"/> No pending approvals. JARVIS is standing by.</div>
            ) : (
              <div className="space-y-3 max-h-[420px] overflow-auto pr-1">
                {b.pending.map((p) => <ApprovalCard key={p.id} proposal={p} onResolved={refresh} />)}
              </div>
            )}
          </div>

          <div className="glass rounded-2xl p-4">
            <div className="flex items-center gap-2 text-sm text-cyan-200 mb-3"><Sparkles size={16}/> Command Log</div>
            <div className="space-y-3 max-h-[360px] overflow-auto pr-1">
              {messages.map((m, i) => (
                <div key={i} className={`flex ${m.role==='user'?'justify-end':'justify-start'}`}>
                  <div className={`max-w-[88%] rounded-xl px-3 py-2 text-sm ${m.role==='user'?'bg-cyan-500/15 border border-cyan-400/25 text-cyan-50':'bg-white/5 border border-[var(--border-soft)] text-slate-200'}`}>
                    <div className="whitespace-pre-wrap leading-relaxed">{m.text}</div>
                    {m.weather?.current && (
                      <div className="mt-2 rounded-lg border border-sky-400/25 bg-sky-500/10 p-2.5">
                        <div className="flex items-center gap-1.5 text-[11px] text-sky-200 mb-0.5"><CloudSun size={12}/> Weather · {m.weather.location?.name}{m.weather.location?.country ? `, ${m.weather.location.country}` : ''}</div>
                        <div className="text-sm font-semibold text-sky-100">{m.weather.current.temperature}°C · {m.weather.current.condition}</div>
                        <div className="text-[10px] text-[var(--muted)]">Feels like {m.weather.current.apparent_temperature}°C · Humidity {m.weather.current.humidity}%</div>
                      </div>
                    )}
                    {m.openUrl && (
                      <button onClick={() => window.open(m.openUrl, '_blank', 'noopener,noreferrer')} className="mt-2 inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-[11px] font-medium bg-cyan-500/15 text-cyan-200 border border-cyan-400/30 hover:bg-cyan-500/25">
                        <ExternalLink size={12}/>{m.openLabel || 'Open link'}
                      </button>
                    )}
                    {m.proposal && <ApprovalCard proposal={m.proposal} onResolved={refresh} />}
                  </div>
                </div>
              ))}
              {busy && <div className="text-xs text-[var(--muted)]">JARVIS is working...</div>}
            </div>
          </div>
        </section>

        <aside className="space-y-4">
          <Panel title="Top Matches" icon={<Briefcase size={15}/>} action={() => navigate('/matched')} actionLabel="All matches">
            {b.topMatches.length === 0 ? <Empty text="No matches yet. Ask JARVIS to scan jobs." /> : b.topMatches.map((m: any) => (
              <div key={m.job_id} className="p-2.5 rounded-lg bg-black/20 border border-[var(--border-soft)]">
                <div className="flex items-center justify-between gap-2"><div className="text-xs text-cyan-100/90 truncate">{m.title}</div><div className="text-xs text-emerald-300 shrink-0">{m.score}%</div></div>
                <div className="text-[11px] text-[var(--muted)] truncate">{m.company || 'Unknown company'}</div>
              </div>
            ))}
          </Panel>

          <Panel title="Inbox / Gmail" icon={<Mail size={15}/>} action={() => navigate('/emails')} actionLabel="Email Access">
            <div className="text-xs text-[var(--muted)]">
              {b.gmail?.connected ? <span className="text-emerald-300">Connected as {b.gmail.email}</span> : <span className="text-amber-300">Not connected - complete Gmail OAuth in docs/GMAIL_SETUP.md</span>}
            </div>
            <div className="text-[11px] text-[var(--muted)] mt-1">Send/draft actions always require your approval.</div>
          </Panel>

          <Panel title="Today" icon={<ListTodo size={15}/>} action={() => navigate('/tasks')} actionLabel="Tasks">
            <div className="grid grid-cols-3 gap-2 text-center">
              <Mini label="Pending" value={b.tasks?.pending ?? '--'} />
              <Mini label="Due" value={b.tasks?.due_today ?? '--'} />
              <Mini label="Overdue" value={b.tasks?.overdue ?? '--'} accent={(b.tasks?.overdue ?? 0) > 0} />
            </div>
          </Panel>

          <Panel title="System" icon={<Cpu size={15}/>} action={() => navigate('/settings')} actionLabel="Settings">
            <div className="text-xs text-[var(--muted)] space-y-1">
              <div>LLM: <span className="text-slate-200">{b.system?.llm?.provider || b.system?.llm?.active || 'unknown'}</span> {b.system?.llm?.model ? <span className="text-[var(--muted)]">({b.system.llm.model})</span> : null}</div>
              <div>RAM: <span className={(b.system?.ram_percent ?? 0) > 85 ? 'text-amber-300' : 'text-slate-200'}>{b.system?.ram_percent ? `${b.system.ram_percent.toFixed(0)}%` : '--'}</span> · CPU: <span className="text-slate-200">{b.system?.cpu_percent ? `${b.system.cpu_percent.toFixed(0)}%` : '--'}</span></div>
            </div>
          </Panel>

          <div className="glass rounded-2xl p-4">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2 text-sm text-cyan-200"><Bell size={15}/> Notifications</div>
              <button onClick={() => navigate('/applications')} className="text-xs text-[var(--muted)] hover:text-cyan-200">Approvals</button>
            </div>
            <div className="space-y-2 max-h-[220px] overflow-auto pr-1">
              {b.notifications.length === 0 ? <Empty text="Nothing new." /> : b.notifications.map((n) => (
                <div key={n.id} className="p-2.5 rounded-lg bg-black/20 border border-[var(--border-soft)]">
                  <div className="flex items-start justify-between gap-2 text-xs">
                    <span className={`font-medium ${n.kind==='error'?'text-red-300':n.kind==='warning'?'text-amber-300':n.kind==='success'?'text-emerald-300':'text-cyan-100/90'}`}>{n.title}</span>
                    {!n.is_read && <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 shrink-0 mt-1" />}
                  </div>
                  {n.body && <div className="text-[11px] text-[var(--muted)] mt-1 line-clamp-2 whitespace-pre-wrap">{n.body}</div>}
                </div>
              ))}
            </div>
          </div>

          <div className="glass rounded-2xl p-4">
            <div className="flex items-center gap-2 text-sm text-cyan-200 mb-3"><Activity size={15}/> Activity</div>
            <div className="space-y-2 max-h-[220px] overflow-auto pr-1">
              {b.activity.length === 0 ? <Empty text="No recent activity." /> : b.activity.map((a) => (
                <div key={a.id} className="p-2.5 rounded-lg bg-black/20 border border-[var(--border-soft)]">
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-cyan-100/90 truncate">{a.agent || 'system'} · {a.action || 'event'}</span>
                    <span className={`${a.status==='failed' || a.status==='error' ? 'text-red-300' : 'text-emerald-300'} shrink-0 ml-2`}>{a.status}</span>
                  </div>
                  {a.detail && <div className="text-[11px] text-[var(--muted)] mt-1 line-clamp-2">{a.detail}</div>}
                </div>
              ))}
            </div>
          </div>
        </aside>
      </div>
    </div>
  )
}

function Stat({ label, value, accent, onClick }: { label: string; value: any; accent?: boolean; onClick?: () => void }) {
  return (
    <button onClick={onClick} className={`text-left glass rounded-xl p-3 border ${accent ? 'border-amber-400/30' : 'border-[var(--border-soft)]'} hover:bg-white/5 transition`}>
      <div className="text-[11px] uppercase tracking-wider text-[var(--muted)]">{label}</div>
      <div className={`mt-1 text-xl font-semibold ${accent ? 'text-amber-300' : 'text-cyan-100'}`}>{value}</div>
    </button>
  )
}

function Panel({ title, icon, action, actionLabel, children }: { title: string; icon: any; action?: () => void; actionLabel?: string; children: any }) {
  return (
    <div className="glass rounded-2xl p-4">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2 text-sm text-cyan-200">{icon}{title}</div>
        {action && <button onClick={action} className="text-xs text-[var(--muted)] hover:text-cyan-200 inline-flex items-center gap-1">{actionLabel} <ChevronRight size={13}/></button>}
      </div>
      <div className="space-y-2">{children}</div>
    </div>
  )
}

function Mini({ label, value, accent }: { label: string; value: any; accent?: boolean }) {
  return <div className="p-2 rounded-lg bg-black/20 border border-[var(--border-soft)]"><div className={`text-lg font-semibold ${accent ? 'text-amber-300' : 'text-cyan-100'}`}>{value}</div><div className="text-[10px] text-[var(--muted)] uppercase tracking-wider">{label}</div></div>
}

function Empty({ text }: { text: string }) { return <div className="text-xs text-[var(--muted)]">{text}</div> }
