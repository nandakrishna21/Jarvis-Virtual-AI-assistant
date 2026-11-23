export type VoiceTurn = {
  id: number
  user: string
  assistant: string
  intent?: string
  needsApproval?: boolean
  openUrl?: string
  openLabel?: string
}

export type VoiceStatus = 'idle' | 'listening' | 'thinking' | 'speaking'

type VoiceState = {
  turns: VoiceTurn[]
  status: VoiceStatus
  interim: string
  continuous: boolean
  wakeWord: boolean
  error: string | null
}

const STORAGE_KEY = 'jarvis.voice.v1'

function load(): Partial<VoiceState> {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return {}
    const parsed = JSON.parse(raw)
    return {
      turns: Array.isArray(parsed.turns) ? parsed.turns.slice(-30) : [],
      continuous: parsed.continuous !== false,
      wakeWord: !!parsed.wakeWord,
    }
  } catch {
    return {}
  }
}

const initialState: VoiceState = {
  turns: load().turns || [],
  status: 'idle',
  interim: '',
  continuous: load().continuous !== false,
  wakeWord: !!load().wakeWord,
  error: null,
}

function persist(state: VoiceState) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({
      turns: state.turns.slice(-30),
      continuous: state.continuous,
      wakeWord: state.wakeWord,
    }))
  } catch {
    /* ignore storage errors */
  }
}

export default function voiceSlice(state = initialState, action: any): VoiceState {
  switch (action.type) {
    case 'voice/status':
      return { ...state, status: action.payload }
    case 'voice/interim':
      return { ...state, interim: action.payload }
    case 'voice/error':
      return { ...state, error: action.payload }
    case 'voice/turnStart': {
      const turns = [...state.turns, { id: action.payload.id, user: action.payload.user, assistant: '' } as VoiceTurn]
      const next = { ...state, turns, status: 'thinking' as VoiceStatus, interim: '' }
      persist(next)
      return next
    }
    case 'voice/turnEnd': {
      const turns = state.turns.map((t) => t.id === action.payload.id
        ? { ...t, assistant: action.payload.assistant, intent: action.payload.intent, needsApproval: !!action.payload.needsApproval, openUrl: action.payload.openUrl, openLabel: action.payload.openLabel }
        : t)
      const next = { ...state, turns }
      persist(next)
      return next
    }
    case 'voice/clear':
      return { ...state, turns: [], error: null }
    case 'voice/continuous': {
      const next = { ...state, continuous: action.payload }
      persist(next)
      return next
    }
    case 'voice/wakeWord': {
      const next = { ...state, wakeWord: action.payload }
      persist(next)
      return next
    }
    default:
      return state
  }
}
