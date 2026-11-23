import { useEffect, useRef, useState } from 'react'
import { api } from '../services/api'
import { useAppDispatch, useAppSelector } from '../store/hooks'
import { ExternalLink, Mic, MicOff, Volume2, Square, Send, Trash2, AlertCircle, Briefcase, ListTodo, Newspaper, Radio, Settings2, Wand2, Command } from 'lucide-react'

const STATUS: Record<string, { label: string; hint: string; color: string; dot: string }> = {
  idle: { label: 'Ready', hint: 'Press Start or type a command', color: 'text-slate-200', dot: 'bg-slate-400' },
  listening: { label: 'Listening', hint: 'Speak now — live transcript appears below', color: 'text-rose-200', dot: 'bg-rose-400 animate-pulse' },
  thinking: { label: 'Processing', hint: 'Understanding and executing your command', color: 'text-amber-200', dot: 'bg-amber-400 animate-pulse' },
  speaking: { label: 'Responding', hint: 'JARVIS is speaking the response', color: 'text-cyan-200', dot: 'bg-cyan-400 animate-pulse' },
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
          {[['Pending', report.pending, 'text-cyan-200'], ['Due today', report.due_today, 'text-amber-200'], ['Overdue', report.overdue, 'text-rose-200']].map(([k, v, c]: any) => (
            <div key={k} className="rounded-lg border border-white/10 bg-black/20 px-2.5 py-2 text-center">
              <div className={`text-base font-semibold ${c}`}>{v ?? 0}</div>
              <div className="text-[10px] text-slate-400">{k}</div>
            </div>
          ))}
        </div>
      )}
      {tasks.length > 0 && <div className="space-y-1.5">{tasks.map((t: any) => (
        <div key={t.id} className="flex items-center justify-between gap-2 rounded-lg border border-white/10 bg-black/15 px-2.5 py-2 text-xs">
          <div className="min-w-0"><div className="truncate text-slate-200">{t.title}</div><div className="text-slate-400">{t.category || 'task'}{t.due_date ? ` · ${t.due_date}` : ''}</div></div>
          <span className={t.overdue ? 'text-rose-300' : 'text-emerald-300'}>{t.overdue ? 'Overdue' : 'Active'}</span>
        </div>
      ))}</div>}
      {jobs.length > 0 && <div className="space-y-1.5">{jobs.map((j: any, i: number) => (
        <div key={j.id || j.url || i} className="rounded-lg border border-white/10 bg-black/15 px-2.5 py-2 text-xs">
          <div className="flex items-center justify-between gap-2"><div className="truncate text-slate-200">{j.title}</div>{j.score != null && <span className="text-cyan-200">{j.score}%</span>}</div>
          <div className="text-slate-400 truncate">{j.company || 'Company'}{j.location ? ` · ${j.location}` : ''}</div>
        </div>
      ))}</div>}
    </div>
  )
}

