import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { DEMO_MAP, type MapReadyPayload } from '../../lib/demoFloorplan'
import { DEMO_HOME_PIN } from '../../lib/demoHome'
import { useProjection } from '../../hooks/useProjection'
import type { Zone } from '../../lib/types'
import { ZonePainter } from './ZonePainter'

type Step = 1 | 2 | 3 | 4

export function Onboarding() {
  const navigate = useNavigate()
  const projection = useProjection()
  const [step, setStep] = useState<Step>(1)
  const [scanning, setScanning] = useState(false)
  const [scanError, setScanError] = useState('')
  const [scanMode, setScanMode] = useState<'demo' | 'live' | null>(null)
  const [scanElapsed, setScanElapsed] = useState(0)
  const [scanAbort] = useState({ aborted: false })
  const [map, setMap] = useState<MapReadyPayload | null>(
    (projection.map_ready as MapReadyPayload | null) || null,
  )
  const [zones, setZones] = useState<Zone[]>([])
  const [home, setHome] = useState<{ x: number; y: number }>(() => {
    const saved = (projection.config.patient as { home?: { x: number; y: number } } | undefined)?.home
    // server default is the (0, 0) corner, which means "not placed yet"
    return saved && (saved.x !== 0 || saved.y !== 0) ? { x: saved.x, y: saved.y } : DEMO_HOME_PIN
  })
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
  const [voiceRecording, setVoiceRecording] = useState(false)
  const [voiceBusy, setVoiceBusy] = useState(false)
  const [voiceStatus, setVoiceStatus] = useState('')
  const [showVoiceScript, setShowVoiceScript] = useState(false)

  async function recordVoice() {
    if (voiceBusy) return
    setVoiceBusy(true)
    setVoiceStatus('')
    let stream: MediaStream
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    } catch {
      setVoiceStatus('Microphone access was denied.')
      setVoiceBusy(false)
      return
    }
    const mimeType = ['audio/webm;codecs=opus', 'audio/ogg;codecs=opus', 'audio/mp4'].find((t) =>
      MediaRecorder.isTypeSupported(t),
    )
    if (!mimeType) {
      stream.getTracks().forEach((t) => t.stop())
      setVoiceStatus('Recording is not supported in this browser.')
      setVoiceBusy(false)
      return
    }
    const recorder = new MediaRecorder(stream, { mimeType })
    const chunks: BlobPart[] = []
    recorder.ondataavailable = (e) => {
      if (e.data.size) chunks.push(e.data)
    }
    recorder.onstop = async () => {
      stream.getTracks().forEach((t) => t.stop())
      setVoiceRecording(false)
      setVoiceStatus('Creating Lantern’s voice…')
      try {
        const contentType = mimeType.split(';')[0]
        const name = encodeURIComponent(patient.preferred_name || patient.name || 'Lantern')
        const r = await fetch(`/api/onboarding/voice-clone?name=${name}`, {
          method: 'POST',
          headers: { 'Content-Type': contentType },
          body: new Blob(chunks, { type: mimeType }),
        })
        const data = await r.json().catch(() => null)
        if (r.ok && typeof data?.voice_id === 'string' && data.voice_id) {
          setVoiceStatus('Voice created and saved.')
        } else if (typeof data?.detail === 'string') {
          setVoiceStatus(data.detail)
        } else if ([502, 503, 504].includes(r.status)) {
          setVoiceStatus(`The upload could not reach the voice service (HTTP ${r.status}). Check that the API, portal, and Cloudflare tunnel are running on the same computer, then retry.`)
        } else {
          setVoiceStatus(`Could not create the voice (HTTP ${r.status}). Please retry.`)
        }
      } catch {
        setVoiceStatus('The upload connection failed. Check your connection and retry.')
      } finally {
        setVoiceBusy(false)
      }
    }
    recorder.start()
    setVoiceRecording(true)
    setVoiceStatus('Recording… speak for about 10 seconds.')
    setTimeout(() => {
      if (recorder.state === 'recording') recorder.stop()
    }, 10000)
  }

  useEffect(() => {
    if (projection.map_ready) {
      setMap(projection.map_ready as MapReadyPayload)
      setScanning(false)
    }
  }, [projection.map_ready])

  async function startScan(forceDemo = false) {
    setScanError('')
    setScanning(true)
    setScanElapsed(0)
    scanAbort.aborted = false
    const started = Date.now()
    const tick = window.setInterval(
      () => setScanElapsed(Math.floor((Date.now() - started) / 1000)),
      500,
    )
    try {
      const r = await fetch('/api/map-scan', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(forceDemo ? { mode: 'demo' } : {}),
      })
      const data = await r.json()
      setScanMode(data.mode === 'live' ? 'live' : 'demo')
      if (data.mode === 'demo' && data.map_ready) {
        await new Promise((res) => setTimeout(res, 1800))
        if (scanAbort.aborted) return
        setMap(data.map_ready as MapReadyPayload)
        setScanning(false)
        setStep(3)
        return
      }
      // live: poll until E2 POSTs map_ready to /api/ingest
      const deadline = Date.now() + 120_000
      while (Date.now() < deadline) {
        if (scanAbort.aborted) return
        const st = await fetch('/api/map-scan/status').then((x) => x.json())
        if (st.map_ready) {
          setMap(st.map_ready as MapReadyPayload)
          setScanning(false)
          setStep(3)
          return
        }
        await new Promise((res) => setTimeout(res, 800))
      }
      setScanError(
        'Timed out waiting for robot map_ready (2 min). Keep MAP_SCAN_MODE=live, have E2 POST /api/ingest, or use demo floorplan.',
      )
      setScanning(false)
    } catch (e) {
      setScanError(String(e))
      setScanning(false)
      setMap(DEMO_MAP)
    } finally {
      window.clearInterval(tick)
    }
  }

  function cancelScan() {
    scanAbort.aborted = true
    setScanning(false)
    setScanMode(null)
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
    if (r.ok) navigate('/watch')
  }

  const steps: { n: Step; label: string }[] = [
    { n: 1, label: 'Patient' },
    { n: 2, label: 'Map home' },
    { n: 3, label: 'Paint zones' },
    { n: 4, label: 'Schedule' },
  ]

  return (
    <div className="mx-auto max-w-[1200px] space-y-6 p-4 pb-24 md:p-8">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="eyebrow">Lantern</p>
          <h1 className="mt-2 text-[40px] md:text-[56px]">Onboarding</h1>
        </div>
        <Link className="btn-ghost !min-h-11" to="/watch">
          Night Watch
        </Link>
      </div>

      <div className="flex flex-wrap gap-2">
        {steps.map((s) => (
          <button
            key={s.n}
            type="button"
            className={`pill min-h-10 px-4 ${step === s.n ? 'bg-[var(--color-ink)] text-[var(--color-surface)]' : ''}`}
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
          <label className="block text-[14px] text-[var(--color-ink-2)]">
            Name
            <input
              className="input-field mt-1"
              value={patient.name}
              onChange={(e) => setPatient({ ...patient, name: e.target.value })}
            />
          </label>
          <label className="block text-[14px] text-[var(--color-ink-2)]">
            Preferred name
            <input
              className="input-field mt-1"
              value={patient.preferred_name}
              onChange={(e) => setPatient({ ...patient, preferred_name: e.target.value })}
            />
          </label>
          <label className="block text-[14px] text-[var(--color-ink-2)]">
            Calming topics (comma-separated)
            <input
              className="input-field mt-1"
              value={patient.calming_topics}
              onChange={(e) => setPatient({ ...patient, calming_topics: e.target.value })}
            />
          </label>
          <label className="block text-[14px] text-[var(--color-ink-2)]">
            Avoid topics
            <input
              className="input-field mt-1"
              value={patient.avoid_topics}
              onChange={(e) => setPatient({ ...patient, avoid_topics: e.target.value })}
            />
          </label>
          <div className="space-y-2 pt-2">
            <p className="text-[14px] text-[var(--color-ink-2)]">Lantern&apos;s voice</p>
            <div className="flex flex-wrap items-center gap-3">
              <button type="button" className="btn-ghost" onClick={recordVoice} disabled={voiceBusy}>
                {voiceRecording ? 'Recording…' : voiceBusy ? 'Creating voice…' : 'Record 10s sample'}
              </button>
              <button
                type="button"
                className="min-h-11 text-[13px] text-[var(--color-ink-2)] underline underline-offset-4 hover:text-[var(--color-ink)]"
                onClick={() => setShowVoiceScript((shown) => !shown)}
                aria-expanded={showVoiceScript}
                aria-controls="voice-reading-script"
              >
                {showVoiceScript ? 'hide script' : 'get script'}
              </button>
            </div>
            {showVoiceScript && (
              <div id="voice-reading-script" className="rounded-xl bg-[var(--color-panel-2)] p-4 space-y-2">
                <p className="text-[15px] leading-relaxed text-[var(--color-ink)]">
                  Good morning! How are you feeling today? The fresh bread smells lovely, and sunshine fills the kitchen. Shall we sit by the window, share a favourite story, and watch the little birds fly past?
                </p>
                <p className="text-[12px] text-[var(--color-ink-2)]">
                  Read in your usual warm voice, at an easy pace. Keep the microphone steady and the room quiet.
                </p>
              </div>
            )}
            {voiceStatus && <p className="text-[13px] text-[var(--color-ink)]">{voiceStatus}</p>}
          </div>
          <button type="button" className="btn-primary" onClick={() => setStep(2)}>
            Next — Map home
          </button>
        </div>
      )}

      {step === 2 && (
        <div className="card max-w-xl space-y-4">
          <h2 className="text-[18px]">Map your home</h2>
          <p className="text-[14px] text-[var(--color-ink-2)]">
            Eventually Lantern will walk through the house and map it on its own. That isn&apos;t
            wired up yet, so for now this step is a placeholder: it loads the demo floor plan, and
            you can paint Night Watch zones on it in the next step.
          </p>
          {scanning ? (
            <div className="space-y-3">
              <div className="h-2 overflow-hidden rounded-full bg-[var(--color-panel-2)]">
                <div className="h-full w-2/3 animate-pulse rounded-full bg-[var(--color-ink)]" />
              </div>
              <p className="text-[14px] text-[var(--color-ink)]">
                {scanMode === 'live'
                  ? `Waiting for robot map… ${scanElapsed}s (E2 → POST /api/ingest map_ready)`
                  : 'Mapping… (placeholder) loading the demo floor plan.'}
              </p>
              <button type="button" className="btn-ghost !min-h-10" onClick={cancelScan}>
                Cancel
              </button>
            </div>
          ) : (
            <div className="flex flex-wrap gap-2">
              <button type="button" className="btn-primary" onClick={() => startScan(true)}>
                Start mapping
              </button>
              {map && (
                <button type="button" className="btn-ghost" onClick={() => setStep(3)}>
                  Continue with current map
                </button>
              )}
            </div>
          )}
          {scanError && (
            <p className="text-[14px] text-[var(--color-ink-2)]">
              {scanError}{' '}
              <button
                type="button"
                className="underline text-[var(--color-ink)]"
                onClick={() => startScan(true)}
              >
                Load demo map
              </button>
            </p>
          )}
          {map && !scanning && (
            <p className="text-[13px] text-[var(--color-ink)]">
              Floor plan ready ({map.width_m}×{map.height_m} m demo home). Continue to paint zones.
            </p>
          )}
        </div>
      )}

      {step === 3 && map && (
        <div className="card space-y-4">
          <h2 className="text-[18px]">Paint zones</h2>
          <p className="text-[14px] text-[var(--color-ink-2)]">
            Everything starts <span className="text-[var(--color-ink)]">Safe</span>. Paint{' '}
            <span className="text-[var(--color-ink)]">Watch</span> and{' '}
            <span className="text-[var(--color-ink)]">Don&apos;t go</span>, then place home.
          </p>
          <ZonePainter
            map={map}
            home={home}
            initialZones={projection.zones}
            onHomeChange={setHome}
            onZonesChange={setZones}
          />
          <div className="flex flex-wrap gap-2">
            <button type="button" className="btn-primary" onClick={finish}>
              Save &amp; open Home
            </button>
            <button type="button" className="btn-ghost" onClick={() => setStep(4)}>
              Next — Schedule
            </button>
          </div>
          {saved && <p className="text-[14px] text-[var(--color-ink)]">{saved}</p>}
        </div>
      )}

      {step === 4 && (
        <div className="card max-w-md space-y-3">
          <h2 className="text-[18px]">Schedule & contacts</h2>
          <label className="block text-[14px] text-[var(--color-ink-2)]">
            Wake time
            <input
              className="input-field mt-1"
              value={schedule.wake_time}
              onChange={(e) => setSchedule({ ...schedule, wake_time: e.target.value })}
            />
          </label>
          <label className="block text-[14px] text-[var(--color-ink-2)]">
            Meals
            <input
              className="input-field mt-1"
              value={schedule.meals}
              onChange={(e) => setSchedule({ ...schedule, meals: e.target.value })}
            />
          </label>
          <div className="flex gap-2">
            <label className="block flex-1 text-[14px] text-[var(--color-ink-2)]">
              Walk start
              <input
                className="input-field mt-1"
                value={schedule.walk_start}
                onChange={(e) => setSchedule({ ...schedule, walk_start: e.target.value })}
              />
            </label>
            <label className="block flex-1 text-[14px] text-[var(--color-ink-2)]">
              Walk end
              <input
                className="input-field mt-1"
                value={schedule.walk_end}
                onChange={(e) => setSchedule({ ...schedule, walk_end: e.target.value })}
              />
            </label>
          </div>
          <label className="block text-[14px] text-[var(--color-ink-2)]">
            Notes
            <textarea
              className="input-field mt-1"
              rows={2}
              value={schedule.notes}
              onChange={(e) => setSchedule({ ...schedule, notes: e.target.value })}
            />
          </label>
          <label className="block text-[14px] text-[var(--color-ink-2)]">
            Primary contact
            <input
              className="input-field mt-1"
              value={contacts.primary}
              onChange={(e) => setContacts({ ...contacts, primary: e.target.value })}
            />
          </label>
          <label className="block text-[14px] text-[var(--color-ink-2)]">
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
          {saved && <p className="text-[14px] text-[var(--color-ink)]">{saved}</p>}
        </div>
      )}
    </div>
  )
}
