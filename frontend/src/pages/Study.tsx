import { useState } from 'react'
import { api } from '../services/api'
import { useApi } from '../hooks/useApi'
import { Badge, Button, Card, Empty, ErrorBox, Loading } from '../components/ui'

type StudyStart = {
  exam: string
  plan: { topic: string; section: string; status: string }[]
  focus_topic: string | null
  teaching: { ok: boolean; response?: string; error?: string; elapsed?: number } | null
}
type Question = { topic: string; question: string; options: string[] }
type AnswerResult = { correct: boolean; correct_option: string; explanation: string; message: string }

export default function Study() {
  const exams = useApi<{ exams: string[] }>('/study/exams')
  const progress = useApi<Record<string, unknown>>('/study/progress')
  const [exam, setExam] = useState('SSC CGL')
  const [session, setSession] = useState<StudyStart | null>(null)
  const [question, setQuestion] = useState<Question | null>(null)
  const [result, setResult] = useState<AnswerResult | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function start() {
    setBusy(true); setError(null); setResult(null); setQuestion(null)
    try {
      const res = await api.post<StudyStart>('/study/start', { exam })
      setSession(res)
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setBusy(false)
    }
  }

  async function loadQuestion(topic: string) {
    setBusy(true); setError(null); setResult(null)
    try {
      const res = await api.get<Question & { error?: string }>(`/study/question?topic=${encodeURIComponent(topic)}`)
      if (res.error) setError(res.error)
      else setQuestion(res)
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setBusy(false)
    }
  }

  async function answer(choice: string) {
    if (!question) return
    setBusy(true)
    try {
      const res = await api.post<AnswerResult>('/study/answer', { exam, topic: question.topic, answer: choice })
      setResult(res)
      progress.reload()
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setBusy(false)
    }
  }

  const weak = (progress.data?.weak_topics ?? []) as { topic: string; mastery: number; attempts: number }[]
  const accuracy = progress.data?.accuracy as number | undefined

  return (
    <div className="space-y-4">
      <Card title="Start preparation">
        <div className="flex flex-wrap items-center gap-2">
          <select
            value={exam}
            onChange={(e) => setExam(e.target.value)}
            className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-200"
          >
            {(exams.data?.exams ?? ['SSC CGL']).map((e) => (
              <option key={e} value={e}>{e}</option>
            ))}
          </select>
          <Button onClick={start} disabled={busy}>{busy ? 'Preparing...' : "Start today's plan"}</Button>
          {accuracy !== undefined && <Badge tone={accuracy >= 60 ? 'green' : 'amber'}>accuracy {accuracy}%</Badge>}
        </div>
        {error && <div className="mt-2"><ErrorBox error={error} /></div>}
      </Card>

      {session && (
        <Card title={`Today's plan - ${session.exam}`}>
          <ul className="mb-3 space-y-1">
            {session.plan.map((p, i) => (
              <li key={i} className="flex items-center justify-between text-sm">
                <span>{p.topic} <span className="text-xs text-slate-500">({p.section})</span></span>
                <Button variant="secondary" onClick={() => loadQuestion(p.topic)} disabled={busy}>Practise</Button>
              </li>
            ))}
          </ul>
          {session.teaching?.ok && (
            <div className="rounded-lg border border-slate-800 bg-slate-950 p-3 text-sm whitespace-pre-wrap text-slate-300">
              {session.teaching.response}
            </div>
          )}
          {session.teaching && !session.teaching.ok && <ErrorBox error={session.teaching.error ?? 'teaching failed'} />}
        </Card>
      )}

      {question && (
        <Card title={`Practice - ${question.topic}`}>
          <p className="mb-3 text-sm">{question.question}</p>
          <div className="grid gap-2 sm:grid-cols-2">
            {question.options.map((opt, i) => (
              <Button key={i} variant="secondary" onClick={() => answer(String.fromCharCode(65 + i))} disabled={busy}>
                {String.fromCharCode(65 + i)}. {opt}
              </Button>
            ))}
          </div>
          {result && (
            <div className={`mt-3 rounded-lg border p-3 text-sm ${result.correct ? 'border-emerald-700 bg-emerald-950/40 text-emerald-200' : 'border-red-800 bg-red-950/40 text-red-200'}`}>
              <div className="font-medium">{result.message} (correct answer: {result.correct_option})</div>
              <div className="mt-1 text-slate-300">{result.explanation}</div>
            </div>
          )}
        </Card>
      )}

      <Card title="Weak topics">
        {progress.loading && <Loading />}
        {!progress.loading && !weak.length && <Empty label="Practise some questions to see weak topics" />}
        <ul className="space-y-1">
          {weak.map((w, i) => (
            <li key={i} className="flex items-center justify-between text-sm">
              <span>{w.topic}</span>
              <Badge tone={w.mastery < 40 ? 'red' : 'amber'}>mastery {w.mastery}% ({w.attempts} attempts)</Badge>
            </li>
          ))}
        </ul>
      </Card>
    </div>
  )
}
