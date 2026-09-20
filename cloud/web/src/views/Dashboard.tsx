import { useState, type ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { timelineLine, zoneContext } from '../lib/copy'
import { useProjection } from '../hooks/useProjection'
import { Hero } from '../components/Hero'
import { PhoneFrame } from '../components/PhoneFrame'
import { AlertBanner } from './AlertBanner'
import { CheckinComposer } from './CheckinComposer'
import { DevMenu } from './DevMenu'
import { DogCamera } from './DogCamera'
import { EmergencyContacts } from './EmergencyContacts'
import { LiveTrack } from './LiveTrack'
import { MapView } from './Map'
import { MorningReport } from './MorningReport'
import { RoutineTab } from './Routine'
import { SpeakerPhone } from './SpeakerPhone'
import { StatePanel } from './StatePanel'
import { TabIsland, type TabId } from './TabIsland'
import { Timeline } from './Timeline'

function PageHeader({
  eyebrow,
  title,
  blurb,
  mood,
}: {
  eyebrow: string
  title: string
  blurb?: string
  mood?: 'happy' | 'sleepy' | 'alert'
}) {
  return (
    <Hero mood={mood} avatar={84}>
      <p className="eyebrow mb-1.5 !text-[var(--color-tint)]">{eyebrow}</p>
      <h1 className="text-[30px] leading-[1.08] !text-white">{title}</h1>
      {blurb && <p className="mt-2 text-[14px] font-semibold leading-[1.5] text-[#a8cdc8]">{blurb}</p>}
    </Hero>
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

  const nightWatchEnabled = (p.config.night_watch_enabled as boolean | undefined) ?? false
  const outside = nightWatchEnabled && zoneContext(p.person_track, p.zones)?.cls === 'outside'
  const patient = p.config.patient as { preferred_name?: string; name?: string } | undefined
  const name = patient?.preferred_name || patient?.name

  const latest = [...p.timeline]
    .reverse()
    .map((msg) => ({ msg, text: timelineLine(msg) }))
    .find((r) => r.text)

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

  const topBar = (
    <div className="flex items-center justify-between">
      <span className="pill !gap-2.5 !py-1.5">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor" aria-hidden>
          <path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z" />
        </svg>
        Night Watch is set for 9 PM - 7 AM
      </span>
    </div>
  )

  return (
    <>
      <PhoneFrame className="bg-[var(--color-bg)]">
        {tab === 'home' && <StatePanel top={topBar} />}
        {tab === 'routine' && (
          <PageHeader
            eyebrow="Daily rhythm"
            title="Routine"
            blurb={`A steady day helps with memory. ${name ? `${name}’s` : 'Their'} plan, at a glance.`}
          />
        )}
        {tab === 'checkin' && (
          <PageHeader
            eyebrow="Stay close"
            title={name ? `Check in on ${name}` : 'Check in'}
            blurb={`Send a message and Lantern will say it out loud in the voice of someone ${name || 'they'} love${name ? 's' : ''}.`}
          />
        )}
        {tab === 'activity' && (
          <PageHeader
            eyebrow="A look back"
            title="Activity"
            blurb={name ? `How ${name}’s nights have been, and anything Lantern noticed.` : 'How the nights have been.'}
          />
        )}
        {tab === 'settings' && <PageHeader eyebrow="Make it yours" title="Settings" mood="sleepy" />}

        <main className="px-4 pb-32 pt-5">
          {tab === 'home' && (
            <Screen>
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
                    <span className="block text-[14px] font-bold text-[var(--color-ink)]">{latest.text}</span>
                  </span>
                  <span aria-hidden className="text-[20px] font-bold text-[var(--color-ink)]">→</span>
                </button>
              )}

            </Screen>
          )}

          {tab === 'routine' && <RoutineTab name={name} />}

          {tab === 'checkin' && (
            <Screen>
              <CheckinComposer onOpenSettings={() => go('settings')} />
            </Screen>
          )}

          {tab === 'activity' && (
            <Screen>
              <MorningReport />
              <Timeline />
            </Screen>
          )}

          {tab === 'settings' && (
            <Screen>
              <div className="card flex flex-col divide-y-2 divide-dashed divide-[var(--color-line)] !p-0">
                <div className="flex items-center justify-between gap-4 p-5">
                  <div>
                    <p className="text-[16px] font-semibold text-[var(--color-ink)]">Night Watch</p>
                    <p className="text-[13px]">
                      Set for 9 PM - 7 AM. Lantern watches the zones you set and lets you know if they need you.
                    </p>
                  </div>
                </div>
                <SpeakerPhone />
                <Link to="/onboarding" className="flex items-center justify-between gap-4 p-5">
                  <div>
                    <p className="text-[16px] font-semibold text-[var(--color-ink)]">Edit home</p>
                    <p className="text-[13px]">Update rooms, zones and the daily routine.</p>
                  </div>
                  <span aria-hidden className="text-[20px] font-bold text-[var(--color-ink)]">→</span>
                </Link>
                <Link to="/" className="flex items-center justify-between gap-4 p-5">
                  <div>
                    <p className="text-[16px] font-semibold text-[var(--color-ink)]">Welcome screen</p>
                    <p className="text-[13px]">Back to the start.</p>
                  </div>
                  <span aria-hidden className="text-[20px] font-bold text-[var(--color-ink)]">→</span>
                </Link>
              </div>
            </Screen>
          )}
        </main>
      </PhoneFrame>

      <DevMenu />
      <TabIsland active={tab} onChange={go} badge={p.checkin_queue.length > 0 ? 'checkin' : null} />
      <AlertBanner
        onOpenCamera={() => setCameraOpen(true)}
        cameraOpen={cameraOpen}
        onTrack={openTracking}
        onCallHelp={() => setHelpOpen(true)}
      />
      {helpOpen && <EmergencyContacts onClose={() => setHelpOpen(false)} />}
    </>
  )
}
