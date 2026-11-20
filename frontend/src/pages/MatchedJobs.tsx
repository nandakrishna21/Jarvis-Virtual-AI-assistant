import { useEffect, useState } from 'react'
import { api } from '../services/api'
import { Briefcase, Download, ThumbsUp, ThumbsDown, Check, X } from 'lucide-react'

export default function MatchedJobs() {
  const [jobs, setJobs] = useState<any[]>([])
  const [min, setMin] = useState(0)
  const [loading, setLoading] = useState(true)
  const [msg, setMsg] = useState<string|null>(null)
  const [selected, setSelected] = useState<number[]>([])
  const [busy, setBusy] = useState(false)
  const [weights, setWeights] = useState<any>(null)

  async function load() {
    try {
      const r = await api.get<any>(`/jobs/matched?min_score=${min}&limit=50`)
      const list = Array.isArray(r) ? r : (r?.jobs || [])
      setJobs(list)
      setSelected(prev => prev.filter(id => list.some((j:any)=>j.job_id===id)))
    } catch (e: any) {
      setMsg(e?.message || 'Failed to load matches')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    let on = true
    ;(async () => {
      try {
        const r = await api.get<any>(`/jobs/matched?min_score=${min}&limit=50`)
        if (!on) return
        const list = Array.isArray(r) ? r : (r?.jobs || [])
        setJobs(list)
        setSelected(prev => prev.filter(id => list.some((j:any)=>j.job_id===id)))
      } catch (e: any) {
        if (on) setMsg(e?.message || 'Failed to load matches')
      } finally {
        if (on) setLoading(false)
      }
    })()
    return () => { on = false }
  }, [min])

  useEffect(() => {
    let on = true
    ;(async () => {
      try {
        const w = await api.get<any>('/jobs/feedback/weights')
        if (on) setWeights(w)
      } catch { }
    })()
    return () => { on = false }
  }, [jobs.length])

  async function prepare(jobId: number) {
    setMsg(null)
    try {
      const res = await api.post<any>('/assistant/chat', { message: `prepare application for job ${jobId}` })
      setMsg(res?.response || 'Approval requested. Check Assistant/Approvals.')
    } catch(e:any){ setMsg(e?.message||'Failed') }
  }

  async function bulk(action: 'approve' | 'reject') {
    if (!selected.length) return
    setBusy(true)
    setMsg(null)
    try {
      const res = await api.post<any>('/jobs/bulk-action', { job_ids: selected, action })
      setMsg(`${action === 'approve' ? 'Approved' : 'Rejected'} ${res?.updated ?? 0} job(s). Ranking re-tuned from your feedback.`)
      setSelected([])
      await load()
    } catch(e:any){ setMsg(e?.message||'Bulk action failed') }
    finally { setBusy(false) }
  }

  async function mark(jobId: number, feedback: 'good' | 'bad') {
    setBusy(true)
    try {
      const res = await api.post<any>(`/jobs/${jobId}/feedback`, { feedback })
      setWeights(res?.weights || null)
      setMsg(`Marked as ${feedback}. Ranking updated.`)
      await load()
    } catch(e:any){ setMsg(e?.message||'Feedback failed') }
    finally { setBusy(false) }
  }

  const allSelected = jobs.length > 0 && selected.length === jobs.length

  return (
    <div className="space-y-4">
      <div className="glass-strong rounded-2xl p-5 flex flex-col md:flex-row md:items-end gap-3 justify-between">
        <div>
          <div className="flex items-center gap-2 text-cyan-100"><Briefcase size={18}/><h1 className="text-lg font-semibold">Matched Jobs</h1></div>
          <p className="text-sm text-[var(--muted)] mt-1">Ranked opportunities scored against your active resume (35% skills, 25% experience, 20% responsibilities, 10% location, 10% education).</p>
        </div>
        <div className="flex flex-wrap items-center gap-2 text-sm">
          <label className="text-[var(--muted)]">Min score</label>
          <select value={min} onChange={e=>{ setLoading(true); setMin(Number(e.target.value)) }} className="px-2 py-1.5 rounded-lg bg-black/30 border border-[var(--border-soft)]">
            {[0,50,60,70,80,90].map(v=> <option key={v} value={v}>{v}%</option>)}
          </select>
          <a href="/api/jobs/export.csv" download className="px-3 py-1.5 rounded-md border border-cyan-400/30 text-cyan-200 hover:bg-cyan-500/10 inline-flex items-center gap-1.5"><Download size={14}/> Export CSV</a>
        </div>
      </div>

      {weights && (weights.samples > 0) && (
        <div className="glass rounded-xl p-3 text-xs text-[var(--muted)]">
          Learned from your feedback: {weights.good_jobs} good job(s), {weights.bad_jobs} rejected.
          {Object.keys(weights.boost||{}).length > 0 && <> Boosted skills: {Object.keys(weights.boost).slice(0,6).join(', ')}.</>}
          {Object.keys(weights.penalize||{}).length > 0 && <> Penalised skills: {Object.keys(weights.penalize).slice(0,6).join(', ')}.</>}
        </div>
      )}

      {msg && <div className="glass rounded-xl p-3 text-sm text-slate-200">{msg}</div>}

      {jobs.length > 0 && (
        <div className="glass rounded-2xl p-3 flex flex-wrap items-center gap-3 text-sm">
          <label className="flex items-center gap-2 cursor-pointer">
            <input type="checkbox" checked={allSelected} onChange={e => setSelected(e.target.checked ? jobs.map((j:any)=>j.job_id) : [])} />
            <span className="text-[var(--muted)]">{selected.length} selected</span>
          </label>
          <button disabled={!selected.length || busy} onClick={()=>bulk('approve')} className="px-3 py-1.5 rounded-md border border-emerald-400/30 text-emerald-200 hover:bg-emerald-500/10 disabled:opacity-40 inline-flex items-center gap-1.5"><Check size={14}/> Approve selected</button>
          <button disabled={!selected.length || busy} onClick={()=>bulk('reject')} className="px-3 py-1.5 rounded-md border border-red-400/30 text-red-200 hover:bg-red-500/10 disabled:opacity-40 inline-flex items-center gap-1.5"><X size={14}/> Reject selected</button>
        </div>
      )}

      <div className="glass rounded-2xl p-4">
        {loading ? <div className="text-sm text-[var(--muted)]">Loading matches...</div> : jobs.length===0 ? <div className="text-sm text-[var(--muted)]">No matched jobs yet. Run Job Discovery and upload a resume.</div> : (
          <div className="grid gap-3">
            {jobs.map((j:any)=> (
              <div key={j.job_id} className="p-4 rounded-xl bg-black/20 border border-[var(--border-soft)]">
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-start gap-3">
                    <input type="checkbox" className="mt-1" checked={selected.includes(j.job_id)} onChange={e => setSelected(e.target.checked ? [...selected, j.job_id] : selected.filter(id=>id!==j.job_id))} />
                    <div>
                      <div className="font-medium text-slate-100">{j.title}</div>
                      <div className="text-xs text-[var(--muted)] mt-0.5">{j.company || 'Company n/a'} · {j.location || 'Location n/a'}</div>
                      <div className="text-[11px] text-[var(--muted)] mt-1 flex flex-wrap gap-2">
                        {j.seniority && <span className="px-1.5 py-0.5 rounded border border-[var(--border-soft)]">{j.seniority}</span>}
                        {j.source && <span className="px-1.5 py-0.5 rounded border border-[var(--border-soft)]">{j.source}</span>}
                        {j.status && <span className="px-1.5 py-0.5 rounded border border-cyan-400/30 text-cyan-200">{j.status}</span>}
                        {j.feedback && <span className={`px-1.5 py-0.5 rounded border ${j.feedback==='good'?'border-emerald-400/30 text-emerald-200':'border-red-400/30 text-red-200'}`}>{j.feedback}</span>}
                      </div>
                    </div>
                  </div>
                  <div className={`text-lg font-semibold ${j.score>=80?'text-emerald-300':j.score>=60?'text-cyan-200':'text-slate-300'}`}>{j.score}%</div>
                </div>
                <div className="mt-2 text-xs grid md:grid-cols-2 gap-2">
                  <div className="text-emerald-300/90"><span className="text-[var(--muted)]">Matching: </span>{j.matching || 'none extracted'}</div>
                  <div className="text-amber-300/90"><span className="text-[var(--muted)]">Gaps: </span>{j.missing || 'none'}</div>
                </div>
                {j.components && Object.keys(j.components).length > 0 && (
                  <div className="mt-2 text-[11px] text-[var(--muted)] flex flex-wrap gap-3">
                    {Object.entries(j.components).map(([k,v]:any) => (
                      <span key={k}>{k}: {Math.round(Number(v)*10)/10}%{j.notes?.[k] ? ` (${j.notes[k]})` : ''}</span>
                    ))}
                  </div>
                )}
                <div className="mt-3 flex flex-wrap items-center gap-2 text-xs">
                  {j.url && <a href={j.url} target="_blank" rel="noreferrer" className="px-3 py-1.5 rounded-md border border-cyan-400/30 text-cyan-200 hover:bg-cyan-500/10">Open job</a>}
                  <button onClick={()=>prepare(j.job_id)} className="px-3 py-1.5 rounded-md border border-amber-400/30 text-amber-200 hover:bg-amber-500/10">Prepare application (needs approval)</button>
                  <button disabled={busy} onClick={()=>mark(j.job_id,'good')} className="px-3 py-1.5 rounded-md border border-emerald-400/30 text-emerald-200 hover:bg-emerald-500/10 inline-flex items-center gap-1.5"><ThumbsUp size={13}/> Good match</button>
                  <button disabled={busy} onClick={()=>mark(j.job_id,'bad')} className="px-3 py-1.5 rounded-md border border-red-400/30 text-red-200 hover:bg-red-500/10 inline-flex items-center gap-1.5"><ThumbsDown size={13}/> Not for me</button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
