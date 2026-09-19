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
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 backdrop-blur-sm">
      <div className="w-full max-w-lg rounded-xl border border-[var(--alert)] bg-[#2a1515] p-6 shadow-2xl">
        <p className="text-xs uppercase tracking-widest text-[#ffb4b4]">
          Alert level {a.level}
          {a.live_tracking ? ' · live tracking' : ''}
        </p>
        <h2 className="mt-2 text-2xl text-[#ffe0e0]">{a.headline}</h2>
        <p className="mt-2 text-sm text-[#ffc9c9]">{a.detail}</p>
        <div className="mt-6 flex flex-wrap gap-2">
          <button
            type="button"
            className="rounded-md bg-[var(--accent)] px-4 py-3 text-base font-medium text-[#1a1408]"
            onClick={() => ack(a.alert_id, 'im_coming')}
          >
            I have this
          </button>
          <button
            type="button"
            className="rounded-md bg-white/10 px-4 py-3 text-sm"
            onClick={() => ack(a.alert_id, 'false_alarm')}
          >
            False alarm
          </button>
          <button
            type="button"
            className="rounded-md bg-white/10 px-4 py-3 text-sm"
            onClick={() => ack(a.alert_id, 'call_help')}
          >
            Call help
          </button>
        </div>
      </div>
    </div>
  )
}
