type UiState = {
  sidebarOpen: boolean
  installAvailable: boolean
  installed: boolean
  toast: { id: number; text: string; kind: 'info' | 'ok' | 'warn' } | null
}

const initialState: UiState = {
  sidebarOpen: false,
  installAvailable: false,
  installed: false,
  toast: null,
}

export default function uiSlice(state = initialState, action: any): UiState {
  switch (action.type) {
    case 'ui/sidebar':
      return { ...state, sidebarOpen: action.payload }
    case 'ui/installAvailable':
      return { ...state, installAvailable: action.payload }
    case 'ui/installed':
      return { ...state, installed: action.payload, installAvailable: false }
    case 'ui/toast':
      return { ...state, toast: action.payload }
    default:
      return state
  }
}
