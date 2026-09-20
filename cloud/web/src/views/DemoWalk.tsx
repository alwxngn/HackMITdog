import { useState } from 'react'
import { useProjection } from '../hooks/useProjection'

export function DemoWalk() {
  const { demo } = useProjection()
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  async function call(path: string) {
    setBusy(true)
    setError('')
    try {
      const r = await fetch(path, { method: 'POST' })
      if (!r.ok) {
        const d = (await r.json().catch(() => ({}))) as { error?: string }
        setError(d.error || 'Could not reach Lantern.')
      }
    } catch {
      setError('Could not reach Lantern.')
    } finally {
      setBusy(false)
    }
  }

  const total = demo.total ?? 5
  const index = demo.step_index ?? 0

  return (
    <section className="card-cream">
      <p className="eyebrow mb-2">Demo</p>
      <h2>Walk-through</h2>
      {demo.running ? (
        <>
          <p className="mt-3 text-[14px] text-[var(--color-ink)]">
            Step {index} of {total} · {demo.step}
          </p>
          <div className="mt-3 flex gap-1.5" aria-hidden>
            {Array.from({ length: total }, (_, i) => (
              <span
                key={i}
                className="h-1.5 flex-1 rounded-full"
                style={{ background: i < index ? 'var(--color-ink)' : 'var(--color-panel-2)' }}
              />
            ))}
          </div>
          <button type="button" className="btn-ghost mt-4" disabled={busy} onClick={() => call('/api/demo/stop')}>
            End demo
          </button>
        </>
      ) : (
        <>
          <p className="mt-3 text-[14px] text-[var(--color-ink-2)]">
            Simulates the person walking from the safe zone into the warning zone, then the Don’t-go zone, and out of
            the house.
          </p>
          <button type="button" className="btn-primary mt-4" disabled={busy} onClick={() => call('/api/demo/walk')}>
            Run demo walk
          </button>
        </>
      )}
      {error && (
        <p role="alert" className="mt-3 text-[13px] text-[var(--color-danger)]">
          {error}
        </p>
      )}
    </section>
  )
}
