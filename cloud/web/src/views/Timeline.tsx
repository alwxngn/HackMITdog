import { timelineLine } from '../lib/copy'
import { useProjection } from '../hooks/useProjection'

export function Timeline() {
  const p = useProjection()
  const lines = p.timeline
    .map((msg, i) => {
      const text = timelineLine(msg)
      if (!text) return null
      return { msg, text, i }
    })
    .filter((row): row is { msg: (typeof p.timeline)[0]; text: string; i: number } => row !== null)

  return (
    <div className="card-mint flex min-h-[220px] flex-col">
      <p className="eyebrow mb-2">Activity</p>
      <h2 className="mb-5">What happened</h2>
      <ul className="flex-1 space-y-4 overflow-y-auto text-[14px]">
        {lines.length === 0 && (
          <li className="text-[var(--color-ink-2)]">Nothing to report. It’s been a calm night so far.</li>
        )}
        {lines.map(({ msg, text, i }) => {
          const isAlert = msg.type === 'alert'
          return (
            <li
              key={`${msg.ts}-${msg.seq}-${i}`}
              className={
                isAlert
                  ? 'border-l-2 border-[var(--color-ink)] pl-3'
                  : 'border-l-2 border-[var(--color-panel-2)] pl-3'
              }
            >
              <p className="text-[12px] text-[var(--color-ink-2)]">
                {new Date(msg.ts * 1000).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })}
              </p>
              <p className={isAlert ? 'text-[var(--color-ink)]' : ''}>{text}</p>
            </li>
          )
        })}
      </ul>
    </div>
  )
}
