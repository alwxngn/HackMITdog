import { useState } from 'react'
import { Link } from 'react-router-dom'
import { MAP_METRES, SVG, svgToWorld, worldToSvg } from '../../lib/frame'
import type { Zone } from '../../lib/types'
import { useProjection } from '../../hooks/useProjection'

const CLASSES: { value: Zone['class']; label: string }[] = [
  { value: 'safe', label: 'Safe' },
  { value: 'watch', label: 'Watch' },
  { value: 'exit', label: "Don't go" },
]

export function Onboarding() {
  const p = useProjection()
  const [step, setStep] = useState<3 | 4>(3)
  const [zones, setZones] = useState<Zone[]>(p.zones.length ? p.zones : [])
  const [drawing, setDrawing] = useState<[number, number][]>([])
  const [zoneClass, setZoneClass] = useState<Zone['class']>('exit')
  const [zoneLabel, setZoneLabel] = useState("Don't go")
  const [kind, setKind] = useState<Zone['kind']>('door')
  const [home, setHome] = useState({ x: 0, y: 0 })
  const [placeHome, setPlaceHome] = useState(false)
  const [schedule, setSchedule] = useState({
    wake_time: '07:30',
    meals: '08:00,12:30,18:00',
    walk_start: '15:00',
    walk_end: '16:30',
    notes: 'likes the porch after lunch',
  })
  const [contacts, setContacts] = useState({
    primary: 'jenny',
    primary_phone: '',
    secondary: 'mark',
  })
  const [saved, setSaved] = useState('')

  function onSvgClick(e: React.MouseEvent<SVGSVGElement>) {
    const rect = e.currentTarget.getBoundingClientRect()
    const cx = ((e.clientX - rect.left) / rect.width) * SVG.width
    const cy = ((e.clientY - rect.top) / rect.height) * SVG.height
    const { x, y } = svgToWorld(cx, cy)
    const rounded = {
      x: Math.round(x * 100) / 100,
      y: Math.round(y * 100) / 100,
    }
    if (placeHome || e.shiftKey) {
      setHome(rounded)
      setPlaceHome(false)
      return
    }
    setDrawing((d) => [...d, [rounded.x, rounded.y]])
  }

  function finishZone() {
    if (drawing.length < 3) return
    const id = `${zoneClass}_${zones.length + 1}`
    const z: Zone = {
      id,
      class: zoneClass,
      label: zoneClass === 'exit' ? "Don't go" : zoneLabel || id,
      kind,
      polygon: drawing,
    }
    setZones((zs) => [...zs, z])
    setDrawing([])
  }

  async function save() {
    const patient = {
      name: 'Arthur',
      preferred_name: 'Art',
      calming_topics: ['fishing at Moosehead', 'his dog Bella'],
      avoid_topics: ["his wife's death"],
      music_url: '/media/arthur_playlist.mp3',
      schedule: {
        wake_time: schedule.wake_time,
        meals: schedule.meals.split(',').map((s) => s.trim()).filter(Boolean),
        walk_window: [schedule.walk_start, schedule.walk_end],
        notes: schedule.notes,
      },
      home: { ...home, lat: null, lon: null },
      route_id: null,
    }
    const escalation = [
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
    ]
    const body = { zones, patient, escalation }
    const r = await fetch('/api/config', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
    setSaved(r.ok ? 'Saved — config_update on the bus' : 'Save failed')
  }

  return (
    <div className="mx-auto max-w-[1200px] space-y-6 p-4 pb-24 md:p-8">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-[12px] tracking-[0.02em] text-[var(--color-lilac-mist)]">Lantern</p>
          <h1 className="text-[32px] tracking-[-0.04em] sm:text-[46px]">
            On<span className="word-highlight">boarding</span>
          </h1>
        </div>
        <Link className="btn-ghost !min-h-11 !text-[14px]" to="/">
          Night Watch
        </Link>
      </div>
      <p className="max-w-2xl text-[14px] text-[var(--color-ash)]">
        Scan the QR on the laptop to set this up on your phone. Steps 3–4: risks, home, schedule.
        Tap the map to drop zone points; use{' '}
        <strong className="text-[var(--color-pearl)]">Place home</strong> then tap (or Shift-click
        on desktop). Frame: SW origin, +x east, metres.
      </p>
      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          className={`pill min-h-11 px-4 ${step === 3 ? 'bg-[var(--color-iris-pulse)] text-white' : 'border border-[var(--color-iris-border)] text-[var(--color-lilac-mist)]'}`}
          onClick={() => setStep(3)}
        >
          3 · Risks & home
        </button>
        <button
          type="button"
          className={`pill min-h-11 px-4 ${step === 4 ? 'bg-[var(--color-iris-pulse)] text-white' : 'border border-[var(--color-iris-border)] text-[var(--color-lilac-mist)]'}`}
          onClick={() => setStep(4)}
        >
          4 · Schedule
        </button>
      </div>

      {step === 3 && (
        <div className="grid gap-4 md:grid-cols-2 md:gap-6">
          <div className="card !p-4">
            <div className="mb-3 flex flex-wrap gap-2 text-[14px]">
              {CLASSES.map((c) => (
                <button
                  key={c.value}
                  type="button"
                  className={`pill ${zoneClass === c.value ? 'bg-[var(--color-iris-pulse)] text-white' : 'border border-[var(--color-iris-border)] text-[var(--color-lilac-mist)]'}`}
                  onClick={() => {
                    setZoneClass(c.value)
                    setZoneLabel(c.label)
                  }}
                >
                  {c.label}
                </button>
              ))}
              <select
                className="input-field !w-auto !py-2"
                value={kind}
                onChange={(e) => setKind(e.target.value as Zone['kind'])}
              >
                <option value="door">door</option>
                <option value="stairs">stairs</option>
                <option value="outdoor_boundary">outdoor_boundary</option>
              </select>
              <button type="button" className="btn-ghost !min-h-10 !px-3 !text-[12px]" onClick={finishZone}>
                Close polygon
              </button>
              <button
                type="button"
                className="btn-ghost !min-h-10 !px-3 !text-[12px]"
                onClick={() => setDrawing([])}
              >
                Clear points
              </button>
              <button
                type="button"
                className={`pill min-h-10 ${placeHome ? 'bg-[color-mix(in_srgb,var(--color-mint-vital)_25%,transparent)] text-[var(--color-mint-vital)]' : 'border border-[var(--color-iris-border)] text-[var(--color-lilac-mist)]'}`}
                onClick={() => setPlaceHome((v) => !v)}
              >
                {placeHome ? 'Tap map for home…' : 'Place home'}
              </button>
            </div>
            <svg
              viewBox={`0 0 ${SVG.width} ${SVG.height}`}
              className="w-full cursor-crosshair rounded-[16px] border border-[var(--color-iris-border)] bg-[var(--color-deep-iris)]"
              onClick={onSvgClick}
            >
              <rect
                x={SVG.pad}
                y={SVG.pad}
                width={SVG.width - SVG.pad * 2}
                height={SVG.height - SVG.pad * 2}
                fill="none"
                stroke="#4846c6"
                strokeDasharray="4 4"
              />
              {zones.map((z) => (
                <polygon
                  key={z.id}
                  points={z.polygon
                    .map(([x, y]) => {
                      const { cx, cy } = worldToSvg(x, y)
                      return `${cx},${cy}`
                    })
                    .join(' ')}
                  fill={
                    z.class === 'exit'
                      ? 'rgba(177,166,246,0.35)'
                      : z.class === 'watch'
                        ? 'rgba(0,177,255,0.22)'
                        : 'rgba(0,255,170,0.22)'
                  }
                  stroke={z.class === 'exit' ? '#b1a6f6' : z.class === 'watch' ? '#00b1ff' : '#00ffaa'}
                />
              ))}
              {drawing.length > 0 && (
                <polyline
                  fill="none"
                  stroke="#00b1ff"
                  strokeWidth={2}
                  points={drawing
                    .map(([x, y]) => {
                      const { cx, cy } = worldToSvg(x, y)
                      return `${cx},${cy}`
                    })
                    .join(' ')}
                />
              )}
              {(() => {
                const { cx, cy } = worldToSvg(home.x, home.y)
                return <rect x={cx - 4} y={cy - 4} width={8} height={8} rx={2} fill="#00ffaa" />
              })()}
            </svg>
            <p className="mt-3 text-[12px] text-[var(--color-fog)]">
              Map {MAP_METRES.width}×{MAP_METRES.height} m · home ({home.x}, {home.y}) ·{' '}
              {drawing.length} points drafting
            </p>
          </div>
          <div className="card space-y-3 text-[14px]">
            <h3 className="text-[18px] tracking-[-0.03em]">Escalation contacts</h3>
            <label className="block text-[var(--color-ash)]">
              Primary
              <input
                className="input-field mt-1"
                value={contacts.primary}
                onChange={(e) => setContacts({ ...contacts, primary: e.target.value })}
              />
            </label>
            <label className="block text-[var(--color-ash)]">
              Secondary
              <input
                className="input-field mt-1"
                value={contacts.secondary}
                onChange={(e) => setContacts({ ...contacts, secondary: e.target.value })}
              />
            </label>
            <ul className="text-[12px] text-[var(--color-fog)]">
              {zones.map((z) => (
                <li key={z.id}>
                  {z.label} ({z.class}/{z.kind}) — {z.polygon.length} pts
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}

      {step === 4 && (
        <div className="card max-w-md space-y-3 text-[14px]">
          <label className="block text-[var(--color-ash)]">
            Wake time
            <input
              className="input-field mt-1"
              value={schedule.wake_time}
              onChange={(e) => setSchedule({ ...schedule, wake_time: e.target.value })}
            />
          </label>
          <label className="block text-[var(--color-ash)]">
            Meals (comma-separated)
            <input
              className="input-field mt-1"
              value={schedule.meals}
              onChange={(e) => setSchedule({ ...schedule, meals: e.target.value })}
            />
          </label>
          <div className="flex gap-2">
            <label className="block flex-1 text-[var(--color-ash)]">
              Walk start
              <input
                className="input-field mt-1"
                value={schedule.walk_start}
                onChange={(e) => setSchedule({ ...schedule, walk_start: e.target.value })}
              />
            </label>
            <label className="block flex-1 text-[var(--color-ash)]">
              Walk end
              <input
                className="input-field mt-1"
                value={schedule.walk_end}
                onChange={(e) => setSchedule({ ...schedule, walk_end: e.target.value })}
              />
            </label>
          </div>
          <label className="block text-[var(--color-ash)]">
            Notes
            <textarea
              className="input-field mt-1 min-h-[88px]"
              rows={3}
              value={schedule.notes}
              onChange={(e) => setSchedule({ ...schedule, notes: e.target.value })}
            />
          </label>
        </div>
      )}

      <button type="button" className="btn-primary w-full sm:w-auto" onClick={save}>
        Publish config_update
      </button>
      {saved && <p className="text-[14px] text-[var(--color-mint-vital)]">{saved}</p>}
    </div>
  )
}
