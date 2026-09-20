export type Source = 'robot' | 'voice' | 'orchestrator' | 'cloud' | 'mock'

export interface Envelope<T = Record<string, unknown>> {
  type: string
  ts: number
  source: Source
  seq: number
  payload: T
}

export interface Zone {
  id: string
  class: 'safe' | 'watch' | 'exit'
  label?: string
  kind?: 'door' | 'stairs' | 'outdoor_boundary'
  /** painted rectangles from one region share this, so the UI labels them once */
  region?: string
  polygon: [number, number][]
}

export interface AgentState {
  state: string
  previous: string | null
  agitation: 'calm' | 'unsettled' | 'agitated'
  calm_mode: boolean
  reason: string
  since_ts: number
}

export interface Pose {
  x: number
  y: number
  theta: number
  battery_pct: number
  mode: string
  map_id: string
  lat?: number | null
  lon?: number | null
}

export interface PersonTrack {
  person_id: string
  tracker: string
  x: number
  y: number
  vx: number
  vy: number
  heading: number
  confidence: number
  posture: string
  zone: string
  projected_zone: string | null
  ttz_s: number | null
  lat: number | null
  lon: number | null
}

export interface Alert {
  alert_id: string
  level: number
  headline: string
  detail: string
  person_position?: { x: number; y: number; zone?: string }
  requires_ack: boolean
  channels: string[]
  context?: string
  live_tracking?: boolean
  ts?: number
}

export interface MapReady {
  request_id: string
  map_id: string
  origin: { x: number; y: number }
  width_m: number
  height_m: number
  outline: [number, number][]
  rooms?: { id: string; polygon: [number, number][] }[]
}

export interface TrailPoint {
  x: number
  y: number
  lat?: number | null
  lon?: number | null
  ts: number
}

export interface DemoStatus {
  running: boolean
  step: string | null
  step_index?: number
  total?: number
}

export interface Projection {
  agent_state: AgentState
  pose: Pose | null
  person_track: PersonTrack | null
  person_trail: TrailPoint[]
  zones: Zone[]
  config: Record<string, unknown>
  open_alert: Alert | null
  live_tracking: boolean
  speech_state: string
  last_transcript: { text: string; confidence?: number } | null
  robot_status: { command_id: string; state: string; detail: string | null; distance_to_person_m?: number } | null
  checkin_queue: { checkin_id: string; from_name: string; text: string }[]
  map_ready: MapReady | null
  map_scan_pending: { request_id: string; mode?: string } | null
  demo: DemoStatus
  timeline: Envelope[]
}

export interface MorningReport {
  episode_count: number
  episodes: {
    start_ts: number
    end_ts: number | null
    duration_s: number
    peak_state: string
    agitation?: string
    reason?: string
    resolution: string | null
    alert_headline?: string
  }[]
  summary: string
}
