import { useEffect, useState } from 'react'
import { useProjection } from '../hooks/useProjection'

interface SpeakerStatus {
  phone_online: boolean
  phone_ready: boolean
}

export function DemoWalk() {
  const { demo } = useProjection()
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [speaker, setSpeaker] = useState<SpeakerStatus | null>(null)
  const [testNote, setTestNote] = useState('')

  // Is the phone on the dog paired and started? Poll so the card stays honest.
  useEffect(() => {
    let cancelled = false
    const poll = () =>
      fetch('/api/speaker')
        .then((r) => r.json())
        .then((s: SpeakerStatus) => !cancelled && setSpeaker(s))
        .catch(() => !cancelled && setSpeaker(null))
    void poll()
    const id = setInterval(poll, 3000)
    return () => {
      cancelled = true
      clearInterval(id)
    }
  }, [])

  async function testSpeaker() {
    setTestNote('')
    try {
      const r = await fetch('/api/speaker/test', { method: 'POST' })
      const d = (await r.json()) as { on_phone?: boolean }
      setTestNote(d.on_phone ? 'Sent — you should hear it on the phone.' : 'No phone is started, so it only appears in the timeline.')
    } catch {
      setTestNote('Could not reach Lantern.')
    }
  }

  const speakerLine = speaker?.phone_ready
    ? { dot: 'var(--color-safe)', text: 'Speaker phone ready' }
    : speaker?.phone_online
      ? { dot: 'var(--color-watch)', text: 'Phone paired — tap Start Lantern on it' }
      : { dot: 'var(--color-tint)', text: 'No speaker phone — scan the QR under Check-in' }

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
      <p className="mt-3 flex items-center gap-2 text-[13px] text-[var(--color-ink-2)]">
        <span className="h-2 w-2 shrink-0 rounded-full" style={{ background: speakerLine.dot }} />
        <span className="min-w-0 flex-1">{speakerLine.text}</span>
        <button type="button" className="shrink-0 underline" onClick={testSpeaker}>
          Test speaker
        </button>
      </p>
      {testNote && <p className="mt-1 text-[12px] text-[var(--color-ink-2)]">{testNote}</p>}
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
