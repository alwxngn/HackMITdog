import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { DEMO_MAP, type MapReadyPayload } from '../../lib/demoFloorplan'
import { useProjection } from '../../hooks/useProjection'
import type { Zone } from '../../lib/types'
import { ZonePainter } from './ZonePainter'

type Step = 1 | 2 | 3 | 4

export function Onboarding() {
  const projection = useProjection()
  const [step, setStep] = useState<Step>(1)
  const [scanning, setScanning] = useState(false)
  const [scanError, setScanError] = useState('')
  const [map, setMap] = useState<MapReadyPayload | null>(
    (projection.map_ready as MapReadyPayload | null) || null,
  )
  const [zones, setZones] = useState<Zone[]>([])
  const [home, setHome] = useState({ x: 0.4, y: 0.4 })
  const [patient, setPatient] = useState({
    name: 'Arthur',
    preferred_name: 'Art',
    calming_topics: 'fishing at Moosehead, his dog Bella',
    avoid_topics: "his wife's death",
  })
  const [schedule, setSchedule] = useState({
    wake_time: '07:30',
    meals: '08:00,12:30,18:00',
    walk_start: '15:00',
    walk_end: '16:30',
    notes: 'likes the porch after lunch',
  })
  const [contacts, setContacts] = useState({ primary: 'jenny', secondary: 'mark' })
  const [saved, setSaved] = useState('')

  useEffect(() => {
    if (projection.map_ready) {
      setMap(projection.map_ready as MapReadyPayload)
      setScanning(false)
    }
  }, [projection.map_ready])

  async function startScan(forceDemo = false) {
    setScanError('')
    setScanning(true)
    try {
      const r = await fetch('/api/map-scan', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(forceDemo ? { mode: 'demo' } : {}),
      })
      const data = await r.json()
      if (data.mode === 'demo' && data.map_ready) {
        // brief animation then show
        await new Promise((res) => setTimeout(res, 1800))
        setMap(data.map_ready as MapReadyPayload)
        setScanning(false)
        setStep(3)
        return
      }
      // live: poll until map_ready on projection / status
      const deadline = Date.now() + 90_000
      while (Date.now() < deadline) {
        const st = await fetch('/api/map-scan/status').then((x) => x.json())
        if (st.map_ready) {
          setMap(st.map_ready as MapReadyPayload)
          setScanning(false)
          setStep(3)
          return
        }
        await new Promise((res) => setTimeout(res, 800))
      }
      setScanError('Timed out waiting for the robot map. Use demo floorplan or retry.')
      setScanning(false)
    } catch (e) {
      setScanError(String(e))
      setScanning(false)
      setMap(DEMO_MAP)
    }
  }

  async function finish() {
    if (!map) return
    const body = {
      zones: zones.length
        ? zones
        : [
            {
              id: 'whole_safe',
              class: 'safe',
              label: 'Safe',
              kind: 'door',
              polygon: map.outline,
            },
          ],
      patient: {
        name: patient.name,
        preferred_name: patient.preferred_name,
        calming_topics: patient.calming_topics.split(',').map((s) => s.trim()).filter(Boolean),
        avoid_topics: patient.avoid_topics.split(',').map((s) => s.trim()).filter(Boolean),
        music_url: '/media/arthur_playlist.mp3',
        schedule: {
          wake_time: schedule.wake_time,
          meals: schedule.meals.split(',').map((s) => s.trim()).filter(Boolean),
          walk_window: [schedule.walk_start, schedule.walk_end],
          notes: schedule.notes,
        },
        home: { ...home, lat: null, lon: null },
        route_id: null,
      },
      escalation: [
        { level: 2, contact: contacts.primary, channel: 'sms', after_s: 0 },
        { level: 3, contact: contacts.primary, channel: 'voice_call', after_s: 60 },
        { level: 4, contact: contacts.secondary, channel: 'voice_call', after_s: 120 },
        {
          level: 5,
          contact: contacts.primary,
          channel: 'voice_call',
          after_s: 0,
          trigger: 'dont_go_breach',
        },
      ],
      map_id: map.map_id,
    }
    const r = await fetch('/api/config', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
    setSaved(r.ok ? 'Saved — Night Watch will use this map and zones.' : 'Save failed')
  }

  const steps: { n: Step; label: string }[] = [
    { n: 1, label: 'Patient' },
    { n: 2, label: 'Scan home' },
    { n: 3, label: 'Paint zones' },
    { n: 4, label: 'Schedule' },
  ]

  return (
    <div className="mx-auto max-w-[1200px] space-y-6 p-4 pb-24 md:p-8">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-[12px] tracking-[0.02em] text-[var(--color-iris-pulse)]">Lantern</p>
          <h1 className="text-[32px] tracking-[-0.04em] sm:text-[46px]">
            On<span className="word-highlight">boarding</span>
          </h1>
        </div>
        <Link className="btn-ghost !min-h-11 !text-[14px]" to="/">
          Night Watch
        </Link>
      </div>

      <div className="flex flex-wrap gap-2">
        {steps.map((s) => (
          <button
            key={s.n}
            type="button"
            className={`pill min-h-10 px-4 ${step === s.n ? 'bg-[var(--color-iris-pulse)] text-white' : 'border border-[var(--color-iris-border)] text-[var(--color-iris-pulse)]'}`}
            onClick={() => {
              if (s.n === 3 && !map) return
              setStep(s.n)
            }}
          >
            {s.n}. {s.label}
          </button>
        ))}
      </div>

      {step === 1 && (
        <div className="card max-w-lg space-y-3">
          <h2 className="text-[18px]">Who are we caring for?</h2>
          <label className="block text-[14px] text-[var(--color-muted-ink)]">
            Name
            <input
              className="input-field mt-1"
              value={patient.name}
              onChange={(e) => setPatient({ ...patient, name: e.target.value })}
            />
          </label>
          <label className="block text-[14px] text-[var(--color-muted-ink)]">
            Preferred name
            <input
              className="input-field mt-1"
              value={patient.preferred_name}
              onChange={(e) => setPatient({ ...patient, preferred_name: e.target.value })}
            />
          </label>
          <label className="block text-[14px] text-[var(--color-muted-ink)]">
            Calming topics (comma-separated)
            <input
              className="input-field mt-1"
              value={patient.calming_topics}
              onChange={(e) => setPatient({ ...patient, calming_topics: e.target.value })}
            />
          </label>
          <label className="block text-[14px] text-[var(--color-muted-ink)]">
            Avoid topics
            <input
              className="input-field mt-1"
              value={patient.avoid_topics}
              onChange={(e) => setPatient({ ...patient, avoid_topics: e.target.value })}
            />
          </label>
          <button type="button" className="btn-primary" onClick={() => setStep(2)}>
            Next — Scan home
          </button>
        </div>
      )}

      {step === 2 && (
        <div className="card max-w-xl space-y-4">
          <h2 className="text-[18px]">Scan home with Lantern</h2>
          <p className="text-[14px] text-[var(--color-muted-ink)]">
            In testing, this asks the Go2 to map the space (E2 / DimOS). At the table demo it loads
            a schematic floorplan — same paint step either way.
          </p>
          {scanning ? (
            <div className="space-y-2">
              <div className="h-2 overflow-hidden rounded-full bg-[var(--color-iris-border)]">
                <div className="h-full w-2/3 animate-pulse rounded-full bg-[var(--color-clinical-cyan)]" />
              </div>
              <p className="text-[14px] text-[var(--color-clinical-cyan)]">
                Mapping… walk the robot through the space (or waiting on demo map).
              </p>
            </div>
          ) : (
            <div className="flex flex-wrap gap-2">
              <button type="button" className="btn-primary" onClick={() => startScan(false)}>
                Scan home
              </button>
              <button type="button" className="btn-ghost" onClick={() => startScan(true)}>
                Use demo floorplan
              </button>
              {map && (
                <button type="button" className="btn-ghost" onClick={() => setStep(3)}>
                  Continue with current map
                </button>
              )}
            </div>
          )}
          {scanError && (
            <p className="text-[14px] text-[var(--color-iris-pulse)]">
              {scanError}{' '}
              <button type="button" className="underline text-[var(--color-clinical-cyan)]" onClick={() => startScan(true)}>
                Load demo map
              </button>
            </p>
          )}
        </div>
      )}

      {step === 3 && map && (
        <div className="card space-y-4">
          <h2 className="text-[18px]">Paint zones</h2>
          <p className="text-[14px] text-[var(--color-muted-ink)]">
            Everything starts <span className="text-[var(--color-mint-vital)]">Safe</span>. Paint{' '}
            <span className="text-[var(--color-clinical-cyan)]">Watch</span> and{' '}
            <span className="text-[var(--color-lilac-mist)]">Don&apos;t go</span>, then place home.
          </p>
          <ZonePainter map={map} home={home} onHomeChange={setHome} onZonesChange={setZones} />
          <button type="button" className="btn-primary" onClick={() => setStep(4)}>
            Next — Schedule
          </button>
        </div>
      )}

      {step === 4 && (
        <div className="card max-w-md space-y-3">
          <h2 className="text-[18px]">Schedule & contacts</h2>
          <label className="block text-[14px] text-[var(--color-muted-ink)]">
            Wake time
            <input
              className="input-field mt-1"
              value={schedule.wake_time}
              onChange={(e) => setSchedule({ ...schedule, wake_time: e.target.value })}
            />
          </label>
          <label className="block text-[14px] text-[var(--color-muted-ink)]">
            Meals
            <input
              className="input-field mt-1"
              value={schedule.meals}
              onChange={(e) => setSchedule({ ...schedule, meals: e.target.value })}
            />
          </label>
          <div className="flex gap-2">
            <label className="block flex-1 text-[14px] text-[var(--color-muted-ink)]">
              Walk start
              <input
                className="input-field mt-1"
                value={schedule.walk_start}
                onChange={(e) => setSchedule({ ...schedule, walk_start: e.target.value })}
              />
            </label>
            <label className="block flex-1 text-[14px] text-[var(--color-muted-ink)]">
              Walk end
              <input
                className="input-field mt-1"
                value={schedule.walk_end}
                onChange={(e) => setSchedule({ ...schedule, walk_end: e.target.value })}
              />
            </label>
          </div>
          <label className="block text-[14px] text-[var(--color-muted-ink)]">
            Notes
            <textarea
              className="input-field mt-1"
              rows={2}
              value={schedule.notes}
              onChange={(e) => setSchedule({ ...schedule, notes: e.target.value })}
            />
          </label>
          <label className="block text-[14px] text-[var(--color-muted-ink)]">
            Primary contact
            <input
              className="input-field mt-1"
              value={contacts.primary}
              onChange={(e) => setContacts({ ...contacts, primary: e.target.value })}
            />
          </label>
          <label className="block text-[14px] text-[var(--color-muted-ink)]">
            Secondary contact
            <input
              className="input-field mt-1"
              value={contacts.secondary}
              onChange={(e) => setContacts({ ...contacts, secondary: e.target.value })}
            />
          </label>
          <button type="button" className="btn-primary w-full sm:w-auto" onClick={finish}>
            Finish — publish config
          </button>
          {saved && <p className="text-[14px] text-[var(--color-iris-pulse)]">{saved}</p>}
        </div>
      )}
    </div>
  )
}
