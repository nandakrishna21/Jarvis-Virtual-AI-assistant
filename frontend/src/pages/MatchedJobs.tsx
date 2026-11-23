import { useEffect, useMemo, useState } from 'react'
import { api } from '../services/api'
import {
  Briefcase, Download, ThumbsUp, ThumbsDown, Check, X, Search, RefreshCw,
  ExternalLink, MapPin, Building2, ChevronDown, ChevronUp, Inbox, Sparkles,
} from 'lucide-react'

const COMPONENTS: [string, string][] = [
  ['skills', 'Skills'],
  ['experience', 'Experience'],
  ['responsibilities', 'Responsibilities'],
  ['location', 'Location'],
  ['education', 'Education'],
]

function scoreTone(score: number) {
  if (score >= 80) return { text: 'text-emerald-300', bar: 'bg-emerald-400', label: 'Strong match' }
  if (score >= 60) return { text: 'text-cyan-200', bar: 'bg-cyan-400', label: 'Good match' }
  if (score >= 45) return { text: 'text-amber-200', bar: 'bg-amber-400', label: 'Partial match' }
  return { text: 'text-slate-300', bar: 'bg-slate-400', label: 'Low match' }
}

function Stat({ label, value, accent }: { label: string; value: number | string; accent?: string }) {
  return (
    <div className="rounded-xl border border-[var(--border-soft)] bg-black/20 px-3 py-2.5">
      <div className={`text-lg font-semibold ${accent || 'text-slate-100'}`}>{value}</div>
      <div className="text-[11px] text-[var(--muted)]">{label}</div>
    </div>
  )
}

