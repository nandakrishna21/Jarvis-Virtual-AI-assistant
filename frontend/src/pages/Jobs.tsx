import { useState } from 'react'
import { api, type Job } from '../services/api'
import { useApi } from '../hooks/useApi'
import { Badge, Button, Card, Empty, ErrorBox, Input, Loading } from '../components/ui'

type SearchResult = Job & { score?: number; matching_skills?: string[]; missing_skills?: string[]; location_note?: string; verified?: string }

export default function Jobs() {
  const stored = useApi<Job[]>('/jobs')
  const [query, setQuery] = useState('Python Backend Developer')
  const [location, setLocation] = useState('India')
  const [results, setResults] = useState<SearchResult[]>([])
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function search() {
    setBusy(true)
    setError(null)
    try {
      const res = await api.post<SearchResult[]>('/jobs/search', { query, location })
      setResults(res)
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setBusy(false)
    }
  }

  async function prepare(jobId: number) {
    setBusy(true)
    setError(null)
    try {
      const res = await api.post<{ application_id: number; approval_id: number; warning: string }>(
        '/applications/prepare',
        { job_id: jobId },
      )
      setError(`Application #${res.application_id} prepared for review (approval #${res.approval_id}). ${res.warning}`)
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="space-y-4">
      <Card title="Search jobs">
        <div className="grid gap-2 md:grid-cols-3">
          <Input value={query} onChange={setQuery} placeholder="Role, e.g. Python Backend Developer" />
          <Input value={location} onChange={setLocation} placeholder="Location, e.g. India / Remote" />
          <Button onClick={search} disabled={busy}>
            {busy ? 'Searching...' : 'Search'}
          </Button>
        </div>
        <p className="mt-2 text-xs text-slate-500">
          Uses permitted public sources only. Results are unverified until you open the original link. JARVIS never applies automatically.
        </p>
        {error && <div className="mt-2"><ErrorBox error={error} /></div>}
      </Card>

      {results.length > 0 && (
        <Card title="Top matches">
          <ul className="space-y-3">
            {results.map((j, i) => (
              <li key={i} className="rounded-lg border border-slate-800 p-3">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="font-medium">{j.title}</span>
                  <div className="flex gap-2">
                    <Badge tone="blue">{j.score ?? 0}% match</Badge>
                    <Badge tone={j.verified === 'verified' ? 'green' : 'amber'}>{j.verified ?? 'unverified'}</Badge>
                  </div>
                </div>
                <div className="mt-1 text-sm text-slate-400">
                  {j.company ?? 'Company not published'} · {j.location ?? 'Location not published'} · source: {j.source ?? 'n/a'}
                </div>
                {j.matching_skills && j.matching_skills.length > 0 && (
                  <div className="mt-2 text-xs text-emerald-300">Matching: {j.matching_skills.join(', ')}</div>
                )}
                {j.missing_skills && j.missing_skills.length > 0 && (
                  <div className="text-xs text-amber-300">Missing: {j.missing_skills.join(', ')}</div>
                )}
                <div className="mt-2 flex flex-wrap gap-2">
                  <a href={j.url} target="_blank" rel="noreferrer">
                    <Button variant="secondary">Open original link</Button>
                  </a>
                  <Button variant="secondary" onClick={() => prepare(j.url ? Number(j.id) : 0)} disabled={busy || !j.id}>
                    Prepare application
                  </Button>
                </div>
              </li>
            ))}
          </ul>
        </Card>
      )}

      <Card title="Stored jobs">
        {stored.error && <ErrorBox error={stored.error} />}
        {stored.loading && <Loading />}
        {!stored.loading && !stored.data?.length && <Empty label="No jobs stored yet" />}
        <ul className="space-y-2">
          {stored.data?.map((j) => (
            <li key={j.id} className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-slate-800 px-3 py-2">
              <div className="min-w-0">
                <div className="truncate text-sm">{j.title}</div>
                <div className="text-xs text-slate-500">{j.company ?? 'Company not published'} · {j.source ?? 'n/a'}</div>
              </div>
              <div className="flex gap-2">
                <Badge tone={j.verified === 'verified' ? 'green' : 'amber'}>{j.verified ?? 'unverified'}</Badge>
                <a href={j.url} target="_blank" rel="noreferrer" className="text-xs text-sky-300 hover:underline">Open</a>
                <Button variant="secondary" onClick={() => prepare(j.id)} disabled={busy}>Prepare application</Button>
              </div>
            </li>
          ))}
        </ul>
      </Card>
    </div>
  )
}
