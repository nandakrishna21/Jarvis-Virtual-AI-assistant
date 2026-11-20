import { useState } from 'react'
import { api } from '../services/api'
import { Search, Sparkles } from 'lucide-react'

export default function JobDiscovery() {
  const [query, setQuery] = useState('Python Backend Developer')
  const [location, setLocation] = useState('Hyderabad, India')
  const [jobs, setJobs] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [msg, setMsg] = useState<string | null>(null)
  const [proposal, setProposal] = useState<any>(null)

  async function search() {
    setLoading(true); setMsg(null); setProposal(null)
    try {
      const res = await api.post<any>('/jobs/search', { query, location })
      if (Array.isArray(res)) { setJobs(res); setMsg(`Found ${res.length} jobs. Scores computed against your active resume.`) }
      else if (res?.requires_approval) { setProposal(res.proposal); setMsg('Search prepared as an action. Approve it to collect jobs.') }
      else { setJobs(res?.jobs || []); setMsg(res?.response || 'Search complete.') }
    } catch (e: any) { setMsg(e?.message || 'Search failed.') }
    finally { setLoading(false) }
  }

  return (
    <div className="space-y-4">
      <div className="glass-strong rounded-2xl p-5">
        <div className="flex items-center gap-2 text-cyan-100 mb-1"><Search size={18}/> <h1 className="text-lg font-semibold">Job Discovery</h1></div>
        <p className="text-sm text-[var(--muted)]">Discover roles from configured sources, normalize listings, and score them against your resume.</p>
        <div className="mt-4 grid grid-cols-1 md:grid-cols-[1fr_1fr_auto] gap-2">
          <input value={query} onChange={e=>setQuery(e.target.value)} placeholder="Role or keywords" className="px-3 py-2.5 rounded-lg text-sm" />
          <input value={location} onChange={e=>setLocation(e.target.value)} placeholder="Location (Hyderabad, India, Remote...)" className="px-3 py-2.5 rounded-lg text-sm" />
          <button onClick={search} disabled={loading} className="px-4 py-2.5 rounded-lg bg-cyan-500/20 border border-cyan-400/30 text-cyan-100 hover:bg-cyan-500/30 disabled:opacity-50">{loading?'Searching...':'Search Jobs'}</button>
        </div>
        {msg && <div className="mt-3 text-sm text-slate-300">{msg}</div>}
        {proposal && <div className="mt-3 text-xs text-amber-300">Approval required: {proposal.title} (open Approvals/Assistant to approve #{proposal.id})</div>}
      </div>
      <div className="glass rounded-2xl p-4">
        <div className="flex items-center gap-2 text-sm text-cyan-200 mb-3"><Sparkles size={16}/> Results</div>
        {jobs.length===0 && <div className="text-sm text-[var(--muted)]">No results yet. Run a search to discover jobs.</div>}
        <div className="grid gap-3">
          {jobs.map((j:any, i:number) => (
            <div key={j.id || j.url || i} className="p-3 rounded-xl bg-black/20 border border-[var(--border-soft)]">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <div className="font-medium text-slate-100">{j.title}</div>
                  <div className="text-xs text-[var(--muted)] mt-0.5">{j.company || 'Company not published'} · {j.location || 'Location not published'}</div>
                </div>
                {j.score != null && <div className="text-sm font-semibold text-cyan-200">{j.score}%</div>}
              </div>
              <div className="mt-2 flex flex-wrap gap-3 text-xs text-slate-300">
                {j.matching_skills?.length ? <span className="text-emerald-300">Match: {j.matching_skills.join(', ')}</span> : j.matching ? <span className="text-emerald-300">Match: {j.matching}</span> : null}
                {j.missing_skills?.length ? <span className="text-amber-300">Gaps: {j.missing_skills.join(', ')}</span> : j.missing ? <span className="text-amber-300">Gaps: {j.missing}</span> : null}
              </div>
              <div className="mt-2 flex items-center justify-between text-xs">
                <span className="text-[var(--muted)]">{j.source || 'source n/a'} · {j.verified || 'unverified'}</span>
                {j.url && <a href={j.url} target="_blank" rel="noreferrer" className="text-cyan-300 hover:underline">Open listing</a>}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
