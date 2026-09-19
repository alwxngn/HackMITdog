import { useProjection } from '../hooks/useProjection'

export function StatePanel() {
  const p = useProjection()
  const a = p.agent_state
  const tracker = p.person_track?.tracker

  return (
    <div className="rounded-lg bg-[var(--panel)] p-4">
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <span className="rounded bg-white/10 px-2 py-1 font-mono text-sm tracking-wide">
          {a.state}
        </span>
        <span
          className={`rounded px-2 py-1 text-xs uppercase ${
            a.agitation === 'agitated'
              ? 'bg-[var(--exit)]/40 text-[#ffb4b4]'
              : a.agitation === 'unsettled'
                ? 'bg-[var(--watch)]/40 text-[#ffd9a0]'
                : 'bg-[var(--safe)]/40 text-[#b8e0c8]'
          }`}
        >
          {a.agitation}
        </span>
        {tracker && (
          <span className="rounded border border-white/20 px-2 py-1 text-xs text-[var(--muted)]">
            tracker: {tracker}
          </span>
        )}
        {p.robot_status?.state === 'yielded' && (
          <span className="rounded bg-[var(--yield)]/40 px-2 py-1 text-xs">yielded</span>
        )}
      </div>
      <p className="text-xl leading-snug text-[var(--accent)] md:text-2xl">{a.reason}</p>
      {p.last_transcript && (
        <p className="mt-3 text-sm text-[var(--muted)]">
          heard: “{p.last_transcript.text}”
        </p>
      )}
    </div>
  )
}
