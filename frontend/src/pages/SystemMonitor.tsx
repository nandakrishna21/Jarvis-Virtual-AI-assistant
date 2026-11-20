import { useEffect, useState } from 'react'
import { api, type SystemStatus } from '../services/api'
import { Badge, Button, Card, ErrorBox, Loading } from '../components/ui'

export default function SystemMonitor() {
  const [status, setStatus] = useState<SystemStatus | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)

  useEffect(() => {
    const load = () => api.get<SystemStatus>('/system/status').then(setStatus).catch((e: Error) => setError(e.message))
    load()
    const timer = setInterval(load, 5000)
    return () => clearInterval(timer)
  }, [])

  async function unload() {
    setNotice(null); setError(null)
    try {
      const res = await api.post<{ ok: boolean; unloaded?: string; error?: string }>('/system/unload-model')
      if (res.ok) setNotice(`Unloaded ${res.unloaded}. RAM should free up shortly.`)
      else setError(res.error ?? 'unload failed')
    } catch (e) {
      setError((e as Error).message)
    }
  }

  const ramTone = !status ? 'slate' : status.ram_percent > 90 ? 'red' : status.ram_percent > 75 ? 'amber' : 'green'

  return (
    <div className="space-y-4">
      {error && <ErrorBox error={error} />}
      {notice && <p className="text-xs text-emerald-300">{notice}</p>}
      {!status ? (
        <Loading />
      ) : (
        <>
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
            <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
              <div className="text-xs uppercase text-slate-500">CPU</div>
              <div className="text-2xl font-semibold">{status.cpu_percent.toFixed(0)}%</div>
            </div>
            <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
              <div className="text-xs uppercase text-slate-500">RAM</div>
              <div className={`text-2xl font-semibold ${status.ram_percent > 90 ? 'text-red-300' : ''}`}>
                {status.ram_percent.toFixed(0)}%
              </div>
              <div className="text-xs text-slate-500">load level: {ramTone}</div>
            </div>
            <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
              <div className="text-xs uppercase text-slate-500">Available RAM</div>
              <div className="text-2xl font-semibold">{status.ram_free_gb} GB</div>
            </div>
            <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
              <div className="text-xs uppercase text-slate-500">Active model</div>
              <div className="text-lg font-semibold">{status.model}</div>
            </div>
          </div>

          <Card title="Ollama">
            <div className="flex flex-wrap items-center gap-2">
              <Badge tone={status.ollama.ok ? 'green' : 'red'}>{status.ollama.ok ? 'service running' : 'service offline'}</Badge>
              {(status.ollama.models || []).map((m) => (
                <Badge key={m} tone={m === status.model ? 'blue' : 'slate'}>{m}</Badge>
              ))}
              <Button variant="secondary" onClick={unload}>Unload model (free RAM)</Button>
            </div>
            {status.loaded_models && status.loaded_models.length > 0 && (
              <div className="mt-3 text-xs text-slate-500">
                Loaded now: {status.loaded_models.map((m) => `${m.name ?? 'model'} (${Math.round((m.size ?? 0) / 1e9)} GB)`).join(', ')}
              </div>
            )}
          </Card>

          <Card title="Performance policy">
            <ul className="list-disc space-y-1 pl-5 text-sm text-slate-400">
              <li>One AI job at a time (semaphore limit = 1).</li>
              <li>Model unloads automatically 2 minutes after the last request.</li>
              <li>No polling loops while schedules are paused.</li>
              <li>Keep RAM below 90% - close heavy apps or unload the model above.</li>
            </ul>
          </Card>
        </>
      )}
    </div>
  )
}
