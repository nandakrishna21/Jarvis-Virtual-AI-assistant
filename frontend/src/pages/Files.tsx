import { useState } from 'react'
import { api, type FileItem } from '../services/api'
import { useApi } from '../hooks/useApi'
import { Button, Card, Empty, ErrorBox, Loading } from '../components/ui'

type FileList = { root: string; count: number; files: FileItem[]; error?: string }

export default function Files() {
  const [subdir, setSubdir] = useState('docs')
  const listing = useApi<FileList>(`/files?subdir=${encodeURIComponent(subdir)}&limit=200`)
  const [selected, setSelected] = useState<string | null>(null)
  const [content, setContent] = useState<string>('')
  const [summary, setSummary] = useState<string>('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function open(path: string) {
    setSelected(path); setContent(''); setSummary(''); setError(null); setBusy(true)
    try {
      const res = await api.get<{ content?: string; text?: string; error?: string }>(`/files/read?path=${encodeURIComponent(path)}`)
      if (res.error) setError(res.error)
      else setContent(res.content ?? res.text ?? '')
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setBusy(false)
    }
  }

  async function summarise(path: string) {
    setBusy(true); setError(null)
    try {
      const res = await api.post<{ summary: { ok: boolean; response?: string; error?: string } }>(
        '/files/summarize',
        { path },
      )
      if (res.summary.ok) setSummary(res.summary.response ?? '')
      else setError(res.summary.error ?? 'summary failed')
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setBusy(false)
    }
  }

  const files = listing.data?.files ?? []
  const dirs = files.filter((f) => f.is_dir)
  const plain = files.filter((f) => !f.is_dir)

  return (
    <div className="space-y-4">
      <Card title="Browse files">
        <div className="flex flex-wrap gap-2">
          <input
            value={subdir}
            onChange={(e) => setSubdir(e.target.value)}
            placeholder="subfolder, e.g. docs or backend"
            className="flex-1 rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-100 outline-none focus:border-sky-500"
          />
          <Button onClick={() => listing.reload()} disabled={listing.loading}>Browse</Button>
        </div>
        <p className="mt-2 text-xs text-slate-500">
          Access is restricted to C:\JARVIS. Files outside this folder are refused. Nothing is ever deleted or moved.
        </p>
        {listing.error && <div className="mt-2"><ErrorBox error={listing.error} /></div>}
        {listing.loading && <Loading />}
        {dirs.length > 0 && (
          <div className="mt-3 flex flex-wrap gap-2">
            {dirs.map((d) => (
              <button
                key={d.path}
                onClick={() => setSubdir(d.path)}
                className="rounded-full border border-slate-700 px-3 py-1 text-xs text-slate-400 hover:border-sky-600 hover:text-sky-300"
              >
                {d.path}
              </button>
            ))}
          </div>
        )}
        <ul className="mt-3 space-y-1">
          {plain.map((f) => (
            <li key={f.path} className="flex items-center justify-between rounded-lg border border-slate-800 px-3 py-1.5 text-sm">
              <span className="truncate">{f.path}</span>
              <div className="flex items-center gap-2">
                <span className="text-xs text-slate-500">{Math.round(f.size / 1024)} KB</span>
                <Button variant="secondary" onClick={() => open(f.path)} disabled={busy}>Open</Button>
                <Button variant="secondary" onClick={() => summarise(f.path)} disabled={busy}>Summarise</Button>
              </div>
            </li>
          ))}
        </ul>
        {!listing.loading && !files.length && <Empty label="No files found in this folder" />}
      </Card>

      {selected && (
        <Card title={`Preview - ${selected}`}>
          {busy && <Loading />}
          {error && <ErrorBox error={error} />}
          {!busy && content && (
            <pre className="max-h-96 overflow-auto whitespace-pre-wrap rounded-lg border border-slate-800 bg-slate-950 p-3 text-xs text-slate-300">
              {content.slice(0, 20000)}
            </pre>
          )}
        </Card>
      )}

      {summary && (
        <Card title="AI summary">
          <div className="whitespace-pre-wrap text-sm text-slate-300">{summary}</div>
        </Card>
      )}
    </div>
  )
}
