import { useCallback, useEffect, useState } from 'react'
import { api } from '../services/api'

export function useApi<T>(path: string | null) {
  const [data, setData] = useState<T | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(Boolean(path))

  const load = useCallback(async () => {
    if (!path) return
    try {
      const d = await api.get<T>(path)
      setData(d)
      setError(null)
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setLoading(false)
    }
  }, [path])

  useEffect(() => {
    let active = true
    const run = async () => {
      if (!path) {
        setLoading(false)
        return
      }
      try {
        const d = await api.get<T>(path)
        if (!active) return
        setData(d)
        setError(null)
      } catch (e) {
        if (!active) return
        setError((e as Error).message)
      } finally {
        if (active) setLoading(false)
      }
    }
    void run()
    return () => {
      active = false
    }
  }, [path])

  return { data, error, loading, reload: load }
}
