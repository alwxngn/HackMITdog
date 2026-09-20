import { useState } from 'react'
import { Link } from 'react-router-dom'
import { DogMascot } from '../components/DogMascot'
import { KineticTextReveal } from '../components/KineticTextReveal'
import { PawBackdrop } from '../components/PawBackdrop'
import { PhoneFrame } from '../components/PhoneFrame'

const CREAM = '#fbf3df'

export function Welcome() {
  const [ready, setReady] = useState(false)

  return (
    <PhoneFrame className="items-center justify-center bg-[var(--color-brand-mid)] px-8 py-16 text-center">
      <PawBackdrop />
      <div className="relative flex w-full flex-col items-center gap-5">
        <DogMascot color={CREAM} className="h-[150px] w-[188px]" />
        <h1
          className="text-[40px] font-bold uppercase leading-none tracking-[0.08em] md:text-[52px]"
          style={{ color: CREAM }}
        >
          <KineticTextReveal
            text="Lantern"
            splitBy="characters"
            stagger={0.06}
            onRevealComplete={() => setReady(true)}
          />
        </h1>

        <div
          className={`flex flex-col items-center gap-5 transition-all duration-700 ${
            ready ? 'translate-y-0 opacity-100' : 'translate-y-3 opacity-0'
          }`}
        >
          <p className="max-w-[340px] text-[15px] font-medium text-white/90">
            A gentle watch over the ones you love. Set up the home, build a daily routine, and let Lantern keep
            them company.
          </p>
          <Link
            className="btn-primary mt-1 !min-w-[220px] !bg-[#fbf3df] !text-[var(--color-ink)] hover:!bg-white"
            to="/onboarding"
          >
            Get started
          </Link>
          <Link className="text-[13px] font-semibold text-white underline underline-offset-4" to="/watch">
            I already set things up
          </Link>
        </div>
      </div>
    </PhoneFrame>
  )
}
