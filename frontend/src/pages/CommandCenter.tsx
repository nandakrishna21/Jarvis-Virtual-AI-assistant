import { useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api, type Greeting, type ChatResponse, type Proposal } from '../services/api'
import Orb, { type OrbState } from '../components/jarvis/Orb'
import ApprovalCard from '../components/jarvis/ApprovalCard'
import { Send, Mic, Activity, Sparkles, ShieldAlert, Bell } from 'lucide-react'

type Msg = { role: 'user' | 'assistant'; text: string; proposal?: Proposal }

export default function CommandCenter() {
  const [greeting, setGreeting] = useState<Greeting | null>(null)
  const [state, setState] = useState<OrbState>('idle')
  const [input, setInput] = useState('')
  const [messages, setMessages] = useState<Msg[]>([])
  const [busy, setBusy] = useState(false)
  const [listening, setListening] = useState(false)
  const [activity, setActivity] = useState<any[]>([])
  const [notifications, setNotifications] = useState<any[]>([])
  const recognitionRef = useRef<any>(null)
  const navigate = useNavigate()

  const loadSide = () => {
    api.get<any>('/assistant/history?limit=12').then((r) => setActivity(r?.history || [])).catch(() => {})
    api.get<any>('/notifications?limit=10').then((r) => setNotifications(r?.notifications || [])).catch(() => {})
  }

  useEffect(() => {
    api.get<Greeting>('/assistant/greeting').then((g) => {
      setGreeting(g)
      setMessages([{ role: 'assistant', text: g.message }])
    }).catch(() => setMessages([{ role: 'assistant', text: 'Good day. I am JARVIS. Systems are initializing.' }]))
    loadSide()
    const t = setInterval(loadSide, 20000)
    return () => clearInterval(t)
  }, [])

  const stats = greeting?.stats

  async function send(text?: string) {
    const msg = (text ?? input).trim()
    if (!msg || busy) return
    setInput('')
    setMessages((m) => [...m, { role: 'user', text: msg }])
    setBusy(true); setState('thinking')
    try {
      setState('executing')
      const res = await api.post<ChatResponse>('/assistant/chat', { message: msg })
      const reply = res?.response || res?.error || 'No response.'
      setMessages((m) => [...m, { role: 'assistant', text: reply, proposal: res?.proposal }])
      setState(res?.ok === false ? 'error' : 'success')
      loadSide()
      setTimeout(() => setState('idle'), 1800)
    } catch (e: any) {
      setMessages((m) => [...m, { role: 'assistant', text: e?.message || 'Request failed.' }])
      setState('error'); setTimeout(() => setState('idle'), 2000)
    } finally { setBusy(false) }
  }

  function toggleMic() {
    const SR: any = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition
    if (!SR) { alert('Voice input is not supported in this browser. Use Chrome/Edge or type your command.'); return }
    if (listening) { recognitionRef.current?.stop(); setListening(false); setState('idle'); return }
    const rec = new SR(); rec.lang = 'en-US'; rec.interimResults = false; rec.continuous = false
    rec.onstart = () => { setListening(true); setState('listening') }
    rec.onend = () => { setListening(false); setState((s) => s === 'listening' ? 'idle' : s) }
    rec.onerror = () => { setListening(false); setState('error'); setTimeout(() => setState('idle'), 1500) }
    rec.onresult = (ev: any) => { const t = ev?.results?.[0]?.[0]?.transcript; if (t) { setInput(t); send(t) } }
    recognitionRef.current = rec; rec.start()
  }

  const panels = useMemo(() => ([
    { label: 'Jobs Discovered', value: stats?.jobs_discovered ?? '--' },
    { label: 'High-Match', value: stats?.high_match ?? '--' },
    { label: 'Prepared', value: stats?.applications_prepared ?? '--' },
    { label: 'Submitted', value: stats?.applications_submitted ?? '--' },
    { label: 'Pending Approvals', value: greeting?.pending_approvals ?? '--', accent: true },
    { label: 'Interviews', value: stats?.interviews_scheduled ?? '--' },
  ]), [stats, greeting])

  return (
    <div className="grid grid-cols-1 xl:grid-cols-[1.2fr_.8fr] gap-5">
      <section className="space-y-4">
        <div className="glass-strong rounded-2xl p-5 relative overflow-hidden">
          <div className="absolute inset-0 scanline opacity-[0.08] pointer-events-none" />
          <div className="flex flex-col lg:flex-row items-center gap-6">
            <div className="flex-shrink-0"><Orb state={state} size={240} /></div>
            <div className="flex-1 w-full">
              <div className="text-sm text-[var(--muted)]">Command Interface</div>
              <h1 className="text-2xl font-semibold mt-1 glow-text">{greeting?.greeting || 'Initializing JARVIS...'}</h1>
              <p className="text-sm text-slate-300/80 mt-2 max-w-2xl">I will plan every action and ask for your approval before I do anything. Tell me what you need.</p>
              <div className="mt-4 flex gap-2">
                <input value={input} onChange={(e) => setInput(e.target.value)} onKeyDown={(e) => e.key==='Enter' && send()} placeholder='Try: "Find Python backend jobs in Hyderabad"' className="flex-1 px-3 py-2.5 rounded-lg text-sm" />
                <button onClick={() => send()} disabled={busy} className="px-3 py-2 rounded-lg bg-cyan-500/20 border border-cyan-400/30 text-cyan-200 hover:bg-cyan-500/30 disabled:opacity-50"><Send size={16}/></button>
                <button onClick={toggleMic} className={`px-3 py-2 rounded-lg border ${listening ? 'bg-emerald-500/20 border-emerald-400/40 text-emerald-200' : 'bg-white/5 border-[var(--border-soft)] text-[var(--muted)] hover:text-cyan-200'}`} title="Voice command"><Mic size={16}/></button>
              </div>
              <div className="mt-3 flex flex-wrap gap-2">
                {(greeting?.quick_commands || []).map((q) => (
                  <button key={q.label} onClick={() => send(q.command)} className="text-xs px-2.5 py-1.5 rounded-full border border-cyan-400/20 text-cyan-100/90 bg-cyan-500/5 hover:bg-cyan-500/10">{q.label}</button>
                ))}
              </div>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
          {panels.map((p) => (
            <div key={p.label} className={`glass rounded-xl p-3 border ${p.accent ? 'border-amber-400/30' : 'border-[var(--border-soft)]'}`}>
              <div className="text-[11px] uppercase tracking-wider text-[var(--muted)]">{p.label}</div>
              <div className={`mt-1 text-2xl font-semibold ${p.accent ? 'text-amber-300' : 'text-cyan-100'}`}>{p.value}</div>
            </div>
          ))}
        </div>

        <div className="glass rounded-2xl p-4">
          <div className="flex items-center gap-2 text-sm text-cyan-200 mb-3"><Sparkles size={16}/> Command Log</div>
          <div className="space-y-3 max-h-[420px] overflow-auto pr-1">
            {messages.map((m, i) => (
              <div key={i} className={`flex ${m.role==='user'?'justify-end':'justify-start'}`}>
                <div className={`max-w-[85%] rounded-xl px-3 py-2 text-sm ${m.role==='user'?'bg-cyan-500/15 border border-cyan-400/25 text-cyan-50':'bg-white/5 border border-[var(--border-soft)] text-slate-200'}`}>
                  <div className="whitespace-pre-wrap leading-relaxed">{m.text}</div>
                  {m.proposal && <ApprovalCard proposal={m.proposal} />}
                </div>
              </div>
            ))}
            {busy && <div className="text-xs text-[var(--muted)]">JARVIS is working...</div>}
          </div>
        </div>
      </section>

      <aside className="space-y-4">
        <div className="glass rounded-2xl p-4">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2 text-sm text-cyan-200"><Bell size={16}/> Notifications</div>
            <button onClick={() => navigate('/applications')} className="text-xs text-[var(--muted)] hover:text-cyan-200">Approvals</button>
          </div>
          <div className="space-y-2 max-h-[280px] overflow-auto pr-1">
            {notifications.length === 0 && <div className="text-xs text-[var(--muted)]">Nothing new. Events appear here as they happen.</div>}
            {notifications.map((n) => (
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
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2 text-sm text-cyan-200"><Activity size={16}/> Activity</div>
            <button onClick={() => navigate('/assistant')} className="text-xs text-[var(--muted)] hover:text-cyan-200">Open assistant</button>
          </div>
          <div className="space-y-2 max-h-[360px] overflow-auto pr-1">
            {activity.length === 0 && <div className="text-xs text-[var(--muted)]">No recent activity yet.</div>}
            {activity.map((a) => (
              <div key={a.id} className="p-2.5 rounded-lg bg-black/20 border border-[var(--border-soft)]">
                <div className="flex items-center justify-between text-xs">
                  <span className="text-cyan-100/90">{a.agent || 'system'} · {a.action || 'event'}</span>
                  <span className={`${a.status==='failed' || a.status==='error' ? 'text-red-300' : 'text-emerald-300'}`}>{a.status}</span>
                </div>
                {a.detail && <div className="text-[11px] text-[var(--muted)] mt-1 line-clamp-2">{a.detail}</div>}
              </div>
            ))}
          </div>
        </div>
        <div className="glass rounded-2xl p-4">
          <div className="flex items-center gap-2 text-sm text-amber-200 mb-2"><ShieldAlert size={16}/> Safety</div>
          <ul className="text-xs text-slate-300/90 space-y-1.5 list-disc list-inside">
            <li>Every action requires your explicit approval.</li>
            <li>No applications or emails are sent automatically.</li>
            <li>All data stays local on this machine.</li>
            <li>n8n automations run locally when available.</li>
          </ul>
        </div>
      </aside>
    </div>
  )
}
