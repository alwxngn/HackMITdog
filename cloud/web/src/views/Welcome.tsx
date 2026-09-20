import { useState } from 'react'
import { Link } from 'react-router-dom'
import { KineticTextReveal } from '../components/KineticTextReveal'

export function Welcome() {
  const [stage, setStage] = useState<'mark' | 'invite'>('mark')

  return (
    <div className="flex min-h-full items-center justify-center px-6 py-16">
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
              Set up the home map, then watch from this screen.
            </p>
            <Link className="btn-primary" to="/onboarding">
              Continue
            </Link>
          </div>
        )}
      </div>
    </div>
  )
}
