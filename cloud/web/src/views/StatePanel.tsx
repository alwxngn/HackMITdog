import { useProjection } from '../hooks/useProjection'

export function StatePanel() {
  const p = useProjection()
  const a = p.agent_state
  const tracker = p.person_track?.tracker

  return (
    <div className="card-metric h-full">
      <div className="mb-5 flex flex-wrap items-center gap-2">
        <span className="pill">{a.state}</span>
        <span className="pill uppercase">{a.agitation}</span>
        {tracker && <span className="pill">tracker: {tracker}</span>}
        {p.robot_status?.state === 'yielded' && <span className="pill">yielded</span>}
      </div>
      <p className="font-[family-name:var(--font-faire-octave)] text-[40px] font-light leading-[1.2] text-[var(--color-forest-ink)]">
        {a.reason}
      </p>
      {p.last_transcript && (
        <p className="mt-4 text-[14px] text-[var(--color-charcoal)]">
          heard: “{p.last_transcript.text}”
        </p>
      )}
    </div>
  )
}
