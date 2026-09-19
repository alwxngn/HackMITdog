import { useEffect, useState } from 'react'
import QRCode from 'qrcode'
import { publicOrigin, publicUrl } from '../lib/origin'

async function toDataUrl(text: string): Promise<string> {
  return QRCode.toDataURL(text, {
    margin: 1,
    width: 160,
    color: { dark: '#0f1419', light: '#ffffff' },
  })
}

export function ShareQR() {
  const [watchQr, setWatchQr] = useState('')
  const [onboardQr, setOnboardQr] = useState('')
  const [open, setOpen] = useState(true)
  const origin = publicOrigin()
  const watchUrl = publicUrl('/')
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
    <div className="rounded-lg border border-white/10 bg-[var(--panel)] p-3">
      <button
        type="button"
        className="flex w-full items-center justify-between text-left text-sm"
        onClick={() => setOpen((v) => !v)}
      >
        <span className="font-medium text-[var(--accent)]">Share on phone</span>
        <span className="text-[var(--muted)]">{open ? 'hide' : 'show'}</span>
      </button>
      {open && (
        <div className="mt-3 space-y-3">
          <p className="text-xs text-[var(--muted)]">
            Scan to open Night Watch or caregiver onboarding. Set{' '}
            <code className="text-[var(--ink)]">VITE_PUBLIC_ORIGIN</code> to your tunnel URL when
            developing on localhost.
          </p>
          {needsTunnelHint && (
            <p className="rounded bg-[var(--watch)]/20 px-2 py-1 text-xs text-[#ffd9a0]">
              These QRs point at localhost — phones cannot open that. Start a tunnel (see
              cloud/README) and set VITE_PUBLIC_ORIGIN.
            </p>
          )}
          <div className="grid grid-cols-2 gap-3">
            <QrCard label="Night Watch" url={watchUrl} src={watchQr} />
            <QrCard label="Onboarding" url={onboardUrl} src={onboardQr} />
          </div>
        </div>
      )}
    </div>
  )
}

function QrCard({ label, url, src }: { label: string; url: string; src: string }) {
  return (
    <div className="flex flex-col items-center gap-2 text-center">
      <div className="rounded bg-white p-2">
        {src ? (
          <img src={src} alt={`QR ${label}`} className="h-28 w-28 sm:h-36 sm:w-36" />
        ) : (
          <div className="flex h-28 w-28 items-center justify-center text-xs text-black/40 sm:h-36 sm:w-36">
            …
          </div>
        )}
      </div>
      <p className="text-xs font-medium">{label}</p>
      <a
        href={url}
        className="max-w-full truncate text-[10px] text-[var(--muted)] underline"
        target="_blank"
        rel="noreferrer"
      >
        {url}
      </a>
    </div>
  )
}
