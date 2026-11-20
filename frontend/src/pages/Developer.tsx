import { useState } from 'react'
import { api } from '../services/api'
import { useApi } from '../hooks/useApi'
import { Badge, Button, Card, ErrorBox, Loading } from '../components/ui'

type Analysis = {
  language: string
  lines: number
  functions: { name: string; line: number }[]
  classes: { name: string; line: number }[]
  imports: string[]
  issues: { type: string; line?: number; message: string }[]
  dangerous_commands: { pattern: string; line: number; text: string }[]
}
type ProjectInfo = { total_files: number; code_files: number; approx_code_lines: number; top_level: string[] }

export default function Developer() {
  const project = useApi<ProjectInfo>('/developer/project?root=backend')
  const [code, setCode] = useState('def add(a, b):\n    return a + b\n')
  const [analysis, setAnalysis] = useState<Analysis | null>(null)
  const [explanation, setExplanation] = useState<string>('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function analyze() {
    setBusy(true); setError(null)
    try {
      const res = await api.post<Analysis>('/developer/analyze', { code })
      setAnalysis(res)
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setBusy(false)
    }
  }

  async function explain() {
    setBusy(true); setError(null)
    try {
      const res = await api.post<{ explanation: { ok: boolean; response?: string; error?: string } }>(
        '/developer/explain',
        { code },
      )
      if (res.explanation.ok) setExplanation(res.explanation.response ?? '')
      else setError(res.explanation.error ?? 'explanation failed')
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="space-y-4">
      <Card title="Project snapshot (C:\\JARVIS\\backend)">
        {project.error && <ErrorBox error={project.error} />}
        {project.loading && <Loading />}
        {project.data && (
          <div className="grid grid-cols-3 gap-3 text-sm">
            <div><div className="text-xs text-slate-500">Files</div><div className="text-xl font-semibold">{project.data.total_files}</div></div>
            <div><div className="text-xs text-slate-500">Code files</div><div className="text-xl font-semibold">{project.data.code_files}</div></div>
            <div><div className="text-xs text-slate-500">~Code lines</div><div className="text-xl font-semibold">{project.data.approx_code_lines}</div></div>
          </div>
        )}
      </Card>

      <Card title="Analyze / explain code">
        <textarea
          value={code}
          onChange={(e) => setCode(e.target.value)}
          rows={12}
          className="w-full rounded-lg border border-slate-700 bg-slate-950 p-3 font-mono text-xs text-slate-100 outline-none focus:border-sky-500"
        />
        <div className="mt-2 flex gap-2">
          <Button onClick={analyze} disabled={busy}>Analyze</Button>
          <Button variant="secondary" onClick={explain} disabled={busy}>Explain with AI</Button>
        </div>
        {error && <div className="mt-2"><ErrorBox error={error} /></div>}
      </Card>

      {analysis && (
        <Card title="Analysis">
          <div className="mb-3 flex flex-wrap gap-2">
            <Badge>{analysis.language}</Badge>
            <Badge>{analysis.lines} lines</Badge>
            <Badge tone="blue">{analysis.functions.length} functions</Badge>
            <Badge tone="blue">{analysis.classes.length} classes</Badge>
          </div>
          {analysis.functions.length > 0 && (
            <div className="mb-2 text-sm text-slate-400">
              Functions: {analysis.functions.map((f) => `${f.name} (L${f.line})`).join(', ')}
            </div>
          )}
          {analysis.issues.length > 0 && (
            <ul className="space-y-1 text-sm">
              {analysis.issues.map((i, idx) => (
                <li key={idx} className="text-amber-300">
                  [{i.type}] {i.line ? `line ${i.line}: ` : ''}{i.message}
                </li>
              ))}
            </ul>
          )}
          {analysis.dangerous_commands.length > 0 && (
            <div className="mt-2 rounded-lg border border-red-800 bg-red-950/40 p-2 text-sm text-red-300">
              Dangerous patterns detected (reported only, never executed):{' '}
              {analysis.dangerous_commands.map((d) => `L${d.line}: ${d.text}`).join(', ')}
            </div>
          )}
        </Card>
      )}

      {explanation && (
        <Card title="AI explanation">
          <div className="whitespace-pre-wrap text-sm text-slate-300">{explanation}</div>
        </Card>
      )}

      <Card title="Safety note">
        <p className="text-sm text-slate-400">
          JARVIS reads and explains code but never runs shell commands from chat. Destructive commands are flagged, not executed.
        </p>
      </Card>
    </div>
  )
}
