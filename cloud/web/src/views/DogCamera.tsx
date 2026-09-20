import { useEffect, useState } from 'react'

type CameraStatus = {
  enabled: boolean
  master_enabled: boolean
  url: string | null
  stream_url: string | null
  proxy_stream: string | null
  hint: string
}

type Props = {
  open: boolean
  onOpen: () => void
  onClose: () => void
}

export function DogCamera({ open, onOpen, onClose }: Props) {
  const [status, setStatus] = useState<CameraStatus | null>(null)

  useEffect(() => {
    let cancelled = false
    fetch('/api/camera/status')
      .then((r) => r.json())
      .then((data: CameraStatus) => {
        if (!cancelled) setStatus(data)
      })
      .catch(() => {
        if (!cancelled) {
          setStatus({
            enabled: false,
            master_enabled: false,
            url: null,
            stream_url: null,
            proxy_stream: null,
            hint: 'Could not load camera config.',
          })
        }
      })
    return () => {
      cancelled = true
    }
  }, [])

  const ready = Boolean(status?.enabled)

  return (
    <div className="card">
      <div className="mb-3 flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="eyebrow mb-2">Dog camera</p>
          <h2 className="text-[18px]">On-demand view</h2>
        </div>
        {open ? (
          <button type="button" className="btn-ghost !min-h-10 !px-3 !py-2 !text-[13px]" onClick={onClose}>
            Stop camera
          </button>
        ) : (
          <button
            type="button"
            className="btn-primary !min-h-10 !px-3 !py-2 !text-[13px] disabled:opacity-50"
            disabled={!ready}
            onClick={onOpen}
          >
            View dog camera
          </button>
        )}
      </div>

      <p className="mb-3 text-[13px] text-[var(--color-ink-2)]">
        Live feed from the Go2 when you need eyes on the room — not always on. E2 serves the
        stream (DimOS cockpit / teleop); this panel only embeds it.
      </p>

      {!ready && (
        <p className="text-[12px] text-[var(--color-ink-2)]">
          {status?.hint ?? 'Camera not configured.'} See <code>robot/README.md</code>.
        </p>
      )}

      {open && ready && (
        <div className="space-y-2">
          <p className="pill !inline-flex !py-1 text-[12px]">Live — caregiver opened</p>
          {status?.proxy_stream && !status.url ? (
            <img
              src={status.proxy_stream}
              alt="Dog camera live feed"
              className="w-full rounded-[14px] bg-[var(--color-panel-2)]"
            />
          ) : status?.url ? (
            <iframe
              title="Dog camera"
              src={status.url}
              className="h-[280px] w-full rounded-[14px] border border-[var(--color-line)] bg-[var(--color-panel-2)] lg:h-[360px]"
              allow="autoplay; microphone; camera"
              referrerPolicy="no-referrer"
            />
          ) : null}
          <p className="text-[11px] text-[var(--color-ink-2)]">
            Close the panel to stop viewing. Feed is not recorded by Lantern cloud.
          </p>
        </div>
      )}
    </div>
  )
}
