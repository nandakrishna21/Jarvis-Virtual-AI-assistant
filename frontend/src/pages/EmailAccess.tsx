import { useEffect, useState } from 'react'
import { api } from '../services/api'
import { Mail, RefreshCw, Download, Copy, ExternalLink, ShieldCheck, Inbox } from 'lucide-react'

const CATEGORIES = ['all', 'recruiter', 'interview', 'assessment', 'job_alert', 'spam', 'other']

type Account = { connected: boolean; email?: string|null; messages_total?: number; can_send?: boolean; hint?: string; error?: string }
type EmailRow = { id: number; sender: string; company?: string; subject: string; received_at?: string; job_role?: string; category: string; snippet?: string }
type Draft = { id: number; email_id: number; recipient: string; subject: string; body: string; status: string }

export default function EmailAccess() {
  const [account, setAccount] = useState<Account|null>(null)
  const [emails, setEmails] = useState<EmailRow[]>([])
  const [drafts, setDrafts] = useState<Draft[]>([])
  const [category, setCategory] = useState('all')
  const [selected, setSelected] = useState<EmailRow|null>(null)
  const [body, setBody] = useState('')
  const [draft, setDraft] = useState<Draft|null>(null)
  const [msg, setMsg] = useState<string|null>(null)
  const [busy, setBusy] = useState(false)
  const [query, setQuery] = useState('newer_than:30d')
  const [maxResults, setMaxResults] = useState(100)
  const [search, setSearch] = useState('')
  const [fromDate, setFromDate] = useState('')
  const [toDate, setToDate] = useState('')

  async function loadAll() {
    try {
      const a = await api.get<Account>('/gmail/account')
      setAccount(a)
    } catch (e:any) { setMsg(e?.message || 'Could not read Gmail status') }
    try {
      const params = new URLSearchParams({ limit: '200' })
      if (category !== 'all') params.set('category', category)
      if (search.trim()) params.set('q', search.trim())
      const list = await api.get<EmailRow[]>(`/emails?${params.toString()}`)
      setEmails(Array.isArray(list) ? list : [])
    } catch {}
    try {
      const d = await api.get<Draft[]>('/emails/drafts')
      setDrafts(Array.isArray(d) ? d : [])
    } catch {}
  }

  useEffect(() => {
    let on = true
    ;(async () => {
      try {
        const a = await api.get<Account>('/gmail/account'); if (on) setAccount(a)
      } catch {}
      try {
        const params = new URLSearchParams({ limit: '200' })
        if (category !== 'all') params.set('category', category)
        if (search.trim()) params.set('q', search.trim())
        const list = await api.get<EmailRow[]>(`/emails?${params.toString()}`)
        if (on) setEmails(Array.isArray(list) ? list : [])
      } catch {}
      try {
        const d = await api.get<Draft[]>('/emails/drafts'); if (on) setDrafts(Array.isArray(d) ? d : [])
      } catch {}
    })()
    return () => { on = false }
  }, [category, search])

  function gmailQuery() {
    let q = query.trim()
    if (fromDate) q += ` after:${fromDate.replaceAll('-', '/')}`
    if (toDate) q += ` before:${toDate.replaceAll('-', '/')}`
    return q.trim() || 'newer_than:30d'
  }

  async function fetchNow() {
    setBusy(true); setMsg(null)
    try {
      const res = await api.post<any>('/emails/fetch', { max_results: maxResults, query: gmailQuery() })
      if (res?.error) setMsg(`${res.error}${res.hint ? ' - ' + res.hint : ''}`)
      else setMsg(`Fetched ${res?.count ?? res?.length ?? 0} message(s) from your inbox.`)
      await loadAll()
    } catch(e:any){ setMsg(e?.message||'Fetch failed') }
    finally { setBusy(false) }
  }

  async function openEmail(row: EmailRow) {
    setSelected(row); setBody('')
    try {
      const r = await api.get<any>(`/emails/${row.id}`)
      setBody(r?.body || r?.snippet || '')
    } catch(e:any){ setMsg(e?.message||'Could not open email') }
  }

  async function prepareReply(row: EmailRow) {
    setBusy(true); setMsg(null)
    try {
      const res = await api.post<any>('/emails/draft', { email_id: row.id })
      if (res?.error) setMsg(res.error)
      else {
        setDraft({ id: res.draft_id, email_id: row.id, recipient: res.recipient, subject: res.subject, body: res.body, status: 'pending' })
        setMsg('Draft prepared. Copy it or open it in Gmail - JARVIS will not send without your approval.')
        const d = await api.get<Draft[]>('/emails/drafts')
        setDrafts(Array.isArray(d) ? d : [])
      }
    } catch(e:any){ setMsg(e?.message||'Draft failed') }
    finally { setBusy(false) }
  }

  async function copy(text: string) {
    try {
      await navigator.clipboard.writeText(text)
      setMsg('Copied to clipboard.')
    } catch {
      setMsg('Copy failed - select the text and copy manually.')
    }
  }

  const connected = !!account?.connected
  const mailto = draft ? `mailto:${draft.recipient}?subject=${encodeURIComponent(draft.subject)}&body=${encodeURIComponent(draft.body)}` : ''
  const visibleEmails = emails.filter(e => {
    if (!fromDate && !toDate) return true
    const t = Date.parse(e.received_at || '')
    if (Number.isNaN(t)) return true
    if (fromDate && t < Date.parse(fromDate)) return false
    if (toDate && t > Date.parse(toDate) + 24*60*60*1000 - 1) return false
    return true
  })

  return (
    <div className="space-y-4">
      <div className="glass-strong rounded-2xl p-5">
        <div className="flex items-center gap-2 text-cyan-100"><Mail size={18}/><h1 className="text-lg font-semibold">Email Access</h1></div>
        <p className="text-sm text-[var(--muted)] mt-1">Connect your inbox so JARVIS can read recruiter emails and prepare replies. You keep the send button - JARVIS never sends mail on its own.</p>
        <div className="mt-4 grid gap-2 md:grid-cols-2 xl:grid-cols-[auto_auto_1fr_160px_140px_140px]">
          <button onClick={fetchNow} disabled={busy || !connected} className="px-4 py-2 rounded-lg bg-cyan-500/20 border border-cyan-400/30 text-cyan-100 hover:bg-cyan-500/30 disabled:opacity-50 inline-flex items-center justify-center gap-2"><Download size={14}/>{busy ? 'Working...' : 'Fetch inbox'}</button>
          <button onClick={() => void loadAll()} className="px-3 py-2 rounded-lg border border-[var(--border-soft)] text-[var(--muted)] hover:text-cyan-200 inline-flex items-center justify-center gap-2"><RefreshCw size={14}/>Refresh</button>
          <input value={query} onChange={e=>setQuery(e.target.value)} placeholder="Gmail query, e.g. newer_than:30d or in:inbox" className="px-3 py-2 rounded-lg text-sm bg-black/20 border border-[var(--border-soft)]" />
          <select value={maxResults} onChange={e=>setMaxResults(Number(e.target.value))} className="px-3 py-2 rounded-lg text-sm bg-black/20 border border-[var(--border-soft)]">
            {[25,50,100,200,500].map(n => <option key={n} value={n}>Fetch {n}</option>)}
          </select>
          <input type="date" value={fromDate} onChange={e=>setFromDate(e.target.value)} className="px-3 py-2 rounded-lg text-sm bg-black/20 border border-[var(--border-soft)]" />
          <input type="date" value={toDate} onChange={e=>setToDate(e.target.value)} className="px-3 py-2 rounded-lg text-sm bg-black/20 border border-[var(--border-soft)]" />
        </div>
        <div className="mt-2 text-[11px] text-[var(--muted)]">Date range applies to Gmail fetch and local inbox filter. Use "in:inbox" to fetch all inbox mail.</div>
        {msg && <div className="mt-3 text-sm text-slate-200">{msg}</div>}
      </div>

      {!connected && (
        <div className="glass rounded-2xl p-5 border border-amber-400/30">
          <div className="flex items-center gap-2 text-amber-200"><ShieldCheck size={16}/><span className="font-medium">Gmail is not connected yet</span></div>
          <p className="text-sm text-[var(--muted)] mt-2">One-time setup, about two minutes. JARVIS asks for <span className="text-slate-200">read-only</span> access; the send scope is optional because you send the mail yourself.</p>
          <ol className="mt-3 text-sm text-slate-300 space-y-1 list-decimal list-inside">
            <li>Google Cloud → enable the <span className="text-cyan-200">Gmail API</span>.</li>
            <li>Create an <span className="text-cyan-200">OAuth 2.0 Desktop client</span> and download the JSON.</li>
            <li>Save it as <span className="text-cyan-200">C:\JARVIS\credentials\credentials.json</span>.</li>
            <li>Run: <code className="text-cyan-200">cd C:\JARVIS\backend; .\.venv\Scripts\python scripts\gmail_auth.py</code></li>
            <li>Press <span className="text-cyan-200">Refresh</span> here - your address appears once connected.</li>
          </ol>
          <div className="text-xs text-[var(--muted)] mt-3">Full walkthrough in <span className="text-cyan-200">docs/GMAIL_SETUP.md</span>. Add <code>--send</code> to the command only if you ever want JARVIS to send after approving the exact message.</div>
        </div>
      )}

      {connected && (
        <div className="glass rounded-2xl p-4 flex flex-wrap items-center gap-3 text-sm">
          <Inbox size={16} className="text-cyan-200"/>
          <span className="text-slate-100">{account?.email}</span>
          <span className="text-xs text-[var(--muted)]">{account?.messages_total ?? 0} messages in the mailbox</span>
          <span className={`text-xs px-2 py-0.5 rounded border ${account?.can_send ? 'border-emerald-400/30 text-emerald-200' : 'border-cyan-400/30 text-cyan-200'}`}>{account?.can_send ? 'read + send scope' : 'read-only scope (you send manually)'}</span>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="glass rounded-2xl p-4">
          <div className="flex flex-col gap-2 mb-3">
            <div className="flex items-center justify-between gap-2">
              <div className="text-sm text-cyan-200">Inbox <span className="text-[var(--muted)]">({visibleEmails.length})</span></div>
              <input value={search} onChange={e=>setSearch(e.target.value)} placeholder="Search mail..." className="px-3 py-1.5 rounded-lg text-xs bg-black/20 border border-[var(--border-soft)] w-44" />
            </div>
            <div className="flex flex-wrap gap-1">
              {CATEGORIES.map(c => (
                <button key={c} onClick={()=>setCategory(c)}
                  className={`px-2 py-1 rounded text-[11px] border ${category===c ? 'border-cyan-400/40 text-cyan-200 bg-cyan-500/10' : 'border-[var(--border-soft)] text-[var(--muted)]'}`}>{c}</button>
              ))}
            </div>
          </div>
          <div className="space-y-2 max-h-[26rem] overflow-auto">
            {visibleEmails.length === 0 && <div className="text-sm text-[var(--muted)]">No emails found for this filter. Try changing category/date or fetch inbox.</div>}
            {visibleEmails.map(e => (
              <div key={e.id} className={`p-3 rounded-lg border ${selected?.id===e.id ? 'border-cyan-400/40 bg-cyan-500/5' : 'border-[var(--border-soft)] bg-black/20'}`}>
                <div className="flex items-start justify-between gap-2">
                  <button onClick={()=>openEmail(e)} className="text-left">
                    <div className="text-sm text-slate-100">{e.subject || '(no subject)'}</div>
                    <div className="text-[11px] text-[var(--muted)] mt-0.5 truncate">{e.sender}{e.company ? ` · ${e.company}` : ''}</div>
                  </button>
                  <span className="text-[10px] px-1.5 py-0.5 rounded border border-[var(--border-soft)] text-[var(--muted)] shrink-0">{e.category}</span>
                </div>
                {e.snippet && <div className="text-[11px] text-slate-400 mt-1 line-clamp-2">{e.snippet}</div>}
                <button onClick={()=>prepareReply(e)} disabled={busy} className="mt-2 px-2.5 py-1 rounded border border-cyan-400/30 text-cyan-200 hover:bg-cyan-500/10 text-[11px] disabled:opacity-50">Prepare reply</button>
              </div>
            ))}
          </div>
        </div>

        <div className="space-y-4">
          <div className="glass rounded-2xl p-4">
            <div className="text-sm text-cyan-200 mb-3">Message</div>
            {!selected ? <div className="text-sm text-[var(--muted)]">Pick a message to read it here.</div> : (
              <div className="space-y-2">
                <div className="text-sm text-slate-100">{selected.subject}</div>
                <div className="text-xs text-[var(--muted)]">{selected.sender} · {selected.received_at}</div>
                <pre className="text-xs text-slate-300 whitespace-pre-wrap max-h-56 overflow-auto bg-black/20 rounded p-3 border border-[var(--border-soft)]">{body || selected.snippet || 'No body stored.'}</pre>
              </div>
            )}
          </div>

          <div className="glass rounded-2xl p-4">
            <div className="text-sm text-cyan-200 mb-3">Reply draft</div>
            {!draft ? <div className="text-sm text-[var(--muted)]">Press “Prepare reply” on a message. The draft is saved as an approval item; nothing is sent.</div> : (
              <div className="space-y-2">
                <div className="text-xs text-[var(--muted)]">To: {draft.recipient}</div>
                <div className="text-xs text-[var(--muted)]">Subject: {draft.subject}</div>
                <pre className="text-xs text-slate-300 whitespace-pre-wrap max-h-48 overflow-auto bg-black/20 rounded p-3 border border-[var(--border-soft)]">{draft.body}</pre>
                <div className="flex flex-wrap gap-2">
                  <button onClick={()=>copy(draft.body)} className="px-3 py-1.5 rounded-md border border-cyan-400/30 text-cyan-200 hover:bg-cyan-500/10 inline-flex items-center gap-1.5"><Copy size={13}/> Copy text</button>
                  {mailto && <a href={mailto} className="px-3 py-1.5 rounded-md border border-emerald-400/30 text-emerald-200 hover:bg-emerald-500/10 inline-flex items-center gap-1.5"><ExternalLink size={13}/> Open in your mail app</a>}
                </div>
                <div className="text-[11px] text-[var(--muted)]">You send it. JARVIS only prepares the text and keeps the approval record.</div>
              </div>
            )}
          </div>

          <div className="glass rounded-2xl p-4">
            <div className="text-sm text-cyan-200 mb-3">Saved drafts</div>
            <div className="space-y-2 max-h-48 overflow-auto">
              {drafts.length === 0 && <div className="text-xs text-[var(--muted)]">None yet.</div>}
              {drafts.map(d => (
                <div key={d.id} className="p-2 rounded border border-[var(--border-soft)] bg-black/20 text-xs">
                  <div className="text-slate-200">{d.subject}</div>
                  <div className="text-[var(--muted)] truncate">to {d.recipient}</div>
                  <div className="text-[var(--muted)] mt-0.5">status: {d.status}</div>
                  <div className="mt-1 flex gap-2">
                    <button onClick={()=>copy(d.body)} className="px-2 py-1 rounded border border-cyan-400/30 text-cyan-200">Copy</button>
                    <a href={`mailto:${d.recipient}?subject=${encodeURIComponent(d.subject)}&body=${encodeURIComponent(d.body)}`} className="px-2 py-1 rounded border border-emerald-400/30 text-emerald-200">Open</a>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
