import { useEffect, useState } from 'react'
import { api } from '../services/api'
import { CalendarClock, Plus, Trash2 } from 'lucide-react'

export default function Interviews() {
  const [items, setItems] = useState<any[]>([])
  const [stats, setStats] = useState<any>(null)
  const [form, setForm] = useState({ company:'', role:'', interview_date:'', interview_time:'', mode:'online', interviewer:'', notes:'' })
  const [msg, setMsg] = useState<string|null>(null)

  async function load() {
    try { const r = await api.get<any>('/interviews'); setItems(r?.interviews||[]); setStats(r?.stats||null) } catch(e:any){ setMsg(e?.message) }
  }
  useEffect(()=>{ const t = setTimeout(() => { void load() }, 0); return () => clearTimeout(t) }, [])

  async function create() {
    if (!form.company) { setMsg('Company is required'); return }
    setMsg(null)
    try { await api.post('/interviews', form); setForm({ company:'', role:'', interview_date:'', interview_time:'', mode:'online', interviewer:'', notes:'' }); load(); setMsg('Interview added.') }
    catch(e:any){ setMsg(e?.message||'Failed') }
  }
  async function update(id:number, status:string) {
    try { await api.patch(`/interviews/${id}`, { status }); load() } catch(e:any){ setMsg(e?.message) }
  }
  async function remove(id:number) {
    if (!confirm('Delete this interview?')) return
    try { await api.del(`/interviews/${id}`); load() } catch(e:any){ setMsg(e?.message) }
  }

  return (
    <div className="space-y-4">
      <div className="glass-strong rounded-2xl p-5 flex flex-col md:flex-row md:items-center justify-between gap-3">
        <div>
          <div className="flex items-center gap-2 text-cyan-100"><CalendarClock size={18}/><h1 className="text-lg font-semibold">Interview Tracker</h1></div>
          <p className="text-sm text-[var(--muted)] mt-1">Track interview schedules, status and notes.</p>
        </div>
        <div className="flex gap-3 text-sm">
          <div className="glass px-3 py-2 rounded-lg"><div className="text-[11px] text-[var(--muted)]">Scheduled</div><div className="text-cyan-100 font-semibold">{stats?.scheduled ?? 0}</div></div>
          <div className="glass px-3 py-2 rounded-lg"><div className="text-[11px] text-[var(--muted)]">Completed</div><div className="text-emerald-300 font-semibold">{stats?.completed ?? 0}</div></div>
        </div>
      </div>
      {msg && <div className="glass rounded-xl p-3 text-sm text-slate-200">{msg}</div>}
      <div className="grid grid-cols-1 lg:grid-cols-[.9fr_1.1fr] gap-4">
        <div className="glass rounded-2xl p-4 space-y-2">
          <div className="text-sm text-cyan-200 mb-2 flex items-center gap-2"><Plus size={14}/> Add interview</div>
          <input placeholder="Company *" value={form.company} onChange={e=>setForm({...form,company:e.target.value})} className="w-full px-3 py-2 rounded-lg text-sm" />
          <input placeholder="Role" value={form.role} onChange={e=>setForm({...form,role:e.target.value})} className="w-full px-3 py-2 rounded-lg text-sm" />
          <div className="grid grid-cols-2 gap-2">
            <input type="date" value={form.interview_date} onChange={e=>setForm({...form,interview_date:e.target.value})} className="px-3 py-2 rounded-lg text-sm" />
            <input type="time" value={form.interview_time} onChange={e=>setForm({...form,interview_time:e.target.value})} className="px-3 py-2 rounded-lg text-sm" />
          </div>
          <div className="grid grid-cols-2 gap-2">
            <select value={form.mode} onChange={e=>setForm({...form,mode:e.target.value})} className="px-3 py-2 rounded-lg text-sm"><option>online</option><option>onsite</option><option>phone</option></select>
            <input placeholder="Interviewer" value={form.interviewer} onChange={e=>setForm({...form,interviewer:e.target.value})} className="px-3 py-2 rounded-lg text-sm" />
          </div>
          <textarea placeholder="Notes" value={form.notes} onChange={e=>setForm({...form,notes:e.target.value})} className="w-full px-3 py-2 rounded-lg text-sm min-h-[80px]" />
          <button onClick={create} className="w-full px-4 py-2 rounded-lg bg-cyan-500/20 border border-cyan-400/30 text-cyan-100 hover:bg-cyan-500/30">Save interview</button>
        </div>
        <div className="glass rounded-2xl p-4">
          <div className="text-sm text-cyan-200 mb-3">Interviews ({items.length})</div>
          <div className="space-y-3 max-h-[520px] overflow-auto pr-1">
            {items.length===0 && <div className="text-sm text-[var(--muted)]">No interviews scheduled.</div>}
            {items.map((i:any)=> (
              <div key={i.id} className="p-3 rounded-xl bg-black/20 border border-[var(--border-soft)]">
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <div className="font-medium text-slate-100">{i.company} {i.role?`· ${i.role}`:''}</div>
                    <div className="text-xs text-[var(--muted)] mt-0.5">{i.interview_date||'Date TBD'} {i.interview_time||''} · {i.mode} {i.interviewer?`· ${i.interviewer}`:''}</div>
                  </div>
                  <button onClick={()=>remove(i.id)} className="text-red-300/80 hover:text-red-300"><Trash2 size={14}/></button>
                </div>
                {i.notes && <div className="text-xs text-slate-300 mt-1">{i.notes}</div>}
                <div className="mt-2 flex items-center gap-2">
                  <span className={`text-xs px-2 py-0.5 rounded-full border ${i.status==='scheduled'?'border-cyan-400/30 text-cyan-200':i.status==='completed'?'border-emerald-400/30 text-emerald-300':'border-slate-500/30 text-slate-300'}`}>{i.status}</span>
                  {['scheduled','completed','cancelled','no_response'].map(s=> <button key={s} onClick={()=>update(i.id,s)} className="text-[11px] text-[var(--muted)] hover:text-cyan-200 underline">{s}</button>)}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
