import { useEffect, useRef, useState } from 'react'
import { api } from '../services/api'
import { useAppDispatch, useAppSelector } from '../store/hooks'
import { ExternalLink, Mic, MicOff, Volume2, Square, Send, Trash2, Sparkles, AlertCircle, Briefcase, ListTodo, Newspaper } from 'lucide-react'

const ORB_STATES: Record<string, string> = {
  idle: 'Ready when you are',
  listening: 'Listening...',
  thinking: 'Thinking...',
  speaking: 'Speaking...',
}

function VoicePayload({ payload }: { payload?: any }) {
  if (!payload) return null
  const report = payload.report
  const tasks = Array.isArray(payload.tasks) ? payload.tasks.slice(0, 5) : []
  const jobs = Array.isArray(payload.jobs) ? payload.jobs.slice(0, 4) : []
  if (!report && !tasks.length && !jobs.length) return null
  return (
    <div className="mt-3 space-y-2">
      {report && (
        <div className="grid grid-cols-3 gap-2">
          {[['Pending', report.pending, 'text-cyan-200'], ['Due today', report.due_today, 'text-amber-200'], ['Overdue', report.overdue, 'text-rose-200']].map(([k,v,c]: any) => (
            <div key={k} className="rounded-lg border border-[var(--border-soft)] bg-black/20 px-2.5 py-2 text-center">
              <div className={`text-base font-semibold ${c}`}>{v ?? 0}</div>
              <div className="text-[10px] text-[var(--muted)]">{k}</div>
            </div>
          ))}
        </div>
      )}
      {tasks.length > 0 && (
        <div className="space-y-1.5">
          {tasks.map((t: any) => (
            <div key={t.id} className="flex items-center justify-between gap-2 rounded-lg border border-[var(--border-soft)] bg-black/15 px-2.5 py-2 text-xs">
              <div className="min-w-0"><div className="truncate text-slate-200">{t.title}</div><div className="text-[var(--muted)]">{t.category || 'task'}{t.due_date ? ` · ${t.due_date}` : ''}</div></div>
              {t.overdue ? <span className="text-rose-300">Overdue</span> : <span className="text-emerald-300">Active</span>}
            </div>
          ))}
        </div>
      )}
      {jobs.length > 0 && (
        <div className="space-y-1.5">
          {jobs.map((j: any, i: number) => (
            <div key={j.id || j.url || i} className="rounded-lg border border-[var(--border-soft)] bg-black/15 px-2.5 py-2 text-xs">
              <div className="flex items-center justify-between gap-2"><div className="truncate text-slate-200">{j.title}</div>{j.score != null && <span className="text-cyan-200">{j.score}%</span>}</div>
              <div className="text-[var(--muted)] truncate">{j.company || 'Company'}{j.location ? ` · ${j.location}` : ''}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default function VoiceAgent() {
  const dispatch = useAppDispatch()
  const turns = useAppSelector((s) => s.voice.turns)
  const state = useAppSelector((s) => s.voice.status)
  const interim = useAppSelector((s) => s.voice.interim)
  const continuous = useAppSelector((s) => s.voice.continuous)
  const wakeWord = useAppSelector((s) => s.voice.wakeWord)
  const error = useAppSelector((s) => s.voice.error)
  const [textInput, setTextInput] = useState('')
  const [silenceMs, setSilenceMs] = useState(3000)
  const isIOS = typeof navigator !== 'undefined' && /iphone|ipad|ipod/i.test(navigator.userAgent)

  const recognitionRef = useRef<any>(null)
  const speakingRef = useRef(false)
  const shouldListenRef = useRef(false)
  const continuousRef = useRef(continuous)
  const wakeWordRef = useRef(wakeWord)
  const turnId = useRef(0)
  const voiceURI = useRef<string | null>(null)
  const silenceRef = useRef<number | null>(null)
  const pendingTextRef = useRef('')
  const lastSentRef = useRef('')
  const statusRef = useRef(state)
  const logRef = useRef<HTMLDivElement | null>(null)
  const silenceMsRef = useRef(3000)
  useEffect(() => { silenceMsRef.current = silenceMs }, [silenceMs])
  useEffect(() => { statusRef.current = state }, [state])
  useEffect(() => { logRef.current?.scrollTo({ top: logRef.current.scrollHeight, behavior: 'smooth' }) }, [turns, interim, state])

  useEffect(() => { continuousRef.current = continuous }, [continuous])
  useEffect(() => { wakeWordRef.current = wakeWord }, [wakeWord])

  useEffect(() => {
    const loadVoices = () => {
      const voices = window.speechSynthesis?.getVoices?.() || []
      const english = voices.find(v => /en-GB/i.test(v.lang)) || voices.find(v => /^en/i.test(v.lang))
      if (english) voiceURI.current = english.voiceURI
    }
    loadVoices()
    window.speechSynthesis?.addEventListener?.('voiceschanged', loadVoices)
    return () => {
      window.speechSynthesis?.removeEventListener?.('voiceschanged', loadVoices)
      window.speechSynthesis?.cancel()
    }
  }, [])

  function primeSpeech() {
    // Unlock speech synthesis inside the user gesture (required by iOS Safari).
    try {
      if (window.speechSynthesis) window.speechSynthesis.speak(new SpeechSynthesisUtterance(' '))
    } catch { /* not supported */ }
  }

  function speak(text: string): Promise<void> {
    return new Promise(resolve => {
      const synth = window.speechSynthesis
      if (!synth || !text) {
        if (shouldListenRef.current && continuousRef.current) {
          try { recognitionRef.current?.start() } catch { /* already running */ }
        }
        resolve(); return
      }
      synth.cancel()
      const utter = new SpeechSynthesisUtterance(text)
      utter.rate = 1.05
      utter.pitch = 1.0
      if (voiceURI.current) {
        utter.voice = window.speechSynthesis.getVoices().find(v => v.voiceURI === voiceURI.current) || null
      }
      speakingRef.current = true
      dispatch({ type: 'voice/status', payload: 'speaking' })
      const done = () => {
        speakingRef.current = false
        statusRef.current = 'idle'
        dispatch({ type: 'voice/status', payload: 'idle' })
        if (shouldListenRef.current && continuousRef.current) {
          setTimeout(() => { try { recognitionRef.current?.start() } catch { /* already running */ } }, 250)
        }
        resolve()
      }
      utter.onend = done
      utter.onerror = done
      synth.speak(utter)
    })
  }

  function stopSpeaking() {
    window.speechSynthesis?.cancel()
    speakingRef.current = false
    dispatch({ type: 'voice/status', payload: 'idle' })
  }

  async function ask(text: string) {
    const clean = text.trim()
    if (!clean) return
    dispatch({ type: 'voice/error', payload: null })
    const id = ++turnId.current
    dispatch({ type: 'voice/turnStart', payload: { id, user: clean } })
    statusRef.current = 'thinking'
    dispatch({ type: 'voice/status', payload: 'thinking' })
    try {
      const history = turns.slice(-6).map(t => ({ user: t.user, assistant: t.assistant }))
      const res = await api.post<any>('/voice/agent', { message: clean, history })
      const reply = res?.spoken || res?.reply || res?.error || 'I did not catch that.'
      dispatch({
        type: 'voice/turnEnd',
        payload: { id, assistant: reply, intent: res?.intent, needsApproval: !!res?.requires_approval, openUrl: res?.open_url, openLabel: res?.open_label, payload: res },
      })
      if (res?.open_url) {
        try { window.open(res.open_url, '_blank', 'noopener,noreferrer') } catch { /* popup blocked */ }
      }
      if (res?.error && !res?.reply) dispatch({ type: 'voice/error', payload: res.error })
      await speak(reply)
    } catch (e: any) {
      dispatch({ type: 'voice/error', payload: e?.message || 'Voice agent failed' })
      dispatch({ type: 'voice/turnEnd', payload: { id, assistant: 'I could not complete that request. Please try again.' } })
      statusRef.current = 'idle'
      dispatch({ type: 'voice/status', payload: 'idle' })
      if (shouldListenRef.current && continuousRef.current) {
        setTimeout(() => { try { recognitionRef.current?.start() } catch {} }, 250)
      }
    }
  }

  function submitVoice(text: string) {
    const clean = text.trim()
    if (!clean || clean === lastSentRef.current) return
    if (silenceRef.current) { window.clearTimeout(silenceRef.current); silenceRef.current = null }
    pendingTextRef.current = ''
    lastSentRef.current = clean
    window.setTimeout(() => { if (lastSentRef.current === clean) lastSentRef.current = '' }, 3000)
    dispatch({ type: 'voice/interim', payload: '' })
    if (wakeWordRef.current) {
      const lower = clean.toLowerCase()
      if (!lower.includes('jarvis')) {
        if (shouldListenRef.current && continuousRef.current) {
          setTimeout(() => { try { recognitionRef.current?.start() } catch {} }, 200)
        }
        return
      }
      statusRef.current = 'thinking'
      try { recognitionRef.current?.stop() } catch { /* restart after reply */ }
      const stripped = lower.replace(/^.*?jarvis\s*/, '').trim()
      void ask(stripped || clean)
      return
    }
    statusRef.current = 'thinking'
    try { recognitionRef.current?.stop() } catch { /* restart after reply */ }
    void ask(clean)
  }

  function startRecognition() {
    const SR: any = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition
    if (!window.isSecureContext) {
      dispatch({ type: 'voice/error', payload: 'Voice needs HTTPS. Open the https:// URL instead of a plain http:// LAN address.' })
      return false
    }
    if (!SR) {
      dispatch({ type: 'voice/error', payload: 'This browser has no speech recognition. Use Chrome or Edge, or type instead.' })
      return false
    }
    const rec = new SR()
    rec.continuous = !isIOS
    rec.interimResults = true
    rec.lang = 'en-US'
    rec.maxAlternatives = 1
    rec.onresult = (event: any) => {
      let finalText = ''
      let interimText = ''
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const transcript = event.results[i][0]?.transcript || ''
        if (event.results[i].isFinal) finalText += transcript + ' '
        else interimText += transcript
      }
      if (finalText.trim()) {
        pendingTextRef.current = `${pendingTextRef.current} ${finalText}`.replace(/\s+/g, ' ').trim()
      }
      const combined = `${pendingTextRef.current} ${interimText}`.replace(/\s+/g, ' ').trim()
      dispatch({ type: 'voice/interim', payload: combined.slice(-180) })
      if (speakingRef.current && combined) {
        window.speechSynthesis?.cancel()
        speakingRef.current = false
      }
      if (combined) {
        if (silenceRef.current) window.clearTimeout(silenceRef.current)
        silenceRef.current = window.setTimeout(() => submitVoice(combined), silenceMsRef.current)
      }
    }
    rec.onerror = (e: any) => {
      const err = e?.error
      if (err === 'not-allowed' || err === 'service-not-allowed') { dispatch({ type: 'voice/error', payload: 'Microphone permission denied. Allow mic access in browser site settings.' }); shouldListenRef.current = false; return }
      if (err === 'no-speech' || err === 'aborted') return
      if (err === 'network') { dispatch({ type: 'voice/error', payload: 'Speech recognition network error. Check internet and try again.' }); return }
      dispatch({ type: 'voice/error', payload: `Speech recognition error: ${err || 'unknown'}` })
    }
    rec.onend = () => {
      if (silenceRef.current) { window.clearTimeout(silenceRef.current); silenceRef.current = null }
      const pending = pendingTextRef.current.trim()
      if (pending && statusRef.current !== 'thinking' && statusRef.current !== 'speaking') {
        submitVoice(pending)
        return
      }
      if (shouldListenRef.current && continuousRef.current && !speakingRef.current && statusRef.current !== 'thinking') {
        setTimeout(() => { try { rec.start() } catch { /* already running */ } }, 250)
      } else if (shouldListenRef.current && !continuousRef.current) {
        dispatch({ type: 'voice/status', payload: 'idle' })
        shouldListenRef.current = false
      }
    }
    try {
      rec.start()
    } catch (err: any) {
      dispatch({ type: 'voice/error', payload: `Could not start the microphone: ${err?.message || err}` })
      return false
    }
    recognitionRef.current = rec
    dispatch({ type: 'voice/status', payload: 'listening' })
    return true
  }

  function stopRecognition() {
    shouldListenRef.current = false
    if (silenceRef.current) { window.clearTimeout(silenceRef.current); silenceRef.current = null }
    pendingTextRef.current = ''
    try { recognitionRef.current?.stop() } catch { }
    recognitionRef.current = null
    dispatch({ type: 'voice/status', payload: 'idle' })
    dispatch({ type: 'voice/interim', payload: '' })
  }

  async function ensureMic() {
    if (!navigator.mediaDevices?.getUserMedia) return true
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      stream.getTracks().forEach(t => t.stop())
      return true
    } catch (e: any) {
      dispatch({ type: 'voice/error', payload: 'Microphone access was blocked. Allow mic permission for this site and try again.' })
      return false
    }
  }

  async function toggleListening() {
    if (state === 'listening') {
      stopRecognition()
      return
    }
    stopSpeaking()
    primeSpeech()
    dispatch({ type: 'voice/error', payload: null })
    shouldListenRef.current = true
    lastSentRef.current = ''
    pendingTextRef.current = ''
    const ok = await ensureMic()
    if (!ok) { shouldListenRef.current = false; return }
    const started = startRecognition()
    if (!started) shouldListenRef.current = false
  }

  useEffect(() => {
    return () => {
      shouldListenRef.current = false
      try { recognitionRef.current?.stop() } catch { }
      window.speechSynthesis?.cancel()
    }
  }, [])

  async function sendText() {
    const text = textInput.trim()
    if (!text) return
    setTextInput('')
    await ask(text)
  }

  const orbColor =
    state === 'listening' ? 'from-rose-500/80 to-orange-400/30 border-rose-300/70 shadow-[0_0_60px_rgba(251,113,133,0.28)]'
    : state === 'thinking' ? 'from-amber-400/70 to-yellow-500/20 border-amber-300/70 shadow-[0_0_60px_rgba(251,191,36,0.22)]'
    : state === 'speaking' ? 'from-cyan-400/80 to-blue-500/20 border-cyan-300/70 shadow-[0_0_60px_rgba(34,211,238,0.28)]'
    : 'from-cyan-500/30 to-indigo-600/10 border-cyan-400/30'
  const lastAssistant = [...turns].reverse().find(t => t.assistant)?.assistant
  const quickActions = [
    { label: 'Open YouTube', icon: ExternalLink, cmd: 'Open YouTube' },
    { label: 'Top matches', icon: Briefcase, cmd: 'Show my top job matches' },
    { label: 'Pending tasks', icon: ListTodo, cmd: 'Show my pending tasks' },
    { label: 'Hiring news', icon: Newspaper, cmd: "Show today's hiring news" },
  ]

  return (
    <div className="mx-auto max-w-7xl space-y-4 pb-4">
      <div className="relative overflow-hidden rounded-3xl border border-cyan-400/10 bg-[radial-gradient(ellipse_at_top,_rgba(34,211,238,0.12),_transparent_45%),linear-gradient(180deg,rgba(255,255,255,0.04),rgba(255,255,255,0.02))] p-4 sm:p-6">
        <div className="absolute inset-0 pointer-events-none bg-[linear-gradient(to_right,rgba(255,255,255,0.03)_1px,transparent_1px),linear-gradient(to_bottom,rgba(255,255,255,0.03)_1px,transparent_1px)] bg-[size:28px_28px]" />
        <div className="relative flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <div className="inline-flex items-center gap-2 rounded-full border border-cyan-400/20 bg-cyan-500/10 px-3 py-1 text-[11px] text-cyan-100"><Sparkles size={12}/> Voice Command Center</div>
            <h1 className="mt-3 text-2xl sm:text-3xl font-semibold tracking-tight text-white">Talk to JARVIS like a real assistant</h1>
            <p className="mt-1 text-sm text-slate-300/80 max-w-2xl">Fast voice commands, live transcription, actionable replies, and hands-free control for jobs, tasks, email and daily work.</p>
          </div>
          <div className="flex flex-wrap gap-2 text-xs">
            <div className={`rounded-full border px-3 py-1.5 ${state === 'listening' ? 'border-red-400/40 bg-red-500/10 text-red-200' : state === 'thinking' ? 'border-amber-400/40 bg-amber-500/10 text-amber-200' : state === 'speaking' ? 'border-cyan-400/40 bg-cyan-500/10 text-cyan-200' : 'border-white/10 bg-white/5 text-slate-300'}`}>{ORB_STATES[state]}</div>
            <label className="flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-1.5 text-slate-300 cursor-pointer"><input type="checkbox" checked={continuous} onChange={(e) => dispatch({ type: 'voice/continuous', payload: e.target.checked })} />Hands-free</label>
            <label className="flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-1.5 text-slate-300 cursor-pointer"><input type="checkbox" checked={wakeWord} onChange={(e) => dispatch({ type: 'voice/wakeWord', payload: e.target.checked })} />"JARVIS" wake word</label>
            <label className="flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-1.5 text-slate-300">Auto-send<select value={silenceMs} onChange={e=>setSilenceMs(Number(e.target.value))} className="bg-transparent text-cyan-200 outline-none"><option value={1500}>1.5s</option><option value={2000}>2s</option><option value={3000}>3s</option><option value={4000}>4s</option></select></label>
          </div>
        </div>
        {error && <div className="relative mt-4 rounded-xl border border-red-400/20 bg-red-500/10 px-4 py-3 text-sm text-red-200">{error}</div>}
      </div>

      <div className="grid gap-4 xl:grid-cols-[420px_minmax(0,1fr)]">
        <div className="rounded-3xl border border-white/10 bg-black/20 p-4 sm:p-6 backdrop-blur">
          <div className="flex flex-col items-center text-center">
            <div className={`relative h-44 w-44 sm:h-56 sm:w-56 rounded-full bg-gradient-to-br ${orbColor} border-4 flex items-center justify-center transition-all`}>
              {(state === 'listening' || state === 'speaking' || state === 'thinking') && <div className="absolute inset-[-12px] rounded-full border border-white/10 animate-ping" />}
              <div className="absolute inset-3 rounded-full border border-white/10" />
              <div className="px-6">
                <div className="text-[11px] uppercase tracking-[0.3em] text-white/70">{state}</div>
                <div className="mt-2 text-base sm:text-lg font-medium text-white">{ORB_STATES[state]}</div>
              </div>
            </div>

            <div className="mt-5 w-full rounded-2xl border border-white/10 bg-white/[0.03] p-4 text-left">
              <div className="flex items-center justify-between text-[11px] uppercase tracking-wide text-slate-400"><span>{state === 'listening' ? 'Live transcript' : 'Assistant status'}</span><span className={state === 'listening' ? 'text-red-300' : state === 'thinking' ? 'text-amber-300' : state === 'speaking' ? 'text-cyan-300' : 'text-slate-400'}>{state}</span></div>
              <div className="mt-2 min-h-[56px] text-sm leading-relaxed text-slate-200">{interim ? <span className="text-cyan-50">“{interim}”</span> : (lastAssistant || 'Tap Start talking, then speak. When you pause, JARVIS will auto-send your command.')}</div>
              <div className="mt-3 flex gap-1">{[0,1,2,3,4,5,6].map(i => <span key={i} className={`h-1.5 flex-1 rounded-full ${state === 'listening' ? 'bg-red-400/70 animate-pulse' : state === 'thinking' ? 'bg-amber-400/60 animate-pulse' : state === 'speaking' ? 'bg-cyan-400/70 animate-pulse' : 'bg-white/10'}`} style={{animationDelay:`${i*90}ms`}} />)}</div>
            </div>

            <div className="mt-4 grid w-full grid-cols-2 gap-2 sm:grid-cols-4">
              <button onClick={toggleListening} className={`col-span-2 sm:col-span-2 rounded-2xl px-4 py-3 text-sm font-medium inline-flex items-center justify-center gap-2 border transition ${state === 'listening' ? 'border-red-400/50 bg-red-500/15 text-red-100' : 'border-cyan-400/40 bg-cyan-500/15 text-cyan-50 hover:bg-cyan-500/25'}`}>{state === 'listening' ? <MicOff size={16}/> : <Mic size={16}/>}{state === 'listening' ? 'Stop listening' : 'Start talking'}</button>
              <button onClick={stopSpeaking} className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-slate-200 hover:bg-white/10 inline-flex items-center justify-center gap-2"><Square size={15}/>Stop</button>
              <button onClick={() => speak(turns[turns.length - 1]?.assistant || '')} disabled={!turns.length} className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-slate-200 hover:bg-white/10 disabled:opacity-40 inline-flex items-center justify-center gap-2"><Volume2 size={15}/>Repeat</button>
            </div>
            <div className="mt-3 flex w-full gap-2">
              <button onClick={() => dispatch({ type: 'voice/clear' })} disabled={!turns.length} className="flex-1 rounded-xl border border-white/10 px-3 py-2 text-xs text-slate-400 hover:text-red-300 disabled:opacity-40 inline-flex items-center justify-center gap-2"><Trash2 size={13}/>Clear conversation</button>
            </div>
            {isIOS && <div className="mt-3 text-[11px] text-amber-300">iPhone Safari may pause continuous listening when screen locks. Tap Start talking if needed.</div>}
          </div>
        </div>

        <div className="rounded-3xl border border-white/10 bg-black/20 backdrop-blur flex flex-col min-h-[560px]">
          <div className="flex items-center justify-between border-b border-white/10 px-4 sm:px-5 py-4">
            <div><div className="text-sm font-medium text-cyan-100">Conversation</div><div className="text-xs text-slate-400">Voice + text commands, action cards, and instant replies</div></div>
            <div className="text-xs text-slate-400">{turns.length} turn{turns.length === 1 ? '' : 's'}</div>
          </div>

          <div ref={logRef} className="flex-1 overflow-auto px-4 sm:px-5 py-4 space-y-4">
            {turns.length === 0 && (
              <div className="rounded-2xl border border-dashed border-white/15 bg-white/[0.02] p-5">
                <div className="text-base font-medium text-slate-100">What can I do for you?</div>
                <p className="mt-1 text-sm text-slate-400">Try a command below, or just press Start talking and speak naturally.</p>
                <div className="mt-4 grid gap-2 sm:grid-cols-2">
                  {quickActions.map(a => <button key={a.label} onClick={() => { setTextInput(a.cmd); void ask(a.cmd) }} className="flex items-center gap-3 rounded-xl border border-white/10 bg-black/20 px-3 py-3 text-left hover:border-cyan-400/30 hover:bg-cyan-500/5"><a.icon size={16} className="text-cyan-300"/><div><div className="text-sm text-slate-200">{a.label}</div><div className="text-[11px] text-slate-400">{a.cmd}</div></div></button>)}
                </div>
              </div>
            )}
            {turns.map((t) => (
              <div key={t.id} className="space-y-2">
                <div className="flex justify-end"><div className="max-w-[85%] rounded-2xl rounded-br-md bg-gradient-to-r from-cyan-500/20 to-blue-500/15 border border-cyan-400/20 px-4 py-2.5 text-sm text-cyan-50">{t.user}</div></div>
                <div className="flex justify-start">
                  <div className="max-w-[92%] rounded-2xl rounded-bl-md bg-white/[0.04] border border-white/10 px-4 py-3 text-sm text-slate-200">
                    {t.assistant || <span className="inline-flex items-center gap-2 text-slate-400"><span className="h-2 w-2 rounded-full bg-cyan-300 animate-pulse"/>Thinking...</span>}
                    <VoicePayload payload={t.payload} />
                    {t.openUrl && <a href={t.openUrl} target="_blank" rel="noreferrer" className="mt-3 inline-flex items-center gap-1.5 rounded-lg border border-cyan-400/30 bg-cyan-500/10 px-3 py-2 text-xs text-cyan-100 hover:bg-cyan-500/20"><ExternalLink size={13}/> {t.openLabel || 'Open link'}</a>}
                    {t.needsApproval && <div className="mt-2 inline-flex items-center gap-1.5 text-[11px] text-amber-300"><AlertCircle size={12}/> Needs your approval in Approvals.</div>}
                  </div>
                </div>
              </div>
            ))}
            {interim && <div className="flex justify-end"><div className="max-w-[85%] rounded-2xl rounded-br-md border border-dashed border-cyan-400/30 bg-cyan-500/5 px-4 py-2.5 text-sm text-cyan-100/80"><div className="text-[10px] uppercase tracking-wide text-cyan-300/70 mb-1">Live transcript</div>“{interim}”</div></div>}
          </div>

          <div className="border-t border-white/10 p-4 sm:p-5">
            <div className="flex gap-2">
              <input value={textInput} onChange={(e) => setTextInput(e.target.value)} onKeyDown={(e) => { if (e.key === 'Enter') sendText() }} placeholder="Ask anything... e.g. 'Open YouTube' or 'Show my pending tasks'" className="flex-1 rounded-2xl border border-white/10 bg-black/20 px-4 py-3 text-sm text-slate-100 placeholder:text-slate-500 focus:outline-none focus:border-cyan-400/40" />
              <button onClick={sendText} className="rounded-2xl border border-cyan-400/30 bg-cyan-500/10 px-4 py-3 text-cyan-100 hover:bg-cyan-500/20 inline-flex items-center gap-2"><Send size={15}/><span className="hidden sm:inline">Send</span></button>
            </div>
            <div className="mt-3 flex flex-wrap gap-2">{quickActions.map(a => <button key={a.label} onClick={() => { setTextInput(a.cmd); void ask(a.cmd) }} className="inline-flex items-center gap-1.5 rounded-full border border-white/10 bg-white/[0.03] px-3 py-1.5 text-[11px] text-slate-300 hover:border-cyan-400/30 hover:text-cyan-100"><a.icon size={12}/>{a.label}</button>)}</div>
          </div>
        </div>
      </div>
    </div>
  )
}
