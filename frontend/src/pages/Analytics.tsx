import { useEffect, useState } from 'react'
import { api } from '../services/api'
import { BarChart3 } from 'lucide-react'
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, PieChart, Pie, Cell } from 'recharts'

const COLORS = ['#00e5ff','#168bff','#22c55e','#f59e0b','#ef4444','#8fb3c9','#a78bfa']

export default function Analytics() {
  const [data, setData] = useState<any>(null)
  useEffect(()=>{ api.get<any>('/analytics/overview').then(setData).catch(()=>{}) }, [])

  const appStatus = data?.applications?.by_status || []
  const jobSources = data?.jobs?.top_sources || []
  const taskCats = data?.tasks?.by_category || []

  const cards = [
    { label: 'Jobs Discovered', value: data?.jobs?.total ?? '--' },
    { label: 'Avg Match Score', value: data?.jobs?.average_score ?? '--' },
    { label: 'Applications', value: data?.applications?.total ?? '--' },
    { label: 'Submitted (week)', value: data?.applications?.this_week ?? '--' },
    { label: 'Interviews', value: data?.interviews?.scheduled ?? '--' },
    { label: 'Tasks Pending', value: data?.tasks?.pending ?? '--' },
  ]

  return (
    <div className="space-y-4">
      <div className="glass-strong rounded-2xl p-5">
        <div className="flex items-center gap-2 text-cyan-100"><BarChart3 size={18}/><h1 className="text-lg font-semibold">Analytics</h1></div>
        <p className="text-sm text-[var(--muted)] mt-1">Real metrics from your local database.</p>
      </div>
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
        {cards.map(c=> (
          <div key={c.label} className="glass rounded-xl p-3"><div className="text-[11px] uppercase tracking-wider text-[var(--muted)]">{c.label}</div><div className="mt-1 text-2xl font-semibold text-cyan-100">{c.value}</div></div>
        ))}
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="glass rounded-2xl p-4">
          <div className="text-sm text-cyan-200 mb-3">Applications by Status</div>
          <div className="h-64">
            {appStatus.length ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={appStatus}><XAxis dataKey="label" tick={{fill:'#8fb3c9', fontSize:11}} interval={0} angle={-20} textAnchor="end" height={60}/><YAxis tick={{fill:'#8fb3c9', fontSize:11}} allowDecimals={false}/><Tooltip contentStyle={{background:'#081321', border:'1px solid rgba(0,229,255,0.2)', color:'#e8f7ff'}}/><Bar dataKey="value" fill="#00e5ff" radius={[4,4,0,0]} /></BarChart>
              </ResponsiveContainer>
            ) : <div className="text-sm text-[var(--muted)] h-full flex items-center justify-center">No application data yet.</div>}
          </div>
        </div>
        <div className="glass rounded-2xl p-4">
          <div className="text-sm text-cyan-200 mb-3">Jobs by Source</div>
          <div className="h-64">
            {jobSources.length ? (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart><Pie data={jobSources} dataKey="value" nameKey="label" outerRadius={90} label={({name,value})=>`${name}: ${value}`}>{jobSources.map((_:any,i:number)=><Cell key={i} fill={COLORS[i%COLORS.length]} />)}</Pie><Tooltip contentStyle={{background:'#081321', border:'1px solid rgba(0,229,255,0.2)', color:'#e8f7ff'}}/></PieChart>
              </ResponsiveContainer>
            ) : <div className="text-sm text-[var(--muted)] h-full flex items-center justify-center">No job source data yet.</div>}
          </div>
        </div>
      </div>
      <div className="glass rounded-2xl p-4">
        <div className="text-sm text-cyan-200 mb-3">Task Categories</div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {(taskCats.length?taskCats:[{label:'general',value:0}]).map((t:any)=> (
            <div key={t.label} className="p-3 rounded-lg bg-black/20 border border-[var(--border-soft)]"><div className="text-xs text-[var(--muted)]">{t.label}</div><div className="text-xl font-semibold text-cyan-100">{t.value}</div></div>
          ))}
        </div>
      </div>
    </div>
  )
}
