import { useEffect, useState } from 'react'
import { api } from '../services/api'
import { Workflow, Play, Pause, Power, RefreshCw } from 'lucide-react'

export default function AutomationCenter() {
  const [data, setData] = useState<any>(null)
  const [msg, setMsg] = useState<string|null>(null)
  const [busy, setBusy] = useState(false)

  async function load() {
    try { setData(await api.get<any>('/automation')) } catch(e:any){ setMsg(e?.message) }
  }

  useEffect(() => {
    let on = true
    ;(async () => {
      try { const r = await api.get<any>('/automation'); if (on) setData(r) } catch(e:any){ if (on) setMsg(e?.message) }
    })()
    return () => { on = false }
  }, [])

  async function run(name:string) {
    setBusy(true); setMsg(null)
    try {
      // go through approval flow
      const res = await api.post<any>('/assistant/chat', { message: `run ${name.replace(/_/g,' ')} workflow` })
      setMsg(res?.response || 'Approval requested for workflow run.')
    } catch(e:any){ setMsg(e?.message||'Failed') }
    finally { setBusy(false); load() }
  }
  async function sched(action:'pause'|'resume') {
    try { await api.post(`/schedules/${action}`); load(); setMsg(`Scheduler ${action}d.`) } catch(e:any){ setMsg(e?.message) }
  }

  const n8n = data?.n8n
  const workflows = data?.workflows || []
  const runs = data?.runs || []

  return (
    <div className="space-y-4">
      <div className="glass-strong rounded-2xl p-5 flex flex-col md:flex-row md:items-center justify-between gap-3">
        <div>
          <div className="flex items-center gap-2 text-cyan-100"><Workflow size={18}/><h1 className="text-lg font-semibold">Automation Center</h1></div>
          <p className="text-sm text-[var(--muted)] mt-1">n8n-powered local workflows with approval before execution. Native fallback runs when n8n is unavailable.</p>
        </div>
        <div className="flex items-center gap-2 text-sm">
          <span className={`px-3 py-1.5 rounded-full border ${n8n?.ok?'border-emerald-400/30 text-emerald-300':'border-amber-400/30 text-amber-300'}`}>n8n {n8n?.ok?'connected':'offline'}</span>
          <button onClick={load} className="p-2 rounded-lg border border-[var(--border-soft)] text-[var(--muted)]"><RefreshCw size={14}/></button>
        </div>
      </div>
      {msg && <div className="glass rounded-xl p-3 text-sm text-slate-200">{msg}</div>}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
        <div className="glass rounded-2xl p-4">
          <div className="flex items-center justify-between mb-3">
            <div className="text-sm text-cyan-200">Workflows</div>
            <div className="flex gap-2">
              <button onClick={()=>sched('resume')} className="text-xs px-2.5 py-1 rounded border border-emerald-400/30 text-emerald-300 inline-flex items-center gap-1"><Play size={12}/>Resume all</button>
              <button onClick={()=>sched('pause')} className="text-xs px-2.5 py-1 rounded border border-amber-400/30 text-amber-300 inline-flex items-center gap-1"><Pause size={12}/>Pause all</button>
            </div>
          </div>
          <div className="space-y-3">
            {workflows.map((w:any)=> (
              <div key={w.name} className="p-3 rounded-xl bg-black/20 border border-[var(--border-soft)]">
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <div className="font-medium text-slate-100">{w.title}</div>
                    <div className="text-xs text-[var(--muted)] mt-0.5">{w.description}</div>
                  </div>
                  <button disabled={busy} onClick={()=>run(w.name)} className="px-3 py-1.5 rounded-md text-xs bg-cyan-500/15 border border-cyan-400/30 text-cyan-100 hover:bg-cyan-500/25 disabled:opacity-50 inline-flex items-center gap-1"><Power size={12}/>Run</button>
                </div>
                <div className="mt-2 text-[11px] text-[var(--muted)]">Cadence: {w.cadence} · Webhook: {w.webhook} · Fallback: {w.native_fallback}</div>
                {w.steps && <ul className="mt-2 text-xs text-slate-300 list-disc list-inside space-y-0.5">{w.steps.slice(0,4).map((s:string,i:number)=><li key={i}>{s}</li>)}</ul>}
              </div>
            ))}
            {workflows.length===0 && <div className="text-sm text-[var(--muted)]">No workflows loaded.</div>}
          </div>
        </div>
        <div className="glass rounded-2xl p-4">
          <div className="text-sm text-cyan-200 mb-3">Execution History</div>
          <div className="space-y-2 max-h-[520px] overflow-auto pr-1">
            {runs.length===0 && <div className="text-sm text-[var(--muted)]">No runs yet.</div>}
            {runs.map((r:any)=> (
              <div key={r.id} className="p-2.5 rounded-lg bg-black/20 border border-[var(--border-soft)] text-xs">
                <div className="flex items-center justify-between"><span className="text-slate-100">{r.workflow} · <span className="text-[var(--muted)]">{r.engine}</span></span><span className={r.status==='success'?'text-emerald-300':'text-amber-300'}>{r.status}</span></div>
                <div className="text-[var(--muted)] mt-1">{r.duration_ms}ms · {r.created_at}</div>
                {r.detail && <div className="mt-1 text-slate-300/80 line-clamp-2">{r.detail}</div>}
              </div>
            ))}
          </div>
          <div className="mt-4 text-xs text-[var(--muted)]">n8n URL: {data?.n8n_url || 'http://127.0.0.1:5678'} · Running a workflow creates an approval request first.</div>
        </div>
      </div>
    </div>
  )
}
