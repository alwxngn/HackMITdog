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
    <div className="min-h-full pb-10">
      <header className="sticky top-0 z-40 border-b border-[var(--color-hairline)] bg-[var(--color-cloud-white)]/95 px-4 py-4 backdrop-blur md:px-8">
        <div className="mx-auto flex max-w-[1200px] flex-wrap items-center justify-between gap-4">
          <div>
            <p className="text-[12px] font-medium tracking-[0.02em] text-[var(--color-iris-pulse)]">
              Lantern
            </p>
            <h1 className="text-[28px] tracking-[-0.04em] text-[var(--color-ink)] sm:text-[36px] md:text-[46px]">
              Night <span className="word-highlight">Watch</span>
            </h1>
          </div>
          <nav className="flex flex-wrap gap-2">
            <Link className="btn-primary !min-h-11 !px-5 !py-2 !text-[14px]" to="/onboarding">
              Onboarding
            </Link>
            <button type="button" className="btn-ghost !min-h-11 !text-[14px]" onClick={resetDemo}>
              Reset
            </button>
          </nav>
        </div>
      </header>

      <div className="mx-auto max-w-[1200px] space-y-4 p-4 md:space-y-6 md:p-8">
        <ShareQR />

        <div className="grid gap-4 lg:grid-cols-[1.2fr_1fr] lg:gap-6">
          <div className="space-y-4 md:space-y-6">
            <StatePanel />
            <MapView />
          </div>
          <div className="space-y-4 md:space-y-6">
            <div className="max-h-[40vh] overflow-hidden lg:max-h-none">
              <Timeline />
            </div>
            <MorningReport />
            <CheckinComposer />
          </div>
        </div>
      </div>

      <AlertBanner />
    </div>
  )
}
