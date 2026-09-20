import type { Envelope, Projection } from './types'

type Listener = (p: Projection) => void

const empty: Projection = {
  agent_state: {
    state: 'IDLE',
    previous: null,
    agitation: 'calm',
    calm_mode: false,
    reason: 'connecting…',
    since_ts: Date.now() / 1000,
  },
  pose: null,
  person_track: null,
  person_trail: [],
  zones: [],
  config: {},
  open_alert: null,
  live_tracking: false,
  speech_state: 'idle',
  last_transcript: null,
  robot_status: null,
  checkin_queue: [],
  map_ready: null,
  map_scan_pending: null,
  demo: { running: false, step: null },
  timeline: [],
}

let state: Projection = empty
const listeners = new Set<Listener>()

export function getState(): Projection {
  return state
}

export function subscribe(fn: Listener): () => void {
  listeners.add(fn)
  fn(state)
  return () => listeners.delete(fn)
}

function emit() {
  for (const fn of listeners) fn(state)
}

/** Merge a config change into `next`. Turning Night Watch off also clears its live state. */
function applyConfig(next: Projection, p: Record<string, unknown>, ts: number) {
  next.config = { ...next.config, ...p }
  if (Array.isArray((p as { zones?: unknown }).zones)) {
    next.zones = (p as { zones: Projection['zones'] }).zones
  }
  if (p.night_watch_enabled === false) {
    const ctx = next.open_alert?.context
    if (ctx === 'night_breach' || ctx === 'zone_watch') next.open_alert = null
    next.live_tracking = false
    next.agent_state = { ...next.agent_state, state: 'IDLE', agitation: 'calm', reason: 'night watch off', since_ts: ts }
  } else if (p.night_watch_enabled === true && next.agent_state.reason === 'night watch off') {
    next.agent_state = { ...next.agent_state, reason: 'night watch idle', since_ts: ts }
  }
}

/** Apply a config change locally right away (after the server accepted it). */
export function patchConfig(patch: Record<string, unknown>) {
  const next = { ...state }
  applyConfig(next, patch, Date.now() / 1000)
  state = next
  emit()
}

export function handleBusMessage(msg: Envelope) {
  const t = msg.type
  const p = msg.payload as Record<string, unknown>

  if (t === 'snapshot') {
    state = { ...empty, ...(p as unknown as Projection), timeline: (p.timeline as Envelope[]) || [] }
    emit()
    return
  }

  const next = { ...state }

  if (t === 'agent_state') next.agent_state = p as unknown as Projection['agent_state']
  else if (t === 'pose') next.pose = p as unknown as Projection['pose']
  else if (t === 'person_track') {
    next.person_track = p as unknown as Projection['person_track']
    const pt = p as { x: number; y: number; lat?: number | null; lon?: number | null }
    next.person_trail = [...next.person_trail, { x: pt.x, y: pt.y, lat: pt.lat, lon: pt.lon, ts: msg.ts }].slice(-600)
  } else if (t === 'alert') {
    next.open_alert = { ...(p as object), ts: msg.ts } as Projection['open_alert']
    if ((p as { live_tracking?: boolean }).live_tracking) next.live_tracking = true
  } else if (t === 'caregiver_ack') {
    const aid = (p as { alert_id: string }).alert_id
    if (next.open_alert?.alert_id === aid) next.open_alert = null
    next.live_tracking = false
  } else if (t === 'config_update') {
    applyConfig(next, p, msg.ts)
  } else if (t === 'speech_state') {
    next.speech_state = (p as { state: string }).state
  } else if (t === 'transcript' && (p as { is_final?: boolean }).is_final) {
    next.last_transcript = p as Projection['last_transcript']
  } else if (t === 'robot_status') {
    next.robot_status = p as Projection['robot_status']
  } else if (t === 'checkin') {
    next.checkin_queue = [...next.checkin_queue, p as Projection['checkin_queue'][0]]
  } else if (t === 'demo_status') {
    next.demo = p as unknown as Projection['demo']
  } else if (t === 'map_scan_request') {
    next.map_scan_pending = p as Projection['map_scan_pending']
  } else if (t === 'map_ready') {
    next.map_ready = p as unknown as Projection['map_ready']
    next.map_scan_pending = null
  }

  const timelineTypes = new Set([
    'agent_state',
    'alert',
    'zone_event',
    'caregiver_ack',
    'transcript',
    'say',
    'checkin',
    'config_update',
    'map_scan_request',
    'map_ready',
  ])
  const yielded = t === 'robot_status' && (p as { state?: string }).state === 'yielded'
  if (timelineTypes.has(t) || yielded) {
    next.timeline = [msg, ...next.timeline].slice(0, 500)
  }

  state = next
  emit()
}
