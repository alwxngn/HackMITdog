import { useState } from 'react'
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
    if (e.shiftKey) {
      setHome({ x: Math.round(x * 100) / 100, y: Math.round(y * 100) / 100 })
      return
    }
    setDrawing((d) => [...d, [Math.round(x * 100) / 100, Math.round(y * 100) / 100]])
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
    <div className="mx-auto max-w-4xl space-y-4 p-4">
      <h1 className="text-3xl">Onboarding</h1>
      <p className="text-sm text-[var(--muted)]">
        Steps 3–4 for caregivers. Click map to drop polygon points; Shift-click sets home.
        Frame: origin SW corner, +x east, metres (see docs/16-e3-portal.md).
      </p>
      <div className="flex gap-2">
        <button
          className={`rounded px-3 py-1 text-sm ${step === 3 ? 'bg-[var(--accent)] text-[#1a1408]' : 'bg-white/10'}`}
          onClick={() => setStep(3)}
        >
          3 · Risks & home
        </button>
        <button
          className={`rounded px-3 py-1 text-sm ${step === 4 ? 'bg-[var(--accent)] text-[#1a1408]' : 'bg-white/10'}`}
          onClick={() => setStep(4)}
        >
          4 · Schedule
        </button>
      </div>

      {step === 3 && (
        <div className="grid gap-4 md:grid-cols-2">
          <div className="rounded-lg bg-[var(--panel)] p-3">
            <div className="mb-2 flex flex-wrap gap-2 text-sm">
              {CLASSES.map((c) => (
                <button
                  key={c.value}
                  className={`rounded px-2 py-1 ${zoneClass === c.value ? 'bg-white/20' : 'bg-white/5'}`}
                  onClick={() => {
                    setZoneClass(c.value)
                    setZoneLabel(c.label)
                  }}
                >
                  {c.label}
                </button>
              ))}
              <select
                className="rounded bg-black/40 px-2"
                value={kind}
                onChange={(e) => setKind(e.target.value as Zone['kind'])}
              >
                <option value="door">door</option>
                <option value="stairs">stairs</option>
                <option value="outdoor_boundary">outdoor_boundary</option>
              </select>
              <button className="rounded bg-white/10 px-2" onClick={finishZone}>
                Close polygon
              </button>
              <button className="rounded bg-white/10 px-2" onClick={() => setDrawing([])}>
                Clear points
              </button>
            </div>
            <svg
              viewBox={`0 0 ${SVG.width} ${SVG.height}`}
              className="w-full cursor-crosshair rounded border border-white/10 bg-[#0b1016]"
              onClick={onSvgClick}
            >
              <rect
                x={SVG.pad}
                y={SVG.pad}
                width={SVG.width - SVG.pad * 2}
                height={SVG.height - SVG.pad * 2}
                fill="none"
                stroke="rgba(255,255,255,0.2)"
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
                      ? 'rgba(181,74,74,0.4)'
                      : z.class === 'watch'
                        ? 'rgba(184,137,61,0.35)'
                        : 'rgba(61,122,95,0.35)'
                  }
                  stroke="white"
                />
              ))}
              {drawing.length > 0 && (
                <polyline
                  fill="none"
                  stroke="var(--accent)"
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
                return <rect x={cx - 4} y={cy - 4} width={8} height={8} fill="var(--safe)" />
              })()}
            </svg>
            <p className="mt-2 text-xs text-[var(--muted)]">
              Map {MAP_METRES.width}×{MAP_METRES.height} m · home ({home.x}, {home.y}) ·{' '}
              {drawing.length} points drafting
            </p>
          </div>
          <div className="space-y-3 rounded-lg bg-[var(--panel)] p-4 text-sm">
            <h3 className="text-base">Escalation contacts</h3>
            <label className="block">
              Primary
              <input
                className="mt-1 w-full rounded border border-white/10 bg-black/30 px-2 py-1"
                value={contacts.primary}
                onChange={(e) => setContacts({ ...contacts, primary: e.target.value })}
              />
            </label>
            <label className="block">
              Secondary
              <input
                className="mt-1 w-full rounded border border-white/10 bg-black/30 px-2 py-1"
                value={contacts.secondary}
                onChange={(e) => setContacts({ ...contacts, secondary: e.target.value })}
              />
            </label>
            <ul className="text-xs text-[var(--muted)]">
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
        <div className="max-w-md space-y-3 rounded-lg bg-[var(--panel)] p-4 text-sm">
          <label className="block">
            Wake time
            <input
              className="mt-1 w-full rounded border border-white/10 bg-black/30 px-2 py-1"
              value={schedule.wake_time}
              onChange={(e) => setSchedule({ ...schedule, wake_time: e.target.value })}
            />
          </label>
          <label className="block">
            Meals (comma-separated)
            <input
              className="mt-1 w-full rounded border border-white/10 bg-black/30 px-2 py-1"
              value={schedule.meals}
              onChange={(e) => setSchedule({ ...schedule, meals: e.target.value })}
            />
          </label>
          <div className="flex gap-2">
            <label className="block flex-1">
              Walk start
              <input
                className="mt-1 w-full rounded border border-white/10 bg-black/30 px-2 py-1"
                value={schedule.walk_start}
                onChange={(e) => setSchedule({ ...schedule, walk_start: e.target.value })}
              />
            </label>
            <label className="block flex-1">
              Walk end
              <input
                className="mt-1 w-full rounded border border-white/10 bg-black/30 px-2 py-1"
                value={schedule.walk_end}
                onChange={(e) => setSchedule({ ...schedule, walk_end: e.target.value })}
              />
            </label>
          </div>
          <label className="block">
            Notes
            <textarea
              className="mt-1 w-full rounded border border-white/10 bg-black/30 px-2 py-1"
              rows={3}
              value={schedule.notes}
              onChange={(e) => setSchedule({ ...schedule, notes: e.target.value })}
            />
          </label>
        </div>
      )}

      <button
        className="rounded bg-[var(--accent)] px-4 py-2 font-medium text-[#1a1408]"
        onClick={save}
      >
        Publish config_update
      </button>
      {saved && <p className="text-sm text-[var(--muted)]">{saved}</p>}
    </div>
  )
}
