import { useState } from 'react'
import { api, type ChatResponse } from '../services/api'
import { Button, Card, ErrorBox, Input } from '../components/ui'

type Message = { role: 'user' | 'jarvis'; text: string; meta?: string }

const suggestions = [
  'Find Python Backend Developer jobs in India',
  'Show my pending tasks',
  'Start my SSC CGL preparation',
  "Show today's hiring news",
  'Explain this Python code',
]

export default function Chat() {
  const [messages, setMessages] = useState<Message[]>([
    { role: 'jarvis', text: 'I am JARVIS, your local assistant. Ask me about jobs, email, study, tasks or code.' },
  ])
  const [input, setInput] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function send(text: string) {
    if (!text.trim() || busy) return
    const question = text.trim()
    setMessages((m) => [...m, { role: 'user', text: question }])
    setInput('')
    setBusy(true)
    setError(null)
    try {
      const res = await api.post<ChatResponse>('/chat', { message: question })
      if (!res.ok) {
        setError(res.error ?? 'Unknown error')
        setMessages((m) => [...m, { role: 'jarvis', text: res.hint ?? res.error ?? 'Request failed.' }])
      } else {
        const meta = res.elapsed ? `${res.elapsed}s · ${res.tokens_per_second ?? 0} tok/s` : undefined
        setMessages((m) => [...m, { role: 'jarvis', text: res.response ?? '', meta }])
      }
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="space-y-4">
      <Card title="AI Chat">
        <div className="space-y-3">
          {messages.map((m, i) => (
            <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div
                className={`max-w-[85%] rounded-xl px-3 py-2 text-sm whitespace-pre-wrap ${
                  m.role === 'user' ? 'bg-sky-700 text-white' : 'border border-slate-800 bg-slate-900 text-slate-200'
                }`}
              >
                {m.text}
                {m.meta && <div className="mt-1 text-[10px] text-slate-500">{m.meta}</div>}
              </div>
            </div>
          ))}
          {busy && <div className="text-xs text-slate-500">JARVIS is thinking (local model)...</div>}
          {error && <ErrorBox error={error} />}
        </div>

        <div className="mt-4 flex gap-2">
          <Input value={input} onChange={setInput} placeholder="Ask JARVIS..." />
          <Button onClick={() => send(input)} disabled={busy}>
            Send
          </Button>
        </div>

        <div className="mt-3 flex flex-wrap gap-2">
          {suggestions.map((s) => (
            <button
              key={s}
              onClick={() => send(s)}
              className="rounded-full border border-slate-700 px-3 py-1 text-xs text-slate-400 hover:border-sky-600 hover:text-sky-300"
            >
              {s}
            </button>
          ))}
        </div>
      </Card>
    </div>
  )
}
