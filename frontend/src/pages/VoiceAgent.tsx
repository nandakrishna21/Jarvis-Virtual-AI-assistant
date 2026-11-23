import { useEffect, useRef, useState } from 'react'
import { api } from '../services/api'
import { useAppDispatch, useAppSelector } from '../store/hooks'
import { Mic, MicOff, Volume2, Square, Send, Radio, Trash2 } from 'lucide-react'

const ORB_STATES: Record<string, string> = {
  idle: 'Ready when you are',
  listening: 'Listening...',
  thinking: 'Thinking...',
  speaking: 'Speaking...',
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
  useEffect(() => { statusRef.current = state }, [state])

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
        payload: { id, assistant: reply, intent: res?.intent, needsApproval: !!res?.requires_approval },
      })
      if (res?.error && !res?.reply) dispatch({ type: 'voice/error', payload: res.error })
      await speak(reply)
    } catch (e: any) {
      dispatch({ type: 'voice/error', payload: e?.message || 'Voice agent failed' })
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
      const combined = `${pendingTextRef.current} ${finalText} ${interimText}`.replace(/\s+/g, ' ').trim()
      dispatch({ type: 'voice/interim', payload: combined.slice(-140) })
      if (speakingRef.current && (interimText.trim() || finalText.trim())) {
        window.speechSynthesis?.cancel()
        speakingRef.current = false
      }
      if (finalText.trim()) {
        pendingTextRef.current = `${pendingTextRef.current} ${finalText}`.replace(/\s+/g, ' ').trim()
        if (silenceRef.current) window.clearTimeout(silenceRef.current)
        silenceRef.current = window.setTimeout(() => submitVoice(pendingTextRef.current), 700)
      }
    }
    rec.onerror = (e: any) => {
      if (e?.error === 'not-allowed') dispatch({ type: 'voice/error', payload: 'Microphone permission denied. Allow it in your browser and try again.' })
      if (e?.error === 'no-speech' || e?.error === 'aborted') return
      dispatch({ type: 'voice/error', payload: `Speech recognition error: ${e?.error}` })
    }
    rec.onend = () => {
      if (silenceRef.current) { window.clearTimeout(silenceRef.current); silenceRef.current = null }
      if (pendingTextRef.current.trim() && statusRef.current !== 'thinking' && statusRef.current !== 'speaking') {
        submitVoice(pendingTextRef.current)
        return
      }
      if (shouldListenRef.current && continuousRef.current && !speakingRef.current && statusRef.current !== 'thinking') {
        setTimeout(() => { try { rec.start() } catch { /* already running */ } }, 200)
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

  function toggleListening() {
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
    state === 'listening' ? 'from-red-500/70 to-rose-500/30 border-red-400/70 shadow-[0_0_40px_rgba(248,113,113,0.25)]'
    : state === 'thinking' ? 'from-amber-400/60 to-orange-500/20 border-amber-300/70 shadow-[0_0_40px_rgba(251,191,36,0.2)]'
    : state === 'speaking' ? 'from-cyan-400/70 to-sky-500/20 border-cyan-300/70 shadow-[0_0_40px_rgba(34,211,238,0.25)]'
    : 'from-cyan-500/30 to-blue-600/10 border-cyan-400/30'
  const lastAssistant = [...turns].reverse().find(t => t.assistant)?.assistant

  return (
    <div className="mx-auto max-w-6xl space-y-4 pb-4">
      <div className="glass-strong rounded-2xl p-4 sm:p-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <div className="flex items-center gap-2 text-cyan-100"><Radio size={18}/><h1 className="text-lg font-semibold">Voice Agent</h1></div>
            <p className="text-sm text-[var(--muted)] mt-1">Speak naturally. JARVIS listens, responds, and keeps the conversation moving.</p>
          </div>
          <div className={`rounded-full border px-3 py-1 text-xs ${state === 'listening' ? 'border-red-400/40 text-red-200 bg-red-500/10' : state === 'thinking' ? 'border-amber-400/40 text-amber-200 bg-amber-500/10' : state === 'speaking' ? 'border-cyan-400/40 text-cyan-200 bg-cyan-500/10' : 'border-[var(--border-soft)] text-[var(--muted)]'}`}>
            {ORB_STATES[state]}
          </div>
        </div>
        <div className="mt-3 flex flex-wrap items-center gap-4 text-xs text-[var(--muted)]">
          <label className="flex items-center gap-2 cursor-pointer"><input type="checkbox" checked={continuous} onChange={(e) => dispatch({ type: 'voice/continuous', payload: e.target.checked })} /><span>Hands-free conversation</span></label>
          <label className="flex items-center gap-2 cursor-pointer"><input type="checkbox" checked={wakeWord} onChange={(e) => dispatch({ type: 'voice/wakeWord', payload: e.target.checked })} /><span>Wake word “JARVIS”</span></label>
        </div>
        {isIOS && <p className="mt-2 text-[11px] text-amber-300">On iPhone/iPad, Safari may pause continuous listening when the screen locks. Tap Start talking for each turn if needed.</p>}
        {error && <div className="mt-3 rounded-lg border border-red-400/20 bg-red-500/10 p-3 text-sm text-red-200">{error}</div>}
      </div>

      <div className="grid gap-4 lg:grid-cols-[minmax(0,420px)_minmax(0,1fr)]">
        <div className="glass rounded-2xl p-4 sm:p-6 flex flex-col items-center justify-center gap-4 min-h-[360px] sm:min-h-[440px]">
          <div className={`relative h-40 w-40 sm:h-52 sm:w-52 rounded-full bg-gradient-to-br ${orbColor} border-4 flex items-center justify-center transition-all ${state === 'listening' ? 'animate-pulse' : ''}`}>
            {(state === 'listening' || state === 'speaking') && <div className="absolute inset-[-10px] rounded-full border border-white/10 animate-ping" />}
            <div className="text-center px-4">
              <div className="text-[11px] uppercase tracking-[0.25em] text-white/70">{state}</div>
              <div className="mt-2 text-sm sm:text-base text-white/90">{ORB_STATES[state]}</div>
            </div>
          </div>

          <div className="w-full max-w-md rounded-xl border border-[var(--border-soft)] bg-black/20 px-4 py-3 min-h-[72px]">
            <div className="text-[11px] uppercase tracking-wide text-[var(--muted)]">{interim ? 'Hearing now' : 'Last response'}</div>
            <div className="mt-1 text-sm text-slate-200 leading-relaxed">
              {interim ? `“${interim}”` : (lastAssistant || 'Say “Find Python backend jobs in Hyderabad” or ask anything.')}
            </div>
          </div>

          <div className="grid w-full max-w-md grid-cols-2 gap-2 sm:flex sm:flex-wrap sm:justify-center">
            <button onClick={toggleListening}
              className={`col-span-2 sm:col-span-1 px-5 py-3 rounded-full border text-sm inline-flex items-center justify-center gap-2 ${state === 'listening' ? 'border-red-400/50 bg-red-500/15 text-red-200' : 'border-cyan-400/40 bg-cyan-500/10 text-cyan-100 hover:bg-cyan-500/20'}`}>
              {state === 'listening' ? <MicOff size={16}/> : <Mic size={16}/>}
              {state === 'listening' ? 'Stop listening' : 'Start talking'}
            </button>
            <button onClick={stopSpeaking} className="px-4 py-3 rounded-full border border-[var(--border-soft)] text-[var(--muted)] hover:text-cyan-200 inline-flex items-center justify-center gap-2"><Square size={14}/> Stop</button>
            <button onClick={() => speak(turns[turns.length - 1]?.assistant || '')} disabled={!turns.length} className="px-4 py-3 rounded-full border border-[var(--border-soft)] text-[var(--muted)] hover:text-cyan-200 disabled:opacity-40 inline-flex items-center justify-center gap-2"><Volume2 size={14}/> Repeat</button>
            {turns.length > 0 && <button onClick={() => dispatch({ type: 'voice/clear' })} className="col-span-2 sm:col-span-1 px-4 py-3 rounded-full border border-[var(--border-soft)] text-[var(--muted)] hover:text-red-300 inline-flex items-center justify-center gap-2"><Trash2 size={14}/> Clear</button>}
          </div>
          <div className="text-[11px] text-[var(--muted)] text-center">Tip: speak, pause briefly, and JARVIS will reply. Interrupt by speaking while it talks.</div>
        </div>

        <div className="glass rounded-2xl p-4 flex flex-col min-h-[360px] sm:min-h-[440px]">
          <div className="flex items-center justify-between gap-2 mb-3">
            <div className="text-sm text-cyan-200">Conversation</div>
            <div className="text-[11px] text-[var(--muted)]">{turns.length} turn{turns.length === 1 ? '' : 's'}</div>
          </div>
          <div className="flex-1 space-y-3 overflow-auto pr-1">
            {turns.length === 0 && <div className="rounded-xl border border-dashed border-[var(--border-soft)] p-4 text-sm text-[var(--muted)]">Try: “Find Python backend jobs in Hyderabad”, “Show my top job matches”, or “Show pending tasks”.</div>}
            {turns.map((t) => (
              <div key={t.id} className="space-y-2">
                <div className="flex justify-end"><div className="max-w-[85%] rounded-2xl rounded-br-md bg-cyan-500/15 border border-cyan-400/20 px-3 py-2 text-sm text-cyan-50">{t.user}</div></div>
                <div className="flex justify-start">
                  <div className="max-w-[90%] rounded-2xl rounded-bl-md bg-black/25 border border-[var(--border-soft)] px-3 py-2 text-sm text-slate-200">
                    {t.assistant || <span className="text-[var(--muted)]">Thinking...</span>}
                    {t.needsApproval && <div className="mt-2 text-[11px] text-amber-300">Needs your approval in Approvals.</div>}
                  </div>
                </div>
              </div>
            ))}
          </div>
          <div className="mt-3 flex gap-2 border-t border-[var(--border-soft)] pt-3">
            <input value={textInput} onChange={(e) => setTextInput(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter') sendText() }}
              placeholder="Type a message..."
              className="flex-1 px-3 py-2.5 rounded-xl text-sm bg-black/20 border border-[var(--border-soft)]" />
            <button onClick={sendText} className="px-4 py-2.5 rounded-xl border border-cyan-400/30 text-cyan-200 inline-flex items-center gap-1 hover:bg-cyan-500/10"><Send size={14}/> Send</button>
          </div>
        </div>
      </div>
    </div>
  )
}
