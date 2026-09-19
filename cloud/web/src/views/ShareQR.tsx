import { useEffect, useState } from 'react'
import QRCode from 'qrcode'
import { publicOrigin, publicUrl } from '../lib/origin'

async function toDataUrl(text: string): Promise<string> {
  return QRCode.toDataURL(text, {
    margin: 1,
    width: 160,
    color: { dark: '#0f3e17', light: '#fffefc' },
  })
}

export function ShareQR({ compact = false }: { compact?: boolean }) {
  const [watchQr, setWatchQr] = useState('')
  const [onboardQr, setOnboardQr] = useState('')
  const [open, setOpen] = useState(true)
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
    <div className={`card h-full ${compact ? '!py-4' : '!py-4'}`}>
      <button
        type="button"
        className="flex w-full items-center justify-between text-left"
        onClick={() => setOpen((v) => !v)}
      >
        <span className="text-[18px] text-[var(--color-forest-ink)]">
          Share on phone
        </span>
        <span className="text-[12px] text-[var(--color-charcoal)]">{open ? 'hide' : 'show'}</span>
      </button>
      {open && (
        <div className="mt-4 space-y-3">
          {!compact && (
            <p className="text-[13px] text-[var(--color-charcoal)]">
              Scan to open Night Watch or caregiver onboarding. Set{' '}
              <code className="text-[var(--color-forest-ink)]">VITE_PUBLIC_ORIGIN</code> to your tunnel
              URL when developing on localhost.
            </p>
          )}
          {needsTunnelHint && (
            <p className="rounded-[14px] bg-[var(--color-cream-paper)] px-3 py-2 text-[13px] text-[var(--color-charcoal)]">
              These QRs point at localhost — phones cannot open that. Start a tunnel (see
              cloud/README) and set VITE_PUBLIC_ORIGIN.
            </p>
          )}
          <div className="grid grid-cols-2 gap-3">
            <QrCard compact={compact} label="Night Watch" url={watchUrl} src={watchQr} />
            <QrCard compact={compact} label="Onboarding" url={onboardUrl} src={onboardQr} />
          </div>
        </div>
      )}
    </div>
  )
}

function QrCard({
  label,
  url,
  src,
  compact,
}: {
  label: string
  url: string
  src: string
  compact?: boolean
}) {
  const size = compact ? 'h-24 w-24' : 'h-28 w-28 sm:h-36 sm:w-36'
  return (
    <div className="flex flex-col items-center gap-2 text-center">
      <div className="rounded-[14px] bg-[var(--color-cream-paper)] p-2">
        {src ? (
          <img src={src} alt={`QR ${label}`} className={size} />
        ) : (
          <div className={`flex items-center justify-center text-[13px] text-[var(--color-charcoal)] ${size}`}>
            …
          </div>
        )}
      </div>
      <p className="text-[14px] text-[var(--color-forest-ink)]">{label}</p>
      {!compact && (
        <a
          href={url}
          className="max-w-full truncate text-[10px] text-[var(--color-forest-ink)] underline"
          target="_blank"
          rel="noreferrer"
        >
          {url}
        </a>
      )}
    </div>
  )
}
