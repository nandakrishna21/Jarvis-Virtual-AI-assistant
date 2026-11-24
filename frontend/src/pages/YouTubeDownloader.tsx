import { useEffect, useState } from 'react'
import { Download, Link2, Loader2, Music2, Video, ListVideo, ExternalLink, FolderDown } from 'lucide-react'
import { api } from '../services/api'

type Job = { id:string; url:string; kind:string; status:string; title?:string; progress?:number; speed?:string; eta?:string; filename?:string; error?:string; downloaded?:number; total?:number; filepath?:string }

export default function YouTubeDownloader() {
  const [url, setUrl] = useState('')
  const [mode, setMode] = useState<'video'|'audio'>('video')
  const [probing, setProbing] = useState(false)
  const [probe, setProbe] = useState<any>(null)
  const [jobs, setJobs] = useState<Job[]>([])
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const loadJobs = async () => {
    try { const r = await api.get<any>('/youtube/jobs'); setJobs(r.jobs || []) } catch {}
  }
  useEffect(() => { loadJobs(); const t = setInterval(loadJobs, 2500); return () => clearInterval(t) }, [])

  async function doProbe() {
    if (!url.trim()) return
    setProbing(true); setError(null); setProbe(null)
    try { const r = await api.get<any>(`/youtube/probe?url=${encodeURIComponent(url.trim())}`); if (r.error || r.ok===false) setError(r.error || 'Probe failed'); else setProbe(r) }
    catch (e:any) { setError(e?.message || 'Probe failed') }
    finally { setProbing(false) }
  }

  async function startDownload() {
    if (!url.trim()) return
    setBusy(true); setError(null)
    try { const r = await api.post<any>('/youtube/download', { url: url.trim(), mode }); if (r.error || r.ok===false) setError(r.error || 'Download failed'); else { setProbe(null); await loadJobs() } }
    catch (e:any) { setError(e?.message || 'Download failed') }
    finally { setBusy(false) }
  }

  return (
    <div className="space-y-4 pb-4">
      <div className="rounded-3xl border border-white/10 bg-[linear-gradient(180deg,rgba(15,23,42,0.7),rgba(2,6,23,0.55))] p-5">
        <div className="inline-flex items-center gap-2 rounded-full border border-red-400/20 bg-red-500/10 px-3 py-1 text-[11px] uppercase tracking-[0.2em] text-red-100"><ListVideo size={12}/> YouTube Downloader</div>
        <h1 className="mt-2 text-2xl sm:text-3xl font-semibold text-white">Download YouTube videos or playlists</h1>
        <p className="mt-1 text-sm text-slate-400">Paste a video or playlist URL. JARVIS uses local yt-dlp and saves files to <code className="text-cyan-200">data/downloads/youtube</code>.</p>

        <div className="mt-4 grid gap-3 lg:grid-cols-[1fr_auto_auto_auto]">
          <div className="flex items-center gap-2 rounded-2xl border border-white/10 bg-black/20 px-3 py-2">
            <Link2 size={16} className="text-slate-400 shrink-0"/>
            <input value={url} onChange={e=>setUrl(e.target.value)} placeholder="https://www.youtube.com/watch?v=... or playlist?list=..." className="w-full bg-transparent text-sm text-slate-100 placeholder:text-slate-500 focus:outline-none"/>
          </div>
          <select value={mode} onChange={e=>setMode(e.target.value as any)} className="rounded-2xl border border-white/10 bg-black/20 px-4 py-3 text-sm text-slate-100">
            <option value="video">Video (MP4)</option>
            <option value="audio">Audio (MP3)</option>
          </select>
          <button onClick={doProbe} disabled={probing || !url.trim()} className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-slate-100 hover:bg-white/10 disabled:opacity-40 inline-flex items-center justify-center gap-2">{probing ? <Loader2 size={16} className="animate-spin"/> : <ListVideo size={16}/>}Inspect</button>
          <button onClick={startDownload} disabled={busy || !url.trim()} className="rounded-2xl border border-cyan-400/30 bg-cyan-500/15 px-4 py-3 text-sm text-cyan-50 hover:bg-cyan-500/25 disabled:opacity-40 inline-flex items-center justify-center gap-2">{busy ? <Loader2 size={16} className="animate-spin"/> : <Download size={16}/>}Download</button>
        </div>
        {error && <div className="mt-3 rounded-xl border border-red-400/20 bg-red-500/10 px-4 py-3 text-sm text-red-200">{error}</div>}

        {probe && (
          <div className="mt-4 rounded-2xl border border-white/10 bg-black/20 p-4">
            <div className="flex items-center justify-between gap-3"><div><div className="text-sm font-medium text-slate-100">{probe.title}</div><div className="text-xs text-slate-400">{probe.is_playlist ? `Playlist · ${probe.count} items` : 'Single video'}{probe.uploader ? ` · ${probe.uploader}` : ''}</div></div>{probe.webpage_url && <a href={probe.webpage_url} target="_blank" rel="noreferrer" className="text-cyan-200 text-xs inline-flex items-center gap-1"><ExternalLink size={13}/>Open</a>}</div>
            {probe.is_playlist && Array.isArray(probe.items) && probe.items.length>0 && (
              <div className="mt-3 max-h-56 overflow-auto space-y-1.5 pr-1">
                {probe.items.slice(0,50).map((it:any, i:number)=>(<div key={it.id||i} className="rounded-lg border border-white/10 bg-white/[0.02] px-3 py-2 text-xs text-slate-300 flex items-center gap-2"><span className="text-slate-500 w-6">{i+1}</span><span className="truncate">{it.title || it.id || 'Item'}</span></div>))}
              </div>
            )}
          </div>
        )}
      </div>

      <div className="rounded-3xl border border-white/10 bg-black/20 p-4 sm:p-5">
        <div className="flex items-center justify-between mb-3"><div className="text-sm font-medium text-slate-100 flex items-center gap-2"><FolderDown size={15} className="text-cyan-300"/>Downloads</div><button onClick={loadJobs} className="text-xs text-slate-400 hover:text-cyan-200">Refresh</button></div>
        <div className="space-y-3">
          {jobs.length===0 && <div className="text-sm text-slate-500 rounded-xl border border-dashed border-white/10 p-4">No downloads yet.</div>}
          {jobs.map(j => (
            <div key={j.id} className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0"><div className="text-sm text-slate-100 truncate flex items-center gap-2">{j.kind==='audio'?<Music2 size={14} className="text-emerald-300"/>:<Video size={14} className="text-cyan-300"/>}{j.filename || j.title || j.url}</div><div className="text-[11px] text-slate-400 truncate">{j.url}</div></div>
                <div className={`text-[11px] px-2 py-1 rounded-full border ${j.status==='completed'?'border-emerald-400/30 text-emerald-200 bg-emerald-500/10':j.status==='failed'?'border-red-400/30 text-red-200 bg-red-500/10':j.status==='running'?'border-cyan-400/30 text-cyan-200 bg-cyan-500/10':'border-white/10 text-slate-300 bg-white/5'}`}>{j.status}</div>
              </div>
              <div className="mt-3 h-2 rounded-full bg-white/10 overflow-hidden"><div className={`h-full ${j.status==='failed'?'bg-red-400/70':'bg-cyan-400/80'}`} style={{width:`${Math.max(0,Math.min(100,j.progress||0))}%`}}/></div>
              <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] text-slate-400">
                <span>{Math.round(j.progress||0)}%</span>{j.speed && <span>{j.speed}</span>}{j.eta && <span>ETA {j.eta}</span>}{(j.total||0)>0 && <span>{j.downloaded||0}/{j.total} items</span>}
                {j.filepath && j.status==='completed' && <a href={`/api/youtube/jobs/${j.id}/file`} className="text-cyan-200 hover:underline inline-flex items-center gap-1"><Download size={12}/>Download file</a>}
              </div>
              {j.error && <div className="mt-2 text-xs text-red-200">{j.error}</div>}
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
