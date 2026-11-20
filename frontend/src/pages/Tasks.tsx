import { useState } from 'react'
import { api, type Productivity, type TaskItem } from '../services/api'
import { useApi } from '../hooks/useApi'
import { Badge, Button, Card, Empty, ErrorBox, Input, Loading } from '../components/ui'

export default function Tasks() {
  const tasks = useApi<TaskItem[]>('/tasks')
  const prod = useApi<Productivity>('/tasks/productivity')
  const [title, setTitle] = useState('')
  const [category, setCategory] = useState('general')
  const [filter, setFilter] = useState<'all' | 'pending' | 'overdue'>('all')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function add() {
    if (!title.trim()) return
    setBusy(true); setError(null)
    try {
      await api.post('/tasks', { title, category })
      setTitle('')
      tasks.reload(); prod.reload()
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setBusy(false)
    }
  }

  async function complete(id: number) {
    setBusy(true)
    try {
      await api.post(`/tasks/${id}/complete`)
      tasks.reload(); prod.reload()
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setBusy(false)
    }
  }

  async function remove(id: number) {
    if (!window.confirm('Delete this task? This cannot be undone.')) return
    setBusy(true)
    try {
      await api.del(`/tasks/${id}?confirmed=true`)
      tasks.reload(); prod.reload()
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setBusy(false)
    }
  }

  const all = tasks.data ?? []
  const list = filter === 'pending' ? all.filter((t) => t.status === 'pending') : filter === 'overdue' ? all.filter((t) => t.overdue) : all

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
          <div className="text-xs uppercase text-slate-500">Pending</div>
          <div className="text-2xl font-semibold">{prod.data?.pending ?? '-'}</div>
        </div>
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
          <div className="text-xs uppercase text-slate-500">Due today</div>
          <div className="text-2xl font-semibold">{prod.data?.due_today ?? '-'}</div>
        </div>
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
          <div className="text-xs uppercase text-slate-500">Overdue</div>
          <div className="text-2xl font-semibold text-red-300">{prod.data?.overdue ?? '-'}</div>
        </div>
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
          <div className="text-xs uppercase text-slate-500">Completed</div>
          <div className="text-2xl font-semibold">{prod.data?.completed ?? '-'}</div>
        </div>
      </div>

      <Card title="Add task">
        <div className="flex flex-wrap gap-2">
          <div className="min-w-[240px] flex-1">
            <Input value={title} onChange={setTitle} placeholder="e.g. Study SQL at 7 PM" />
          </div>
          <select
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-200"
          >
            {['general', 'study', 'job', 'follow-up'].map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
          <Button onClick={add} disabled={busy || !title.trim()}>Add</Button>
        </div>
        <p className="mt-2 text-xs text-slate-500">
          Natural dates work: "today", "tomorrow", "7 PM", "today at 9 PM".
        </p>
        {error && <div className="mt-2"><ErrorBox error={error} /></div>}
      </Card>

      <Card
        title="Tasks"
        action={
          <select
            value={filter}
            onChange={(e) => setFilter(e.target.value as 'all' | 'pending' | 'overdue')}
            className="rounded-lg border border-slate-700 bg-slate-950 px-2 py-1 text-xs text-slate-200"
          >
            <option value="all">all</option>
            <option value="pending">pending</option>
            <option value="overdue">overdue</option>
          </select>
        }
      >
        {tasks.error && <ErrorBox error={tasks.error} />}
        {tasks.loading && <Loading />}
        {!tasks.loading && !list.length && <Empty label="No tasks here" />}
        <ul className="space-y-2">
          {list.map((t) => (
            <li key={t.id} className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-slate-800 px-3 py-2">
              <div className="min-w-0">
                <div className={`truncate text-sm ${t.status === 'completed' ? 'text-slate-500 line-through' : t.overdue ? 'text-red-300' : ''}`}>
                  {t.title}
                </div>
                <div className="text-xs text-slate-500">
                  {t.due_date ?? 'no date'} {t.due_time ?? ''} · {t.category}
                </div>
              </div>
              <div className="flex items-center gap-2">
                {t.overdue && <Badge tone="red">overdue</Badge>}
                {t.status === 'completed' && <Badge tone="green">done</Badge>}
                {t.status !== 'completed' && (
                  <Button variant="secondary" onClick={() => complete(t.id)} disabled={busy}>Complete</Button>
                )}
                <Button variant="danger" onClick={() => remove(t.id)} disabled={busy}>Delete</Button>
              </div>
            </li>
          ))}
        </ul>
      </Card>
    </div>
  )
}
