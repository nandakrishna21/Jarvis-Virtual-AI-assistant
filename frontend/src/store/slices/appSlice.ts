type AppState = {
  status: any | null
  pending: number
  provider: string
  model: string
  gmailConnected: boolean
  gmailEmail: string | null
  lastSync: number | null
}

const initialState: AppState = {
  status: null,
  pending: 0,
  provider: '',
  model: '',
  gmailConnected: false,
  gmailEmail: null,
  lastSync: null,
}

export default function appSlice(state = initialState, action: any): AppState {
  switch (action.type) {
    case 'app/status':
      return { ...state, status: action.payload, lastSync: Date.now() }
    case 'app/pending':
      return { ...state, pending: action.payload }
    case 'app/provider':
      return { ...state, provider: action.payload.provider || '', model: action.payload.model || '' }
    case 'app/gmail':
      return {
        ...state,
        gmailConnected: !!action.payload.connected,
        gmailEmail: action.payload.email || null,
      }
    default:
      return state
  }
}
