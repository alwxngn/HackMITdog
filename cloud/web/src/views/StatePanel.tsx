import { statusDetail, statusHeadline } from '../lib/copy'
import { useProjection } from '../hooks/useProjection'

export function StatePanel() {
  const p = useProjection()
  const a = p.agent_state
  const name =
    (p.config.patient as { preferred_name?: string; name?: string } | undefined)?.preferred_name ||
    (p.config.patient as { name?: string } | undefined)?.name

  return (
    <section className="card-metric">
      <p className="eyebrow mb-3">{name ? `${name} · now` : 'Right now'}</p>
      <h1 className="text-[32px] leading-[1.2] lg:text-[40px]">{statusHeadline(a)}</h1>
      <p className="mt-3 max-w-2xl text-[16px] leading-[1.5] text-[var(--color-charcoal)]">
        {statusDetail(a)}
        {p.robot_status?.state === 'yielded' ? ' Someone walked by, so Lantern paused.' : ''}
      </p>
      {p.last_transcript?.text && (
        <p className="mt-4 text-[14px] text-[var(--color-charcoal)]">
          Last heard: “{p.last_transcript.text}”
        </p>
      )}
    </section>
  )
}
