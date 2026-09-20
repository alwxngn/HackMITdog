import type { ReactNode } from 'react'
import { Hero } from '../components/Hero'
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

/** Home hero: live status of the person, with Lantern's mood mirroring it. */
export function StatePanel({ top }: { top?: ReactNode }) {
  const p = useProjection()
  const a = p.agent_state
  const name =
    (p.config.patient as { preferred_name?: string; name?: string } | undefined)?.preferred_name ||
    (p.config.patient as { name?: string } | undefined)?.name

  const watching = (p.config.night_watch_enabled as boolean | undefined) ?? false
  const zone = watching ? zoneContext(p.person_track, p.zones) : null
  const danger = zone?.cls === 'outside' || zone?.cls === 'exit' || a.state === 'ESCALATE' || a.state === 'EMERGENCY'
  const zoneTone = danger ? 'var(--color-danger)' : zone?.cls === 'watch' ? 'var(--color-watch)' : null
  const tone = zoneTone ?? STATE_TONE[a.state] ?? 'var(--color-accent)'
  const mood = danger ? 'alert' : watching ? 'happy' : 'sleepy'

  return (
    <Hero top={top} mood={mood} alert={watching}>
      <p className="eyebrow mb-2 !text-[10.5px] !leading-[1.9] !tracking-[0.06em] !text-[var(--color-tint)]">
        {name ? `Lantern is looking after ${name}` : 'Lantern is on watch'}
        <span className="ml-2 inline-flex items-center gap-1.5 rounded-full bg-[var(--color-ink)] py-1 pl-2 pr-2.5 align-middle text-[10px] font-bold uppercase leading-none tracking-[0.08em] text-white">
          <span className="relative flex h-2 w-2">
            <span
              className="absolute inline-flex h-full w-full animate-ping rounded-full opacity-70"
              style={{ background: tone }}
            />
            <span className="relative inline-flex h-2 w-2 rounded-full" style={{ background: tone }} />
          </span>
          Live
        </span>
      </p>
      <h1 className="text-[32px] capitalize leading-[1.08] !text-white">{statusHeadline(a, zone, name)}</h1>
      <p className="mt-2 text-[14px] font-semibold leading-[1.5] text-[#a8cdc8]">
        {statusDetail(a, zone)}
        {p.robot_status?.state === 'yielded' ? ' Someone walked by, so Lantern paused.' : ''}
      </p>
      {p.last_transcript?.text && (
        <p className="mt-2 text-[13px] font-semibold text-[var(--color-accent)]">
          Last heard: “{p.last_transcript.text}”
        </p>
      )}
    </Hero>
  )
}
