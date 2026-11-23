import { useEffect, useRef, useState } from 'react'
import { api } from '../services/api'
import { useAppDispatch, useAppSelector } from '../store/hooks'
import { Mic, MicOff, Volume2, Square, Send, Sparkles, Radio, Trash2 } from 'lucide-react'

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
      if (!synth || !text) { resolve(); return }
      synth.cancel()
      const utter = new SpeechSynthesisUtterance(text)
      utter.rate = 1.03
      utter.pitch = 1.0
      if (voiceURI.current) {
        utter.voice = window.speechSynthesis.getVoices().find(v => v.voiceURI === voiceURI.current) || null
      }
      speakingRef.current = true
      dispatch({ type: 'voice/status', payload: 'speaking' })
      const done = () => {
        speakingRef.current = false
        dispatch({ type: 'voice/status', payload: 'idle' })
        if (shouldListenRef.current && continuousRef.current) {
          try { recognitionRef.current?.start() } catch { /* already running */ }
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
    dispatch({ type: 'voice/status', payload: 'thinking' })
    try {
      const history = turns.slice(-5).map(t => ({ user: t.user, assistant: t.assistant }))
      const res = await api.post<any>('/voice/agent', { message: clean, history })
      const reply = res?.spoken || res?.reply || res?.error || ''
      dispatch({
        type: 'voice/turnEnd',
        payload: { id, assistant: reply, intent: res?.intent, needsApproval: !!res?.requires_approval },
      })
      if (res?.error && !res?.reply) dispatch({ type: 'voice/error', payload: res.error })
      await speak(reply)
    } catch (e: any) {
      dispatch({ type: 'voice/error', payload: e?.message || 'Voice agent failed' })
      dispatch({ type: 'voice/status', payload: 'idle' })
    }
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
    rec.continuous = true
    rec.interimResults = true
    rec.lang = 'en-US'
    rec.onresult = (event: any) => {
      let finalText = ''
      let interimText = ''
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const transcript = event.results[i][0].transcript
        if (event.results[i].isFinal) finalText += transcript
        else interimText += transcript
      }
      dispatch({ type: 'voice/interim', payload: interimText })
      if (interimText && speakingRef.current) {
        window.speechSynthesis?.cancel()
        speakingRef.current = false
        dispatch({ type: 'voice/status', payload: 'listening' })
      }
      if (finalText.trim()) {
        dispatch({ type: 'voice/interim', payload: '' })
        if (wakeWordRef.current) {
          const lower = finalText.toLowerCase()
          if (!lower.includes('jarvis')) return
          const stripped = lower.replace(/^.*?jarvis\s*/, '')
          ask(stripped || finalText)
          return
        }
        ask(finalText)
      }
    }
    rec.onerror = (e: any) => {
      if (e?.error === 'not-allowed') dispatch({ type: 'voice/error', payload: 'Microphone permission denied. Allow it in your browser and try again.' })
      if (e?.error === 'no-speech' || e?.error === 'aborted') return
      dispatch({ type: 'voice/error', payload: `Speech recognition error: ${e?.error}` })
    }
    rec.onend = () => {
      if (shouldListenRef.current && continuousRef.current && !speakingRef.current) {
        try { rec.start() } catch { /* already running */ }
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
    state === 'listening' ? 'from-red-500/60 to-rose-500/30 border-red-400/60'
    : state === 'thinking' ? 'from-amber-400/50 to-orange-500/20 border-amber-300/60'
    : state === 'speaking' ? 'from-cyan-400/60 to-sky-500/20 border-cyan-300/60'
    : 'from-cyan-500/30 to-blue-600/10 border-cyan-400/30'

  return (
    <div className="space-y-4">
      <div className="glass-strong rounded-2xl p-4 sm:p-5">
        <div className="flex items-center gap-2 text-cyan-100"><Radio size={18}/><h1 className="text-lg font-semibold">Voice Agent</h1></div>
        <p className="text-sm text-[var(--muted)] mt-1">Talk to JARVIS like a person. Speak, it answers out loud, then it listens again - so you stay in one conversation instead of pressing buttons.</p>
        <div className="mt-3 flex flex-wrap items-center gap-4 text-xs text-[var(--muted)]">
          <label className="flex items-center gap-2 cursor-pointer">
            <input type="checkbox" checked={continuous}
              onChange={(e) => dispatch({ type: 'voice/continuous', payload: e.target.checked })} />
            <span>Keep the conversation going</span>
          </label>
          <label className="flex items-center gap-2 cursor-pointer">
            <input type="checkbox" checked={wakeWord}
              onChange={(e) => dispatch({ type: 'voice/wakeWord', payload: e.target.checked })} />
            <span>Only answer when I say “JARVIS”</span>
          </label>
        </div>
        {isIOS && (
          <p className="mt-2 text-[11px] text-amber-300">
            On iPhone/iPad, tap “Start talking” for each turn. Safari pauses continuous listening when the screen locks or the tab is hidden.
          </p>
        )}
        {error && <div className="mt-3 text-sm text-red-300">{error}</div>}
      </div>

      <div className="glass rounded-2xl p-4 sm:p-6 flex flex-col items-center gap-4">
        <div className={`relative h-36 w-36 sm:h-40 sm:w-40 rounded-full bg-gradient-to-br ${orbColor} border-4 flex items-center justify-center transition-all ${state === 'listening' ? 'animate-pulse' : ''}`}>
          <div className="text-center px-4">
            <div className="text-[11px] uppercase tracking-widest text-white/70">{state}</div>
            <div className="text-xs text-white/80 mt-1">{ORB_STATES[state]}</div>
          </div>
        </div>

        <div className="flex flex-wrap items-center justify-center gap-2">
          <button onClick={toggleListening}
            className={`px-5 py-3 rounded-full border text-sm inline-flex items-center gap-2 ${state === 'listening' ? 'border-red-400/50 bg-red-500/15 text-red-200' : 'border-cyan-400/40 bg-cyan-500/10 text-cyan-100 hover:bg-cyan-500/20'}`}>
            {state === 'listening' ? <MicOff size={16}/> : <Mic size={16}/>}
            {state === 'listening' ? 'Stop listening' : 'Start talking'}
          </button>
          <button onClick={stopSpeaking} className="px-4 py-3 rounded-full border border-[var(--border-soft)] text-[var(--muted)] hover:text-cyan-200 inline-flex items-center gap-2"><Square size={14}/> <span className="hidden sm:inline">Stop speaking</span></button>
          <button onClick={() => speak(turns[turns.length - 1]?.assistant || '')} disabled={!turns.length} className="px-4 py-3 rounded-full border border-[var(--border-soft)] text-[var(--muted)] hover:text-cyan-200 inline-flex items-center gap-2"><Volume2 size={14}/> <span className="hidden sm:inline">Repeat</span></button>
          {turns.length > 0 && <button onClick={() => dispatch({ type: 'voice/clear' })} className="px-4 py-3 rounded-full border border-[var(--border-soft)] text-[var(--muted)] hover:text-red-300 inline-flex items-center gap-2"><Trash2 size={14}/> <span className="hidden sm:inline">Clear</span></button>}
        </div>

        {interim && <div className="text-sm text-slate-400 italic text-center">“{interim}”</div>}
        {state === 'listening' && continuous && <div className="text-xs text-[var(--muted)] text-center">Listening - JARVIS will answer automatically, then listen again.</div>}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="glass rounded-2xl p-4">
          <div className="text-sm text-cyan-200 mb-3">Conversation</div>
          <div className="space-y-3 max-h-[26rem] overflow-auto">
            {turns.length === 0 && <div className="text-sm text-[var(--muted)]">Say something like “Find Python backend jobs in India” or “Show my pending tasks”.</div>}
            {turns.map((t) => (
              <div key={t.id} className="space-y-1">
                <div className="text-xs text-cyan-300">You: {t.user}</div>
                <div className="text-sm text-slate-200 bg-black/20 rounded p-2 border border-[var(--border-soft)]">
                  {t.assistant || <span className="text-[var(--muted)]">thinking...</span>}
                  {t.needsApproval && <div className="mt-1 text-[11px] text-amber-300">Waiting for your approval in the Approvals panel.</div>}
                  {t.intent && <div className="mt-1 text-[10px] text-[var(--muted)]">intent: {t.intent}</div>}
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="space-y-4">
          <div className="glass rounded-2xl p-4">
            <div className="text-sm text-cyan-200 mb-2">Type instead</div>
            <div className="flex gap-2">
              <input value={textInput} onChange={(e) => setTextInput(e.target.value)}
                onKeyDown={(e) => { if (e.key === 'Enter') sendText() }}
                placeholder="Ask JARVIS anything..."
                className="flex-1 px-3 py-2 rounded-lg text-sm bg-black/20 border border-[var(--border-soft)]" />
              <button onClick={sendText} className="px-3 py-2 rounded-lg border border-cyan-400/30 text-cyan-200 inline-flex items-center gap-1"><Send size={14}/></button>
            </div>
          </div>
          <div className="glass rounded-2xl p-4">
            <div className="text-sm text-cyan-200 mb-2 inline-flex items-center gap-1.5"><Sparkles size={13}/> Try saying</div>
            <ul className="text-xs text-[var(--muted)] space-y-1">
              <li>“Find Python backend developer jobs in India”</li>
              <li>“Show my pending tasks”</li>
              <li>“Show today's hiring news”</li>
              <li>“What are my top job matches”</li>
              <li>“Read my latest recruiter email”</li>
              <li>“Show pending approvals”</li>
            </ul>
            <div className="text-[11px] text-[var(--muted)] mt-3">Voice never bypasses approvals - sending an email, preparing an application or generating a document still needs your click.</div>
          </div>
        </div>
      </div>
    </div>
  )
}
