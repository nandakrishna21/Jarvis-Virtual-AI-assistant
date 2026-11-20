import { useState } from 'react'
import { api, type NewsItem } from '../services/api'
import { useApi } from '../hooks/useApi'
import { Badge, Button, Card, Empty, ErrorBox, Loading } from '../components/ui'

export default function News() {
  const news = useApi<NewsItem[]>('/hiring-news?limit=50')
  const [currentOnly, setCurrentOnly] = useState(true)
  const [busy, setBusy] = useState(false)
  const [notice, setNotice] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  async function fetch() {
    setBusy(true); setError(null); setNotice(null)
    try {
      const res = await api.post<{ inserted: number; updated: number; skipped: number; source_errors: string[] }>(
        '/hiring-news/fetch',
      )
      setNotice(`Inserted ${res.inserted}, updated ${res.updated}, skipped ${res.skipped}.`)
      if (res.source_errors.length) setError(`Source issues: ${res.source_errors.join(' | ')}`)
      news.reload()
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setBusy(false)
    }
  }

  const list = currentOnly ? (news.data ?? []).filter((n) => n.is_current) : (news.data ?? [])

  return (
    <div className="space-y-4">
      <Card title="Hiring news">
        <div className="flex flex-wrap items-center gap-3">
          <Button onClick={fetch} disabled={busy}>{busy ? 'Fetching...' : 'Fetch latest'}</Button>
          <label className="flex items-center gap-2 text-xs text-slate-400">
            <input type="checkbox" checked={currentOnly} onChange={(e) => setCurrentOnly(e.target.checked)} />
            only recent (within 45 days)
          </label>
        </div>
        {notice && <p className="mt-2 text-xs text-emerald-300">{notice}</p>}
        {error && <div className="mt-2"><ErrorBox error={error} /></div>}
      </Card>

      <Card title="Announcements">
        {news.error && <ErrorBox error={news.error} />}
        {news.loading && <Loading />}
        {!news.loading && !list.length && <Empty label="No hiring announcements stored yet" />}
        <ul className="space-y-2">
          {list.map((n) => (
            <li key={n.id} className="rounded-lg border border-slate-800 px-3 py-2">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <span className="text-sm">{n.title}</span>
                <div className="flex gap-2">
                  <Badge tone="blue">relevance {n.relevance}</Badge>
                  <Badge tone={n.is_current ? 'green' : 'amber'}>{n.is_current ? 'recent' : 'older'}</Badge>
                </div>
              </div>
              <div className="mt-1 text-xs text-slate-500">
                {n.company ?? 'Company not published'} · {n.role ?? 'Role not published'} · {n.location ?? 'Location not published'}
                {n.experience ? ` · ${n.experience}` : ''} {n.salary ? ` · ${n.salary}` : ''}
                {n.posting_date ? ` · posted ${n.posting_date}` : ''}
              </div>
              <div className="mt-1 text-xs text-slate-600">source: {n.source ?? 'n/a'}</div>
              {n.application_url && (
                <a href={n.application_url} target="_blank" rel="noreferrer" className="mt-1 inline-block text-xs text-sky-300 hover:underline">
                  Application link
                </a>
              )}
            </li>
          ))}
        </ul>
      </Card>
    </div>
  )
}