export default function MatchedJobs() {
  const [jobs, setJobs] = useState<any[]>([])
  const [stats, setStats] = useState<any>({})
  const [sources, setSources] = useState<string[]>([])
  const [min, setMin] = useState(0)
  const [q, setQ] = useState('')
  const [debouncedQ, setDebouncedQ] = useState('')
  const [source, setSource] = useState('')
  const [sort, setSort] = useState('score')
  const [remoteOnly, setRemoteOnly] = useState(false)
  const [hideIrrelevant, setHideIrrelevant] = useState(true)
  const [reloadKey, setReloadKey] = useState(0)
  const [loading, setLoading] = useState(true)
  const [msg, setMsg] = useState<string | null>(null)
  const [selected, setSelected] = useState<number[]>([])
  const [busy, setBusy] = useState(false)
  const [busyId, setBusyId] = useState<number | null>(null)
  const [expanded, setExpanded] = useState<number | null>(null)
  const [weights, setWeights] = useState<any>(null)

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedQ(q), 300)
    return () => clearTimeout(timer)
  }, [q])

  useEffect(() => {
    let active = true
    setLoading(true)
    const params = new URLSearchParams({
      min_score: String(min),
      limit: '50',
      sort,
      remote_only: String(remoteOnly),
      hide_irrelevant: String(hideIrrelevant),
    })
    if (debouncedQ.trim()) params.set('q', debouncedQ.trim())
    if (source) params.set('source', source)
    api.get<any>(`/jobs/matched?${params.toString()}`)
      .then(r => {
        if (!active) return
        const list = r?.jobs || []
        setJobs(list)
        setStats(r?.stats || {})
        setSources(r?.sources || [])
        setSelected(prev => prev.filter(id => list.some((j: any) => j.job_id === id)))
      })
      .catch((e: any) => { if (active) setMsg(e?.message || 'Failed to load matches') })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [min, debouncedQ, source, sort, remoteOnly, hideIrrelevant, reloadKey])

  useEffect(() => {
    let active = true
    api.get<any>('/jobs/feedback/weights')
      .then(w => { if (active) setWeights(w) })
      .catch(() => {})
    return () => { active = false }
  }, [reloadKey])

  function reload() { setReloadKey(k => k + 1) }

  async function prepare(jobId: number) {
    setMsg(null)
    try {
      const res = await api.post<any>('/assistant/chat', { message: `prepare application for job ${jobId}` })
      setMsg(res?.response || 'Approval requested. Check Assistant or Approvals.')
    } catch (e: any) { setMsg(e?.message || 'Failed to prepare application') }
  }

  async function bulk(action: 'approve' | 'reject') {
    if (!selected.length) return
    setBusy(true); setMsg(null)
    try {
      const res = await api.post<any>('/jobs/bulk-action', { job_ids: selected, action })
      setMsg(`${action === 'approve' ? 'Approved' : 'Rejected'} ${res?.updated ?? 0} role(s). Ranking re-tuned from your feedback.`)
      setSelected([])
      reload()
    } catch (e: any) { setMsg(e?.message || 'Bulk action failed') }
    finally { setBusy(false) }
  }

  async function mark(jobId: number, feedback: 'good' | 'bad') {
    setBusyId(jobId); setMsg(null)
    try {
      const res = await api.post<any>(`/jobs/${jobId}/feedback`, { feedback })
      setWeights(res?.weights || weights)
      setMsg(`Marked as ${feedback}. Future rankings updated.`)
      reload()
    } catch (e: any) { setMsg(e?.message || 'Feedback failed') }
    finally { setBusyId(null) }
  }

  function clearFilters() {
    setMin(0); setQ(''); setSource(''); setSort('score')
    setRemoteOnly(false); setHideIrrelevant(true)
  }

  const allSelected = jobs.length > 0 && selected.length === jobs.length
  const activeFilters = Boolean(q || source || min > 0 || remoteOnly || !hideIrrelevant)
  const shown = jobs.length
  const total = stats.total ?? shown
  const learned = useMemo(() => Boolean(weights && weights.samples > 0), [weights])

  return (
    <div className="space-y-4">
      <div className="glass-strong rounded-2xl p-5">
        <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
          <div>
            <div className="flex items-center gap-2 text-cyan-100">
              <Briefcase size={18} />
              <h1 className="text-lg font-semibold">Matched Jobs</h1>
            </div>
            <p className="mt-1 max-w-2xl text-sm text-[var(--muted)]">
              Resume-scored roles. Unrelated listings are hidden automatically, and every score shows exactly why it ranked.
            </p>
          </div>
          <a href={`/api/jobs/export.csv?min_score=${min}`} download className="inline-flex items-center gap-1.5 rounded-md border border-cyan-400/30 px-3 py-2 text-sm text-cyan-200 hover:bg-cyan-500/10">
            <Download size={14} /> Export CSV
          </a>
        </div>

        <div className="mt-4 grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-5">
          <Stat label="On board" value={total} />
          <Stat label="Strong (80%+)" value={stats.strong ?? 0} accent="text-emerald-300" />
          <Stat label="Good (60-79%)" value={stats.good ?? 0} accent="text-cyan-200" />
          <Stat label="Applied" value={stats.applied ?? 0} accent="text-violet-200" />
          <Stat label="Filtered out" value={stats.hidden ?? 0} accent="text-slate-400" />
        </div>
      </div>

      {msg && <div className="glass rounded-xl p-3 text-sm text-slate-200">{msg}</div>}

      {learned && (
        <div className="glass rounded-xl p-3 text-xs text-[var(--muted)]">
          Learned from your feedback: {weights.good_jobs} good role(s), {weights.bad_jobs} rejected.
          {Object.keys(weights.boost || {}).length > 0 && <> Boosted skills: {Object.keys(weights.boost).slice(0, 6).join(', ')}.</>}
          {Object.keys(weights.penalize || {}).length > 0 && <> Penalised skills: {Object.keys(weights.penalize).slice(0, 6).join(', ')}.</>}
        </div>
      )}

      <div className="glass rounded-2xl p-4 space-y-3">
        <div className="grid gap-2 md:grid-cols-[1fr_auto_auto_auto]">
          <div className="relative">
            <Search size={16} className="pointer-events-none absolute left-3 top-3 text-slate-400" />
            <input
              value={q}
              onChange={e => setQ(e.target.value)}
              placeholder="Search title, company, location or skill..."
              className="w-full rounded-lg py-2.5 pl-9 pr-3 text-sm"
            />
          </div>
          <select value={min} onChange={e => setMin(Number(e.target.value))} className="rounded-lg bg-black/30 border border-[var(--border-soft)] px-3 py-2.5 text-sm" aria-label="Minimum score">
            {[0, 50, 60, 70, 80, 90].map(v => <option key={v} value={v}>Min score: {v}%</option>)}
          </select>
          <select value={source} onChange={e => setSource(e.target.value)} className="rounded-lg bg-black/30 border border-[var(--border-soft)] px-3 py-2.5 text-sm" aria-label="Source">
            <option value="">All sources</option>
            {sources.map(s => <option key={s} value={s}>{s}</option>)}
          </select>
          <select value={sort} onChange={e => setSort(e.target.value)} className="rounded-lg bg-black/30 border border-[var(--border-soft)] px-3 py-2.5 text-sm" aria-label="Sort">
            <option value="score">Sort: Best match</option>
            <option value="newest">Sort: Newest</option>
            <option value="company">Sort: Company A-Z</option>
          </select>
        </div>
        <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-xs text-[var(--muted)]">
          <label className="flex cursor-pointer items-center gap-2">
            <input type="checkbox" checked={hideIrrelevant} onChange={e => setHideIrrelevant(e.target.checked)} />
            Hide unrelated listings
          </label>
          <label className="flex cursor-pointer items-center gap-2">
            <input type="checkbox" checked={remoteOnly} onChange={e => setRemoteOnly(e.target.checked)} />
            Remote only
          </label>
          <span className="inline-flex items-center gap-1"><Sparkles size={12} /> Showing {shown} of {total}</span>
          <button onClick={reload} className="ml-auto inline-flex items-center gap-1.5 rounded-md border border-[var(--border-soft)] px-2.5 py-1.5 hover:bg-white/5">
            <RefreshCw size={12} className={loading ? 'animate-spin' : ''} /> Refresh
          </button>
        </div>
      </div>

      {jobs.length > 0 && (
        <div className="glass rounded-2xl p-3 flex flex-wrap items-center gap-3 text-sm">
          <label className="flex cursor-pointer items-center gap-2">
            <input type="checkbox" checked={allSelected} onChange={e => setSelected(e.target.checked ? jobs.map((j: any) => j.job_id) : [])} />
            <span className="text-[var(--muted)]">{selected.length} selected</span>
          </label>
          <button disabled={!selected.length || busy} onClick={() => bulk('approve')} className="inline-flex items-center gap-1.5 rounded-md border border-emerald-400/30 px-3 py-1.5 text-emerald-200 hover:bg-emerald-500/10 disabled:opacity-40">
            <Check size={14} /> Approve selected
          </button>
          <button disabled={!selected.length || busy} onClick={() => bulk('reject')} className="inline-flex items-center gap-1.5 rounded-md border border-red-400/30 px-3 py-1.5 text-red-200 hover:bg-red-500/10 disabled:opacity-40">
            <X size={14} /> Reject selected
          </button>
          {selected.length > 0 && <button onClick={() => setSelected([])} className="text-xs text-[var(--muted)] hover:text-slate-200">Clear selection</button>}
        </div>
      )}

      {loading ? (
        <div className="space-y-3">
          {[0, 1, 2].map(i => (
            <div key={i} className="glass animate-pulse rounded-2xl p-4">
              <div className="h-4 w-1/3 rounded bg-white/10" />
              <div className="mt-2 h-3 w-1/4 rounded bg-white/5" />
              <div className="mt-4 h-3 w-full rounded bg-white/5" />
            </div>
          ))}
        </div>
      ) : jobs.length === 0 ? (
        <div className="glass rounded-2xl p-8 text-center">
          <Inbox size={28} className="mx-auto text-slate-500" />
          <div className="mt-3 text-sm text-slate-200">No matches with these filters.</div>
          <p className="mt-1 text-xs text-[var(--muted)]">Run Job Discovery to collect roles, or relax the filters below.</p>
          <button onClick={clearFilters} className="mt-4 rounded-md border border-cyan-400/30 px-3 py-1.5 text-sm text-cyan-200 hover:bg-cyan-500/10">Clear filters</button>
          {activeFilters && <div className="mt-2 text-[11px] text-[var(--muted)]">Filters are active.</div>}
        </div>
      ) : (
        <div className="grid gap-3">
          {jobs.map((j: any) => {
            const tone = scoreTone(Number(j.score) || 0)
            const isOpen = expanded === j.job_id
            const matching: string[] = j.matching_skills || []
            const missing: string[] = j.missing_skills || []
            return (
              <article key={j.job_id} className="rounded-2xl border border-[var(--border-soft)] bg-black/20 p-4">
                <div className="flex items-start gap-3">
                  <input
                    type="checkbox"
                    className="mt-1"
                    aria-label={`Select ${j.title}`}
                    checked={selected.includes(j.job_id)}
                    onChange={e => setSelected(e.target.checked ? [...selected, j.job_id] : selected.filter(id => id !== j.job_id))}
                  />
                  <div className="min-w-0 flex-1">
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        <h2 className="truncate font-semibold text-slate-100">{j.title}</h2>
                        <div className="mt-1 flex flex-wrap gap-x-3 gap-y-1 text-xs text-[var(--muted)]">
                          <span className="inline-flex items-center gap-1"><Building2 size={12} />{j.company || 'Company not published'}</span>
                          <span className="inline-flex items-center gap-1"><MapPin size={12} />{j.location || 'Location not published'}</span>
                          {j.employment_type && <span>{j.employment_type}</span>}
                        </div>
                      </div>
                      <div className="shrink-0 text-right">
                        <div className={`text-xl font-semibold ${tone.text}`}>{Math.round(Number(j.score) || 0)}%</div>
                        <div className="text-[10px] uppercase tracking-wide text-[var(--muted)]">{tone.label}</div>
                      </div>
                    </div>

                    <div className="mt-2 flex flex-wrap gap-1.5 text-[11px]">
                      {j.source && <span className="rounded border border-[var(--border-soft)] px-1.5 py-0.5">{j.source}</span>}
                      {j.seniority && <span className="rounded border border-[var(--border-soft)] px-1.5 py-0.5">{j.seniority}</span>}
                      {j.status && <span className="rounded border border-cyan-400/30 px-1.5 py-0.5 text-cyan-200">{j.status}</span>}
                      {j.feedback && (
                        <span className={`rounded border px-1.5 py-0.5 ${j.feedback === 'good' ? 'border-emerald-400/30 text-emerald-200' : 'border-red-400/30 text-red-200'}`}>
                          {j.feedback}
                        </span>
                      )}
                    </div>

                    <div className="mt-2.5 grid gap-1.5 text-xs">
                      <div className="flex flex-wrap items-center gap-1.5">
                        <span className="text-[var(--muted)]">Matching:</span>
                        {matching.length ? matching.slice(0, 6).map(s => (
                          <span key={s} className="rounded-full border border-emerald-400/25 bg-emerald-500/10 px-2 py-0.5 text-emerald-200">{s}</span>
                        )) : <span className="text-amber-300/90">no skill overlap detected — review manually</span>}
                        {matching.length > 6 && <span className="text-[var(--muted)]">+{matching.length - 6}</span>}
                      </div>
                      {missing.length > 0 && (
                        <div className="flex flex-wrap items-center gap-1.5">
                          <span className="text-[var(--muted)]">Gaps:</span>
                          {missing.slice(0, 6).map(s => (
                            <span key={s} className="rounded-full border border-amber-400/25 bg-amber-500/10 px-2 py-0.5 text-amber-200">{s}</span>
                          ))}
                          {missing.length > 6 && <span className="text-[var(--muted)]">+{missing.length - 6}</span>}
                        </div>
                      )}
                    </div>

                    <div className="mt-3 grid grid-cols-2 gap-x-4 gap-y-1.5 sm:grid-cols-5">
                      {COMPONENTS.map(([key, label]) => {
                        const value = Number(j.components?.[key] ?? 0)
                        return (
                          <div key={key} title={j.notes?.[key] || ''}>
                            <div className="flex items-center justify-between text-[10px] text-[var(--muted)]">
                              <span>{label}</span>
                              <span>{Math.round(value)}%</span>
                            </div>
                            <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-white/10">
                              <div className={`h-full ${scoreTone(value).bar}`} style={{ width: `${Math.max(0, Math.min(100, value))}%` }} />
                            </div>
                          </div>
                        )
                      })}
                    </div>

                    {isOpen && (
                      <div className="mt-3 space-y-3 rounded-xl border border-[var(--border-soft)] bg-black/20 p-3">
                        <p className="text-xs leading-relaxed text-slate-300">
                          {j.description || 'No description was provided by this source. Open the listing for full details.'}
                        </p>
                        {j.required_skills?.length > 0 && (
                          <div className="text-[11px] text-[var(--muted)]">
                            <span className="text-slate-300">Required skills: </span>{j.required_skills.join(', ')}
                          </div>
                        )}
                        {j.tags?.length > 0 && (
                          <div className="text-[11px] text-[var(--muted)]">
                            <span className="text-slate-300">Tags: </span>{j.tags.join(', ')}
                          </div>
                        )}
                        <div className="grid gap-1 text-[11px] text-[var(--muted)] sm:grid-cols-2">
                          {Object.entries(j.notes || {}).map(([k, v]: any) => (
                            <div key={k}><span className="text-slate-400">{k}:</span> {String(v)}</div>
                          ))}
                        </div>
                      </div>
                    )}

                    <div className="mt-3 flex flex-wrap items-center gap-2 text-xs">
                      {j.url && (
                        <a href={j.url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1.5 rounded-md border border-cyan-400/30 px-3 py-1.5 text-cyan-200 hover:bg-cyan-500/10">
                          <ExternalLink size={13} /> Open role
                        </a>
                      )}
                      <button onClick={() => prepare(j.job_id)} className="rounded-md border border-amber-400/30 px-3 py-1.5 text-amber-200 hover:bg-amber-500/10">
                        Prepare application <span className="text-[10px] text-amber-300/70">(needs approval)</span>
                      </button>
                      <button onClick={() => setExpanded(isOpen ? null : j.job_id)} className="inline-flex items-center gap-1.5 rounded-md border border-[var(--border-soft)] px-3 py-1.5 text-slate-300 hover:bg-white/5">
                        {isOpen ? <ChevronUp size={13} /> : <ChevronDown size={13} />} {isOpen ? 'Hide details' : 'Details'}
                      </button>
                      <button disabled={busyId === j.job_id} onClick={() => mark(j.job_id, 'good')} className="inline-flex items-center gap-1.5 rounded-md border border-emerald-400/30 px-3 py-1.5 text-emerald-200 hover:bg-emerald-500/10 disabled:opacity-40">
                        <ThumbsUp size={13} /> Good match
                      </button>
                      <button disabled={busyId === j.job_id} onClick={() => mark(j.job_id, 'bad')} className="inline-flex items-center gap-1.5 rounded-md border border-red-400/30 px-3 py-1.5 text-red-200 hover:bg-red-500/10 disabled:opacity-40">
                        <ThumbsDown size={13} /> Not for me
                      </button>
                    </div>
                  </div>
                </div>
              </article>
            )
          })}
        </div>
      )}
    </div>
  )
}