export default function VoiceAgent() {
  const dispatch = useAppDispatch()
  const turns = useAppSelector((s) => s.voice.turns)
  const state = useAppSelector((s) => s.voice.status)
  useAppSelector((s) => s.voice.interim) // kept for store compatibility; live transcript uses captured state
  const continuous = useAppSelector((s) => s.voice.continuous)
  const wakeWord = useAppSelector((s) => s.voice.wakeWord)
  const error = useAppSelector((s) => s.voice.error)

  const [textInput, setTextInput] = useState('')
  const [silenceMs, setSilenceMs] = useState(() => { const v = Number(localStorage.getItem('jarvis.voice.silenceMs')); return [1500, 2000, 3000, 4000].includes(v) ? v : 3000 })
  const [captured, setCaptured] = useState('')
  const [autoSpeak, setAutoSpeak] = useState(() => localStorage.getItem('jarvis.voice.autoSpeak') !== '0')
  const [showSettings, setShowSettings] = useState(false)
  const [wakeFlash, setWakeFlash] = useState(false)
  const [sttMode, setSttMode] = useState<'browser' | 'whisper'>(() => (localStorage.getItem('jarvis.voice.sttMode') as any) === 'whisper' ? 'whisper' : 'browser')
  const [micLevel, setMicLevel] = useState(0)
  const [sttInfo, setSttInfo] = useState<string>('')
  const [telemetry, setTelemetry] = useState({ restarts: 0, errors: 0, fallbacks: 0, last: 'idle' })
  const isIOS = typeof navigator !== 'undefined' && /iphone|ipad|ipod/i.test(navigator.userAgent)

  const recognitionRef = useRef<any>(null)
  const speakingRef = useRef(false)
  const shouldListenRef = useRef(false)
  const recActiveRef = useRef(false)
  const continuousRef = useRef(continuous)
  const wakeWordRef = useRef(wakeWord)
  const autoSpeakRef = useRef(autoSpeak)
  const sttModeRef = useRef(sttMode)
  const turnId = useRef(0)
  const voiceURI = useRef<string | null>(null)
  const silenceRef = useRef<number | null>(null)
  const pendingTextRef = useRef('')
  const lastSentRef = useRef<{ text: string; at: number }>({ text: '', at: 0 })
  const statusRef = useRef(state)
  const logRef = useRef<HTMLDivElement | null>(null)
  const silenceMsRef = useRef(silenceMs)
  const listenStartedAt = useRef(0)
  const watchdogRef = useRef<number | null>(null)
  const recorderRef = useRef<MediaRecorder | null>(null)
  const recorderChunksRef = useRef<Blob[]>([])
  const streamRef = useRef<MediaStream | null>(null)
  const audioCtxRef = useRef<AudioContext | null>(null)
  const analyserRef = useRef<AnalyserNode | null>(null)
  const meterRafRef = useRef<number | null>(null)

  useEffect(() => { silenceMsRef.current = silenceMs; try { localStorage.setItem('jarvis.voice.silenceMs', String(silenceMs)) } catch {} }, [silenceMs])
  useEffect(() => { autoSpeakRef.current = autoSpeak; try { localStorage.setItem('jarvis.voice.autoSpeak', autoSpeak ? '1' : '0') } catch {} }, [autoSpeak])
  useEffect(() => { sttModeRef.current = sttMode; try { localStorage.setItem('jarvis.voice.sttMode', sttMode) } catch {} }, [sttMode])
  useEffect(() => { statusRef.current = state }, [state])
  const logTelemetry = (kind: 'restart'|'error'|'fallback', msg: string) => {
    setTelemetry(t => ({ ...t, [kind === 'restart' ? 'restarts' : kind === 'error' ? 'errors' : 'fallbacks']: (t as any)[kind === 'restart' ? 'restarts' : kind === 'error' ? 'errors' : 'fallbacks'] + 1, last: msg.slice(0,80) }))
  }
  useEffect(() => { continuousRef.current = continuous }, [continuous])
  useEffect(() => { wakeWordRef.current = wakeWord }, [wakeWord])
  useEffect(() => { logRef.current?.scrollTo({ top: 0, behavior: 'smooth' }) }, [turns.length, state])

  useEffect(() => {
    const loadVoices = () => {
      const voices = window.speechSynthesis?.getVoices?.() || []
      const preferred = voices.find(v => /en-IN|en-GB|en-US/i.test(v.lang) && /natural|google|microsoft/i.test(v.name))
        || voices.find(v => /en-IN|en-GB|en-US/i.test(v.lang))
        || voices.find(v => /^en/i.test(v.lang))
      if (preferred) voiceURI.current = preferred.voiceURI
    }
    loadVoices(); window.speechSynthesis?.addEventListener?.('voiceschanged', loadVoices)
    return () => { window.speechSynthesis?.removeEventListener?.('voiceschanged', loadVoices); window.speechSynthesis?.cancel() }
  }, [])

  function primeSpeech() { try { if (window.speechSynthesis) window.speechSynthesis.speak(new SpeechSynthesisUtterance(' ')) } catch {} }

  function stopMeter() {
    if (meterRafRef.current) { cancelAnimationFrame(meterRafRef.current); meterRafRef.current = null }
    setMicLevel(0)
  }

  function startMeter(stream: MediaStream) {
    try {
      stopMeter()
      const Ctx: any = (window as any).AudioContext || (window as any).webkitAudioContext
      if (!Ctx) return
      const ctx = audioCtxRef.current || new Ctx()
      audioCtxRef.current = ctx
      const src = ctx.createMediaStreamSource(stream)
      const analyser = ctx.createAnalyser()
      analyser.fftSize = 512
      src.connect(analyser)
      analyserRef.current = analyser
      const data = new Uint8Array(analyser.frequencyBinCount)
      const tick = () => {
        if (!analyserRef.current) return
        analyserRef.current.getByteTimeDomainData(data)
        let sum = 0
        for (let i = 0; i < data.length; i++) { const v = (data[i] - 128) / 128; sum += v * v }
        const rms = Math.sqrt(sum / data.length)
        setMicLevel(Math.min(100, Math.round(rms * 220)))
        meterRafRef.current = requestAnimationFrame(tick)
      }
      tick()
    } catch { /* meter optional */ }
  }

  async function getMicStream() {
    if (streamRef.current) return streamRef.current
    const stream = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true } })
    streamRef.current = stream
    startMeter(stream)
    return stream
  }

  async function transcribeBlob(blob: Blob) {
    const form = new FormData()
    form.append('audio', blob, `voice-${Date.now()}.webm`)
    const res = await api.upload<any>('/voice/transcribe', form)
    if (res?.error) throw new Error(res.error)
    return String(res?.text || '').trim()
  }

  function startWhisperCapture() {
    return getMicStream().then((stream) => {
      recorderChunksRef.current = []
      const mime = MediaRecorder.isTypeSupported('audio/webm;codecs=opus') ? 'audio/webm;codecs=opus' : (MediaRecorder.isTypeSupported('audio/webm') ? 'audio/webm' : '')
      const rec = new MediaRecorder(stream, mime ? { mimeType: mime } : undefined)
      rec.ondataavailable = (e) => { if (e.data && e.data.size > 0) recorderChunksRef.current.push(e.data) }
      rec.onstop = async () => {
        const blob = new Blob(recorderChunksRef.current, { type: rec.mimeType || 'audio/webm' })
        recorderChunksRef.current = []
        if (!shouldListenRef.current) return
        if (blob.size < 1500) { if (shouldListenRef.current && continuousRef.current && statusRef.current !== 'thinking') setTimeout(() => startWhisperCapture().catch(()=>{}), 300); return }
        try {
          statusRef.current = 'thinking'; dispatch({ type: 'voice/status', payload: 'thinking' })
          setSttInfo('Transcribing with Whisper fallback…')
          const text = await transcribeBlob(blob)
          setSttInfo(text ? 'Whisper transcript received.' : 'Whisper heard no speech.')
          if (text) submitVoice(text)
          else if (shouldListenRef.current && continuousRef.current) { statusRef.current = 'listening'; dispatch({ type: 'voice/status', payload: 'listening' }); setTimeout(() => startWhisperCapture().catch(()=>{}), 250) }
        } catch (e: any) {
          dispatch({ type: 'voice/error', payload: `Whisper fallback failed: ${e?.message || e}` })
          setSttInfo('Whisper fallback error.')
          if (shouldListenRef.current && continuousRef.current) { statusRef.current = 'listening'; dispatch({ type: 'voice/status', payload: 'listening' }); setTimeout(() => startWhisperCapture().catch(()=>{}), 1200) }
        }
      }
      recorderRef.current = rec
      rec.start()
      statusRef.current = 'listening'; dispatch({ type: 'voice/status', payload: 'listening' })
      setSttInfo('Using Whisper fallback recording.')
      if (silenceRef.current) window.clearTimeout(silenceRef.current)
      silenceRef.current = window.setTimeout(() => { try { if (rec.state === 'recording') rec.stop() } catch {} }, Math.max(3500, silenceMsRef.current + 1500))
    })
  }

  function releaseMic() {
    stopMeter()
    try { recorderRef.current?.stop() } catch {}
    recorderRef.current = null
    recorderChunksRef.current = []
    if (streamRef.current) { streamRef.current.getTracks().forEach(t => t.stop()); streamRef.current = null }
  }

  function speak(text: string): Promise<void> {
    return new Promise(resolve => {
      const synth = window.speechSynthesis
      if (!synth || !text || !autoSpeakRef.current) {
        if (shouldListenRef.current && continuousRef.current && statusRef.current !== 'thinking') safeRestart(250)
        statusRef.current = 'idle'; dispatch({ type: 'voice/status', payload: 'idle' }); resolve(); return
      }
      synth.cancel()
      const utter = new SpeechSynthesisUtterance(text)
      utter.rate = 1.02; utter.pitch = 1.0
      if (voiceURI.current) utter.voice = synth.getVoices().find(v => v.voiceURI === voiceURI.current) || null
      speakingRef.current = true; statusRef.current = 'speaking'; dispatch({ type: 'voice/status', payload: 'speaking' })
      const done = () => {
        speakingRef.current = false; statusRef.current = 'idle'; dispatch({ type: 'voice/status', payload: 'idle' })
        if (shouldListenRef.current && continuousRef.current) safeRestart(300)
        resolve()
      }
      utter.onend = done; utter.onerror = done; synth.speak(utter)
    })
  }

  function stopSpeaking() { window.speechSynthesis?.cancel(); speakingRef.current = false; if (statusRef.current === 'speaking') { statusRef.current = 'idle'; dispatch({ type: 'voice/status', payload: 'idle' }) } }

  async function ask(text: string) {
    const clean = text.trim()
    if (!clean) return
    dispatch({ type: 'voice/error', payload: null })
    const id = ++turnId.current
    dispatch({ type: 'voice/turnStart', payload: { id, user: clean } })
    statusRef.current = 'thinking'; dispatch({ type: 'voice/status', payload: 'thinking' })
    try {
      const history = turns.slice(-6).map(t => ({ user: t.user, assistant: t.assistant }))
      const res = await api.post<any>('/voice/agent', { message: clean, history })
      const reply = res?.spoken || res?.reply || res?.error || 'I did not catch that. Please try again.'
      dispatch({ type: 'voice/turnEnd', payload: { id, assistant: reply, intent: res?.intent, needsApproval: !!res?.requires_approval, openUrl: res?.open_url, openLabel: res?.open_label, payload: res } })
      if (res?.open_url) { try { window.open(res.open_url, '_blank', 'noopener,noreferrer') } catch {} }
      if (res?.error && !res?.reply) dispatch({ type: 'voice/error', payload: res.error })
      await speak(reply)
    } catch (e: any) {
      dispatch({ type: 'voice/error', payload: e?.message || 'Voice agent request failed' })
      dispatch({ type: 'voice/turnEnd', payload: { id, assistant: 'I could not complete that request. Check your connection and try again.' } })
      statusRef.current = 'idle'; dispatch({ type: 'voice/status', payload: 'idle' })
      if (shouldListenRef.current && continuousRef.current) safeRestart(350)
    }
  }

  function submitVoice(text: string) {
    const clean = text.trim()
    if (!clean) return
    const now = Date.now()
    if (clean === lastSentRef.current.text && now - lastSentRef.current.at < 1200) return
    if (wakeWordRef.current && !/\b(jarvis|javis|jarvus)\b/i.test(clean)) {
      pendingTextRef.current = ''; setCaptured(''); dispatch({ type: 'voice/interim', payload: '' })
      if (shouldListenRef.current && continuousRef.current) safeRestart(250)
      return
    }
    if (silenceRef.current) { window.clearTimeout(silenceRef.current); silenceRef.current = null }
    pendingTextRef.current = ''; lastSentRef.current = { text: clean, at: now }
    dispatch({ type: 'voice/interim', payload: '' }); setCaptured('')
    const command = wakeWordRef.current ? clean.replace(/^.*?\b(jarvis|javis|jarvus)\b[\s,.:!-]*/i, '').trim() || clean : clean
    statusRef.current = 'thinking'; dispatch({ type: 'voice/status', payload: 'thinking' })
    try { recognitionRef.current?.stop() } catch {}
    void ask(command)
  }

  function safeRestart(delay = 300) {
    if (!shouldListenRef.current || !continuousRef.current) return
    window.setTimeout(() => {
      if (!shouldListenRef.current || !continuousRef.current) return
      if (speakingRef.current || statusRef.current === 'thinking' || recActiveRef.current) return
      try { recognitionRef.current?.abort?.() } catch {}
      try { recognitionRef.current?.stop?.() } catch {}
      recognitionRef.current = null
      startRecognition()
    }, delay)
  }

  function startRecognition() {
    const SR: any = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition
    if (!window.isSecureContext) { dispatch({ type: 'voice/error', payload: 'Voice requires HTTPS. Use the Tailscale HTTPS URL on mobile.' }); return false }
    if (!SR) { dispatch({ type: 'voice/error', payload: 'Speech recognition is not supported in this browser. Use Chrome/Edge, or type your command.' }); return false }
    if (recognitionRef.current) { try { recognitionRef.current.onend = null; recognitionRef.current.abort?.() } catch {} recognitionRef.current = null }
    const rec = new SR()
    rec.continuous = !isIOS; rec.interimResults = true; rec.lang = 'en-US'; rec.maxAlternatives = 1
    rec.onstart = () => { recActiveRef.current = true }
    rec.onresult = (event: any) => {
      let finalText = ''; let interimText = ''
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const t = event.results[i][0]?.transcript || ''
        if (event.results[i].isFinal) finalText += t + ' '; else interimText += t
      }
      if (finalText.trim()) pendingTextRef.current = `${pendingTextRef.current} ${finalText}`.replace(/\s+/g, ' ').trim()
      const combined = `${pendingTextRef.current} ${interimText}`.replace(/\s+/g, ' ').trim()
      setCaptured(combined); dispatch({ type: 'voice/interim', payload: combined.slice(-200) })
      if (speakingRef.current && combined) { window.speechSynthesis?.cancel(); speakingRef.current = false }

      const wakeEnabled = wakeWordRef.current
      const hasWake = !wakeEnabled || /\b(jarvis|javis|jarvus)\b/i.test(combined)
      if (wakeEnabled && /\b(jarvis|javis|jarvus)\b/i.test(interimText || finalText)) { setWakeFlash(true); window.setTimeout(() => setWakeFlash(false), 900) }
      if (combined && hasWake) {
        if (silenceRef.current) window.clearTimeout(silenceRef.current)
        silenceRef.current = window.setTimeout(() => submitVoice(pendingTextRef.current.trim() || combined), silenceMsRef.current)
      } else if (combined && wakeEnabled && !hasWake) {
        if (silenceRef.current) { window.clearTimeout(silenceRef.current); silenceRef.current = null }
        // In wake-word mode, ignore background speech but keep mic alive.
        if (combined.length > 80) { pendingTextRef.current = ''; setCaptured(''); dispatch({ type: 'voice/interim', payload: '' }) }
      }
    }
    rec.onerror = (e: any) => {
      const err = e?.error
      if (err === 'not-allowed' || err === 'service-not-allowed') { dispatch({ type: 'voice/error', payload: 'Microphone permission denied. Allow mic access in browser site settings.' }); shouldListenRef.current = false; recActiveRef.current = false; return }
      if (err === 'aborted') { recActiveRef.current = false; return }
      if (err === 'no-speech') { recActiveRef.current = false; if (shouldListenRef.current && continuousRef.current) safeRestart(250); return }
      if (err === 'network') { dispatch({ type: 'voice/error', payload: 'Speech recognition network error. Check internet and retry.' }); recActiveRef.current = false; if (shouldListenRef.current && continuousRef.current) safeRestart(1200); return }
      logTelemetry('error',`speech ${err||'unknown'}`); dispatch({ type: 'voice/error', payload: `Speech recognition error: ${err || 'unknown'}` })
      recActiveRef.current = false
      if (shouldListenRef.current && continuousRef.current) { logTelemetry('restart','error restart'); safeRestart(800) }
    }
    rec.onend = () => {
      recActiveRef.current = false
      if (silenceRef.current) { window.clearTimeout(silenceRef.current); silenceRef.current = null }
      const pending = pendingTextRef.current.trim()
      if (pending && statusRef.current !== 'thinking' && statusRef.current !== 'speaking') { submitVoice(pending); return }
      if (shouldListenRef.current && continuousRef.current && !speakingRef.current && statusRef.current !== 'thinking') {
        safeRestart(350)
      } else if (shouldListenRef.current && !continuousRef.current) {
        statusRef.current = 'idle'; dispatch({ type: 'voice/status', payload: 'idle' }); shouldListenRef.current = false
      }
    }
    try { rec.start() } catch (err: any) {
      recognitionRef.current = null
      logTelemetry('fallback','browser->whisper'); dispatch({ type: 'voice/error', payload: `Could not start speech recognition: ${err?.message || err}. Falling back to Whisper when possible.` })
      if (shouldListenRef.current) { setSttMode('whisper'); startWhisperCapture().catch(()=>{}); return true }
      return false
    }
    recognitionRef.current = rec; listenStartedAt.current = Date.now(); statusRef.current = 'listening'; dispatch({ type: 'voice/status', payload: 'listening' }); setSttInfo('Browser speech recognition active.'); return true
  }

  function stopRecognition() {
    shouldListenRef.current = false
    recActiveRef.current = false
    if (silenceRef.current) { window.clearTimeout(silenceRef.current); silenceRef.current = null }
    if (watchdogRef.current) { window.clearInterval(watchdogRef.current); watchdogRef.current = null }
    pendingTextRef.current = ''; setCaptured('')
    try { if (recognitionRef.current) recognitionRef.current.onend = null as any; recognitionRef.current?.abort?.() } catch {}
    try { recognitionRef.current?.stop() } catch {}; recognitionRef.current = null
    try { if (recorderRef.current?.state === 'recording') recorderRef.current.stop() } catch {}
    releaseMic()
    statusRef.current = 'idle'; dispatch({ type: 'voice/status', payload: 'idle' }); dispatch({ type: 'voice/interim', payload: '' })
  }

  async function ensureMic() {
    if (!navigator.mediaDevices?.getUserMedia) return true
    try { await getMicStream(); return true }
    catch (e: any) { dispatch({ type: 'voice/error', payload: `Microphone blocked/unavailable: ${e?.message || 'permission denied'}` }); return false }
  }

  function startWatchdog() {
    if (watchdogRef.current) window.clearInterval(watchdogRef.current)
    watchdogRef.current = window.setInterval(() => {
      if (!shouldListenRef.current || !continuousRef.current) return
      if (sttModeRef.current !== 'browser') return
      if (speakingRef.current || statusRef.current === 'thinking') return
      const age = Date.now() - listenStartedAt.current
      if (age > 45000 && !pendingTextRef.current.trim()) {
        setSttInfo('Refreshing speech recognizer…')
        try { recognitionRef.current?.abort?.() } catch {}
      }
      if (!recActiveRef.current) safeRestart(200)
    }, 7000)
  }

  async function toggleListening() {
    if (state === 'listening' || recActiveRef.current || recorderRef.current?.state === 'recording') {
      if (captured.trim()) { submitVoice(captured); return }
      stopRecognition(); return
    }
    stopSpeaking(); primeSpeech(); dispatch({ type: 'voice/error', payload: null })
    shouldListenRef.current = true; lastSentRef.current = { text: '', at: 0 }; pendingTextRef.current = ''; setCaptured('')
    setSttInfo('')
    const ok = await ensureMic(); if (!ok) { shouldListenRef.current = false; return }
    if (sttModeRef.current === 'whisper' || !((window as any).SpeechRecognition || (window as any).webkitSpeechRecognition)) {
      setSttMode('whisper')
      await startWhisperCapture().catch((e: any) => dispatch({ type: 'voice/error', payload: `Whisper fallback unavailable: ${e?.message || e}` }))
      return
    }
    listenStartedAt.current = Date.now()
    const started = startRecognition(); if (!started) shouldListenRef.current = false
    startWatchdog()
  }

  useEffect(() => () => { shouldListenRef.current = false; if (watchdogRef.current) window.clearInterval(watchdogRef.current); try { recognitionRef.current?.stop() } catch {}; window.speechSynthesis?.cancel(); releaseMic(); try { audioCtxRef.current?.close?.() } catch {} }, [])

  async function sendText() { const text = textInput.trim(); if (!text) return; setTextInput(''); await ask(text) }

  const quickActions = [
    { label: 'Open YouTube', icon: ExternalLink, cmd: 'Open YouTube' },
    { label: 'Top job matches', icon: Briefcase, cmd: 'Show my top job matches' },
    { label: 'Pending tasks', icon: ListTodo, cmd: 'Show my pending tasks' },
    { label: 'Hiring news', icon: Newspaper, cmd: "Show today's hiring news" },
  ]
  const lastAssistant = [...turns].reverse().find(t => t.assistant)?.assistant
  const status = STATUS[state] || STATUS.idle
  const draftVisible = captured && (state === 'listening' || state === 'thinking') && !turns.some(t => t.user === captured && !t.assistant)

  return (
    <div className="mx-auto max-w-7xl space-y-4 pb-4">
      <div className="rounded-3xl border border-white/10 bg-[linear-gradient(180deg,rgba(15,23,42,0.7),rgba(2,6,23,0.55))] p-4 sm:p-5">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <div className="inline-flex items-center gap-2 rounded-full border border-cyan-400/20 bg-cyan-500/10 px-3 py-1 text-[11px] uppercase tracking-[0.2em] text-cyan-100"><Radio size={12} /> JARVIS Voice</div>
            <h1 className="mt-2 text-2xl sm:text-3xl font-semibold text-white">Voice Command Center</h1>
            <p className="mt-1 text-sm text-slate-400">Speak naturally. Your command is transcribed live, auto-sent after pause, and executed by JARVIS.</p>
          </div>
          <div className="flex flex-wrap items-center gap-2 text-xs">
            <span className={`inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-1.5 ${status.color}`}><span className={`h-2 w-2 rounded-full ${status.dot}`} />{status.label}</span>
            <button onClick={() => setShowSettings(v => !v)} className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-1.5 text-slate-300 hover:bg-white/10"><Settings2 size={13} />Settings</button>
          </div>
        </div>
        {showSettings && (
          <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-5 rounded-2xl border border-white/10 bg-black/20 p-4 text-sm">
            <label className="flex items-center justify-between gap-3 text-slate-300"><span>Hands-free</span><input type="checkbox" checked={continuous} onChange={e => dispatch({ type: 'voice/continuous', payload: e.target.checked })} /></label>
            <label className="flex items-center justify-between gap-3 text-slate-300"><span>Wake word "JARVIS"</span><input type="checkbox" checked={wakeWord} onChange={e => dispatch({ type: 'voice/wakeWord', payload: e.target.checked })} /></label>
            <label className="flex items-center justify-between gap-3 text-slate-300"><span>Speak replies</span><input type="checkbox" checked={autoSpeak} onChange={e => setAutoSpeak(e.target.checked)} /></label>
            <label className="flex items-center justify-between gap-3 text-slate-300"><span>Auto-send pause</span><select value={silenceMs} onChange={e => setSilenceMs(Number(e.target.value))} className="rounded-md border border-white/10 bg-slate-900 px-2 py-1 text-cyan-200"><option value={1500}>1.5s</option><option value={2000}>2s</option><option value={3000}>3s</option><option value={4000}>4s</option></select></label>
            <label className="flex items-center justify-between gap-3 text-slate-300"><span>STT mode</span><select value={sttMode} onChange={e => setSttMode(e.target.value as any)} className="rounded-md border border-white/10 bg-slate-900 px-2 py-1 text-cyan-200"><option value="browser">Browser</option><option value="whisper">Whisper fallback</option></select></label>
          </div>
        )}
        {error && <div className="mt-4 rounded-xl border border-red-400/20 bg-red-500/10 px-4 py-3 text-sm text-red-200 flex items-start gap-2"><AlertCircle size={16} className="mt-0.5 shrink-0" /><span>{error}</span></div>}
      </div>

      <div className="grid gap-4 xl:grid-cols-[360px_minmax(0,1fr)]">
        <div className="rounded-3xl border border-white/10 bg-black/20 p-4 sm:p-5 space-y-4">
          <div className="rounded-2xl border border-white/10 bg-[radial-gradient(ellipse_at_top,rgba(34,211,238,0.12),transparent_60%)] p-5 text-center">
            <div className={`mx-auto relative h-36 w-36 sm:h-44 sm:w-44 rounded-full border-4 flex items-center justify-center transition-all ${wakeFlash ? 'border-emerald-400/80 bg-emerald-500/15 shadow-[0_0_50px_rgba(52,211,153,0.25)]' : state === 'listening' ? 'border-red-400/60 bg-red-500/10 shadow-[0_0_40px_rgba(251,113,133,0.2)]' : state === 'thinking' ? 'border-amber-400/60 bg-amber-500/10 shadow-[0_0_40px_rgba(251,191,36,0.15)]' : state === 'speaking' ? 'border-cyan-400/60 bg-cyan-500/10 shadow-[0_0_40px_rgba(34,211,238,0.2)]' : 'border-cyan-400/20 bg-cyan-500/5'}`}>
              {(state === 'listening' || state === 'thinking' || state === 'speaking') && <div className="absolute inset-[-8px] rounded-full border border-white/10 animate-ping" />}
              <div>
                <div className="text-[10px] uppercase tracking-[0.3em] text-slate-400">{state}</div>
                <div className="mt-2 text-lg font-medium text-white">{status.label}</div>
              </div>
            </div>
            <p className="mt-4 text-sm text-slate-300 min-h-[40px]">{wakeFlash ? 'Wake word detected.' : state === 'listening' ? (captured ? `“${captured}”` : wakeWord ? 'Say “JARVIS…” and your command.' : 'Listening… speak your command.') : state === 'thinking' ? 'Processing your command…' : state === 'speaking' ? (lastAssistant?.slice(0, 110) || 'Speaking…') : 'Ready for your next command.'}</p>
            <div className="mt-4 flex gap-1 justify-center">{Array.from({ length: 12 }).map((_, i) => <span key={i} className={`w-1.5 rounded-full ${state === 'idle' ? 'h-2 bg-white/10' : 'bg-cyan-400/70 animate-pulse'}`} style={{ height: state === 'idle' ? 8 : 8 + (i % 5) * 5, animationDelay: `${i * 60}ms` }} />)}</div>
            <div className="mt-4">
              <div className="flex items-center justify-between text-[11px] text-slate-400"><span>Mic level</span><span>{micLevel}% · {sttMode === 'whisper' ? 'Whisper' : 'Browser STT'}</span></div>
              <div className="mt-1 h-2 rounded-full bg-white/10 overflow-hidden"><div className="h-full bg-cyan-400/80 transition-all" style={{ width: `${micLevel}%` }} /></div>
              {sttInfo && <div className="mt-1 text-[11px] text-slate-500">{sttInfo}</div>}
              <div className="mt-1 text-[10px] text-slate-500">restarts:{telemetry.restarts} errors:{telemetry.errors} fallback:{telemetry.fallbacks} · {telemetry.last}</div>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-2">
            <button onClick={toggleListening} className={`col-span-2 rounded-2xl px-4 py-3.5 text-sm font-semibold inline-flex items-center justify-center gap-2 border transition ${state === 'listening' ? 'border-red-400/50 bg-red-500/15 text-red-100 hover:bg-red-500/20' : 'border-cyan-400/40 bg-cyan-500/15 text-cyan-50 hover:bg-cyan-500/25'}`}>
              {state === 'listening' ? (captured ? <Send size={16} /> : <MicOff size={16} />) : <Mic size={16} />}
              {state === 'listening' ? (captured ? 'Send now' : 'Stop listening') : 'Start talking'}
            </button>
            <button onClick={stopSpeaking} className="rounded-xl border border-white/10 bg-white/5 px-3 py-2.5 text-sm text-slate-200 hover:bg-white/10 inline-flex items-center justify-center gap-2"><Square size={14} />Stop voice</button>
            <button onClick={() => speak(lastAssistant || '')} disabled={!lastAssistant} className="rounded-xl border border-white/10 bg-white/5 px-3 py-2.5 text-sm text-slate-200 hover:bg-white/10 disabled:opacity-40 inline-flex items-center justify-center gap-2"><Volume2 size={14} />Repeat</button>
          </div>

          <div className="rounded-2xl border border-white/10 bg-white/[0.02] p-4">
            <div className="text-[11px] uppercase tracking-wide text-slate-400 mb-3 flex items-center gap-2"><Wand2 size={12} />Quick commands</div>
            <div className="grid gap-2">
              {quickActions.map(a => <button key={a.label} onClick={() => { setTextInput(a.cmd); void ask(a.cmd) }} className="flex items-center gap-3 rounded-xl border border-white/10 bg-black/20 px-3 py-2.5 text-left hover:border-cyan-400/30 hover:bg-cyan-500/5"><a.icon size={15} className="text-cyan-300" /><div><div className="text-sm text-slate-200">{a.label}</div><div className="text-[11px] text-slate-500">{a.cmd}</div></div></button>)}
            </div>
          </div>

          <button onClick={() => { stopRecognition(); stopSpeaking(); dispatch({ type: 'voice/clear' }); setCaptured('') }} disabled={!turns.length && !captured} className="w-full rounded-xl border border-white/10 px-3 py-2.5 text-xs text-slate-400 hover:text-red-300 disabled:opacity-40 inline-flex items-center justify-center gap-2"><Trash2 size={13} />Clear conversation</button>
          {isIOS && <div className="text-[11px] text-amber-300">iOS Safari may pause continuous listening when screen locks. Tap Start talking if needed.</div>}
        </div>

        <div className="rounded-3xl border border-white/10 bg-black/20 flex flex-col h-[72vh] min-h-[560px] max-h-[760px]">
          <div className="flex items-center justify-between border-b border-white/10 px-4 sm:px-5 py-4">
            <div><div className="text-sm font-medium text-slate-100 flex items-center gap-2"><Command size={14} className="text-cyan-300" />Conversation</div><div className="text-xs text-slate-400">{status.hint}</div></div>
            <div className="text-xs text-slate-500">{turns.length} turn{turns.length === 1 ? '' : 's'}</div>
          </div>

          <div ref={logRef} className="flex-1 overflow-y-scroll overscroll-contain px-4 sm:px-5 py-4 space-y-4" style={{ scrollbarGutter: 'stable' }}>
            {draftVisible && (
              <div className="space-y-2">
                <div className="flex justify-end">
                  <div className="max-w-[85%] rounded-2xl rounded-br-md bg-gradient-to-r from-cyan-500/20 to-blue-500/15 border border-cyan-400/30 px-4 py-2.5 text-sm text-cyan-50">
                    <div className="text-[10px] uppercase tracking-wide text-cyan-300/70 mb-1">{state === 'thinking' ? 'Sending command' : 'Live transcript'}</div>
                    {captured}
                    {state === 'listening' && <div className="mt-1.5 text-[11px] text-cyan-200/60 inline-flex items-center gap-2"><span className="h-1.5 w-1.5 rounded-full bg-cyan-300 animate-pulse" />Auto-sending after pause…</div>}
                  </div>
                </div>
                {state === 'thinking' && <div className="flex justify-start"><div className="rounded-2xl rounded-bl-md bg-white/[0.04] border border-white/10 px-4 py-3 text-sm text-slate-400 inline-flex items-center gap-2"><span className="h-2 w-2 rounded-full bg-cyan-300 animate-pulse" />Thinking...</div></div>}
              </div>
            )}

            {[...turns].reverse().map((t) => (
              <div key={t.id} className="space-y-2">
                <div className="flex justify-end"><div className="max-w-[85%] rounded-2xl rounded-br-md bg-gradient-to-r from-cyan-500/20 to-blue-500/15 border border-cyan-400/20 px-4 py-2.5 text-sm text-cyan-50">{t.user}</div></div>
                <div className="flex justify-start">
                  <div className="max-w-[92%] rounded-2xl rounded-bl-md bg-white/[0.04] border border-white/10 px-4 py-3 text-sm text-slate-200">
                    {t.assistant || <span className="inline-flex items-center gap-2 text-slate-400"><span className="h-2 w-2 rounded-full bg-cyan-300 animate-pulse" />Thinking...</span>}
                    <VoicePayload payload={t.payload} />
                    {t.openUrl && <a href={t.openUrl} target="_blank" rel="noreferrer" className="mt-3 inline-flex items-center gap-1.5 rounded-lg border border-cyan-400/30 bg-cyan-500/10 px-3 py-2 text-xs text-cyan-100 hover:bg-cyan-500/20"><ExternalLink size={13} /> {t.openLabel || 'Open link'}</a>}
                    {t.needsApproval && <div className="mt-2 inline-flex items-center gap-1.5 text-[11px] text-amber-300"><AlertCircle size={12} /> Needs your approval in Approvals.</div>}
                  </div>
                </div>
              </div>
            ))}

            {turns.length === 0 && !draftVisible && (
              <div className="rounded-2xl border border-dashed border-white/15 bg-white/[0.02] p-6 text-center">
                <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-cyan-500/10 text-cyan-300"><Mic size={20} /></div>
                <div className="text-base font-medium text-slate-100">Ready for your command</div>
                <p className="mt-1 text-sm text-slate-400 max-w-md mx-auto">Press <span className="text-cyan-200">Start talking</span>, speak naturally, and pause. Your transcript appears live and JARVIS auto-sends it.</p>
              </div>
            )}
          </div>

          <div className="border-t border-white/10 p-4 sm:p-5">
            <div className="flex gap-2">
              <input value={textInput} onChange={e => setTextInput(e.target.value)} onKeyDown={e => { if (e.key === 'Enter') sendText() }} placeholder="Type a command, or use voice..." className="flex-1 rounded-2xl border border-white/10 bg-black/20 px-4 py-3 text-sm text-slate-100 placeholder:text-slate-500 focus:outline-none focus:border-cyan-400/40" />
              <button onClick={sendText} disabled={!textInput.trim()} className="rounded-2xl border border-cyan-400/30 bg-cyan-500/10 px-4 py-3 text-cyan-100 hover:bg-cyan-500/20 disabled:opacity-40 inline-flex items-center gap-2"><Send size={15} /><span className="hidden sm:inline">Send</span></button>
            </div>
            <div className="mt-3 flex flex-wrap gap-2">{quickActions.map(a => <button key={a.label} onClick={() => { setTextInput(a.cmd); void ask(a.cmd) }} className="inline-flex items-center gap-1.5 rounded-full border border-white/10 bg-white/[0.03] px-3 py-1.5 text-[11px] text-slate-300 hover:border-cyan-400/30 hover:text-cyan-100"><a.icon size={12} />{a.label}</button>)}</div>
          </div>
        </div>
      </div>
    </div>
  )
}
