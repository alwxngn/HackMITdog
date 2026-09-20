import { useEffect, useState } from 'react'
import { useProjection } from '../hooks/useProjection'

async function ack(alertId: string, action: string) {
  await fetch(`/api/ack?alert_id=${encodeURIComponent(alertId)}&action=${action}`, {
    method: 'POST',
  })
}

type Props = {
  onOpenCamera?: () => void
  cameraOpen?: boolean
  onTrack?: () => void
  onCallHelp?: () => void
}

const TOAST_MS = 10_000

export function AlertBanner({ onOpenCamera, cameraOpen, onTrack, onCallHelp }: Props = {}) {
  const p = useProjection()
  const a = p.open_alert
  const [minimizedId, setMinimizedId] = useState<string | null>(null)
  const [dismissedId, setDismissedId] = useState<string | null>(null)

  const headsUp = a ? a.level <= 1 || a.requires_ack === false : false
  const alertId = a?.alert_id

  // Heads-up notifications fade on their own; they never need an answer.
  useEffect(() => {
    if (!alertId || !headsUp) return
    const t = setTimeout(() => setDismissedId(alertId), TOAST_MS)
    return () => clearTimeout(t)
  }, [alertId, headsUp])

  if (!a) return null

  if (headsUp) {
    if (dismissedId === a.alert_id) return null
    return (
      <div
        role="status"
        className="fixed inset-x-0 top-0 z-50 flex justify-center px-4"
        style={{ paddingTop: 'calc(env(safe-area-inset-top, 0px) + 12px)' }}
      >
        <div className="flex w-full max-w-[460px] items-start gap-3 rounded-[14px] bg-[var(--color-surface)] p-4 shadow-[var(--shadow-card)] ring-1 ring-[var(--color-line)]">
          <span className="mt-1.5 h-2.5 w-2.5 shrink-0 rounded-full bg-[var(--color-watch)]" />
          <div className="min-w-0 flex-1">
            <p className="eyebrow mb-1">Heads-up</p>
            <p className="text-[15px] font-medium text-[var(--color-ink)]">{a.headline}</p>
            <p className="mt-1 text-[13px] text-[var(--color-ink-2)]">{a.detail}</p>
          </div>
          <button
            type="button"
            aria-label="Dismiss"
            className="text-[18px] leading-none text-[var(--color-ink-2)]"
            onClick={() => setDismissedId(a.alert_id)}
          >
            ×
          </button>
        </div>
      </div>
    )
  }

  const critical = a.level >= 5

  if (minimizedId === a.alert_id) {
    return (
      <div
        className="fixed inset-x-0 top-0 z-50 flex justify-center px-4"
        style={{ paddingTop: 'calc(env(safe-area-inset-top, 0px) + 12px)' }}
      >
        <div className="flex w-full max-w-[460px] items-center gap-3 rounded-[14px] bg-[var(--color-ink)] p-3 pl-4 text-white shadow-[var(--shadow-card)]">
          <span className="h-2.5 w-2.5 shrink-0 animate-pulse rounded-full bg-[var(--color-danger)]" />
          <button
            type="button"
            className="min-w-0 flex-1 truncate text-left text-[14px] font-medium"
            onClick={() => setMinimizedId(null)}
          >
            {a.headline}
          </button>
          <button
            type="button"
            className="shrink-0 rounded-full bg-white px-3 py-1.5 text-[13px] font-medium text-[var(--color-ink)]"
            onClick={() => ack(a.alert_id, 'dismiss')}
          >
            Dismiss
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-[color-mix(in_srgb,var(--color-ink)_35%,transparent)] p-0 sm:items-center sm:p-4">
      <div
        className={`w-full max-w-lg rounded-t-[14px] bg-[var(--color-surface)] p-8 sm:rounded-[14px] ${
          critical ? 'border-t-4 border-[var(--color-danger)]' : ''
        }`}
      >
        <p className="eyebrow" style={critical ? { color: 'var(--color-danger)' } : undefined}>
          {critical ? 'Critical alert' : 'Needs your attention'}
          {a.live_tracking ? ' · live tracking' : ''}
        </p>
        <h2 className="mt-3 text-[40px]">{a.headline}</h2>
        <p className="mt-3 text-[14px] text-[var(--color-ink-2)]">{a.detail}</p>
        {onOpenCamera && !cameraOpen && (
          <p className="mt-4 rounded-[14px] bg-[var(--color-accent-soft)] px-4 py-3 text-[13px] text-[var(--color-ink)]">
            Need eyes on the room?{' '}
            <button type="button" className="underline" onClick={onOpenCamera}>
              Open dog camera
            </button>{' '}
            (on-demand — not always recording).
          </p>
        )}
        <div className="mt-8 flex flex-col gap-[14px] sm:flex-row">
          {onTrack && a.live_tracking && (
            <button
              type="button"
              className="btn-primary"
              onClick={() => {
                setMinimizedId(a.alert_id)
                onTrack()
              }}
            >
              Track live location
            </button>
          )}
          <button
            type="button"
            className={onTrack && a.live_tracking ? 'btn-ghost' : 'btn-primary'}
            onClick={() => ack(a.alert_id, 'dismiss')}
          >
            Dismiss
          </button>
          <button
            type="button"
            className="btn-ghost"
            onClick={() => {
              void ack(a.alert_id, 'call_help')
              onCallHelp?.()
            }}
          >
            Call help
          </button>
        </div>
      </div>
    </div>
  )
}
