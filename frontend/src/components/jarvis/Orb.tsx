export type OrbState = 'idle' | 'listening' | 'thinking' | 'executing' | 'success' | 'error'

const stateLabel: Record<OrbState, string> = {
  idle: 'IDLE',
  listening: 'LISTENING',
  thinking: 'THINKING',
  executing: 'EXECUTING',
  success: 'SUCCESS',
  error: 'ERROR',
}

const stateColor: Record<OrbState, string> = {
  idle: '#00e5ff',
  listening: '#168bff',
  thinking: '#00e5ff',
  executing: '#168bff',
  success: '#22c55e',
  error: '#ef4444',
}

export function Orb({ state = 'idle', size = 260 }: { state?: OrbState; size?: number }) {
  const c = stateColor[state]
  const bars = 24
  return (
    <div className="relative flex items-center justify-center" style={{ width: size, height: size }}>
      <div className="absolute inset-0 rounded-full animate-spin-slow" style={{ border: `1px solid ${c}33`, boxShadow: `0 0 40px ${c}22 inset` }} />
      <div className="absolute inset-[10%] rounded-full animate-spin-rev" style={{ border: `1px dashed ${c}55` }} />
      <div className="absolute inset-[20%] rounded-full animate-pulse-ring" style={{ border: `1px solid ${c}66`, boxShadow: `0 0 30px ${c}22` }} />
      <svg className="absolute inset-0" viewBox="0 0 200 200">
        <defs>
          <linearGradient id="arc" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stopColor={c} stopOpacity="0.9" />
            <stop offset="100%" stopColor="#168bff" stopOpacity="0.1" />
          </linearGradient>
        </defs>
        <circle cx="100" cy="100" r="78" fill="none" stroke="url(#arc)" strokeWidth="1.5" strokeDasharray="18 10 4 10" className={state === 'thinking' || state === 'executing' ? 'animate-dash' : ''} />
        <circle cx="100" cy="100" r="64" fill="none" stroke={c} strokeOpacity="0.25" strokeWidth="1" />
        {Array.from({ length: 8 }).map((_, i) => (
          <line key={i} x1="100" y1="18" x2="100" y2="28" stroke={c} strokeOpacity="0.5" transform={`rotate(${i * 45} 100 100)`} />
        ))}
      </svg>
      <div className="absolute inset-[30%] rounded-full flex items-center justify-center" style={{ background: `radial-gradient(circle at 50% 40%, ${c}22, rgba(5,11,20,0.9) 70%)`, boxShadow: `0 0 40px ${c}22 inset` }}>
        {state === 'listening' ? (
          <div className="flex items-end gap-[3px] h-10">
            {Array.from({ length: bars / 2 }).map((_, i) => (
              <span key={i} className="w-[3px] rounded-full" style={{ background: c, height: `${30 + (i % 5) * 14}%`, animation: `wave ${0.8 + (i % 4) * 0.15}s ease-in-out ${i * 0.05}s infinite` }} />
            ))}
          </div>
        ) : state === 'thinking' || state === 'executing' ? (
          <div className="relative w-14 h-14">
            <div className="absolute inset-0 rounded-full border border-t-transparent animate-spin" style={{ borderColor: `${c}88`, borderTopColor: 'transparent', animationDuration: '1.2s' }} />
            <div className="absolute inset-2 rounded-full border border-b-transparent animate-spin-rev" style={{ borderColor: `${c}55`, borderBottomColor: 'transparent', animationDuration: '1.6s' }} />
            <div className="absolute inset-[38%] rounded-full animate-pulse-soft" style={{ background: c }} />
          </div>
        ) : (
          <div className="text-center">
            <div className="text-[10px] tracking-[0.35em] text-[var(--muted)]">J.A.R.V.I.S</div>
            <div className="mt-1 h-2 w-2 rounded-full mx-auto animate-pulse-soft" style={{ background: c, boxShadow: `0 0 12px ${c}` }} />
          </div>
        )}
      </div>
      <div className="absolute -bottom-2 px-3 py-1 rounded-full glass text-[10px] tracking-[0.25em]" style={{ color: c, borderColor: `${c}44` }}>
        {stateLabel[state]}
      </div>
    </div>
  )
}

export default Orb
