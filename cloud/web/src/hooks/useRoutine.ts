import { useCallback } from 'react'
import { patchConfig } from '../lib/store'
import type { RoutineItem } from '../lib/routine'
import { useProjection } from './useProjection'

/**
 * The saved daily routine (config.routine). `seed` is what to show until one is saved,
 * e.g. mock data on the Routine tab or an empty list during onboarding.
 */
export function useRoutine(seed: RoutineItem[]) {
  const p = useProjection()
  const saved = p.config.routine as RoutineItem[] | undefined
  const items = saved ?? seed
  const hasSaved = Array.isArray(saved) && saved.length > 0

  const save = useCallback(async (next: RoutineItem[]) => {
    patchConfig({ routine: next })
    try {
      await fetch('/api/config', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ routine: next }),
      })
    } catch {
      /* the local copy is already updated; the next save retries */
    }
  }, [])

  return { items, hasSaved, save }
}
