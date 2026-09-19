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
    <div className="card flex h-full min-h-[220px] flex-col">
      <h2 className="mb-3 text-[18px] tracking-[-0.03em]">Timeline</h2>
      <ul className="flex-1 space-y-3 overflow-y-auto text-[14px]">
        {p.timeline.length === 0 && (
          <li className="text-[var(--color-fog)]">Waiting for events…</li>
        )}
        {p.timeline.map((msg, i) => {
          const yielded =
            msg.type === 'robot_status' &&
            (msg.payload as { state?: string }).state === 'yielded'
          const isAlert = msg.type === 'alert'
          return (
            <li
              key={`${msg.ts}-${msg.seq}-${i}`}
              className={
                isAlert
                  ? 'border-l-2 border-[var(--color-teal-signal)] pl-3'
                  : yielded
                    ? 'border-l-2 border-[var(--color-lilac-mist)] pl-3'
                    : 'border-l-2 border-[var(--color-iris-border)] pl-3'
              }
            >
              <span className="mr-2 text-[12px] tracking-[0.02em] text-[var(--color-fog)]">
                {new Date(msg.ts * 1000).toLocaleTimeString()}
              </span>
              <span className={isAlert ? 'text-[var(--color-clinical-cyan)]' : ''}>
                {lineFor(msg)}
              </span>
            </li>
          )
        })}
      </ul>
    </div>
  )
}
