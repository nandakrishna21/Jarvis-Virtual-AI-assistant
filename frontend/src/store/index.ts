import { configureStore } from '@reduxjs/toolkit'
import appReducer from './slices/appSlice'
import uiReducer from './slices/uiSlice'
import resumeReducer from './slices/resumeSlice'
import voiceReducer from './slices/voiceSlice'

export const store = configureStore({
  reducer: {
    app: appReducer,
    ui: uiReducer,
    resume: resumeReducer,
    voice: voiceReducer,
  },
  middleware: (getDefault) =>
    getDefault({
      serializableCheck: {
        ignoredActions: ['voice/persist', 'ui/persist'],
      },
    }),
})

export type RootState = ReturnType<typeof store.getState>
export type AppDispatch = typeof store.dispatch
