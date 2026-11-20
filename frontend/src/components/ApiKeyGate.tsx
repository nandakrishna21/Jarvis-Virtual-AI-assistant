import { useEffect, useState } from 'react'
import { api, setApiKey } from '../services/api'
import { KeyRound, Loader2, ShieldCheck } from 'lucide-react'

export default function ApiKeyGate({ children }: { children: React.ReactNode }) {
  const [value, setValue] = useState('')
  const [checking, setChecking] = useState(true)
  const [locked, setLocked] = useState(false)
  const [error, setError] = useState<string | null>(null)

  function applyResult(e: any) {
    if (e?.status === 401 || e?.status === 503) {
      setLocked(true)
      setError(e?.message || 'This JARVIS needs an API key.')
    } else {
      setLocked(false)
      setError(null)
    }
    setChecking(false)
  }

  useEffect(() => {
    let alive = true
    api.get('/health').then(
      () => { if (alive) { setLocked(false); setError(null); setChecking(false) } },
      (e: any) => { if (alive) applyResult(e) },
    )
    return () => { alive = false }
  }, [])

  async function unlock() {
    if (!value.trim()) return
    setApiKey(value.trim())
    setError(null)
    setChecking(true)
    try {
      await api.get('/health')
      setLocked(false)
      setChecking(false)
    } catch (e: any) {
      applyResult(e)
    }
  }

  if (checking && !locked) {
    return (
      <div className="min-h-screen flex items-center justify-center text-[var(--muted)] text-sm gap-2">
        <Loader2 size={16} className="animate-spin"/> Connecting to JARVIS...
      </div>
    )
  }

  if (locked) {
    return (
      <div className="min-h-screen flex items-center justify-center p-4">
        <div className="glass-strong rounded-2xl p-6 w-full max-w-sm space-y-4">
          <div className="flex items-center gap-2 text-cyan-100"><KeyRound size={18}/><h1 className="text-lg font-semibold">Unlock JARVIS</h1></div>
          <p className="text-sm text-[var(--muted)]">
            This JARVIS is running in LAN mode, so every request needs the API key from
            <code className="mx-1 text-cyan-200">backend\.env</code>
            (<code className="text-cyan-200">JARVIS_API_KEY</code>). It is stored only on this device.
          </p>
          <input
            value={value}
            onChange={(e) => setValue(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter') unlock() }}
            placeholder="Paste API key"
            type="password"
            className="w-full px-3 py-2 rounded-lg text-sm bg-black/20 border border-[var(--border-soft)]"
          />
          {error && <div className="text-xs text-red-300">{error}</div>}
          <button onClick={unlock} className="w-full px-4 py-2 rounded-lg bg-cyan-500/20 border border-cyan-400/30 text-cyan-100 inline-flex items-center justify-center gap-2">
            <ShieldCheck size={14}/> Unlock
          </button>
        </div>
      </div>
    )
  }

  return <>{children}</>
}
