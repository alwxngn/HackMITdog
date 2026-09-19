import { useSyncExternalStore } from 'react'
import { getState, subscribe } from '../lib/store'
import type { Projection } from '../lib/types'

export function useProjection(): Projection {
  return useSyncExternalStore(subscribe, getState, getState)
}
