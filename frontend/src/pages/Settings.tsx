import { useEffect, useState } from 'react'
import { api } from '../services/api'
import { Settings as SettingsIcon, Save, Play, Pause, RotateCw, Cpu, ShieldCheck } from 'lucide-react'

export default function Settings() {
  const [profile, setProfile] = useState<any>(null)
  const [schedules, setSchedules] = useState<any>(null)
  const [gmail, setGmail] = useState<any>(null)
  const [startup, setStartup] = useState<any>(null)
  const [llm, setLlm] = useState<any>(null)
  const [auth, setAuth] = useState<any>(null)
  const [msg, setMsg] = useState<string|null>(null)
  const [saving, setSaving] = useState(false)

  async function load() {
    try { setProfile(await api.get('/profile')) } catch {}
    try { setSchedules(await api.get('/schedules')) } catch {}
    try { setGmail(await api.get('/gmail/status')) } catch {}
    try { setStartup(await api.get('/system/startup')) } catch {}
    try { setLlm(await api.get('/system/llm')) } catch {}
    try { setAuth(await api.get('/system/auth')) } catch {}
  }
  useEffect(()=>{ const t = setTimeout(() => { void load() }, 0); return () => clearTimeout(t) }, [])

  async function saveProfile() {
    if (!profile) return
    setSaving(true); setMsg(null)
    try { const p = await api.put('/profile', profile); setProfile(p); setMsg('Profile saved.') }
    catch(e:any){ setMsg(e?.message||'Save failed') }
    finally { setSaving(false) }
  }
  async function sched(action:string) { try { await api.post(`/schedules/${action}`); load(); setMsg(`Scheduler ${action}`) } catch(e:any){ setMsg(e?.message) } }
  async function startupAction(action:string) { try { const r = await api.post(`/system/startup/${action}`); setMsg(JSON.stringify(r)); load() } catch(e:any){ setMsg(e?.message) } }
  async function setProvider(provider:string) {
    try { const r = await api.put<any>('/system/llm', { provider }); setLlm(r); setMsg(`LLM provider: ${r.active}`) }
    catch(e:any){ setMsg(e?.message||'Could not switch provider') }
  }

  function setList(key:string, value:string) { setProfile({...profile, [key]: value.split(',').map(s=>s.trim()).filter(Boolean)}) }

  return (
    <div className="space-y-4">
      <div className="glass-strong rounded-2xl p-5 flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2 text-cyan-100"><SettingsIcon size={18}/><h1 className="text-lg font-semibold">Settings</h1></div>
          <p className="text-sm text-[var(--muted)] mt-1">Preferences, automations, integrations and startup.</p>
        </div>
        <button onClick={load} className="p-2 rounded-lg border border-[var(--border-soft)] text-[var(--muted)]"><RotateCw size={14}/></button>
      </div>
      {msg && <div className="glass rounded-xl p-3 text-sm text-slate-200 break-all">{msg}</div>}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="glass rounded-2xl p-4 space-y-3">
          <div className="text-sm text-cyan-200">User Profile & Preferences</div>
          {!profile ? <div className="text-sm text-[var(--muted)]">Loading...</div> : (
            <>
              <div className="grid grid-cols-2 gap-2">
                <label className="text-xs text-[var(--muted)]">Name<input value={profile.name||''} onChange={e=>setProfile({...profile,name:e.target.value})} className="mt-1 w-full px-3 py-2 rounded-lg text-sm" /></label>
                <label className="text-xs text-[var(--muted)]">Location<input value={profile.location||''} onChange={e=>setProfile({...profile,location:e.target.value})} className="mt-1 w-full px-3 py-2 rounded-lg text-sm" /></label>
              </div>
              <label className="text-xs text-[var(--muted)]">Target roles (comma separated)<textarea value={(profile.target_categories||[]).join(', ')} onChange={e=>setList('target_categories',e.target.value)} className="mt-1 w-full px-3 py-2 rounded-lg text-sm min-h-[70px]" /></label>
              <div className="grid grid-cols-2 gap-2">
                <label className="text-xs text-[var(--muted)]">Markets<input value={(profile.markets||[]).join(', ')} onChange={e=>setList('markets',e.target.value)} className="mt-1 w-full px-3 py-2 rounded-lg text-sm" /></label>
                <label className="text-xs text-[var(--muted)]">Work modes<input value={(profile.work_modes||[]).join(', ')} onChange={e=>setList('work_modes',e.target.value)} className="mt-1 w-full px-3 py-2 rounded-lg text-sm" /></label>
                <label className="text-xs text-[var(--muted)]">Employment types<input value={(profile.employment_types||[]).join(', ')} onChange={e=>setList('employment_types',e.target.value)} className="mt-1 w-full px-3 py-2 rounded-lg text-sm" /></label>
                <label className="text-xs text-[var(--muted)]">Experience levels<input value={(profile.experience_levels||[]).join(', ')} onChange={e=>setList('experience_levels',e.target.value)} className="mt-1 w-full px-3 py-2 rounded-lg text-sm" /></label>
              </div>
              <div className="grid grid-cols-2 gap-2">
                <label className="text-xs text-[var(--muted)]">Salary<input value={profile.salary||''} onChange={e=>setProfile({...profile,salary:e.target.value})} className="mt-1 w-full px-3 py-2 rounded-lg text-sm" /></label>
                <label className="text-xs text-[var(--muted)]">Search interval (min)<input type="number" value={profile.search_interval_minutes||240} onChange={e=>setProfile({...profile,search_interval_minutes:Number(e.target.value)})} className="mt-1 w-full px-3 py-2 rounded-lg text-sm" /></label>
              </div>
              <button onClick={saveProfile} disabled={saving} className="px-4 py-2 rounded-lg bg-cyan-500/20 border border-cyan-400/30 text-cyan-100 inline-flex items-center gap-2"><Save size={14}/>{saving?'Saving...':'Save preferences'}</button>
            </>
          )}
        </div>

        <div className="space-y-4">
          <div className="glass rounded-2xl p-4">
            <div className="text-sm text-cyan-200 mb-3">Scheduler & Automations</div>
            <div className="flex gap-2 mb-3">
              <button onClick={()=>sched('resume')} className="px-3 py-1.5 rounded-md text-xs border border-emerald-400/30 text-emerald-300 inline-flex items-center gap-1"><Play size={12}/>Resume</button>
              <button onClick={()=>sched('pause')} className="px-3 py-1.5 rounded-md text-xs border border-amber-400/30 text-amber-300 inline-flex items-center gap-1"><Pause size={12}/>Pause</button>
            </div>
            <div className="space-y-2 text-xs">
              {(schedules?.schedules||[]).map((s:any)=> (
                <div key={s.id} className="p-2 rounded border border-[var(--border-soft)] bg-black/20 flex items-center justify-between"><span className="text-slate-200">{s.name} · {s.job_type} {s.time_of_day?`@ ${s.time_of_day}`:''}</span><span className={s.enabled?'text-emerald-300':'text-[var(--muted)]'}>{s.enabled?'enabled':'disabled'}</span></div>
              ))}
              {(!schedules?.schedules || schedules.schedules.length===0) && <div className="text-[var(--muted)]">No schedules configured.</div>}
            </div>
          </div>
          <div className="glass rounded-2xl p-4">
            <div className="text-sm text-cyan-200 mb-2">Integrations</div>
            <div className="space-y-2 text-sm">
              <div className="p-2 rounded border border-[var(--border-soft)] bg-black/20"><div className="text-slate-200">Gmail</div><div className="text-xs text-[var(--muted)]">Credentials: {String(gmail?.credentials_present)} · Token: {String(gmail?.token_present)} · Read-only: {gmail?.readonly_scope||'configured in backend'}</div><div className="text-xs text-[var(--muted)] mt-1">Run backend script: <code>python scripts/gmail_auth.py</code> with <code>C:\JARVIS\credentials\credentials.json</code></div></div>
              <div className="p-2 rounded border border-[var(--border-soft)] bg-black/20"><div className="text-slate-200">n8n (local automation)</div><div className="text-xs text-[var(--muted)]">URL: http://127.0.0.1:5678 · Workflows installed in Automation Center. Start n8n to enable webhook execution.</div></div>
            </div>
          </div>
          <div className="glass rounded-2xl p-4">
            <div className="text-sm text-cyan-200 mb-3">AI Provider</div>
            <div className="space-y-2 text-xs">
              <div className="p-2 rounded border border-[var(--border-soft)] bg-black/20">
                <div className="flex items-center gap-2 text-slate-200"><Cpu size={13}/>Active: {llm?.active || 'ollama'}</div>
                <div className="text-[var(--muted)] mt-1">Fallback: {llm?.fallback || 'ollama'} · keys are never stored in the database</div>
                <div className="flex flex-wrap gap-2 mt-2">
                  {['ollama','nvidia','gemini','openrouter'].map(p => (
                    <button key={p} onClick={()=>setProvider(p)} disabled={!llm?.available?.[p]}
                      className={`px-3 py-1.5 rounded-md border text-xs disabled:opacity-40 ${llm?.active===p?'border-cyan-400/40 text-cyan-100 bg-cyan-500/15':'border-[var(--border-soft)] text-[var(--muted)]'}`}>
                      {p}{llm?.available?.[p] ? '' : ' (no key)'}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </div>
          <div className="glass rounded-2xl p-4">
            <div className="text-sm text-cyan-200 mb-2">Security</div>
            <div className="p-2 rounded border border-[var(--border-soft)] bg-black/20 text-xs">
              <div className="flex items-center gap-2 text-slate-200"><ShieldCheck size={13}/>API key guard: {auth?.enabled ? 'enabled' : 'off (single-user local)'}</div>
              <div className="text-[var(--muted)] mt-1">
                {auth?.enabled
                  ? `Key fingerprint ${auth.fingerprint}. Mutating requests need the X-API-Key header.`
                  : 'Set JARVIS_API_KEY in the environment to require a key on POST/PUT/PATCH/DELETE.'}
              </div>
            </div>
          </div>
          <div className="glass rounded-2xl p-4">
            <div className="text-sm text-cyan-200 mb-2">Mobile app</div>
            <div className="text-xs text-[var(--muted)] space-y-1">
              <div>JARVIS is an installable PWA: open it on a phone and use the browser menu - Install app / Add to Home Screen.</div>
              <div>To use it from a phone on the same Wi-Fi, start the server in LAN mode:</div>
              <div className="text-cyan-200"><code>powershell -NoProfile -ExecutionPolicy Bypass -File C:\JARVIS\scripts\start_prod.ps1 -Lan</code></div>
              <div>LAN mode needs <code>JARVIS_API_KEY</code> in <code>backend\.env</code>; the phone asks for it once and keeps it on the device.</div>
              <div className="text-amber-300">Offline install (full PWA with offline shell) needs HTTPS. Over plain http:// on your LAN, add it as a home-screen shortcut - the app still works while the phone is on the same network.</div>
            </div>
          </div>
          <div className="glass rounded-2xl p-4">
            <div className="text-sm text-cyan-200 mb-2">Startup</div>
            <div className="text-xs text-[var(--muted)] mb-2">Windows startup entry: {String(startup?.exists ?? startup?.enabled ?? 'unknown')}</div>
            <div className="flex gap-2">
              <button onClick={()=>startupAction('enable')} className="px-3 py-1.5 rounded-md text-xs border border-cyan-400/30 text-cyan-100">Enable startup</button>
              <button onClick={()=>startupAction('disable')} className="px-3 py-1.5 rounded-md text-xs border border-[var(--border-soft)] text-[var(--muted)]">Disable</button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
