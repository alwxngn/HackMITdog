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
      <nav className="bg-transparent">
        <div className="mx-auto flex max-w-[1200px] items-center justify-between px-6 py-6">
          <Link to="/" className="font-[family-name:var(--font-faire-octave)] text-[28px] font-light text-[var(--color-forest-ink)]">
            Lantern
          </Link>
          <div className="flex gap-2">
            <Link className="btn-ghost !min-h-10 !py-2" to="/onboarding">
              Onboarding
            </Link>
            <button type="button" className="btn-primary !min-h-10 !py-2" onClick={resetDemo}>
              Reset
            </button>
          </div>
        </div>
      </nav>

      <main className="mx-auto max-w-[1200px] px-6">
        <p className="eyebrow mb-3">Night Watch</p>
        <h1 className="mb-10 text-[40px] md:text-[56px]">Tonight, at a glance</h1>
        <div className="grid grid-cols-1 gap-[21px] md:grid-cols-12">
          <div className="md:col-span-8">
            <StatePanel />
          </div>
          <div className="md:col-span-4">
            <ShareQR compact />
          </div>
          <div className="md:col-span-7">
            <MapView />
          </div>
          <div className="min-h-[280px] md:col-span-5">
            <Timeline />
          </div>
          <div className="md:col-span-6">
            <MorningReport />
          </div>
          <div className="md:col-span-6">
            <CheckinComposer />
          </div>
        </div>
      </main>

      <AlertBanner />
    </div>
  )
}
