import { useEffect, useRef, useState } from 'react'
import { useLocation } from 'react-router-dom'
import { api, type ChatResponse, type Proposal } from '../services/api'
import ApprovalCard from '../components/jarvis/ApprovalCard'
import { Send, Mic, Bot, User, Minus, Maximize2, Minimize2, ExternalLink, CloudSun } from 'lucide-react'

type Msg = {
  role: 'user' | 'assistant'
  text: string
  proposal?: Proposal
  intent?: string
  openUrl?: string
  openLabel?: string
  weather?: any
}

type Size = 'sm' | 'md' | 'lg'

const SIZES: { key: Size; label: string; height: string; maxWidth: string }[] = [
  { key: 'sm', label: 'S', height: 'h-[360px]', maxWidth: 'max-w-[720px] mx-auto' },
  { key: 'md', label: 'M', height: 'h-[calc(100dvh-140px)] min-h-[320px]', maxWidth: '' },
  { key: 'lg', label: 'L', height: 'h-[calc(100dvh-120px)] min-h-[360px]', maxWidth: '' },
]

export default function Assistant() {
  const location = useLocation() as any
  const [messages, setMessages] = useState<Msg[]>([
    { role: 'assistant', text: 'I am JARVIS. Ask me to find jobs, analyze your resume, prepare applications, run automations, check the weather, or open YouTube. I will ask for your approval before taking any action.' }
  ])
  const [input, setInput] = useState('')
  const [busy, setBusy] = useState(false)
  const [listening, setListening] = useState(false)
  const [minimized, setMinimized] = useState(false)
  const [maximized, setMaximized] = useState(false)
  const [size, setSize] = useState<Size>('md')
  const recRef = useRef<any>(null)
  const endRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages, busy])
  useEffect(() => {
    const prefill = location?.state?.prefill
    if (!prefill) return
    const id = setTimeout(() => { setInput(prefill); window.history.replaceState({}, document.title) }, 0)
    return () => clearTimeout(id)
  }, [location])

  async function send(text?: string) {
    const msg = (text ?? input).trim()
    if (!msg || busy) return
    setInput('')
    setMessages((m) => [...m, { role: 'user', text: msg }])
    setBusy(true)
    try {
      const res = await api.post<ChatResponse>('/assistant/chat', { message: msg })
      const reply = res?.response || res?.error || (res?.ok ? 'Done.' : 'No response.')
      setMessages((m) => [...m, {
        role: 'assistant',
        text: reply,
        proposal: res?.proposal,
        intent: res?.intent,
        openUrl: res?.open_url,
        openLabel: res?.open_label,
        weather: res?.weather,
      }])
    } catch (e: any) {
      setMessages((m) => [...m, { role: 'assistant', text: e?.message || 'Request failed.' }])
    } finally { setBusy(false) }
  }

  function toggleMic() {
    const SR: any = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition
    if (!SR) { alert('Voice input is not supported in this browser.'); return }
    if (listening) { recRef.current?.stop(); setListening(false); return }
    const rec = new SR(); rec.lang = 'en-US'; rec.interimResults = false
    rec.onstart = () => setListening(true)
    rec.onend = () => setListening(false)
    rec.onerror = () => setListening(false)
    rec.onresult = (ev: any) => { const t = ev?.results?.[0]?.[0]?.transcript; if (t) send(t) }
    recRef.current = rec; rec.start()
  }

  const preset = SIZES.find((s) => s.key === size) || SIZES[1]
  const frameClass = maximized
    ? 'fixed inset-4 z-[80] h-auto'
    : `${preset.height} ${preset.maxWidth}`

  return (
    <div className={`${frameClass} ${minimized ? 'h-auto' : ''} flex flex-col glass-strong rounded-2xl overflow-hidden transition-all duration-200`}>
      <div className="px-3 sm:px-4 py-2 border-b border-[var(--border-soft)] flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 min-w-0">
          <Bot size={15} className="text-cyan-300 shrink-0" />
          <div className="text-sm font-medium text-cyan-100 truncate">AI Assistant</div>
          {!minimized && <span className="hidden md:inline text-[11px] text-[var(--muted)] truncate">Approval required before actions · Local mode</span>}
        </div>
        <div className="flex items-center gap-1 shrink-0">
          <div className="flex items-center rounded-md border border-[var(--border-soft)] overflow-hidden">
            {SIZES.map((s) => (
              <button
                key={s.key}
                onClick={() => { setSize(s.key); setMaximized(false); setMinimized(false) }}
                className={`w-6 h-6 text-[11px] font-semibold transition ${size === s.key && !maximized ? 'bg-cyan-500/25 text-cyan-200' : 'text-[var(--muted)] hover:bg-white/10 hover:text-cyan-200'}`}
                title={`${s.key.toUpperCase()} size`}
                aria-label={`Set assistant to ${s.key.toUpperCase()} size`}
              >{s.label}</button>
            ))}
          </div>
          <button onClick={() => setMinimized(v => !v)} className="p-1 rounded-md hover:bg-white/10 text-[var(--muted)] hover:text-cyan-200" title={minimized ? 'Restore' : 'Minimize'} aria-label={minimized ? 'Restore assistant' : 'Minimize assistant'}><Minus size={14}/></button>
          <button onClick={() => { setMaximized(v => !v); setMinimized(false) }} className="p-1 rounded-md hover:bg-white/10 text-[var(--muted)] hover:text-cyan-200" title={maximized ? 'Restore size' : 'Maximize'} aria-label={maximized ? 'Restore assistant size' : 'Maximize assistant'}>{maximized ? <Minimize2 size={14}/> : <Maximize2 size={14}/>}</button>
        </div>
      </div>
      {!minimized && <>
      <div className="flex-1 overflow-auto p-4 space-y-4">
        {messages.map((m, i) => (
          <div key={i} className={`flex gap-3 ${m.role==='user'?'justify-end':'justify-start'}`}>
            {m.role==='assistant' && <div className="w-7 h-7 rounded-full bg-cyan-500/15 border border-cyan-400/30 flex items-center justify-center text-cyan-300 flex-shrink-0"><Bot size={14}/></div>}
            <div className={`max-w-[88%] ${m.role==='user'?'order-1':''}`}>
              <div className={`rounded-xl px-3.5 py-2.5 text-sm whitespace-pre-wrap leading-relaxed ${m.role==='user'?'bg-cyan-500/15 border border-cyan-400/25 text-cyan-50':'bg-white/5 border border-[var(--border-soft)] text-slate-200'}`}>{m.text}</div>
              {m.weather?.current && (
                <div className="mt-2 rounded-xl border border-sky-400/25 bg-sky-500/10 p-3">
                  <div className="flex items-center gap-2 text-xs text-sky-200 mb-1"><CloudSun size={14}/> Weather · {m.weather.location?.name}{m.weather.location?.country ? `, ${m.weather.location.country}` : ''}</div>
                  <div className="text-lg font-semibold text-sky-100">{m.weather.current.temperature}°C · {m.weather.current.condition}</div>
                  <div className="text-[11px] text-[var(--muted)] mt-1">Feels like {m.weather.current.apparent_temperature}°C · Humidity {m.weather.current.humidity}% · Wind {m.weather.current.wind_speed} km/h</div>
                  {Array.isArray(m.weather.forecast) && m.weather.forecast.length > 1 && (
                    <div className="mt-2 grid grid-cols-2 sm:grid-cols-3 gap-1.5 text-[11px]">
                      {m.weather.forecast.slice(1).map((d: any, idx: number) => (
                        <div key={idx} className="rounded-lg bg-black/20 border border-[var(--border-soft)] px-2 py-1">
                          <div className="text-[var(--muted)]">{d.date}</div>
                          <div className="text-sky-100">{d.temp_min}° / {d.temp_max}°C</div>
                          <div className="text-[var(--muted)] truncate">{d.condition}</div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
              {m.openUrl && (
                <button
                  onClick={() => window.open(m.openUrl, '_blank', 'noopener,noreferrer')}
                  className="mt-2 inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-cyan-500/15 text-cyan-200 border border-cyan-400/30 hover:bg-cyan-500/25"
                >
                  <ExternalLink size={13}/>{m.openLabel || 'Open link'}
                </button>
              )}
              {m.proposal && <ApprovalCard proposal={m.proposal} onResolved={(p) => setMessages((ms) => ms.map((x, idx) => idx===i ? { ...x, proposal: p } : x))} />}
              {m.intent && m.role==='assistant' && <div className="mt-1 text-[10px] text-[var(--muted)]">intent: {m.intent}</div>}
            </div>
            {m.role==='user' && <div className="w-7 h-7 rounded-full bg-white/10 border border-[var(--border-soft)] flex items-center justify-center text-slate-300 flex-shrink-0"><User size={14}/></div>}
          </div>
        ))}
        {busy && <div className="text-xs text-[var(--muted)] pl-10">JARVIS is preparing a response...</div>}
        <div ref={endRef} />
      </div>
      <div className="p-3 border-t border-[var(--border-soft)] bg-black/10">
        <div className="flex gap-2">
          <input value={input} onChange={(e) => setInput(e.target.value)} onKeyDown={(e) => e.key==='Enter' && !e.shiftKey && send()} placeholder="Message JARVIS..." className="flex-1 px-3 py-2.5 rounded-lg text-sm" />
          <button onClick={toggleMic} className={`px-3 rounded-lg border ${listening ? 'bg-emerald-500/20 border-emerald-400/40 text-emerald-200' : 'bg-white/5 border-[var(--border-soft)] text-[var(--muted)]'}`} title="Voice"><Mic size={16}/></button>
          <button onClick={() => send()} disabled={busy} className="px-4 rounded-lg bg-cyan-500/20 border border-cyan-400/30 text-cyan-100 hover:bg-cyan-500/30 disabled:opacity-50 flex items-center gap-2 text-sm"><Send size={15}/> Send</button>
        </div>
      </div>
      </>}
    </div>
  )
}
