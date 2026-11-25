import { useEffect, useState } from 'react'
import { Bot, ExternalLink, RefreshCw, Terminal, FolderGit2 } from 'lucide-react'
import { api } from '../services/api'

export default function OpenJarvisPage() {
  const [status, setStatus] = useState<any>(null)
  const [loading, setLoading] = useState(false)
  const load = async () => { setLoading(true); try { setStatus(await api.get('/openjarvis/status')) } finally { setLoading(false) } }
  useEffect(() => { load() }, [])
  return (
    <div className="space-y-4 pb-4">
      <div className="rounded-3xl border border-white/10 bg-[linear-gradient(180deg,rgba(15,23,42,0.7),rgba(2,6,23,0.55))] p-5">
        <div className="inline-flex items-center gap-2 rounded-full border border-cyan-400/20 bg-cyan-500/10 px-3 py-1 text-[11px] uppercase tracking-[0.2em] text-cyan-100"><Bot size={12}/> OpenJarvis</div>
        <h1 className="mt-2 text-2xl font-semibold text-white">OpenJarvis Integration</h1>
        <p className="mt-1 text-sm text-slate-400">Stanford OpenJarvis is installed as a git submodule at <code className="text-cyan-200">external/OpenJarvis</code>. Use it as a local-first agent/research stack alongside JARVIS.</p>
        <div className="mt-4 flex gap-2">
          <button onClick={load} className="rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-sm text-slate-200 inline-flex items-center gap-2"><RefreshCw size={14} className={loading?'animate-spin':''}/>Refresh</button>
          <a href="https://open-jarvis.github.io/OpenJarvis/" target="_blank" rel="noreferrer" className="rounded-xl border border-cyan-400/30 bg-cyan-500/10 px-3 py-2 text-sm text-cyan-100 inline-flex items-center gap-2"><ExternalLink size={14}/>Docs</a>
        </div>
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        <div className="rounded-2xl border border-white/10 bg-black/20 p-4">
          <div className="text-sm font-medium text-slate-100 flex items-center gap-2 mb-3"><FolderGit2 size={15} className="text-cyan-300"/>Status</div>
          <div className="space-y-2 text-sm">
            {['installed','submodule','uv_available','jarvis_version','path'].map(k => (
              <div key={k} className="flex items-center justify-between gap-3 rounded-lg border border-white/10 bg-white/[0.02] px-3 py-2"><span className="text-slate-400">{k}</span><span className="text-slate-200 text-right break-all">{String(status?.[k] ?? '...')}</span></div>
            ))}
          </div>
        </div>
        <div className="rounded-2xl border border-white/10 bg-black/20 p-4">
          <div className="text-sm font-medium text-slate-100 flex items-center gap-2 mb-3"><Terminal size={15} className="text-cyan-300"/>Setup / Run</div>
          <div className="space-y-2 text-xs text-slate-300">
            <div className="rounded-lg border border-white/10 bg-black/30 p-3 font-mono">git submodule update --init --recursive</div>
            <div className="rounded-lg border border-white/10 bg-black/30 p-3 font-mono">powershell -ExecutionPolicy Bypass -File scripts/openjarvis_setup.ps1</div>
            <div className="rounded-lg border border-white/10 bg-black/30 p-3 font-mono">powershell -ExecutionPolicy Bypass -File scripts/openjarvis_run.ps1 doctor</div>
            <div className="rounded-lg border border-white/10 bg-black/30 p-3 font-mono">powershell -ExecutionPolicy Bypass -File scripts/openjarvis_run.ps1 -- --help</div>
          </div>
          <p className="mt-3 text-xs text-slate-400">OpenJarvis has its own Python environment/deps; use the scripts above so it doesn’t conflict with JARVIS’s backend venv.</p>
        </div>
      </div>
    </div>
  )
}
