import { useEffect, useState } from 'react'
import { api } from '../services/api'
import { useAppDispatch, useAppSelector } from '../store/hooks'
import { Wand2, FileText, Download, RefreshCw, Sparkles, AlertTriangle, Check, Plus, X, Save, User } from 'lucide-react'

type Group = 'experience' | 'education' | 'projects'

export default function ResumeGenerator() {
  const dispatch = useAppDispatch()
  const details = useAppSelector((s) => s.resume.details)
  const resumeId = useAppSelector((s) => s.resume.resumeId)
  const resumeMessage = useAppSelector((s) => s.resume.message)
  const resumeDirty = useAppSelector((s) => s.resume.dirty)

  const [jd, setJd] = useState('')
  const [role, setRole] = useState('')
  const [company, setCompany] = useState('')
  const [polish, setPolish] = useState(true)
  const [result, setResult] = useState<any>(null)
  const [versions, setVersions] = useState<any[]>([])
  const [busy, setBusy] = useState(false)
  const [msg, setMsg] = useState<string|null>(null)
  const [activeTab, setActiveTab] = useState<'generate'|'details'|'versions'>('generate')
  const [skillInput, setSkillInput] = useState('')
  const [linkInput, setLinkInput] = useState('')

  async function loadVersions() {
    try {
      const r = await api.get<any>('/resume-generator/versions?limit=20')
      setVersions(r?.documents || [])
    } catch {}
  }

  async function loadDetails() {
    try {
      const list = await api.get<any>('/resumes')
      const activeId = list?.active_id ?? list?.resumes?.[0]?.id ?? null
      if (!activeId) return
      const r = await api.get<any>(`/resumes/${activeId}/details`)
      if (r?.details) {
        dispatch({ type: 'resume/load', payload: { resumeId: activeId, details: r.details } })
      }
    } catch {}
  }

  useEffect(() => {
    let on = true
    ;(async () => {
      try {
        const r = await api.get<any>('/resume-generator/versions?limit=20')
        if (on) setVersions(r?.documents || [])
      } catch {}
    })()
    return () => { on = false }
  }, [])

  async function generate(save: boolean) {
    if (!jd.trim()) { setMsg('Paste the job description first.'); return }
    setBusy(true); setMsg(null)
    try {
      const path = save ? '/resume-generator/save' : '/resume-generator/preview'
      const r = await api.post<any>(path, { jd, role: role || null, company: company || null, polish_summary: polish })
      if (r?.error) setMsg(r.error)
      else {
        setResult(r)
        setMsg(save ? 'Saved as a new version. Download it below.' : 'Preview ready - review it before saving.')
        if (save) await loadVersions()
      }
    } catch(e:any){ setMsg(e?.message||'Generation failed') }
    finally { setBusy(false) }
  }

  async function saveDetails() {
    if (!resumeId) { setMsg('Upload a resume first (Resume Intelligence page).'); return }
    setBusy(true); setMsg(null)
    dispatch({ type: 'resume/saving', payload: true })
    try {
      const r = await api.put<any>(`/resumes/${resumeId}/details`, details)
      if (r?.error) {
        dispatch({ type: 'resume/error', payload: r.error })
        setMsg(r.error)
      }
      else {
        dispatch({ type: 'resume/saved' })
        setMsg(`Saved. Resume text rebuilt from your details (${r?.resume?.text_length || 0} chars, ${r?.skills?.length || 0} skills).`)
        await loadDetails()
      }
    } catch(e:any){
      dispatch({ type: 'resume/error', payload: e?.message||'Could not save details' })
      setMsg(e?.message||'Could not save details')
    }
    finally { setBusy(false) }
  }

  const setField = (field: string, value: any) =>
    dispatch({ type: 'resume/setField', payload: { field, value } })

  const updateEntry = (group: Group, index: number, field: string, value: string) =>
    dispatch({ type: 'resume/setEntry', payload: { section: group, index, value: { [field]: value } } })

  const addEntry = (group: Group) => dispatch({ type: 'resume/addEntry', payload: { section: group } })
  const removeEntry = (group: Group, index: number) =>
    dispatch({ type: 'resume/removeEntry', payload: { section: group, index } })

  function addSkill() {
    const value = skillInput.trim().toLowerCase()
    if (!value || details.skills.includes(value)) { setSkillInput(''); return }
    setField('skills', [...details.skills, value]); setSkillInput('')
  }

  function addLink() {
    const value = linkInput.trim()
    if (!value || details.links.includes(value)) { setLinkInput(''); return }
    setField('links', [...details.links, value]); setLinkInput('')
  }

  const analysis = result?.analysis
  const content = result?.content || result?.document?.content || ''

  const entryForm = (group: Group, label: string) => (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <div className="text-xs text-[var(--muted)]">{label}</div>
        <button onClick={()=>addEntry(group)} className="px-2 py-1 rounded border border-cyan-400/30 text-cyan-200 inline-flex items-center gap-1"><Plus size={11}/> Add</button>
      </div>
      {details[group].length === 0 && <div className="text-xs text-[var(--muted)]">Nothing added yet.</div>}
      {details[group].map((entry, idx) => (
        <div key={idx} className="p-3 rounded-lg border border-[var(--border-soft)] bg-black/20 space-y-2">
          <div className="flex items-center gap-2">
            <input value={entry.title} onChange={e=>updateEntry(group, idx, 'title', e.target.value)}
              placeholder={group === 'education' ? 'Degree (e.g. B.Tech Computer Science)' : group === 'projects' ? 'Project name' : 'Role title (e.g. Backend Developer)'}
              className="flex-1 px-2 py-1.5 rounded text-xs bg-black/30 border border-[var(--border-soft)]" />
            <button onClick={()=>removeEntry(group, idx)} className="text-red-300 hover:text-red-200"><X size={13}/></button>
          </div>
          <div className="grid grid-cols-2 gap-2">
            <input value={entry.organization} onChange={e=>updateEntry(group, idx, 'organization', e.target.value)}
              placeholder={group === 'projects' ? 'Link / tech used' : 'Company / Institution'} className="px-2 py-1.5 rounded text-xs bg-black/30 border border-[var(--border-soft)]" />
            <input value={entry.location} onChange={e=>updateEntry(group, idx, 'location', e.target.value)} placeholder="Location (optional)" className="px-2 py-1.5 rounded text-xs bg-black/30 border border-[var(--border-soft)]" />
          </div>
          <div className="grid grid-cols-2 gap-2">
            <input value={entry.start_date} onChange={e=>updateEntry(group, idx, 'start_date', e.target.value)} placeholder="Start (e.g. 2024)" className="px-2 py-1.5 rounded text-xs bg-black/30 border border-[var(--border-soft)]" />
            <input value={entry.end_date} onChange={e=>updateEntry(group, idx, 'end_date', e.target.value)} placeholder="End (blank = present)" className="px-2 py-1.5 rounded text-xs bg-black/30 border border-[var(--border-soft)]" />
          </div>
          <textarea value={entry.description} onChange={e=>updateEntry(group, idx, 'description', e.target.value)} rows={4}
            placeholder="One achievement per line. Only real facts - the generator reuses these lines."
            className="w-full px-2 py-1.5 rounded text-xs bg-black/30 border border-[var(--border-soft)] font-mono" />
        </div>
      ))}
    </div>
  )

  return (
    <div className="space-y-4">
      <div className="glass-strong rounded-2xl p-4 sm:p-5">
        <div className="flex items-center gap-2 text-cyan-100"><Wand2 size={18}/><h1 className="text-lg font-semibold">Resume Generator</h1></div>
        <p className="text-sm text-[var(--muted)] mt-1">Paste a job description. JARVIS reads your old resume, keeps every fact you wrote, and re-orders it around that job - then tells you exactly which requirements you still lack.</p>
        <div className="mt-4 flex flex-wrap gap-2 text-sm">
          <button onClick={()=>setActiveTab('generate')} className={`px-3 py-1.5 rounded-lg border ${activeTab==='generate' ? 'border-cyan-400/40 text-cyan-200 bg-cyan-500/10' : 'border-[var(--border-soft)] text-[var(--muted)]'}`}>Generate</button>
          <button onClick={()=>{ setActiveTab('details'); loadDetails() }} className={`px-3 py-1.5 rounded-lg border ${activeTab==='details' ? 'border-cyan-400/40 text-cyan-200 bg-cyan-500/10' : 'border-[var(--border-soft)] text-[var(--muted)]'}`}>My details</button>
          <button onClick={()=>{ setActiveTab('versions'); loadVersions() }} className={`px-3 py-1.5 rounded-lg border ${activeTab==='versions' ? 'border-cyan-400/40 text-cyan-200 bg-cyan-500/10' : 'border-[var(--border-soft)] text-[var(--muted)]'}`}>Saved versions</button>
        </div>
        {msg && <div className="mt-3 text-sm text-slate-200">{msg}</div>}
        {resumeMessage && !msg && <div className="mt-3 text-xs text-[var(--muted)]">{resumeMessage}</div>}
      </div>

      {activeTab === 'generate' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <div className="space-y-4">
            <div className="glass rounded-2xl p-4">
              <div className="text-sm text-cyan-200 mb-2">Job description</div>
              <textarea value={jd} onChange={e=>setJd(e.target.value)} rows={16}
                placeholder={'Paste the full job posting here.\n\nExample:\nPython Backend Developer\nCompany: Acme Technologies\nRequirements:\n- Python, FastAPI, SQL, Docker...'}
                className="w-full text-xs text-slate-200 bg-black/20 rounded p-3 border border-[var(--border-soft)] font-mono" />
              <div className="grid grid-cols-2 gap-2 mt-3">
                <input value={role} onChange={e=>setRole(e.target.value)} placeholder="Target role (optional)" className="px-3 py-2 rounded-lg text-sm bg-black/20 border border-[var(--border-soft)]" />
                <input value={company} onChange={e=>setCompany(e.target.value)} placeholder="Company (optional)" className="px-3 py-2 rounded-lg text-sm bg-black/20 border border-[var(--border-soft)]" />
              </div>
              <label className="flex items-center gap-2 mt-3 text-xs text-[var(--muted)]">
                <input type="checkbox" checked={polish} onChange={e=>setPolish(e.target.checked)} />
                <span className="inline-flex items-center gap-1"><Sparkles size={12}/> Let the AI rewrite the summary (checked against your facts)</span>
              </label>
              <div className="flex flex-wrap gap-2 mt-3">
                <button onClick={()=>generate(false)} disabled={busy || !jd.trim()} className="px-4 py-2 rounded-lg bg-cyan-500/20 border border-cyan-400/30 text-cyan-100 hover:bg-cyan-500/30 disabled:opacity-50 inline-flex items-center gap-2"><RefreshCw size={14}/>{busy?'Working...':'Preview resume'}</button>
                <button onClick={()=>generate(true)} disabled={busy || !jd.trim()} className="px-4 py-2 rounded-lg border border-emerald-400/30 text-emerald-200 hover:bg-emerald-500/10 disabled:opacity-50 inline-flex items-center gap-2"><FileText size={14}/>Save version</button>
              </div>
            </div>

            {analysis && (
              <div className="glass rounded-2xl p-4">
                <div className="text-sm text-cyan-200 mb-2">Coverage analysis</div>
                <div className="flex items-center gap-3 mb-3">
                  <div className="text-2xl font-semibold text-cyan-100">{analysis.coverage_pct}%</div>
                  <div className="text-xs text-[var(--muted)]">of the JD skills are evidenced in your resume</div>
                </div>
                <div className="text-xs mb-2">
                  <div className="text-emerald-300 mb-1">Covered ({analysis.covered.length})</div>
                  <div className="flex flex-wrap gap-1.5">
                    {analysis.covered.map((s:string)=> <span key={s} className="px-2 py-0.5 rounded-full border border-emerald-400/30 text-emerald-200 inline-flex items-center gap-1"><Check size={10}/>{s}</span>)}
                    {analysis.covered.length===0 && <span className="text-[var(--muted)]">none found</span>}
                  </div>
                </div>
                <div className="text-xs">
                  <div className="text-amber-300 mb-1 inline-flex items-center gap-1"><AlertTriangle size={11}/> Not in your resume yet ({analysis.gaps.length})</div>
                  <div className="flex flex-wrap gap-1.5">
                    {analysis.gaps.map((s:string)=> <span key={s} className="px-2 py-0.5 rounded-full border border-amber-400/30 text-amber-200">{s}</span>)}
                    {analysis.gaps.length===0 && <span className="text-[var(--muted)]">nothing missing</span>}
                  </div>
                  <div className="text-[var(--muted)] mt-2">Gaps are never written into the resume. Add them to your resume first if you want to claim them.</div>
                </div>
                {analysis.min_years > 0 && <div className="text-xs text-[var(--muted)] mt-2">JD asks for {analysis.min_years}+ year(s) of experience.</div>}
              </div>
            )}
          </div>

          <div className="glass rounded-2xl p-4">
            <div className="flex items-center justify-between mb-2">
              <div className="text-sm text-cyan-200">Generated resume</div>
              {result?.document?.id && (
                <a href={`/api/resume-generator/${result.document.id}/download`} download
                  className="px-3 py-1.5 rounded-md border border-cyan-400/30 text-cyan-200 hover:bg-cyan-500/10 inline-flex items-center gap-1.5"><Download size={13}/> Download</a>
              )}
            </div>
            {!content ? <div className="text-sm text-[var(--muted)]">Paste a job description and press “Preview resume”.</div> : (
              <pre className="text-xs text-slate-300 whitespace-pre-wrap max-h-[34rem] overflow-auto bg-black/20 rounded p-3 border border-[var(--border-soft)]">{content}</pre>
            )}
            {result?.highlights && (
              <div className="mt-3 text-xs text-[var(--muted)] space-y-1">
                {result.highlights.map((h:string)=> <div key={h}>- {h}</div>)}
              </div>
            )}
          </div>
        </div>
      )}

      {activeTab === 'details' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <div className="glass rounded-2xl p-4 space-y-3">
            <div className="flex items-center gap-2 text-cyan-100"><User size={16}/><span className="text-sm font-medium">Your details</span></div>
            <div className="text-xs text-[var(--muted)]">Fill this in once. The Resume Generator, Document Studio and job matching all read from it - nothing is invented, only what you type here. Your edits are kept on this device even if you close the app.</div>
            <div className="grid grid-cols-2 gap-2">
              <input value={details.name} onChange={e=>setField('name', e.target.value)} placeholder="Full name" className="px-3 py-2 rounded-lg text-sm bg-black/20 border border-[var(--border-soft)]" />
              <input value={details.location} onChange={e=>setField('location', e.target.value)} placeholder="City, Country" className="px-3 py-2 rounded-lg text-sm bg-black/20 border border-[var(--border-soft)]" />
              <input value={details.email} onChange={e=>setField('email', e.target.value)} placeholder="Email" className="px-3 py-2 rounded-lg text-sm bg-black/20 border border-[var(--border-soft)]" />
              <input value={details.phone} onChange={e=>setField('phone', e.target.value)} placeholder="Phone" className="px-3 py-2 rounded-lg text-sm bg-black/20 border border-[var(--border-soft)]" />
            </div>
            <div>
              <div className="text-xs text-[var(--muted)] mb-1">Links (LinkedIn, GitHub, portfolio)</div>
              <div className="flex flex-wrap gap-1.5 mb-2">
                {details.links.map(l => (
                  <span key={l} className="text-xs px-2 py-1 rounded-full border border-cyan-400/20 text-cyan-100 inline-flex items-center gap-1">
                    {l}<button onClick={()=>setField('links', details.links.filter(x=>x!==l))}><X size={11}/></button>
                  </span>
                ))}
              </div>
              <div className="flex gap-2">
                <input value={linkInput} onChange={e=>setLinkInput(e.target.value)} onKeyDown={e=>{ if(e.key==='Enter'){ e.preventDefault(); addLink() } }} placeholder="https://linkedin.com/in/you" className="flex-1 px-3 py-2 rounded-lg text-sm bg-black/20 border border-[var(--border-soft)]" />
                <button onClick={addLink} className="px-3 py-2 rounded-lg border border-cyan-400/30 text-cyan-200"><Plus size={14}/></button>
              </div>
            </div>
            <div>
              <div className="text-xs text-[var(--muted)] mb-1">Professional summary</div>
              <textarea value={details.summary} onChange={e=>setField('summary', e.target.value)} rows={4}
                placeholder="2-3 lines about what you do. The AI may polish this for a specific JD."
                className="w-full px-3 py-2 rounded-lg text-sm bg-black/20 border border-[var(--border-soft)]" />
            </div>
            <div>
              <div className="text-xs text-[var(--muted)] mb-1">Skills</div>
              <div className="flex flex-wrap gap-1.5 mb-2">
                {details.skills.map(s => (
                  <span key={s} className="text-xs px-2 py-1 rounded-full bg-cyan-500/10 border border-cyan-400/20 text-cyan-100 inline-flex items-center gap-1">
                    {s}<button onClick={()=>setField('skills', details.skills.filter(x=>x!==s))}><X size={11}/></button>
                  </span>
                ))}
              </div>
              <div className="flex gap-2">
                <input value={skillInput} onChange={e=>setSkillInput(e.target.value)} onKeyDown={e=>{ if(e.key==='Enter'){ e.preventDefault(); addSkill() } }} placeholder="add a skill (e.g. fastapi)" className="flex-1 px-3 py-2 rounded-lg text-sm bg-black/20 border border-[var(--border-soft)]" />
                <button onClick={addSkill} className="px-3 py-2 rounded-lg border border-cyan-400/30 text-cyan-200"><Plus size={14}/></button>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <button onClick={saveDetails} disabled={busy} className="px-4 py-2 rounded-lg bg-cyan-500/20 border border-cyan-400/30 text-cyan-100 hover:bg-cyan-500/30 disabled:opacity-50 inline-flex items-center gap-2"><Save size={14}/>Save details</button>
              {resumeDirty && <span className="text-xs text-amber-300">Unsaved changes - kept on this device</span>}
            </div>
          </div>

          <div className="space-y-4">
            <div className="glass rounded-2xl p-4 space-y-4">
              {entryForm('experience', 'Experience')}
              {entryForm('projects', 'Projects')}
              {entryForm('education', 'Education')}
            </div>
          </div>
        </div>
      )}

      {activeTab === 'versions' && (
        <div className="glass rounded-2xl p-4">
          <div className="text-sm text-cyan-200 mb-3">Saved resume versions</div>
          <div className="space-y-2">
            {versions.length===0 && <div className="text-sm text-[var(--muted)]">No versions yet.</div>}
            {versions.map(v => (
              <div key={v.id} className="p-3 rounded-lg border border-[var(--border-soft)] bg-black/20 text-xs">
                <div className="flex items-center justify-between">
                  <span className="text-slate-200">Version {v.version} · {v.match_score ?? '--'}% coverage</span>
                  <a href={`/api/resume-generator/${v.id}/download`} download className="px-2 py-1 rounded border border-cyan-400/30 text-cyan-200 inline-flex items-center gap-1"><Download size={11}/> Download</a>
                </div>
                <div className="text-[var(--muted)] mt-1">{v.created_at}</div>
                {(v.highlights||[]).map((h:string)=> <div key={h} className="text-[var(--muted)]">- {h}</div>)}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
