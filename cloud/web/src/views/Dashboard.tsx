import { useState, type ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { timelineLine, zoneContext } from '../lib/copy'
import { useProjection } from '../hooks/useProjection'
import { AlertBanner } from './AlertBanner'
import { CheckinComposer } from './CheckinComposer'
import { DemoWalk } from './DemoWalk'
import { DogCamera } from './DogCamera'
import { EmergencyContacts } from './EmergencyContacts'
import { LiveTrack } from './LiveTrack'
import { MapView } from './Map'
import { MorningReport } from './MorningReport'
import { StatePanel } from './StatePanel'
import { TabIsland, type TabId } from './TabIsland'
import { Timeline } from './Timeline'

function PageHeader({ eyebrow, title }: { eyebrow: string; title: string }) {
  return (
    <header className="pb-1 pt-2">
      <p className="eyebrow mb-1">{eyebrow}</p>
      <h1 className="text-[30px] leading-[1.1]">{title}</h1>
    </header>
  )
}

function Screen({ children }: { children: ReactNode }) {
  return <div className="flex flex-col gap-4">{children}</div>
}

export function Dashboard() {
  const [tab, setTab] = useState<TabId>('home')
  const [cameraOpen, setCameraOpen] = useState(false)
  const [trackOpen, setTrackOpen] = useState(false)
  const [helpOpen, setHelpOpen] = useState(false)
  const p = useProjection()
  const outside = zoneContext(p.person_track, p.zones)?.cls === 'outside'
  const nightWatchEnabled = (p.config.night_watch_enabled as boolean | undefined) ?? true
  const patient = p.config.patient as { preferred_name?: string; name?: string } | undefined
  const name = patient?.preferred_name || patient?.name

  const latest = [...p.timeline]
    .reverse()
    .map((msg) => ({ msg, text: timelineLine(msg) }))
    .find((r) => r.text)

  async function setNightWatch(enabled: boolean) {
    await fetch('/api/config', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ night_watch_enabled: enabled }),
    })
  }

  // Collapse the map once they are back inside so the next run starts tidy.
  const [wasOutside, setWasOutside] = useState(false)
  if (outside !== wasOutside) {
    setWasOutside(outside)
    if (!outside) setTrackOpen(false)
  }

  function openTracking() {
    setTab('home')
    setTrackOpen(true)
    setTimeout(() => document.getElementById('live-track')?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 50)
  }

  function go(next: TabId) {
    setTab(next)
    window.scrollTo({ top: 0 })
  }

  return (
    <div className="min-h-full">
      <main className="mx-auto w-full max-w-[460px] px-4 pb-32 pt-5">
        {tab === 'home' && (
          <Screen>
            <div className="flex items-center justify-between pb-1">
              <div>
                <Link
                  to="/"
                  className="inline-flex items-center gap-2 font-[family-name:var(--font-display)] text-[22px] font-semibold leading-none tracking-[-0.03em] text-[var(--color-ink)]"
                >
                  <span className="grid h-7 w-7 place-items-center rounded-[9px] bg-[var(--color-ink)]">
                    <span className="h-2.5 w-2.5 rounded-full bg-[var(--color-accent)] shadow-[0_0_10px_2px_rgba(37,99,255,0.7)]" />
                  </span>
                  Lantern
                </Link>
                <p className="eyebrow mt-2">{name ? `Watching over ${name}` : 'Night Watch'}</p>
              </div>
              <span className="pill !gap-2 !py-2 shadow-[var(--shadow-card)]">
                <span
                  className={`h-2 w-2 rounded-full ${nightWatchEnabled ? 'bg-[var(--color-safe)]' : 'bg-[var(--color-tint)]'}`}
                />
                {nightWatchEnabled ? 'Night Watch on' : 'Night Watch off'}
              </span>
            </div>

            <StatePanel />
            {outside && (
              <LiveTrack open={trackOpen} onToggle={() => setTrackOpen((v) => !v)} onCallHelp={() => setHelpOpen(true)} />
            )}
            <MapView />
            <DogCamera
              open={cameraOpen}
              onOpen={() => setCameraOpen(true)}
              onClose={() => setCameraOpen(false)}
            />

            {latest && (
              <button
                type="button"
                onClick={() => go('activity')}
                className="card-cream flex cursor-pointer items-center justify-between gap-4 !p-5 text-left"
              >
                <span>
                  <span className="eyebrow mb-1 block">Latest</span>
                  <span className="block text-[14px]">{latest.text}</span>
                </span>
                <span aria-hidden className="text-[var(--color-ink)]">→</span>
              </button>
            )}

            <DemoWalk />
          </Screen>
        )}

        {tab === 'checkin' && (
          <Screen>
            <PageHeader eyebrow="Talk to Lantern" title="Check in" />
            <CheckinComposer />
          </Screen>
        )}

        {tab === 'activity' && (
          <Screen>
            <PageHeader eyebrow="Tonight & last night" title="Activity" />
            <MorningReport />
            <Timeline />
          </Screen>
        )}

        {tab === 'settings' && (
          <Screen>
            <PageHeader eyebrow="Lantern" title="Settings" />
            <div className="card flex flex-col divide-y divide-[var(--color-line)] !p-0">
              <div className="flex items-center justify-between gap-4 p-5">
                <div>
                  <p className="text-[16px] text-[var(--color-ink)]">Night Watch</p>
                  <p className="text-[13px]">Lantern keeps an eye out while it’s dark.</p>
                </div>
                <button
                  type="button"
                  role="switch"
                  aria-checked={nightWatchEnabled}
                  aria-label="Night Watch"
                  onClick={() => setNightWatch(!nightWatchEnabled)}
                  className={`relative h-7 w-12 shrink-0 cursor-pointer rounded-full transition-colors ${
                    nightWatchEnabled ? 'bg-[var(--color-accent)]' : 'bg-[var(--color-tint)]'
                  }`}
                >
                  <span
                    className={`absolute top-1 h-5 w-5 rounded-full bg-[var(--color-surface)] shadow transition-all ${
                      nightWatchEnabled ? 'left-6' : 'left-1'
                    }`}
                  />
                </button>
              </div>
              <Link to="/onboarding" className="flex items-center justify-between gap-4 p-5">
                <div>
                  <p className="text-[16px] text-[var(--color-ink)]">Edit home</p>
                  <p className="text-[13px]">Rescan rooms, paint zones, update routines.</p>
                </div>
                <span aria-hidden className="text-[var(--color-ink)]">→</span>
              </Link>
              <Link to="/" className="flex items-center justify-between gap-4 p-5">
                <div>
                  <p className="text-[16px] text-[var(--color-ink)]">Welcome screen</p>
                  <p className="text-[13px]">Back to the start.</p>
                </div>
                <span aria-hidden className="text-[var(--color-ink)]">→</span>
              </Link>
            </div>
          </Screen>
        )}
      </main>

      <TabIsland active={tab} onChange={go} badge={p.checkin_queue.length > 0 ? 'checkin' : null} />
      <AlertBanner
        onOpenCamera={() => setCameraOpen(true)}
        cameraOpen={cameraOpen}
        onTrack={openTracking}
        onCallHelp={() => setHelpOpen(true)}
      />
      {helpOpen && <EmergencyContacts onClose={() => setHelpOpen(false)} />}
    </div>
  )
}
