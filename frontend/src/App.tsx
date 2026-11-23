import { lazy, Suspense } from 'react'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import Layout from './components/Layout'

const CommandCenter = lazy(() => import('./pages/CommandCenter'))
const Assistant = lazy(() => import('./pages/Assistant'))
const JobDiscovery = lazy(() => import('./pages/JobDiscovery'))
const MatchedJobs = lazy(() => import('./pages/MatchedJobs'))
const ResumeIntelligence = lazy(() => import('./pages/ResumeIntelligence'))
const ResumeGenerator = lazy(() => import('./pages/ResumeGenerator'))
const VoiceAgent = lazy(() => import('./pages/VoiceAgent'))
const EmailAccess = lazy(() => import('./pages/EmailAccess'))
const DocumentStudio = lazy(() => import('./pages/DocumentStudio'))
const ApplicationManager = lazy(() => import('./pages/ApplicationManager'))
const Interviews = lazy(() => import('./pages/Interviews'))
const AutomationCenter = lazy(() => import('./pages/AutomationCenter'))
const Analytics = lazy(() => import('./pages/Analytics'))
const Settings = lazy(() => import('./pages/Settings'))
const Jobs = lazy(() => import('./pages/Jobs'))
const Applications = lazy(() => import('./pages/Applications'))

const qc = new QueryClient({ defaultOptions: { queries: { refetchOnWindowFocus: false, retry: 1 } } })

function PageFallback() {
  return (
    <div className="flex items-center justify-center py-24 text-sm text-[var(--muted)]">
      <span className="inline-block w-2 h-2 rounded-full bg-cyan-400 mr-3 animate-pulse" />
      Loading JARVIS module...
    </div>
  )
}

export default function App() {
  return (
    <QueryClientProvider client={qc}>
      <BrowserRouter>
          <Routes>
            <Route element={<Layout />}>
              <Route index element={<Suspense fallback={<PageFallback />}><CommandCenter /></Suspense>} />
              <Route path="assistant" element={<Suspense fallback={<PageFallback />}><Assistant /></Suspense>} />
              <Route path="jobs" element={<Suspense fallback={<PageFallback />}><JobDiscovery /></Suspense>} />
              <Route path="jobs/all" element={<Suspense fallback={<PageFallback />}><Jobs /></Suspense>} />
              <Route path="matched" element={<Suspense fallback={<PageFallback />}><MatchedJobs /></Suspense>} />
              <Route path="resume" element={<Suspense fallback={<PageFallback />}><ResumeIntelligence /></Suspense>} />
              <Route path="resume-generator" element={<Suspense fallback={<PageFallback />}><ResumeGenerator /></Suspense>} />
              <Route path="voice" element={<Suspense fallback={<PageFallback />}><VoiceAgent /></Suspense>} />
              <Route path="emails" element={<Suspense fallback={<PageFallback />}><EmailAccess /></Suspense>} />
              <Route path="documents" element={<Suspense fallback={<PageFallback />}><DocumentStudio /></Suspense>} />
              <Route path="applications" element={<Suspense fallback={<PageFallback />}><ApplicationManager /></Suspense>} />
              <Route path="applications/legacy" element={<Suspense fallback={<PageFallback />}><Applications /></Suspense>} />
              <Route path="interviews" element={<Suspense fallback={<PageFallback />}><Interviews /></Suspense>} />
              <Route path="automation" element={<Suspense fallback={<PageFallback />}><AutomationCenter /></Suspense>} />
              <Route path="analytics" element={<Suspense fallback={<PageFallback />}><Analytics /></Suspense>} />
              <Route path="settings" element={<Suspense fallback={<PageFallback />}><Settings /></Suspense>} />
            </Route>
          </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  )
}
