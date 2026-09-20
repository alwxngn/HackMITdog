import { useEffect, useState } from 'react'
import QRCode from 'qrcode'
import { publicOrigin, publicUrl } from '../lib/origin'

async function toDataUrl(text: string): Promise<string> {
  return QRCode.toDataURL(text, {
    margin: 1,
    width: 160,
    color: { dark: '#0e1116', light: '#ffffff' },
  })
}

export function ShareQR() {
  const [watchQr, setWatchQr] = useState('')
  const [onboardQr, setOnboardQr] = useState('')
  const [open, setOpen] = useState(false)
  const origin = publicOrigin()
  const watchUrl = publicUrl('/watch')
  const onboardUrl = publicUrl('/onboarding')
  const needsTunnelHint = origin.includes('127.0.0.1') || origin.includes('localhost')

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      const [w, o] = await Promise.all([toDataUrl(watchUrl), toDataUrl(onboardUrl)])
      if (!cancelled) {
        setWatchQr(w)
        setOnboardQr(o)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [watchUrl, onboardUrl])

  return (
    <div className="relative">
      <button type="button" className="btn-ghost !min-h-10 !py-2" onClick={() => setOpen((v) => !v)}>
        {open ? 'Hide codes' : 'Phone codes'}
      </button>
      {open && (
        <div className="absolute right-0 z-30 mt-2 w-[min(92vw,360px)] rounded-[14px] bg-[var(--color-panel)] p-5">
          <p className="mb-3 text-[14px] text-[var(--color-ink-2)]">
            Scan to open this dashboard or home setup on a phone.
          </p>
          {needsTunnelHint && (
            <p className="mb-3 rounded-[14px] bg-[var(--color-surface)] px-3 py-2 text-[12px]">
              These codes point at this computer. Phones need a tunnel URL in VITE_PUBLIC_ORIGIN.
            </p>
          )}
          <div className="grid grid-cols-2 gap-3">
            <QrCard label="Watch" url={watchUrl} src={watchQr} />
            <QrCard label="Setup" url={onboardUrl} src={onboardQr} />
          </div>
        </div>
      )}
    </div>
  )
}

function QrCard({ label, url, src }: { label: string; url: string; src: string }) {
  return (
    <div className="flex flex-col items-center gap-2 text-center">
      <div className="rounded-[14px] bg-[var(--color-surface)] p-2">
        {src ? (
          <img src={src} alt={`QR ${label}`} className="h-24 w-24" />
        ) : (
          <div className="flex h-24 w-24 items-center justify-center text-[13px]">…</div>
        )}
      </div>
      <p className="text-[14px] text-[var(--color-ink)]">{label}</p>
      <a href={url} className="sr-only">
        {url}
      </a>
    </div>
  )
}
