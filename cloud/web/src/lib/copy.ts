import type { AgentState, Envelope, PersonTrack, Zone } from './types'

const STATE_TITLE: Record<string, string> = {
  IDLE: 'All is quiet',
  ATTEND: 'Lantern is with them',
  LEAD: 'Guiding them back',
  ESCALATE: 'Needs you now',
  EMERGENCY: 'Emergency',
  WALK: 'Out on a walk',
  FOLLOW: 'Staying close',
  CONFIRM_HOME: 'Checking they are home',
  GUIDE_HOME: 'Helping them home',
}

const STATE_VERB: Record<string, string> = {
  IDLE: 'resting nearby',
  ATTEND: 'checking in',
  LEAD: 'gently guiding them',
  ESCALATE: 'calling for you',
  EMERGENCY: 'in an emergency',
  WALK: 'on a walk with them',
  FOLLOW: 'following at a distance',
  CONFIRM_HOME: 'confirming they are home',
  GUIDE_HOME: 'helping them home',
}

const MOOD: Record<string, string> = {
  calm: 'They seem settled.',
  unsettled: 'They seem a little uneasy.',
  agitated: 'They seem distressed.',
}

const SKIP_TIMELINE = new Set([
  'pose',
  'person_track',
  'speech_state',
  'map_scan_request',
  'prosody',
  'snapshot',
])

/** Where the person is right now, in terms the caregiver cares about. */
export interface ZoneContext {
  cls: 'safe' | 'watch' | 'exit' | 'outside'
  label: string
}

export function zoneContext(track: PersonTrack | null, zones: Zone[]): ZoneContext | null {
  if (!track) return null
  if (track.zone === 'outside') return { cls: 'outside', label: 'Outside' }
  const z = zones.find((zone) => zone.id === track.zone)
  return z ? { cls: z.class, label: z.label || z.id } : null
}

export function statusHeadline(a: AgentState, zone?: ZoneContext | null, name?: string): string {
  const who = name ? `${name} is` : 'They are'
  if (zone?.cls === 'outside') return name ? `${name} has left the house` : 'They have left the house'
  if (zone?.cls === 'exit') return `${who} in the Don't-go zone`
  if (zone?.cls === 'watch') return `${who} in the warning zone`
  return STATE_TITLE[a.state] || 'Lantern is with them'
}

export function statusDetail(a: AgentState, zone?: ZoneContext | null): string {
  const verb = STATE_VERB[a.state] || 'nearby'
  const mood = MOOD[a.agitation] || ''
  if (zone?.cls === 'outside') {
    return 'Lantern is following at a distance. Open live tracking to see where they are.'
  }
  // The headline already says which zone they are in, so skip the raw reason here.
  if (zone?.cls === 'exit') return `Lantern is ${verb}. ${mood}`.trim()
  if (zone?.cls === 'watch') return `Near ${zone.label}. Lantern is ${verb}. ${mood}`.trim()
  const reason = humanReason(a.reason)
  return (reason ? `Lantern is ${verb}. ${reason} ${mood}` : `Lantern is ${verb}. ${mood}`).trim()
}

function humanReason(reason: string): string {
  const r = (reason || '').trim()
  if (!r || r === 'boot' || r === 'connecting…' || r === 'connecting...') {
    return ''
  }
  if (r.startsWith('projected_zone=')) return 'They may be heading toward an edge of the home.'
  return r.endsWith('.') ? r : `${r}.`
}

export function timelineLine(msg: Envelope): string | null {
  if (SKIP_TIMELINE.has(msg.type)) return null
  const p = msg.payload as Record<string, unknown>
  switch (msg.type) {
    case 'agent_state': {
      const state = String(p.state || '')
      const reason = humanReason(String(p.reason || ''))
      const title = STATE_TITLE[state]
      if (!title) return null
      if (state === 'IDLE' && !reason) return 'The house is quiet again.'
      return reason ? `${title} — ${reason}` : title
    }
    case 'alert':
      return String(p.headline || 'Needs attention')
    case 'zone_event': {
      const label = String(p.zone_label || p.zone_id || 'a doorway')
      const ev = String(p.event || '')
      const cls = String(p.zone_class || '')
      if (ev === 'exited' && p.outside === true) return 'Left the house.'
      if (ev === 'approaching') return null
      if (ev === 'enter' || ev === 'entered') {
        if (cls === 'watch') return `Entered the warning zone (${label}).`
        if (cls === 'exit') return "Reached the Don't-go zone."
        return `Near ${label}.`
      }
      if (ev === 'exit' || ev === 'exited' || ev === 'left') return `Left ${label}.`
      return `At ${label}.`
    }
    case 'caregiver_ack': {
      const action = String(p.action || '')
      if (action === 'im_coming') return 'You said you’ll handle it.'
      if (action === 'false_alarm') return 'Marked as a false alarm.'
      if (action === 'call_help') return 'You asked to call for help.'
      return 'You responded to an alert.'
    }
    case 'transcript':
      return p.text ? `They said “${p.text}”` : null
    case 'say':
      return p.text ? `Lantern said “${p.text}”` : null
    case 'robot_status': {
      const st = String(p.state || '')
      if (st === 'yielded') return 'Lantern stepped aside for someone nearby.'
      if (st === 'arrived' || st === 'done') return 'Lantern finished that movement.'
      return null
    }
    case 'checkin':
      return p.from_name ? `Check-in from ${p.from_name} is waiting.` : 'A check-in is waiting.'
    case 'config_update':
      return 'Home setup was saved.'
    case 'map_ready':
      return 'The home map is ready.'
    default:
      return null
  }
}

export function episodeLine(e: {
  peak_state: string
  duration_s: number
  resolution: string | null
  reason?: string
  alert_headline?: string
}): string {
  const mins = Math.max(1, Math.round(e.duration_s / 60))
  const what = STATE_TITLE[e.peak_state] || e.peak_state
  const done = e.resolution ? 'resolved' : 'still open'
  const extra = e.alert_headline || e.reason || ''
  return extra ? `${what} · about ${mins} min · ${done} — ${extra}` : `${what} · about ${mins} min · ${done}`
}
