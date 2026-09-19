import { useProjection } from '../hooks/useProjection'
import type { Envelope } from '../lib/types'

function lineFor(msg: Envelope): string {
  const p = msg.payload as Record<string, unknown>
  switch (msg.type) {
    case 'agent_state':
      return `${p.state}: ${p.reason}`
    case 'alert':
      return `ALERT L${p.level}: ${p.headline}`
    case 'zone_event':
      return `zone ${p.zone_id} ${p.event} (${p.zone_class})`
    case 'caregiver_ack':
      return `ack by ${p.by}: ${p.action}`
    case 'transcript':
      return `patient: “${p.text}”`
    case 'say':
      return `robot: “${p.text}”`
    case 'robot_status':
      return `robot ${p.state}${p.detail ? ` — ${p.detail}` : ''}`
    case 'checkin':
      return `check-in from ${p.from_name}`
    case 'config_update':
      return 'config updated'
    default:
      return msg.type
  }
}

export function Timeline() {
  const p = useProjection()
  return (
    <div className="flex h-full min-h-[220px] flex-col rounded-lg bg-[var(--panel)] p-3">
      <h2 className="mb-2 text-lg">Timeline</h2>
      <ul className="flex-1 space-y-2 overflow-y-auto text-sm">
        {p.timeline.length === 0 && (
          <li className="text-[var(--muted)]">Waiting for events…</li>
        )}
        {p.timeline.map((msg, i) => (
          <li
            key={`${msg.ts}-${msg.seq}-${i}`}
            className={
              msg.type === 'robot_status' &&
              (msg.payload as { state?: string }).state === 'yielded'
                ? 'border-l-2 border-[var(--yield)] pl-2'
                : msg.type === 'alert'
                  ? 'border-l-2 border-[var(--alert)] pl-2'
                  : 'border-l-2 border-white/10 pl-2'
            }
          >
            <span className="mr-2 font-mono text-[10px] text-[var(--muted)]">
              {new Date(msg.ts * 1000).toLocaleTimeString()}
            </span>
            {lineFor(msg)}
          </li>
        ))}
      </ul>
    </div>
  )
}
