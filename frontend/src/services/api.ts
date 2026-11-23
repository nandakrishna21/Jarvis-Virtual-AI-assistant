// Same-origin by default (FastAPI serves the built SPA). Set
// VITE_API_BASE_URL when the frontend is hosted separately, e.g.
// https://jarvis-api.onrender.com/api
const BASE = ((import.meta.env.VITE_API_BASE_URL as string | undefined) || '/api').replace(/\/$/, '')
const KEY_STORAGE = 'jarvis.apiKey'

export function getApiKey(): string {
  try { return localStorage.getItem(KEY_STORAGE) || '' } catch { return '' }
}

export function setApiKey(value: string) {
  try {
    if (value) localStorage.setItem(KEY_STORAGE, value)
    else localStorage.removeItem(KEY_STORAGE)
  } catch { /* storage blocked */ }
}

export async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const isForm = typeof FormData !== 'undefined' && init.body instanceof FormData
  const headers = new Headers(init.headers || {})
  if (!isForm && init.body && !headers.has('Content-Type')) headers.set('Content-Type', 'application/json')
  const key = getApiKey()
  if (key && !headers.has('X-API-Key')) headers.set('X-API-Key', key)
  const res = await fetch(`${BASE}${path}`, { ...init, headers })
  const text = await res.text()
  let data: any = null
  try { data = text ? JSON.parse(text) : null } catch { data = { raw: text } }
  if (!res.ok) {
    const msg = data?.error || data?.detail || data?.message || res.statusText
    const error = new Error(typeof msg === 'string' ? msg : JSON.stringify(msg))
    ;(error as any).status = res.status
    ;(error as any).payload = data
    throw error
  }
  return data as T
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body?: any) => request<T>(path, { method: 'POST', body: body === undefined ? undefined : JSON.stringify(body) }),
  put: <T>(path: string, body?: any) => request<T>(path, { method: 'PUT', body: body === undefined ? undefined : JSON.stringify(body) }),
  patch: <T>(path: string, body?: any) => request<T>(path, { method: 'PATCH', body: body === undefined ? undefined : JSON.stringify(body) }),
  del: <T>(path: string) => request<T>(path, { method: 'DELETE' }),
  upload: <T>(path: string, form: FormData) => request<T>(path, { method: 'POST', body: form }),
}

export type SystemStatus = {
  cpu_percent: number
  ram_percent: number
  ram_free_gb: number
  ollama: { ok: boolean; models?: string[]; active_model?: string; model_available?: boolean; error?: string }
  llm?: { provider: string; active: string; available: Record<string, boolean>; models: Record<string, string> }
  ai_ok?: boolean
  demo?: boolean
  model: string
  loaded_models: any[]
}

export type Proposal = {
  id: number
  action_type: string
  title: string
  reason: string
  plan: string[]
  payload: any
  status: 'pending' | 'approved' | 'rejected' | 'executed' | 'failed'
  source: string
  result: any
  error?: string | null
  created_at?: string
  decided_at?: string
  executed_at?: string
}

export type ChatResponse = {
  ok: boolean
  intent?: string
  response?: string
  error?: string
  hint?: string
  requires_approval?: boolean
  proposal?: Proposal
  jobs?: any[]
  tasks?: any[]
  report?: any
  [k: string]: any
}

export type Greeting = {
  greeting: string
  message: string
  name: string
  pending_approvals: number
  stats: {
    jobs_discovered: number
    high_match: number
    matches: number
    applications_prepared: number
    applications_submitted: number
    interviews_scheduled: number
  }
  quick_commands: { label: string; command: string }[]
}

export type Job = { id: number; title: string; company?: string; location?: string; url: string; source?: string; verified?: string; salary?: string; posting_date?: string }
export type JobMatch = { job_id: number; title: string; company?: string; url: string; location?: string; score: number; matching?: string; missing?: string }
export type Application = { id: number; job_id: number; status: string; created_at: string; job?: any; cover_letter?: string; answers?: any; approval_status?: string }
export type Approval = { id: number; application_id?: number; draft_id?: number; action: string; status: string; snapshot?: string; created_at: string }
export type Interview = { id: number; company: string; role?: string; interview_date?: string; interview_time?: string; mode?: string; interviewer?: string; notes?: string; status: string }
export type NotificationItem = { id: number; kind: string; title: string; body?: string; link?: string; is_read: boolean; created_at?: string }
export type ScheduleItem = { id: number; name: string; job_type: string; time_of_day?: string; enabled: boolean; last_run?: string }
export type Health = { status: string; app: string }
export type TopMatch = { job_id: number; title: string; company?: string | null; url: string; score: number; matching?: string | null; missing?: string | null }
export type EmailItem = { id: number; sender: string; company?: string | null; subject: string; received_at?: string | null; job_role?: string | null; category: string; important_details?: string | null; snippet?: string | null }
export type NewsItem = { id: number; company?: string | null; role?: string | null; location?: string | null; experience?: string | null; salary?: string | null; posting_date?: string | null; source?: string | null; official_source?: string | null; application_url?: string | null; relevance: number; is_current: boolean; title: string }
export type TaskItem = { id: number; title: string; notes?: string | null; category: string; due_date?: string | null; due_time?: string | null; priority: number; status: string; overdue?: boolean }
export type Productivity = { date: string; pending: number; due_today: number; overdue: number; completed: number; by_category: Record<string, number>; today_tasks: { id: number; title: string; due_time?: string | null; category: string }[] }
export type StudyProgress = { exam: string; topics_tracked: number; topics_practised: number; total_attempts: number; accuracy: number; weak_topics: { exam: string; topic: string; mastery: number; attempts: number }[]; strong_topics: { exam: string; topic: string; mastery: number }[] }
export type FileItem = { path: string; is_dir: boolean; size: number }

export async function uploadFile<T>(path: string, file: File, field = 'file'): Promise<T> {
  const form = new FormData()
  form.append(field, file)
  return api.upload<T>(path, form)
}
