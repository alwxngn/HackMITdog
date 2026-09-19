import { Link } from 'react-router-dom'
import { AlertBanner } from './AlertBanner'
import { CheckinComposer } from './CheckinComposer'
import { MapView } from './Map'
import { MorningReport } from './MorningReport'
import { StatePanel } from './StatePanel'
import { Timeline } from './Timeline'

async function resetDemo() {
  await fetch('/api/reset', { method: 'POST' })
}

export function Dashboard() {
  return (
    <div className="min-h-full p-4 md:p-6">
      <header className="mb-4 flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="text-xs uppercase tracking-[0.2em] text-[var(--muted)]">Lantern</p>
          <h1 className="text-3xl md:text-4xl">Night Watch</h1>
        </div>
        <nav className="flex gap-3 text-sm">
          <Link className="text-[var(--accent)] underline" to="/onboarding">
            Onboarding
          </Link>
          <button className="text-[var(--muted)] underline" onClick={resetDemo}>
            Reset
          </button>
        </nav>
      </header>

      <div className="grid gap-4 lg:grid-cols-[1.2fr_1fr]">
        <div className="space-y-4">
          <StatePanel />
          <MapView />
        </div>
        <div className="space-y-4">
          <Timeline />
          <MorningReport />
          <CheckinComposer />
        </div>
      </div>

      <AlertBanner />
    </div>
  )
}
