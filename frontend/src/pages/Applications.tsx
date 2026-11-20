import { useState } from 'react'
import { api, type Application } from '../services/api'
import { useApi } from '../hooks/useApi'
import { Badge, Button, Card, Empty, ErrorBox, Loading } from '../components/ui'

const STATUSES = [
  'Discovered', 'Shortlisted', 'Under review', 'Ready for approval', 'Approved', 'Submitted',
  'Assessment', 'Interview', 'Rejected', 'Offer', 'Withdrawn',
]

export default function Applications() {
  const apps = useApi<Application[]>('/applications')
  const [status, setStatus] = useState('Under review')
  const [error, setError] = useState<string | null>(null)

  async function updateStatus(id: number, next: string) {
    setError(null)
    try {
      await api.post(`/applications/${id}/status`, { status: next })
      apps.reload()
    } catch (e) {
      setError((e as Error).message)
    }
  }

  return (
    <div className="space-y-4">
      <Card title="Applications">
        {apps.error && <ErrorBox error={apps.error} />}
        {apps.loading && <Loading />}
        {!apps.loading && !apps.data?.length && <Empty label="No applications yet - prepare one from the Jobs page" />}
        {error && <ErrorBox error={error} />}
        <ul className="space-y-3">
          {apps.data?.map((a) => (
            <li key={a.id} className="rounded-lg border border-slate-800 p-3">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <span className="text-sm">Application #{a.id} · Job #{a.job_id}</span>
                <Badge tone={a.status === 'Rejected' || a.status === 'Withdrawn' ? 'red' : a.status === 'Offer' ? 'green' : 'blue'}>
                  {a.status}
                </Badge>
              </div>
              <div className="mt-2 flex flex-wrap items-center gap-2">
                <select
                  value={status}
                  onChange={(e) => setStatus(e.target.value)}
                  className="rounded-lg border border-slate-700 bg-slate-950 px-2 py-1 text-xs text-slate-200"
                >
                  <option value="">Set status...</option>
                  {STATUSES.map((s) => (
                    <option key={s} value={s}>{s}</option>
                  ))}
                </select>
                <Button
                  variant="secondary"
                  disabled={!status}
                  onClick={() => updateStatus(a.id, status)}
                >
                  Update
                </Button>
              </div>
            </li>
          ))}
        </ul>
      </Card>

      <Card title="How submission works">
        <ul className="list-disc space-y-1 pl-5 text-sm text-slate-400">
          <li>Preparing an application creates a review copy and a pending approval. Nothing is submitted.</li>
          <li>You must approve the exact content on the Approvals page.</li>
          <li>JARVIS never bypasses CAPTCHA, MFA, or site rules - you submit on the original site.</li>
        </ul>
      </Card>
    </div>
  )
}
