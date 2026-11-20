import { useState } from 'react'
import { api, type EmailItem } from '../services/api'
import { useApi } from '../hooks/useApi'
import { Badge, Button, Card, Empty, ErrorBox, Loading } from '../components/ui'

export default function Emails() {
  const emails = useApi<EmailItem[]>('/emails?limit=50')
  const status = useApi<{ credentials_present: boolean; token_present: boolean }>('/gmail/status')
  const [category, setCategory] = useState<string>('')
  const [notice, setNotice] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  async function fetchEmails() {
    setBusy(true); setError(null); setNotice(null)
    try {
      const res = await api.post<unknown[]>('/emails/fetch', { max_results: 25, query: 'newer_than:14d' })
      setNotice(`Fetched ${res.length} messages.`)
      emails.reload()
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setBusy(false)
    }
  }

  async function draft(id: number) {
    setBusy(true); setError(null); setNotice(null)
    try {
      const res = await api.post<{ draft_id: number; approval_id: number; warning: string }>('/emails/draft', { email_id: id })
      setNotice(`Draft #${res.draft_id} created with approval #${res.approval_id}. ${res.warning}`)
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setBusy(false)
    }
  }

  const list = category ? (emails.data ?? []).filter((e) => e.category === category) : (emails.data ?? [])

  return (
    <div className="space-y-4">
      <Card title="Gmail connection">
        <div className="flex flex-wrap items-center gap-2">
          <Badge tone={status.data?.credentials_present ? 'green' : 'amber'}>
            credentials.json {status.data?.credentials_present ? 'present' : 'missing'}
          </Badge>
          <Badge tone={status.data?.token_present ? 'green' : 'amber'}>
            token {status.data?.token_present ? 'present' : 'missing'}
          </Badge>
          <Button onClick={fetchEmails} disabled={busy}>{busy ? 'Fetching...' : 'Fetch recent emails'}</Button>
        </div>
        <p className="mt-2 text-xs text-slate-500">
          Read-only scope by default. Run <code>python scripts/gmail_auth.py</code> in C:\JARVIS\backend to authenticate.
        </p>
        {notice && <p className="mt-2 text-xs text-emerald-300">{notice}</p>}
        {error && <div className="mt-2"><ErrorBox error={error} /></div>}
      </Card>

      <Card
        title="Inbox"
        action={
          <select
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            className="rounded-lg border border-slate-700 bg-slate-950 px-2 py-1 text-xs text-slate-200"
          >
            <option value="">all</option>
            {['recruiter', 'interview', 'assessment', 'job_alert', 'spam', 'other'].map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
        }
      >
        {emails.error && <ErrorBox error={emails.error} />}
        {emails.loading && <Loading />}
        {!emails.loading && !list.length && <Empty label="No emails stored yet" />}
        <ul className="space-y-2">
          {list.map((e) => (
            <li key={e.id} className="rounded-lg border border-slate-800 px-3 py-2">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <span className="truncate text-sm">{e.subject}</span>
                <Badge tone={['recruiter', 'interview'].includes(e.category) ? 'green' : e.category === 'spam' ? 'red' : 'slate'}>
                  {e.category}
                </Badge>
              </div>
              <div className="text-xs text-slate-500">
                {e.sender} · {e.received_at ?? ''} {e.company ? `· ${e.company}` : ''} {e.job_role ? `· ${e.job_role}` : ''}
              </div>
              {e.snippet && <div className="mt-1 line-clamp-2 text-xs text-slate-400">{e.snippet}</div>}
              <div className="mt-2">
                <Button variant="secondary" onClick={() => draft(e.id)} disabled={busy}>Prepare reply draft</Button>
              </div>
            </li>
          ))}
        </ul>
      </Card>
    </div>
  )
}
