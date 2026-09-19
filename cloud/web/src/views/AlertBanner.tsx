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
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/70 p-0 backdrop-blur-sm sm:items-center sm:p-4">
      <div className="w-full max-w-lg rounded-t-2xl border border-[var(--alert)] bg-[#2a1515] p-5 shadow-2xl sm:rounded-xl sm:p-6">
        <p className="text-xs uppercase tracking-widest text-[#ffb4b4]">
          Alert level {a.level}
          {a.live_tracking ? ' · live tracking' : ''}
        </p>
        <h2 className="mt-2 text-xl text-[#ffe0e0] sm:text-2xl">{a.headline}</h2>
        <p className="mt-2 text-sm text-[#ffc9c9]">{a.detail}</p>
        <div className="mt-6 flex flex-col gap-2 sm:flex-row sm:flex-wrap">
          <button
            type="button"
            className="min-h-12 w-full rounded-md bg-[var(--accent)] px-4 py-3 text-base font-medium text-[#1a1408] sm:w-auto"
            onClick={() => ack(a.alert_id, 'im_coming')}
          >
            I have this
          </button>
          <button
            type="button"
            className="min-h-12 w-full rounded-md bg-white/10 px-4 py-3 text-sm sm:w-auto"
            onClick={() => ack(a.alert_id, 'false_alarm')}
          >
            False alarm
          </button>
          <button
            type="button"
            className="min-h-12 w-full rounded-md bg-white/10 px-4 py-3 text-sm sm:w-auto"
            onClick={() => ack(a.alert_id, 'call_help')}
          >
            Call help
          </button>
        </div>
      </div>
    </div>
  )
}
