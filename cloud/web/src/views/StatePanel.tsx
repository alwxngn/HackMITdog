import { statusDetail, statusHeadline, zoneContext } from '../lib/copy'
import { useProjection } from '../hooks/useProjection'

const STATE_TONE: Record<string, string> = {
  IDLE: 'var(--color-safe)',
  ATTEND: 'var(--color-accent)',
  FOLLOW: 'var(--color-accent)',
  WALK: 'var(--color-accent)',
  LEAD: 'var(--color-watch)',
  GUIDE_HOME: 'var(--color-watch)',
  CONFIRM_HOME: 'var(--color-watch)',
  ESCALATE: 'var(--color-danger)',
  EMERGENCY: 'var(--color-danger)',
}

export function StatePanel() {
  const p = useProjection()
  const a = p.agent_state
  const name =
    (p.config.patient as { preferred_name?: string; name?: string } | undefined)?.preferred_name ||
    (p.config.patient as { name?: string } | undefined)?.name

  const watching = (p.config.night_watch_enabled as boolean | undefined) ?? true
  const zone = watching ? zoneContext(p.person_track, p.zones) : null
  const zoneTone =
    zone?.cls === 'outside' || zone?.cls === 'exit'
      ? 'var(--color-danger)'
      : zone?.cls === 'watch'
        ? 'var(--color-watch)'
        : null
  const tone = zoneTone ?? STATE_TONE[a.state] ?? 'var(--color-accent)'

  return (
    <section className="card-metric">
      <div className="mb-4 flex items-center justify-between gap-3">
        <p className="eyebrow inline-flex items-center gap-2">
          <span className="relative flex h-2 w-2">
            <span
              className="absolute inline-flex h-full w-full animate-ping rounded-full opacity-60"
              style={{ background: tone }}
            />
            <span className="relative inline-flex h-2 w-2 rounded-full" style={{ background: tone }} />
          </span>
          {name ? `${name} · live` : 'Live'}
        </p>
        <span className="rounded-full bg-[var(--color-panel)] px-2.5 py-1 text-[11px] font-medium capitalize text-[var(--color-ink-2)]">
          {a.agitation}
        </span>
      </div>
      <h1 className="text-[32px] leading-[1.12]">{statusHeadline(a, zone, name)}</h1>
      <p className="mt-3 max-w-2xl text-[15px] leading-[1.55] text-[var(--color-ink-2)]">
        {statusDetail(a, zone)}
        {p.robot_status?.state === 'yielded' ? ' Someone walked by, so Lantern paused.' : ''}
      </p>
      {p.last_transcript?.text && (
        <p className="mt-4 text-[14px] text-[var(--color-ink-2)]">
          Last heard: “{p.last_transcript.text}”
        </p>
      )}
    </section>
  )
}
