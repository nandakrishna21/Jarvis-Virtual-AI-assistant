import { useEffect, useState } from 'react'
import { api } from '../services/api'
import { FileText, Download, Sparkles, Trash2, RefreshCw } from 'lucide-react'

const sectionTypes = ['summary', 'experience', 'education', 'projects', 'skills', 'custom']
const blankSection = { section_type: 'experience', title: '', organization: '', location: '', start_date: '', end_date: '', description: '' }

export default function DocumentStudio() {
  const [resumes, setResumes] = useState<any[]>([])
  const [jobs, setJobs] = useState<any[]>([])
  const [resumeId, setResumeId] = useState<number | null>(null)
  const [jobId, setJobId] = useState<number | null>(null)
  const [docs, setDocs] = useState<any[]>([])
  const [sections, setSections] = useState<any[]>([])
  const [draft, setDraft] = useState<any>({ ...blankSection })
  const [msg, setMsg] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [view, setView] = useState<any | null>(null)

  async function loadAll() {
    try {
      const r = await api.get<any>('/resumes')
      setResumes(r?.resumes || [])
      if (r?.resumes?.length && !resumeId) setResumeId(r.resumes[0].id)
    } catch {}
    try {
      const j = await api.get<any[]>('/jobs')
      setJobs(Array.isArray(j) ? j : (j as any)?.jobs || [])
    } catch {}
    try {
      const d = await api.get<any>('/documents')
      setDocs(d?.documents || [])
    } catch {}
  }
  useEffect(() => {
    let on = true
    ;(async () => {
      try {
        const r = await api.get<any>('/resumes')
        if (on) setResumes(r?.resumes || [])
        try {
          const j = await api.get<any[]>('/jobs')
          if (on) setJobs(Array.isArray(j) ? j : (j as any)?.jobs || [])
        } catch {}
        try {
          const d = await api.get<any>('/documents')
          if (on) setDocs(d?.documents || [])
        } catch {}
      } catch {}
    })()
    return () => { on = false }
  }, [])

  async function loadSections() {
    if (!resumeId) return
    try {
      const r = await api.get<any>(`/resumes/${resumeId}/sections`)
      setSections(r?.sections || [])
    } catch { setSections([]) }
  }
  useEffect(() => {
    let on = true
    ;(async () => {
      if (!resumeId) { if (on) setSections([]); return }
      try {
        const r = await api.get<any>(`/resumes/${resumeId}/sections`)
        if (on) setSections(r?.sections || [])
      } catch { if (on) setSections([]) }
    })()
    return () => { on = false }
  }, [resumeId])

  async function addSection() {
    if (!resumeId) { setMsg('Upload a resume first.'); return }
    if (!draft.title && !draft.description) { setMsg('Add a title or a description.'); return }
    try {
      await api.post(`/resumes/${resumeId}/sections`, draft)
      setDraft({ ...blankSection })
      setMsg('Section saved.')
      loadSections()
    } catch (e: any) { setMsg(e?.message || 'Failed to save section') }
  }

  async function removeSection(id: number) {
    try { await api.del(`/sections/${id}`); loadSections() }
    catch (e: any) { setMsg(e?.message || 'Failed') }
  }

  async function generate() {
    if (!resumeId) { setMsg('Upload a resume first.'); return }
    setBusy(true); setMsg(null)
    try {
      const res = await api.post<any>('/documents/generate', {
        resume_id: resumeId,
        job_id: jobId || null,
        types: ['resume', 'cover_letter'],
      })
      if (res?.error) setMsg(res.error)
      else {
        setMsg(`Generated ${res.count} document version(s). Drafts only, nothing submitted.`)
        loadAll()
      }
    } catch (e: any) { setMsg(e?.message || 'Generation failed') }
    finally { setBusy(false) }
  }

  async function requestViaChat() {
    if (!jobId) { setMsg('Pick a job first so I can tailor it.'); return }
    setMsg(null)
    try {
      const res = await api.post<any>('/assistant/chat', { message: `tailor my resume for job ${jobId}` })
      setMsg(res?.response || 'Approval requested. Review it in Assistant or Approvals.')
    } catch (e: any) { setMsg(e?.message || 'Failed') }
  }

  return (
    <div className="space-y-4">
      <div className="glass-strong rounded-2xl p-5">
        <div className="flex items-center gap-2 text-cyan-100"><FileText size={18} /><h1 className="text-lg font-semibold">Document Studio</h1></div>
        <p className="text-sm text-[var(--muted)] mt-1">
          Build structured resume sections, generate job-specific resumes and cover letters, and keep every version for download.
          Drafts only. Nothing is ever submitted to an employer.
        </p>
        <div className="mt-4 grid grid-cols-1 md:grid-cols-3 gap-3 items-end">
          <label className="text-xs text-[var(--muted)]">
            Resume
            <select value={resumeId ?? ''} onChange={e => setResumeId(Number(e.target.value))} className="mt-1 w-full px-2 py-1.5 rounded-lg bg-black/30 border border-[var(--border-soft)]">
              {resumes.length === 0 && <option value="">No resume uploaded</option>}
              {resumes.map(r => <option key={r.id} value={r.id}>#{r.id} · {r.skill_count} skills</option>)}
            </select>
          </label>
          <label className="text-xs text-[var(--muted)]">
            Target job (optional)
            <select value={jobId ?? ''} onChange={e => setJobId(e.target.value ? Number(e.target.value) : null)} className="mt-1 w-full px-2 py-1.5 rounded-lg bg-black/30 border border-[var(--border-soft)]">
              <option value="">General (no job)</option>
              {jobs.map(j => <option key={j.id} value={j.id}>#{j.id} · {j.title} {j.company ? `· ${j.company}` : ''}</option>)}
            </select>
          </label>
          <div className="flex gap-2">
            <button onClick={generate} disabled={busy || !resumeId} className="px-4 py-2 rounded-lg bg-cyan-500/20 border border-cyan-400/30 text-cyan-100 hover:bg-cyan-500/30 disabled:opacity-50 inline-flex items-center gap-2">
              <Sparkles size={14} />{busy ? 'Generating...' : 'Generate'}
            </button>
            <button onClick={requestViaChat} className="px-3 py-2 rounded-lg border border-[var(--border-soft)] text-[var(--muted)] hover:text-cyan-200 inline-flex items-center gap-2">
              <RefreshCw size={14} />Via assistant
            </button>
          </div>
        </div>
        {msg && <div className="mt-3 text-sm text-slate-200">{msg}</div>}
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
        <div className="glass rounded-2xl p-4">
          <div className="text-sm text-cyan-200 mb-3">Resume Sections ({sections.length})</div>
          <div className="space-y-2 max-h-[320px] overflow-auto pr-1">
            {sections.length === 0 && <div className="text-sm text-[var(--muted)]">No structured sections yet. Add them below to get tailored documents.</div>}
            {sections.map(s => (
              <div key={s.id} className="p-3 rounded-xl bg-black/20 border border-[var(--border-soft)]">
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <div className="text-sm text-slate-100">{s.title || s.section_type}</div>
                    <div className="text-[11px] text-[var(--muted)]">
                      {s.section_type}{s.organization ? ` · ${s.organization}` : ''}{s.start_date || s.end_date ? ` · ${s.start_date || ''} - ${s.end_date || 'present'}` : ''}
                    </div>
                  </div>
                  <button onClick={() => removeSection(s.id)} className="text-red-300/80 hover:text-red-300"><Trash2 size={14} /></button>
                </div>
                {s.description && <p className="mt-1.5 text-xs text-slate-300 whitespace-pre-wrap">{s.description}</p>}
              </div>
            ))}
          </div>

          <div className="mt-4 border-t border-[var(--border-soft)] pt-4 space-y-2">
            <div className="text-xs text-[var(--muted)]">Add a section</div>
            <div className="grid grid-cols-2 gap-2">
              <select value={draft.section_type} onChange={e => setDraft({ ...draft, section_type: e.target.value })} className="px-2 py-1.5 rounded-lg bg-black/30 border border-[var(--border-soft)] text-xs">
                {sectionTypes.map(t => <option key={t} value={t}>{t}</option>)}
              </select>
              <input value={draft.title} onChange={e => setDraft({ ...draft, title: e.target.value })} placeholder="Title (e.g. Backend Developer)" className="px-2 py-1.5 rounded-lg bg-black/30 border border-[var(--border-soft)] text-xs" />
              <input value={draft.organization} onChange={e => setDraft({ ...draft, organization: e.target.value })} placeholder="Company / school" className="px-2 py-1.5 rounded-lg bg-black/30 border border-[var(--border-soft)] text-xs" />
              <input value={draft.location} onChange={e => setDraft({ ...draft, location: e.target.value })} placeholder="Location" className="px-2 py-1.5 rounded-lg bg-black/30 border border-[var(--border-soft)] text-xs" />
              <input value={draft.start_date} onChange={e => setDraft({ ...draft, start_date: e.target.value })} placeholder="Start (YYYY-MM)" className="px-2 py-1.5 rounded-lg bg-black/30 border border-[var(--border-soft)] text-xs" />
              <input value={draft.end_date} onChange={e => setDraft({ ...draft, end_date: e.target.value })} placeholder="End (YYYY-MM)" className="px-2 py-1.5 rounded-lg bg-black/30 border border-[var(--border-soft)] text-xs" />
            </div>
            <textarea value={draft.description} onChange={e => setDraft({ ...draft, description: e.target.value })} rows={3} placeholder="What you did. Use your real facts only." className="w-full px-2 py-1.5 rounded-lg bg-black/30 border border-[var(--border-soft)] text-xs" />
            <button onClick={addSection} className="px-3 py-1.5 rounded-lg bg-cyan-500/15 border border-cyan-400/30 text-cyan-100 text-xs">Save section</button>
          </div>
        </div>

        <div className="glass rounded-2xl p-4">
          <div className="text-sm text-cyan-200 mb-3">Document Versions ({docs.length})</div>
          <div className="space-y-2 max-h-[420px] overflow-auto pr-1">
            {docs.length === 0 && <div className="text-sm text-[var(--muted)]">No documents generated yet.</div>}
            {docs.map(d => (
              <div key={d.id} className="p-3 rounded-xl bg-black/20 border border-[var(--border-soft)]">
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <div className="text-sm text-slate-100 capitalize">{d.doc_type.replace('_', ' ')} · v{d.version}</div>
                    <div className="text-[11px] text-[var(--muted)]">
                      job #{d.job_id ?? 'n/a'}{d.match_score != null ? ` · match ${d.match_score}%` : ''} · {d.created_at?.slice(0, 16).replace('T', ' ')}
                    </div>
                  </div>
                  <div className="flex gap-1.5">
                    <button onClick={() => setView(d)} className="text-cyan-300 hover:text-cyan-200 text-[11px]">View</button>
                    <a href={`/api/documents/${d.id}/download`} className="text-cyan-300 hover:text-cyan-200" title="Download"><Download size={14} /></a>
                  </div>
                </div>
                {d.highlights?.length > 0 && (
                  <ul className="mt-1.5 text-[11px] text-slate-400 list-disc pl-4">
                    {d.highlights.map((h: string, i: number) => <li key={i}>{h}</li>)}
                  </ul>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>

      {view && (
        <div className="glass rounded-2xl p-4">
          <div className="flex items-center justify-between mb-3">
            <div className="text-sm text-cyan-200 capitalize">{view.doc_type.replace('_', ' ')} · v{view.version}</div>
            <div className="flex gap-2">
              <a href={`/api/documents/${view.id}/download`} className="px-3 py-1.5 rounded-lg bg-cyan-500/15 border border-cyan-400/30 text-cyan-100 text-xs inline-flex items-center gap-1"><Download size={12} />Download</a>
              <button onClick={() => setView(null)} className="px-3 py-1.5 rounded-lg border border-[var(--border-soft)] text-[var(--muted)] text-xs">Close</button>
            </div>
          </div>
          <pre className="text-xs text-slate-300 whitespace-pre-wrap max-h-96 overflow-auto bg-black/20 rounded p-3 border border-[var(--border-soft)]">{view.content}</pre>
        </div>
      )}
    </div>
  )
}
