import { useEffect, useRef, useState } from 'react'
import { api, type ChatResponse } from '../services/api'
import { useApi } from '../hooks/useApi'
import { Badge, Button, Card, ErrorBox, Input, Loading } from '../components/ui'

type VoiceStatus = {
  stt_available: boolean
  stt_loaded: boolean
  stt_loading: boolean
  stt_engine: string
  whisper_model: string
  model_load_seconds: number
  tts_available: boolean
  tts_engine: string
  error?: string | null
}

type Transcript = { text: string; elapsed?: number; duration?: number }

export default function Voice() {
  const status = useApi<VoiceStatus>('/voice/status')
  const [listening, setListening] = useState(false)
  const [recording, setRecording] = useState(false)
  const [transcript, setTranscript] = useState<Transcript | null>(null)
  const [reply, setReply] = useState('')
  const [textInput, setTextInput] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [micError, setMicError] = useState<string | null>(null)

  const mediaRecorder = useRef<MediaRecorder | null>(null)
  const chunks = useRef<Blob[]>([])

  useEffect(() => {
    return () => {
      if (mediaRecorder.current?.state === 'recording') mediaRecorder.current.stop()
    }
  }, [])

  async function startRecording() {
    setMicError(null)
    if (!navigator.mediaDevices?.getUserMedia) {
      setMicError('This browser does not support microphone capture.')
      return
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const recorder = new MediaRecorder(stream)
      chunks.current = []
      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunks.current.push(e.data)
      }
      recorder.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop())
        setRecording(false)
        setListening(false)
        const blob = new Blob(chunks.current, { type: recorder.mimeType || 'audio/webm' })
        if (blob.size === 0) {
          setError('No audio captured.')
          return
        }
        setBusy(true)
        setError(null)
        try {
          const form = new FormData()
          form.append('audio', blob, 'clip.webm')
          const res = await fetch('/api/voice/transcribe', { method: 'POST', body: form })
          const data = await res.json()
          if (data.error) setError(`${data.error}${data.hint ? ` - ${data.hint}` : ''}`)
          else {
            setTranscript(data)
            if (data.text) await ask(data.text)
          }
        } catch (e) {
          setError((e as Error).message)
        } finally {
          setBusy(false)
        }
      }
      recorder.start()
      mediaRecorder.current = recorder
      setRecording(true)
      setListening(true)
    } catch (e) {
      setMicError(
        `Microphone blocked or unavailable: ${(e as Error).message}. ` +
          'Allow microphone access for this site in your browser, then try again.',
      )
      setListening(false)
    }
  }

  function stopRecording() {
    if (mediaRecorder.current?.state === 'recording') mediaRecorder.current.stop()
  }

  async function ask(text: string) {
    setBusy(true)
    setError(null)
    try {
      const res = await api.post<ChatResponse>('/chat', { message: text })
      const answer = res.response ?? res.error ?? ''
      setReply(answer)
      speak(answer)
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setBusy(false)
    }
  }

  function speak(text: string) {
    if (!text) return
    const synth = window.speechSynthesis
    if (!synth) return
    synth.cancel()
    const utter = new SpeechSynthesisUtterance(text)
    utter.rate = 1.05
    synth.speak(utter)
  }

  async function sendText() {
    if (!textInput.trim()) return
    const t = textInput.trim()
    setTextInput('')
    setTranscript({ text: t })
    await ask(t)
  }

  return (
    <div className="space-y-4">
      <Card title="Voice status">
        <div className="flex flex-wrap items-center gap-2">
          <Badge tone={listening ? 'red' : 'slate'}>
            {listening ? 'MICROPHONE ACTIVE' : 'Microphone off'}
          </Badge>
          {recording && <Badge tone="amber">recording</Badge>}
          <Badge tone={status.data?.stt_loaded ? 'green' : 'slate'}>
            STT: {status.data?.stt_loaded ? 'model loaded' : 'loads on first use'}
          </Badge>
          <Badge tone={status.data?.tts_available ? 'green' : 'amber'}>TTS: {status.data?.tts_available ? 'ready' : 'unavailable'}</Badge>
          {status.data?.stt_loading && <Badge tone="amber">loading Whisper model...</Badge>}
        </div>
        <p className="mt-2 text-xs text-slate-500">
          Speech recognition runs locally with faster-whisper ({status.data?.whisper_model ?? 'tiny'}). Replies are spoken by
          your browser voice engine. The microphone is only active while you hold the button - it is never left open.
        </p>
        {status.data?.error && <div className="mt-2"><ErrorBox error={status.data.error} /></div>}
        {micError && <div className="mt-2"><ErrorBox error={micError} /></div>}
      </Card>

      <Card title="Push to talk">
        <div className="flex flex-col items-center gap-3 py-4">
          <button
            onMouseDown={startRecording}
            onMouseUp={stopRecording}
            onMouseLeave={stopRecording}
            onTouchStart={startRecording}
            onTouchEnd={stopRecording}
            disabled={busy}
            className={`flex h-28 w-28 items-center justify-center rounded-full border-4 text-sm font-semibold transition ${
              recording
                ? 'border-red-500 bg-red-600 text-white shadow-lg shadow-red-900/50'
                : 'border-slate-700 bg-slate-800 text-slate-200 hover:border-sky-600 hover:bg-slate-700'
            }`}
          >
            {recording ? 'Release to send' : 'Hold to talk'}
          </button>
          <p className="text-center text-xs text-slate-500">
            Try: "Find Python Backend Developer jobs in India", "Show my pending tasks", "Start my SSC CGL preparation"
          </p>
        </div>
        {busy && <Loading label="Processing locally..." />}
        {error && <div className="mt-2"><ErrorBox error={error} /></div>}
      </Card>

      <Card title="Transcript">
        {transcript ? (
          <div className="text-sm">
            <div className="text-xs text-slate-500">
              you said {transcript.elapsed ? `(${transcript.elapsed}s to transcribe)` : ''}
            </div>
            <div className="mt-1 rounded-lg bg-slate-950 px-3 py-2">{transcript.text}</div>
          </div>
        ) : (
          <p className="text-sm text-slate-500">Nothing captured yet.</p>
        )}
      </Card>

      <Card title="JARVIS reply">
        {reply ? (
          <>
            <div className="whitespace-pre-wrap rounded-lg bg-slate-950 px-3 py-2 text-sm text-slate-200">{reply}</div>
            <div className="mt-2 flex gap-2">
              <Button variant="secondary" onClick={() => speak(reply)}>Speak again</Button>
              <Button variant="secondary" onClick={() => window.speechSynthesis?.cancel()}>Stop speaking</Button>
            </div>
          </>
        ) : (
          <p className="text-sm text-slate-500">No reply yet.</p>
        )}
      </Card>

      <Card title="Type instead">
        <div className="flex gap-2">
          <Input value={textInput} onChange={setTextInput} placeholder="Type a command..." />
          <Button onClick={sendText} disabled={busy || !textInput.trim()}>Send</Button>
        </div>
        <p className="mt-2 text-xs text-slate-500">Voice never bypasses approvals - sending an email or applying still needs your click.</p>
      </Card>
    </div>
  )
}
