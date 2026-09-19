import { Link } from 'react-router-dom'
import { AlertBanner } from './AlertBanner'
import { CheckinComposer } from './CheckinComposer'
import { MapView } from './Map'
import { MorningReport } from './MorningReport'
import { ShareQR } from './ShareQR'
import { StatePanel } from './StatePanel'
import { Timeline } from './Timeline'

async function resetDemo() {
  await fetch('/api/reset', { method: 'POST' })
}

export function Dashboard() {
  return (
    <div className="min-h-full pb-16">
      <nav>
        <div className="mx-auto flex max-w-[1400px] flex-wrap items-center justify-between gap-4 px-6 py-6">
          <div>
            <Link
              to="/"
              className="font-[family-name:var(--font-faire-octave)] text-[28px] font-light text-[var(--color-forest-ink)]"
            >
              Lantern
            </Link>
            <p className="eyebrow mt-1">Night Watch</p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <ShareQR />
            <Link className="btn-ghost !min-h-10 !py-2" to="/onboarding">
              Edit home
            </Link>
            <button type="button" className="btn-primary !min-h-10 !py-2" onClick={resetDemo}>
              Reset
            </button>
          </div>
        </div>
      </nav>

      <main className="mx-auto grid max-w-[1400px] grid-cols-1 gap-[21px] px-6 lg:grid-cols-12 lg:items-start">
        <div className="lg:sticky lg:top-6 lg:col-span-7">
          <MapView />
        </div>
        <div className="flex flex-col gap-[21px] lg:col-span-5">
          <StatePanel />
          <CheckinComposer />
          <Timeline />
          <MorningReport />
        </div>
      </main>

      <AlertBanner />
    </div>
  )
}
