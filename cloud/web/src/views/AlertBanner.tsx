import { useProjection } from '../hooks/useProjection'

async function ack(alertId: string, action: string) {
  await fetch(`/api/ack?alert_id=${encodeURIComponent(alertId)}&action=${action}`, {
    method: 'POST',
  })
}

export function AlertBanner() {
  const p = useProjection()
  const a = p.open_alert
  if (!a) return null

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-[color-mix(in_srgb,var(--color-forest-ink)_35%,transparent)] p-0 sm:items-center sm:p-4">
      <div className="w-full max-w-lg rounded-t-[14px] bg-[var(--color-cream-paper)] p-8 sm:rounded-[14px]">
        <p className="eyebrow">
          Alert level {a.level}
          {a.live_tracking ? ' · live tracking' : ''}
        </p>
        <h2 className="mt-3 text-[40px]">{a.headline}</h2>
        <p className="mt-3 text-[14px] text-[var(--color-charcoal)]">{a.detail}</p>
        <div className="mt-8 flex flex-col gap-[14px] sm:flex-row">
          <button type="button" className="btn-primary" onClick={() => ack(a.alert_id, 'im_coming')}>
            I have this
          </button>
          <button type="button" className="btn-ghost" onClick={() => ack(a.alert_id, 'false_alarm')}>
            False alarm
          </button>
          <button type="button" className="btn-ghost" onClick={() => ack(a.alert_id, 'call_help')}>
            Call help
          </button>
        </div>
      </div>
    </div>
  )
}
