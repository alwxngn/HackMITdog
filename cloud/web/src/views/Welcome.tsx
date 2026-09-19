import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import QRCode from 'qrcode'
import { KineticTextReveal } from '../components/KineticTextReveal'
import { publicOrigin, publicUrl } from '../lib/origin'
import { CheckinButton } from './CheckinButton'

export function Welcome() {
  const [stage, setStage] = useState<'mark' | 'invite' | 'phone'>('mark')
  const [qr, setQr] = useState('')
  const origin = publicOrigin()
  const onboardUrl = publicUrl('/onboarding')
  const needsTunnel = origin.includes('127.0.0.1') || origin.includes('localhost')

  useEffect(() => {
    let cancelled = false
    QRCode.toDataURL(onboardUrl, {
      margin: 1,
      width: 220,
      color: { dark: '#0f3e17', light: '#fffefc' },
    }).then((src) => {
      if (!cancelled) setQr(src)
    })
    return () => {
      cancelled = true
    }
  }, [onboardUrl])

  return (
    <div className="flex min-h-full items-center justify-center px-6 py-16">
      <CheckinButton />
      <div className="w-full max-w-[720px] rounded-[14px] bg-[var(--color-keylime-wash)] px-8 py-16 text-center md:px-16 md:py-24">
        {stage === 'mark' && (
          <h1 className="text-[56px] leading-[1.05] tracking-[-0.03em] md:text-[74px]">
            <KineticTextReveal
              text="Lantern"
              splitBy="characters"
              stagger={0.06}
              onRevealComplete={() => setStage('invite')}
            />
          </h1>
        )}

        {stage === 'invite' && (
          <div className="space-y-8">
            <p className="eyebrow">Night Watch</p>
            <h1 className="text-[40px] leading-[1.2] tracking-[-0.02em] md:text-[56px]">
              <KineticTextReveal text="Begin onboarding" splitBy="words" stagger={0.09} />
            </h1>
            <p className="mx-auto max-w-md text-[14px] text-[var(--color-charcoal)]">
              Set up the home map on a phone, then watch from this screen.
            </p>
            <button type="button" className="btn-primary" onClick={() => setStage('phone')}>
              Continue
            </button>
          </div>
        )}

        {stage === 'phone' && (
          <div className="space-y-8">
            <p className="eyebrow">Step one</p>
            <h1 className="text-[40px] leading-[1.2] tracking-[-0.02em] md:text-[56px]">
              <KineticTextReveal text="Do this on your phone" splitBy="words" stagger={0.08} />
            </h1>
            <p className="mx-auto max-w-md text-[14px] text-[var(--color-charcoal)]">
              Scan the code to paint zones and set schedule. When you finish, this laptop opens Night
              Watch.
            </p>
            <div className="mx-auto inline-block rounded-[14px] bg-[var(--color-cream-paper)] p-4">
              {qr ? (
                <img src={qr} alt="Onboarding QR" className="h-44 w-44" />
              ) : (
                <div className="flex h-44 w-44 items-center justify-center text-[14px]">…</div>
              )}
            </div>
            {needsTunnel && (
              <p className="text-[12px] text-[var(--color-charcoal)]">
                Localhost QRs will not open on a phone. Set VITE_PUBLIC_ORIGIN to your tunnel URL.
              </p>
            )}
            <div className="flex flex-wrap items-center justify-center gap-3">
              <Link className="btn-primary" to="/onboarding">
                Set up here
              </Link>
              <Link className="btn-ghost" to="/watch">
                Desktop dashboard
              </Link>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
