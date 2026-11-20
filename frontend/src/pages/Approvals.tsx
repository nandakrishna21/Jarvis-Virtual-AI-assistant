import { useState } from 'react'
import { api, type Approval } from '../services/api'
import { useApi } from '../hooks/useApi'
import { Badge, Button, Card, Empty, ErrorBox, Loading } from '../components/ui'

export default function Approvals() {
  const approvals = useApi<Approval[]>('/approvals')
  const [notice, setNotice] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  async function decide(id: number, approve: boolean) {
    setError(null); setNotice(null)
    try {
      const path = approve ? `/approvals/${id}/approve` : `/approvals/${id}/reject`
      const res = await api.post<{ status?: string; application_status?: string; submission?: string; error?: string }>(path)
      if (res.error) setError(res.error)
      else {
        setNotice(
          approve
            ? `Approved. Application status: ${res.application_status}. ${res.submission ?? ''}`
            : 'Rejected. The action was cancelled.',
        )
      }
      approvals.reload()
    } catch (e) {
      setError((e as Error).message)
    }
  }

  async function decideEmail(id: number, approve: boolean) {
    setError(null); setNotice(null)
    try {
      const path = approve
        ? `/emails/approve-send?approval_id=${id}`
        : `/emails/approve-reject?approval_id=${id}`
      const res = await api.post<{ sent?: boolean; error?: string; subject?: string; recipient?: string }>(path)
      if (res.error) setError(res.error)
      else setNotice(res.sent ? `Email sent to ${res.recipient}.` : 'Email draft rejected and cancelled.')
    } catch (e) {
      setError((e as Error).message)
    }
  }

  return (
    <div className="space-y-4">
      <Card title="Pending approvals">
        <p className="mb-3 text-xs text-slate-500">
          Every approval shows the exact content that will be used. Job applications are never auto-submitted; emails are only sent
          when you approve the exact message and the token holds the gmail.send scope.
        </p>
        {approvals.error && <ErrorBox error={approvals.error} />}
        {approvals.loading && <Loading />}
        {!approvals.loading && !approvals.data?.length && <Empty label="Nothing waiting for approval" />}
        {notice && <p className="mb-2 text-xs text-emerald-300">{notice}</p>}
        {error && <div className="mb-2"><ErrorBox error={error} /></div>}
        <ul className="space-y-3">
          {approvals.data?.map((a) => (
            <li key={a.id} className="rounded-lg border border-slate-800 p-3">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <span className="text-sm">#{a.id} · {a.action}</span>
                <Badge tone={a.status === 'approved' ? 'green' : a.status === 'rejected' ? 'red' : 'amber'}>{a.status}</Badge>
              </div>
              <div className="text-xs text-slate-500">created {a.created_at}</div>
              {a.snapshot && (
                <pre className="mt-2 max-h-48 overflow-auto whitespace-pre-wrap rounded-lg border border-slate-800 bg-slate-950 p-2 text-xs text-slate-400">
                  {a.snapshot.slice(0, 3000)}
                </pre>
              )}
              {a.status === 'pending' && (
                <div className="mt-2 flex flex-wrap gap-2">
                  {a.draft_id !== undefined ? (
                    <>
                      <Button onClick={() => decideEmail(a.id, true)}>Approve and send</Button>
                      <Button variant="danger" onClick={() => decideEmail(a.id, false)}>Reject</Button>
                    </>
                  ) : (
                    <>
                      <Button onClick={() => decide(a.id, true)}>Approve</Button>
                      <Button variant="danger" onClick={() => decide(a.id, false)}>Reject</Button>
                    </>
                  )}
                </div>
              )}
            </li>
          ))}
        </ul>
      </Card>
    </div>
  )
}
