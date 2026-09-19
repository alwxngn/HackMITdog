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
    <div className="min-h-full pb-8">
      <header className="sticky top-0 z-40 border-b border-white/10 bg-[var(--bg)]/95 px-4 py-3 backdrop-blur md:px-6">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <p className="text-xs uppercase tracking-[0.2em] text-[var(--muted)]">Lantern</p>
            <h1 className="text-2xl sm:text-3xl md:text-4xl">Night Watch</h1>
          </div>
          <nav className="flex flex-wrap gap-3 text-sm">
            <Link className="min-h-11 rounded bg-white/10 px-3 py-2 text-[var(--accent)]" to="/onboarding">
              Onboarding
            </Link>
            <button
              type="button"
              className="min-h-11 rounded bg-white/5 px-3 py-2 text-[var(--muted)]"
              onClick={resetDemo}
            >
              Reset
            </button>
          </nav>
        </div>
      </header>

      <div className="space-y-4 p-4 md:p-6">
        <ShareQR />

        <div className="grid gap-4 lg:grid-cols-[1.2fr_1fr]">
          <div className="space-y-4">
            <StatePanel />
            <MapView />
          </div>
          <div className="space-y-4">
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
