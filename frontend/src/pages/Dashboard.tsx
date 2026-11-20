import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useApi } from '../hooks/useApi'
import type { Productivity, TaskItem, TopMatch, EmailItem, NewsItem, StudyProgress } from '../services/api'
import { Badge, Button, Card, Empty, ErrorBox, Loading, Stat } from '../components/ui'

export default function Dashboard() {
  const prod = useApi<Productivity>('/tasks/productivity')
  const tasks = useApi<TaskItem[]>('/tasks?status=pending')
  const jobs = useApi<TopMatch[]>('/jobs/top-matches')
  const emails = useApi<EmailItem[]>('/emails?limit=5')
  const news = useApi<NewsItem[]>('/hiring-news?current_only=true&limit=5')
  const study = useApi<StudyProgress>('/study/progress')

  const [now] = useState(() => new Date().toLocaleString())

  return (
    <div className="space-y-4">
      <Card>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-xl font-semibold">Welcome back</h2>
            <p className="text-sm text-slate-500">{now}</p>
          </div>
          <Link to="/chat">
            <Button>Ask JARVIS</Button>
          </Link>
        </div>
      </Card>

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Stat label="Pending tasks" value={prod.data?.pending ?? '-'} hint={`${prod.data?.due_today ?? 0} due today`} />
        <Stat label="Overdue" value={prod.data?.overdue ?? '-'} hint="needs attention" />
        <Stat label="Top job matches" value={jobs.data?.length ?? '-'} hint="ranked for you" />
        <Stat label="Study accuracy" value={study.data ? `${study.data.accuracy}%` : '-'} hint={study.data ? `${study.data.topics_practised} topics practised` : ''} />
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card title="Today's tasks">
          {prod.error && <ErrorBox error={prod.error} />}
          {prod.loading && <Loading />}
          {!prod.loading && !prod.data?.today_tasks.length && <Empty label="Nothing scheduled for today" />}
          <ul className="space-y-2">
            {prod.data?.today_tasks.map((t: any) => (
              <li key={t.id} className="flex items-center justify-between rounded-lg border border-slate-800 px-3 py-2">
                <span className="text-sm">{t.title}</span>
                <Badge>{t.due_time ?? 'no time'}</Badge>
              </li>
            ))}
          </ul>
        </Card>

        <Card title="Top job matches">
          {jobs.error && <ErrorBox error={jobs.error} />}
          {jobs.loading && <Loading />}
          {!jobs.loading && !jobs.data?.length && <Empty label="Run a job search from the Jobs page" />}
          <ul className="space-y-2">
            {jobs.data?.map((j) => (
              <li key={j.job_id} className="rounded-lg border border-slate-800 px-3 py-2">
                <div className="flex items-center justify-between gap-2">
                  <a href={j.url} target="_blank" rel="noreferrer" className="truncate text-sm text-sky-300 hover:underline">
                    {j.title}
                  </a>
                  <Badge tone="blue">{j.score?.toFixed?.(0) ?? j.score}%</Badge>
                </div>
                <div className="text-xs text-slate-500">{j.company ?? 'Company not published'}</div>
              </li>
            ))}
          </ul>
        </Card>

        <Card title="Important emails">
          {emails.error && <ErrorBox error={emails.error} />}
          {emails.loading && <Loading />}
          {!emails.loading && !emails.data?.length && <Empty label="No emails fetched yet (Gmail OAuth pending)" />}
          <ul className="space-y-2">
            {emails.data?.map((e) => (
              <li key={e.id} className="rounded-lg border border-slate-800 px-3 py-2">
                <div className="truncate text-sm">{e.subject}</div>
                <div className="text-xs text-slate-500">{e.sender}</div>
                <Badge tone={e.category === 'recruiter' || e.category === 'interview' ? 'green' : 'slate'}>{e.category}</Badge>
              </li>
            ))}
          </ul>
        </Card>

        <Card title="Hiring updates">
          {news.error && <ErrorBox error={news.error} />}
          {news.loading && <Loading />}
          {!news.loading && !news.data?.length && <Empty label="No current hiring items stored" />}
          <ul className="space-y-2">
            {news.data?.map((n) => (
              <li key={n.id} className="rounded-lg border border-slate-800 px-3 py-2">
                <div className="truncate text-sm">{n.title}</div>
                <div className="text-xs text-slate-500">
                  {n.company ?? 'Unknown'} · {n.role ?? 'role not published'} · relevance {n.relevance}
                </div>
              </li>
            ))}
          </ul>
        </Card>
      </div>

      <Card title="Pending tasks (all)">
        {tasks.loading && <Loading />}
        {!tasks.loading && !tasks.data?.length && <Empty label="No pending tasks" />}
        <ul className="space-y-1">
          {tasks.data?.map((t) => (
            <li key={t.id} className="flex items-center justify-between text-sm">
              <span className={t.overdue ? 'text-red-300' : 'text-slate-300'}>{t.title}</span>
              <span className="text-xs text-slate-500">
                {t.due_date ?? 'no date'} {t.due_time ?? ''} · {t.category}
              </span>
            </li>
          ))}
        </ul>
      </Card>
    </div>
  )
}
