export type ResumeEntry = {
  title: string
  organization: string
  location: string
  start_date: string
  end_date: string
  description: string
}

export type ResumeDetails = {
  name: string
  email: string
  phone: string
  location: string
  links: string[]
  summary: string
  skills: string[]
  experience: ResumeEntry[]
  education: ResumeEntry[]
  projects: ResumeEntry[]
}

export const emptyEntry = (): ResumeEntry => ({
  title: '', organization: '', location: '', start_date: '', end_date: '', description: '',
})

export const emptyDetails = (): ResumeDetails => ({
  name: '', email: '', phone: '', location: '', links: [], summary: '', skills: [],
  experience: [], education: [], projects: [],
})

type ResumeState = {
  resumeId: number | null
  details: ResumeDetails
  dirty: boolean
  saving: boolean
  savedAt: number | null
  message: string
}

const STORAGE_KEY = 'jarvis.resume.details.v1'

function load(): { resumeId: number | null; details: ResumeDetails } {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return { resumeId: null, details: emptyDetails() }
    const parsed = JSON.parse(raw)
    return {
      resumeId: parsed.resumeId ?? null,
      details: { ...emptyDetails(), ...(parsed.details || {}) },
    }
  } catch {
    return { resumeId: null, details: emptyDetails() }
  }
}

const persisted = load()

const initialState: ResumeState = {
  resumeId: persisted.resumeId,
  details: persisted.details,
  dirty: false,
  saving: false,
  savedAt: null,
  message: '',
}

function persist(state: ResumeState) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ resumeId: state.resumeId, details: state.details }))
  } catch {
    /* storage full or blocked - the app still works, it just will not remember */
  }
}

export default function resumeSlice(state = initialState, action: any): ResumeState {
  switch (action.type) {
    case 'resume/load': {
      return {
        ...state,
        resumeId: action.payload.resumeId ?? state.resumeId,
        details: { ...emptyDetails(), ...(action.payload.details || {}) },
        dirty: false,
        message: '',
      }
    }
    case 'resume/setField': {
      const details = { ...state.details, [action.payload.field]: action.payload.value } as ResumeDetails
      const next = { ...state, details, dirty: true }
      persist(next)
      return next
    }
    case 'resume/setEntry': {
      const { section, index, value } = action.payload
      const entries = [...(state.details[section as keyof ResumeDetails] as ResumeEntry[])]
      entries[index] = { ...entries[index], ...value }
      const details = { ...state.details, [section]: entries } as ResumeDetails
      const next = { ...state, details, dirty: true }
      persist(next)
      return next
    }
    case 'resume/addEntry': {
      const section = action.payload.section as keyof ResumeDetails
      const entries = [...((state.details[section] as ResumeEntry[]) || []), emptyEntry()]
      const details = { ...state.details, [section]: entries } as ResumeDetails
      const next = { ...state, details, dirty: true }
      persist(next)
      return next
    }
    case 'resume/removeEntry': {
      const { section, index } = action.payload
      const key = section as keyof ResumeDetails
      const entries = [...((state.details[key] as ResumeEntry[]) || [])]
      entries.splice(index, 1)
      const details = { ...state.details, [section]: entries } as ResumeDetails
      const next = { ...state, details, dirty: true }
      persist(next)
      return next
    }
    case 'resume/saving':
      return { ...state, saving: action.payload, message: action.payload ? 'Saving...' : state.message }
    case 'resume/saved': {
      const next = { ...state, saving: false, dirty: false, savedAt: Date.now(), message: 'Saved' }
      persist(next)
      return next
    }
    case 'resume/error':
      return { ...state, saving: false, message: action.payload }
    default:
      return state
  }
}
