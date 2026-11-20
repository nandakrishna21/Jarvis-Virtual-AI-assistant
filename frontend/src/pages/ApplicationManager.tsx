import { useEffect, useState } from 'react'
import { api } from '../services/api'
import { FolderKanban, Check, X, ExternalLink } from 'lucide-react'

const statuses = ['Discovered','Matched','Shortlisted','Draft prepared','Awaiting approval','Approved','Applied','Interview','Rejected','Offer','Withdrawn']

export default function ApplicationManager() {
  const [apps, setApps] = useState<any[]>([])
  const [approvals, setApprovals] = useState<any[]>([])
  const [actions, setActions] = useState<any[]>([])
  const [msg, setMsg] = useState<string|null>(null)
  const [loading, setLoading] = useState(true)

  async function load() {
    setLoading(true)
    try { const a = await api.get<any[]>('/applications'); setApps(Array.isArray(a)?a:(a as any)?.applications||[]) } catch {}
    try { const r = await api.get<any[]>('/approvals'); setApprovals(Array.isArray(r)?r:[]) } catch {}
    try { const p = await api.get<any>('/actions?status=pending'); setActions(p?.actions||[]) } catch {}
    setLoading(false)
  }
  useEffect(()=>{ const t = setTimeout(() => { void load() }, 0); return () => clearTimeout(t) }, [])

  async function decideLegacy(id: number, action: 'approve'|'reject') {
    setMsg(null)
    try { const r = await api.post<any>(`/approvals/${id}/${action}`); setMsg(`Approval ${id}: ${r?.status || r?.application_status || 'done'}. ${r?.submission||''}`); load() }
    catch(e:any){ setMsg(e?.message||'Failed') }
  }
  async function decideAction(id: number, action: 'approve'|'reject') {
    setMsg(null)
    try { const r = await api.post<any>(`/actions/${id}/${action}`); setMsg(r?.proposal?.title ? `${r.proposal.title}: ${r.proposal.status}` : (r?.ok?'Done':'Failed')); load() }
    catch(e:any){ setMsg(e?.message||'Failed') }
  }
  async function setStatus(id: number, status: string) {
    try { await api.patch(`/applications/${id}`, { status }); load() } catch(e:any){ setMsg(e?.message) }
  }

  const appPending = approvals.filter(a=>a.status==='pending')

  return (
    <div className="space-y-4">
      <div className="glass-strong rounded-2xl p-5">
        <div className="flex items-center gap-2 text-cyan-100"><FolderKanban size={18}/><h1 className="text-lg font-semibold">Application Manager</h1></div>
        <p className="text-sm text-[var(--muted)] mt-1">Prepare, review and track applications. Nothing is submitted without your explicit approval.</p>
      </div>
      {msg && <div className="glass rounded-xl p-3 text-sm text-slate-200">{msg}</div>}

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
        <div className="glass rounded-2xl p-4">
          <div className="text-sm text-amber-200 mb-3">Pending Approvals ({appPending.length + actions.filter(a=>['prepare_application','prepare_email_reply','send_email'].includes(a.action_type)).length})</div>
          <div className="space-y-3 max-h-[420px] overflow-auto pr-1">
            {actions.filter(a=>['prepare_application','send_email','draft_email','prepare_email_reply'].includes(a.action_type)).map(a=> (
              <div key={`act-${a.id}`} className="p-3 rounded-xl bg-black/20 border border-amber-400/20">
                <div className="text-sm font-medium text-slate-100">{a.title}</div>
                <div className="text-xs text-[var(--muted)] mt-1">Action #{a.id} · {a.action_type}</div>
                <div className="mt-2 flex gap-2">
                  <button onClick={()=>decideAction(a.id,'approve')} className="px-3 py-1.5 rounded-md text-xs bg-emerald-500/15 border border-emerald-500/30 text-emerald-300 inline-flex items-center gap-1"><Check size={12}/>Approve</button>
                  <button onClick={()=>decideAction(a.id,'reject')} className="px-3 py-1.5 rounded-md text-xs bg-red-500/10 border border-red-500/30 text-red-300 inline-flex items-center gap-1"><X size={12}/>Reject</button>
                </div>
              </div>
            ))}
            {appPending.map(a=> (
              <div key={`app-${a.id}`} className="p-3 rounded-xl bg-black/20 border border-amber-400/20">
                <div className="text-sm font-medium text-slate-100">Application approval #{a.id}</div>
                <div className="text-xs text-[var(--muted)] mt-1">{a.action} · status: {a.status}</div>
                {a.snapshot && <pre className="mt-2 text-[11px] text-slate-300 whitespace-pre-wrap max-h-28 overflow-auto">{typeof a.snapshot==='string'?a.snapshot:JSON.stringify(a.snapshot,null,2)}</pre>}
                <div className="mt-2 flex gap-2">
                  <button onClick={()=>decideLegacy(a.id,'approve')} className="px-3 py-1.5 rounded-md text-xs bg-emerald-500/15 border border-emerald-500/30 text-emerald-300 inline-flex items-center gap-1"><Check size={12}/>Approve</button>
                  <button onClick={()=>decideLegacy(a.id,'reject')} className="px-3 py-1.5 rounded-md text-xs bg-red-500/10 border border-red-500/30 text-red-300 inline-flex items-center gap-1"><X size={12}/>Reject</button>
                </div>
              </div>
            ))}
            {appPending.length===0 && actions.filter(a=>['prepare_application','prepare_email_reply','send_email'].includes(a.action_type)).length===0 && <div className="text-sm text-[var(--muted)]">No pending application approvals.</div>}
          </div>
        </div>

        <div className="glass rounded-2xl p-4">
          <div className="text-sm text-cyan-200 mb-3">Applications ({apps.length})</div>
          {loading ? <div className="text-sm text-[var(--muted)]">Loading...</div> : (
            <div className="space-y-3 max-h-[420px] overflow-auto pr-1">
              {apps.length===0 && <div className="text-sm text-[var(--muted)]">No applications yet. Prepare one from Matched Jobs or ask JARVIS in Assistant.</div>}
              {apps.map((a:any)=> (
                <div key={a.id} className="p-3 rounded-xl bg-black/20 border border-[var(--border-soft)]">
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <div className="text-sm font-medium text-slate-100">Application #{a.id} · Job #{a.job_id}</div>
                      <div className="text-xs text-[var(--muted)] mt-0.5">{a.job?.title || ''} {a.job?.company ? `· ${a.job.company}`:''}</div>
                    </div>
                    {a.job?.url && <a href={a.job.url} target="_blank" rel="noreferrer" className="text-cyan-300"><ExternalLink size={14}/></a>}
                  </div>
                  <div className="mt-2 flex flex-wrap items-center gap-2">
                    <span className={`text-xs px-2 py-0.5 rounded-full border ${a.status==='Approved'||a.status==='Applied'||a.status==='Offer'?'border-emerald-400/30 text-emerald-300':a.status==='Rejected'||a.status==='Withdrawn'?'border-red-400/30 text-red-300':'border-cyan-400/20 text-cyan-100'}`}>{a.status}</span>
                    <select value={a.status} onChange={e=>setStatus(a.id,e.target.value)} className="text-xs px-2 py-1 rounded">
                      {statuses.map(s=> <option key={s} value={s}>{s}</option>)}
                    </select>
                  </div>
                  <div className="mt-1 text-[11px] text-[var(--muted)]">Approval: {a.approval_status || 'n/a'} · Submission: manual only (never auto-submitted)</div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
