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
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-[color-mix(in_srgb,var(--color-deep-iris)_75%,black)]/80 p-0 backdrop-blur-sm sm:items-center sm:p-4">
      <div className="w-full max-w-lg rounded-t-[32px] border border-[var(--color-iris-border)] bg-[var(--color-iris-glow)] p-6 shadow-[0_0_40px_rgba(60,57,185,0.45)] sm:rounded-[32px]">
        <p className="text-[12px] uppercase tracking-[0.08em] text-[var(--color-lilac-mist)]">
          Alert level {a.level}
          {a.live_tracking ? ' · live tracking' : ''}
        </p>
        <h2 className="mt-2 text-[28px] font-semibold tracking-[-0.04em] text-[var(--color-cloud-white)] sm:text-[36px]">
          {a.headline}
        </h2>
        <p className="mt-3 text-[14px] text-[var(--color-pearl)]">{a.detail}</p>
        <div className="mt-6 flex flex-col gap-2 sm:flex-row sm:flex-wrap">
          <button
            type="button"
            className="btn-primary w-full sm:w-auto"
            onClick={() => ack(a.alert_id, 'im_coming')}
          >
            I have this
          </button>
          <button
            type="button"
            className="btn-ghost w-full sm:w-auto"
            onClick={() => ack(a.alert_id, 'false_alarm')}
          >
            False alarm
          </button>
          <button
            type="button"
            className="btn-ghost w-full sm:w-auto"
            onClick={() => ack(a.alert_id, 'call_help')}
          >
            Call help
          </button>
        </div>
      </div>
    </div>
  )
}
