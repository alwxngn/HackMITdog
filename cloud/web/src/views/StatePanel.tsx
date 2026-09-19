import { useProjection } from '../hooks/useProjection'

export function StatePanel() {
  const p = useProjection()
  const a = p.agent_state
  const tracker = p.person_track?.tracker

  const agitationClass =
    a.agitation === 'agitated'
      ? 'bg-[var(--color-iris-pulse)] text-[var(--color-cloud-white)]'
      : a.agitation === 'unsettled'
        ? 'bg-[var(--color-iris-glow)] text-[var(--color-cyan-soft)]'
        : 'bg-[color-mix(in_srgb,var(--color-mint-vital)_18%,transparent)] text-[var(--color-mint-vital)]'

  return (
    <div className="card-metric">
      <div className="mb-4 flex flex-wrap items-center gap-2">
        <span className="pill bg-[var(--color-iris-pulse)] text-[var(--color-cloud-white)]">
          {a.state}
        </span>
        <span className={`pill uppercase ${agitationClass}`}>{a.agitation}</span>
        {tracker && (
          <span className="pill border border-[var(--color-iris-border)] text-[var(--color-iris-pulse)]">
            tracker: {tracker}
          </span>
        )}
        {p.robot_status?.state === 'yielded' && (
          <span className="pill border border-[var(--color-iris-pulse)] text-[var(--color-iris-pulse)]">
            yielded
          </span>
        )}
      </div>
      <p className="text-[24px] font-semibold leading-[1.2] tracking-[-0.03em] text-[var(--color-clinical-cyan)] md:text-[32px]">
        {a.reason}
      </p>
      {p.last_transcript && (
        <p className="mt-4 text-[14px] tracking-[0.02em] text-[var(--color-muted-ink)]">
          heard: “{p.last_transcript.text}”
        </p>
      )}
    </div>
  )
}
