import { useState } from 'react'
import { api, type Proposal } from '../../services/api'
import { CheckCircle2, XCircle, Clock, ShieldAlert } from 'lucide-react'

export function ApprovalCard({ proposal, onResolved }: { proposal: Proposal; onResolved?: (p: Proposal) => void }) {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [local, setLocal] = useState(proposal)

  async function decide(action: 'approve' | 'reject') {
    setBusy(true); setError(null)
    try {
      const res = await api.post<any>(`/actions/${local.id}/${action}`)
      if (res?.ok === false && res?.error) throw new Error(res.error)
      const next: Proposal = res?.proposal || { ...local, status: action === 'approve' ? 'executed' : 'rejected' }
      setLocal(next)
      onResolved?.(next)
    } catch (e: any) {
      setError(e?.message || 'Action failed')
    } finally { setBusy(false) }
  }

  const pending = local.status === 'pending'
  const tone = local.status === 'executed' || local.status === 'approved' ? 'border-emerald-500/30' : local.status === 'rejected' || local.status === 'failed' ? 'border-red-500/30' : 'border-amber-400/30'
  return (
    <div className={`mt-3 rounded-xl glass glow-amber border ${tone} p-3`}>
      <div className="flex items-start gap-2">
        <div className="mt-0.5 text-amber-300">{pending ? <Clock size={16}/> : local.status === 'rejected' || local.status === 'failed' ? <XCircle size={16} className="text-red-400"/> : <CheckCircle2 size={16} className="text-emerald-400"/>}</div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between gap-2">
            <div className="text-sm font-medium text-[var(--text)]">{local.title}</div>
            <span className={`text-[10px] uppercase tracking-wider px-2 py-0.5 rounded-full border ${pending ? 'border-amber-400/40 text-amber-300' : local.status === 'rejected' || local.status === 'failed' ? 'border-red-400/40 text-red-300' : 'border-emerald-400/40 text-emerald-300'}`}>{local.status}</span>
          </div>
          {local.reason && <div className="text-xs text-[var(--muted)] mt-1">{local.reason}</div>}
          {Array.isArray(local.plan) && local.plan.length > 0 && (
            <ol className="mt-2 space-y-1 text-xs text-slate-300 list-decimal list-inside">
              {local.plan.map((s, i) => <li key={i}>{s}</li>)}
            </ol>
          )}
          <div className="mt-2 flex items-center gap-2 text-[11px] text-[var(--muted)]">
            <ShieldAlert size={12} className="text-amber-300"/> JARVIS will not act without your approval.
          </div>
          {error && <div className="mt-2 text-xs text-red-300">{error}</div>}
          {local.error && !pending && <div className="mt-2 text-xs text-red-300">{local.error}</div>}
          {local.result && !pending && (
            <pre className="mt-2 text-[11px] text-emerald-200/90 whitespace-pre-wrap max-h-40 overflow-auto bg-black/20 rounded p-2 border border-emerald-500/20">{typeof local.result === 'string' ? local.result : JSON.stringify(local.result, null, 2)}</pre>
          )}
          {pending && (
            <div className="mt-3 flex gap-2">
              <button disabled={busy} onClick={() => decide('approve')} className="px-3 py-1.5 rounded-md text-xs font-medium bg-emerald-500/15 text-emerald-300 border border-emerald-500/30 hover:bg-emerald-500/25 disabled:opacity-50">Approve & Execute</button>
              <button disabled={busy} onClick={() => decide('reject')} className="px-3 py-1.5 rounded-md text-xs font-medium bg-red-500/10 text-red-300 border border-red-500/30 hover:bg-red-500/20 disabled:opacity-50">Reject</button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default ApprovalCard
