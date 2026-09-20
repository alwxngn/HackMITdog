export type RoutineKind = 'meal' | 'meds' | 'walk' | 'social' | 'sleep' | 'other'

export interface RoutineItem {
  id: string
  /** 24h "HH:MM" */
  time: string
  title: string
  kind: RoutineKind
  /** Monday first: Mon … Sun */
  days: boolean[]
  enabled: boolean
}

export const DAY_LABELS = ['M', 'T', 'W', 'T', 'F', 'S', 'S']
export const DAY_NAMES = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

export const KIND_META: Record<RoutineKind, { label: string; emoji: string; bg: string }> = {
  meal: { label: 'Meal', emoji: '🍳', bg: '#fde7c8' },
  meds: { label: 'Meds', emoji: '💊', bg: '#d3e8ef' },
  walk: { label: 'Walk', emoji: '🦮', bg: '#cdeadd' },
  social: { label: 'Call', emoji: '📞', bg: '#fbd9d6' },
  sleep: { label: 'Sleep', emoji: '🌙', bg: '#dbe9f0' },
  other: { label: 'Other', emoji: '⭐', bg: '#f6ecc0' },
}

const everyDay = () => [true, true, true, true, true, true, true]

/** Mon = 0 … Sun = 6 (JS getDay() is Sun = 0). */
export const todayIndex = () => (new Date().getDay() + 6) % 7

export function newId() {
  return `r_${Math.random().toString(36).slice(2, 8)}`
}

export function makeItem(time: string, title: string, kind: RoutineKind, days = everyDay()): RoutineItem {
  return { id: newId(), time, title, kind, days, enabled: true }
}

/** Placeholder day shown in the Routine tab until a routine is saved. */
export const MOCK_ROUTINE: RoutineItem[] = [
  { id: 'm1', time: '07:30', title: 'Wake up & stretch', kind: 'other', days: everyDay(), enabled: true },
  { id: 'm2', time: '08:00', title: 'Breakfast', kind: 'meal', days: everyDay(), enabled: true },
  { id: 'm3', time: '09:00', title: 'Morning pills', kind: 'meds', days: everyDay(), enabled: true },
  { id: 'm4', time: '10:30', title: 'Call with Jenny', kind: 'social', days: [true, false, true, false, true, false, false], enabled: true },
  { id: 'm5', time: '12:30', title: 'Lunch', kind: 'meal', days: everyDay(), enabled: true },
  { id: 'm6', time: '15:00', title: 'Walk with Lantern', kind: 'walk', days: everyDay(), enabled: true },
  { id: 'm7', time: '18:00', title: 'Dinner', kind: 'meal', days: everyDay(), enabled: true },
  { id: 'm8', time: '20:30', title: 'Evening pills', kind: 'meds', days: everyDay(), enabled: true },
  { id: 'm9', time: '21:30', title: 'Lights out', kind: 'sleep', days: everyDay(), enabled: true },
]

/** What onboarding starts with: meds, a walk and bedtime. Fixed ids so edits stay attached. */
export const DEFAULT_ROUTINE: RoutineItem[] = [
  { id: 'd_meds', time: '09:00', title: 'Morning meds', kind: 'meds', days: everyDay(), enabled: true },
  { id: 'd_walk', time: '15:00', title: 'Walk with Lantern', kind: 'walk', days: everyDay(), enabled: true },
  { id: 'd_sleep', time: '21:30', title: 'Bedtime', kind: 'sleep', days: everyDay(), enabled: true },
]

/** One-tap starters for onboarding. */
export const SUGGESTIONS: { time: string; title: string; kind: RoutineKind }[] = [
  { time: '07:30', title: 'Wake up', kind: 'other' },
  { time: '08:00', title: 'Breakfast', kind: 'meal' },
  { time: '09:00', title: 'Morning pills', kind: 'meds' },
  { time: '12:30', title: 'Lunch', kind: 'meal' },
  { time: '15:00', title: 'Walk with Lantern', kind: 'walk' },
  { time: '18:00', title: 'Dinner', kind: 'meal' },
  { time: '21:30', title: 'Lights out', kind: 'sleep' },
]

export function formatTime(t: string) {
  const [h, m] = t.split(':').map(Number)
  if (Number.isNaN(h)) return t
  const hh = ((h + 11) % 12) + 1
  return `${hh}:${String(m).padStart(2, '0')} ${h < 12 ? 'AM' : 'PM'}`
}

export function describeDays(days: boolean[]) {
  const on = days.filter(Boolean).length
  if (on === 7) return 'Every day'
  if (on === 0) return 'No days'
  if (on === 5 && !days[5] && !days[6]) return 'Weekdays'
  if (on === 2 && days[5] && days[6]) return 'Weekends'
  return DAY_NAMES.filter((_, i) => days[i]).join(', ')
}

export const byTime = (a: RoutineItem, b: RoutineItem) => a.time.localeCompare(b.time)
