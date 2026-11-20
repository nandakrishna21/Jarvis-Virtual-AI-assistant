import { useEffect, useState } from 'react'
import { api, uploadFile } from '../services/api'
import { FileUser, Upload, RefreshCw, Plus, X, Save, AlertTriangle, Check } from 'lucide-react'

export default function ResumeIntelligence() {
  const [resumes, setResumes] = useState<any[]>([])
  const [activeId, setActiveId] = useState<number|null>(null)
  const [profile, setProfile] = useState<any>(null)
  const [file, setFile] = useState<File|null>(null)
  const [msg, setMsg] = useState<string|null>(null)
  const [busy, setBusy] = useState(false)
  const [skillInput, setSkillInput] = useState('')
  const [skillDraft, setSkillDraft] = useState<string[]>([])
  const [textDraft, setTextDraft] = useState('')
  const [dirty, setDirty] = useState(false)

  async function load() {
    try {
      const r = await api.get<any>('/resumes')
      setResumes(r?.resumes || [])
      setActiveId(r?.active_id ?? (r?.resumes?.[0]?.id ?? null))
      const current = (r?.resumes || []).find((x:any)=>x.id === (r?.active_id ?? r?.resumes?.[0]?.id))
      if (current) { setSkillDraft(current.skills || []); setTextDraft(current.text_preview || ''); setDirty(false) }
    } catch {}
    try { const p = await api.get<any>('/profile'); setProfile(p) } catch {}
  }
  useEffect(()=>{ const t = setTimeout(() => { void load() }, 0); return () => clearTimeout(t) }, [])

  async function upload() {
    if (!file) return
    setBusy(true); setMsg(null)
    try {
      const r = await uploadFile<any>('/resumes/upload', file)
      if (r?.error) setMsg(r.error); else { setMsg(`Uploaded and analyzed. ${r?.skills?.length || 0} skills extracted.`); setFile(null); load() }
    } catch(e:any){ setMsg(e?.message||'Upload failed') }
    finally { setBusy(false) }
  }

  function addSkill() {
    const value = skillInput.trim().toLowerCase()
    if (!value || skillDraft.includes(value)) { setSkillInput(''); return }
    setSkillDraft([...skillDraft, value]); setSkillInput(''); setDirty(true)
  }

  function removeSkill(s: string) {
    setSkillDraft(skillDraft.filter(x => x !== s)); setDirty(true)
  }

  async function saveSkills() {
    if (!activeId) return
    setBusy(true); setMsg(null)
    try {
      await api.put(`/resumes/${activeId}`, { extracted_skills: skillDraft.join(',') })
      setMsg('Skills saved. Job matching now uses this list.')
      setDirty(false)
      await load()
    } catch(e:any){ setMsg(e?.message||'Save failed') }
    finally { setBusy(false) }
  }

  async function saveText() {
    if (!activeId) return
    setBusy(true); setMsg(null)
    try {
      const r = await api.put<any>(`/resumes/${activeId}`, { raw_text: textDraft })
      setMsg(`Text saved. ${r?.skill_count ?? 0} skills detected from it.`)
      setDirty(false)
      await load()
    } catch(e:any){ setMsg(e?.message||'Save failed') }
    finally { setBusy(false) }
  }

  async function activate(id: number) {
    setBusy(true); setMsg(null)
    try {
      await api.post(`/resumes/${id}/activate`)
      setMsg('This resume is now the active one for job matching.')
      await load()
    } catch(e:any){ setMsg(e?.message||'Could not activate') }
    finally { setBusy(false) }
  }

  const active = resumes.find(r => r.id === activeId) || resumes[0]

  return (
    <div className="space-y-4">
      <div className="glass-strong rounded-2xl p-5">
        <div className="flex items-center gap-2 text-cyan-100"><FileUser size={18}/><h1 className="text-lg font-semibold">Resume Intelligence</h1></div>
        <p className="text-sm text-[var(--muted)] mt-1">Upload your resume (PDF/DOCX/TXT) or paste the text. JARVIS extracts skills from the real content, and you can correct them here - matching uses exactly what you save.</p>
        <div className="mt-4 flex flex-wrap items-center gap-2">
          <input type="file" accept=".pdf,.docx,.txt" onChange={e=>setFile(e.target.files?.[0]||null)} className="text-sm" />
          <button onClick={upload} disabled={!file||busy} className="px-4 py-2 rounded-lg bg-cyan-500/20 border border-cyan-400/30 text-cyan-100 hover:bg-cyan-500/30 disabled:opacity-50 inline-flex items-center gap-2"><Upload size={14}/>{busy?'Analyzing...':'Upload & Analyze'}</button>
          <button onClick={load} className="px-3 py-2 rounded-lg border border-[var(--border-soft)] text-[var(--muted)] hover:text-cyan-200 inline-flex items-center gap-2"><RefreshCw size={14}/>Refresh</button>
        </div>
        {msg && <div className="mt-3 text-sm text-slate-200">{msg}</div>}
      </div>

      {active?.looks_stub && (
        <div className="glass rounded-2xl p-4 border border-amber-400/30 flex items-start gap-3">
          <AlertTriangle size={18} className="text-amber-300 mt-0.5"/>
          <div className="text-sm">
            <div className="text-amber-200">This resume only has {active.text_length} characters of text</div>
            <div className="text-[var(--muted)] mt-1">Job matching can only work with the skills that are actually in your resume. Upload the real file, or paste your resume text below and press “Save text”.</div>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="glass rounded-2xl p-4">
          <div className="text-sm text-cyan-200 mb-3">Active Resume</div>
          {!active ? <div className="text-sm text-[var(--muted)]">No resume uploaded yet.</div> : (
            <div className="space-y-3">
              <div className="text-xs text-[var(--muted)] break-all">{active.file_path}</div>
              <div className="grid grid-cols-3 gap-2">
                <div className="p-3 rounded-lg bg-black/20 border border-[var(--border-soft)]"><div className="text-[11px] text-[var(--muted)]">Skills</div><div className="text-xl text-cyan-100 font-semibold">{skillDraft.length}</div></div>
                <div className="p-3 rounded-lg bg-black/20 border border-[var(--border-soft)]"><div className="text-[11px] text-[var(--muted)]">Text length</div><div className="text-xl text-cyan-100 font-semibold">{active.text_length}</div></div>
                <div className="p-3 rounded-lg bg-black/20 border border-[var(--border-soft)]"><div className="text-[11px] text-[var(--muted)]">Versions</div><div className="text-xl text-cyan-100 font-semibold">{resumes.length}</div></div>
              </div>

              <div>
                <div className="text-xs text-[var(--muted)] mb-1">Skills used for matching (click × to remove)</div>
                <div className="flex flex-wrap gap-1.5 mb-2">
                  {skillDraft.map(s => (
                    <span key={s} className="text-xs px-2 py-1 rounded-full bg-cyan-500/10 border border-cyan-400/20 text-cyan-100 inline-flex items-center gap-1">
                      {s}
                      <button onClick={()=>removeSkill(s)} className="hover:text-red-300" title="remove"><X size={11}/></button>
                    </span>
                  ))}
                  {skillDraft.length===0 && <span className="text-xs text-[var(--muted)]">No skills yet - add them below.</span>}
                </div>
                <div className="flex gap-2">
                  <input value={skillInput} onChange={e=>setSkillInput(e.target.value)}
                    onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); addSkill() } }}
                    placeholder="add a skill (e.g. fastapi)"
                    className="flex-1 px-3 py-2 rounded-lg text-sm bg-black/20 border border-[var(--border-soft)]" />
                  <button onClick={addSkill} className="px-3 py-2 rounded-lg border border-cyan-400/30 text-cyan-200 inline-flex items-center gap-1.5"><Plus size={14}/>Add</button>
                  <button onClick={saveSkills} disabled={busy || !dirty} className="px-3 py-2 rounded-lg bg-cyan-500/20 border border-cyan-400/30 text-cyan-100 disabled:opacity-40 inline-flex items-center gap-1.5"><Save size={14}/>Save</button>
                </div>
              </div>

              <div>
                <div className="text-xs text-[var(--muted)] mb-1">Resume text (paste the full text if the file did not extract)</div>
                <textarea value={textDraft} onChange={e=>{ setTextDraft(e.target.value); setDirty(true) }}
                  rows={8}
                  className="w-full text-xs text-slate-300 bg-black/20 rounded p-3 border border-[var(--border-soft)] font-mono" />
                <button onClick={saveText} disabled={busy} className="mt-2 px-3 py-2 rounded-lg bg-cyan-500/20 border border-cyan-400/30 text-cyan-100 disabled:opacity-40 inline-flex items-center gap-1.5"><Save size={14}/>Save text & re-detect skills</button>
              </div>
            </div>
          )}
        </div>
        <div className="glass rounded-2xl p-4">
          <div className="text-sm text-cyan-200 mb-3">Profile & Preferences</div>
          {!profile ? <div className="text-sm text-[var(--muted)]">Loading profile...</div> : (
            <div className="space-y-3 text-sm">
              <div><div className="text-xs text-[var(--muted)]">Name</div><div className="text-slate-100">{profile.name}</div></div>
              <div><div className="text-xs text-[var(--muted)]">Location</div><div className="text-slate-100">{profile.location}</div></div>
              <div><div className="text-xs text-[var(--muted)]">Target roles</div><div className="flex flex-wrap gap-1.5 mt-1">{(profile.target_categories||[]).map((r:string)=><span key={r} className="text-xs px-2 py-1 rounded-full border border-[var(--border-soft)] text-slate-200">{r}</span>)}</div></div>
              <div className="grid grid-cols-2 gap-3">
                <div><div className="text-xs text-[var(--muted)]">Markets</div><div>{(profile.markets||[]).join(', ')}</div></div>
                <div><div className="text-xs text-[var(--muted)]">Work modes</div><div>{(profile.work_modes||[]).join(', ')}</div></div>
                <div><div className="text-xs text-[var(--muted)]">Employment</div><div>{(profile.employment_types||[]).join(', ')}</div></div>
                <div><div className="text-xs text-[var(--muted)]">Experience</div><div>{(profile.experience_levels||[]).join(', ')}</div></div>
              </div>
              <div className="text-xs text-[var(--muted)]">Edit these in Settings. Resume data shown above comes from the uploaded file only.</div>
            </div>
          )}
          <div className="mt-4">
            <div className="text-xs text-[var(--muted)] mb-2">Resume versions</div>
            <div className="space-y-2 max-h-56 overflow-auto">
              {resumes.map(r=> (
                <div key={r.id} className="text-xs p-2 rounded border border-[var(--border-soft)] bg-black/20">
                  <div className="flex items-center justify-between">
                    <span className="text-slate-200">#{r.id} · {r.skill_count} skills · {r.text_length} chars</span>
                    {r.id === active?.id ? <span className="inline-flex items-center gap-1 text-emerald-300"><Check size={11}/> active</span> :
                      <button onClick={()=>activate(r.id)} className="px-2 py-0.5 rounded border border-cyan-400/30 text-cyan-200">Set active</button>}
                  </div>
                  <div className="text-[var(--muted)] truncate mt-0.5">{r.file_path}</div>
                </div>
              ))}
              {resumes.length===0 && <div className="text-xs text-[var(--muted)]">None</div>}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
