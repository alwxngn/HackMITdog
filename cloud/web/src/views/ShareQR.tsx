import { useEffect, useState } from 'react'
import QRCode from 'qrcode'
import { publicOrigin, publicUrl } from '../lib/origin'

async function toDataUrl(text: string): Promise<string> {
  return QRCode.toDataURL(text, {
    margin: 1,
    width: 160,
    color: { dark: '#16165c', light: '#ffffff' },
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
    <div className="card !py-4">
      <button
        type="button"
        className="flex w-full items-center justify-between text-left"
        onClick={() => setOpen((v) => !v)}
      >
        <span className="text-[17px] font-semibold tracking-[-0.03em] text-[var(--color-clinical-cyan)]">
          Share on phone
        </span>
        <span className="text-[12px] text-[var(--color-iris-pulse)]">{open ? 'hide' : 'show'}</span>
      </button>
      {open && (
        <div className="mt-4 space-y-3">
          <p className="text-[12px] tracking-[0.02em] text-[var(--color-muted-ink)]">
            Scan to open Night Watch or caregiver onboarding. Set{' '}
            <code className="text-[var(--color-ink)]">VITE_PUBLIC_ORIGIN</code> to your tunnel URL
            when developing on localhost.
          </p>
          {needsTunnelHint && (
            <p className="rounded-[16px] border border-dashed border-[var(--color-clinical-cyan)] px-3 py-2 text-[12px] text-[var(--color-iris-pulse)]">
              These QRs point at localhost — phones cannot open that. Start a tunnel (see
              cloud/README) and set VITE_PUBLIC_ORIGIN.
            </p>
          )}
          <div className="grid grid-cols-2 gap-4">
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
      <div className="rounded-[16px] bg-[var(--color-cloud-white)] p-2">
        {src ? (
          <img src={src} alt={`QR ${label}`} className="h-28 w-28 sm:h-36 sm:w-36" />
        ) : (
          <div className="flex h-28 w-28 items-center justify-center text-[12px] text-[var(--color-fog)] sm:h-36 sm:w-36">
            …
          </div>
        )}
      </div>
      <p className="text-[14px] font-semibold text-[var(--color-ink)]">{label}</p>
      <a
        href={url}
        className="max-w-full truncate text-[10px] text-[var(--color-clinical-cyan)] underline"
        target="_blank"
        rel="noreferrer"
      >
        {url}
      </a>
    </div>
  )
}
