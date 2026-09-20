import { useState } from 'react'
import { polygonToPoints, SVG, worldToSvg, type MapBounds } from '../lib/frame'
import { PAINT_FILL, PAINT_LABEL, PAINT_STROKE, zoneName } from '../lib/zonePaint'
import type { Zone } from '../lib/types'
import { useProjection } from '../hooks/useProjection'
import { DEMO_HOME_MAP_ID, DEMO_HOME_PIN } from '../lib/demoHome'
import { HomeFloor, HomeStructures } from './HomeScene'
import { Map3D } from './Map3D'

/** One label per painted region (or per zone), centred on the region's bounding box. */
function zoneLabels(zones: Zone[], bounds: MapBounds) {
  const groups = new Map<string, { zs: Zone[] }>()
  for (const z of zones) {
    if (z.class === 'safe' || z.polygon.length === 0) continue
    const k = z.region ?? z.id
    const g = groups.get(k) ?? { zs: [] }
    g.zs.push(z)
    groups.set(k, g)
  }
  return [...groups.entries()].map(([key, { zs }]) => {
    const pts = zs.flatMap((z) => z.polygon)
    const xs = pts.map(([x]) => x)
    const ys = pts.map(([, y]) => y)
    const mid = worldToSvg((Math.min(...xs) + Math.max(...xs)) / 2, (Math.min(...ys) + Math.max(...ys)) / 2, bounds)
    return { key, text: zoneName(zs[0]), ...mid }
  })
}

export function MapView() {
  const p = useProjection()
  const patientName =
    (p.config.patient as { preferred_name?: string; name?: string } | undefined)?.preferred_name ||
    (p.config.patient as { name?: string } | undefined)?.name ||
    'Patient'
  // Zones only exist while Night Watch is on; off hides them (and the legend).
  const zonesOn = (p.config.night_watch_enabled as boolean | undefined) ?? false
  const zones = zonesOn ? p.zones : []
  const [view, setView] = useState<'map' | '3d'>('map')
  const live = p.live_tracking || Boolean(p.open_alert?.live_tracking)
  // A patient coordinate is sensitive and can become stale. Only display it while the
  // caregiver explicitly has Night Watch, a demo walk, or escalation tracking active.
  const patientTrackingActive = zonesOn || p.demo.running || live
  const bounds: MapBounds = {
    width: p.map_ready?.width_m ?? 2,
    height: p.map_ready?.height_m ?? 2,
  }
  // Demo table-top home is hard-coded; a real robot scan falls back to plain room outlines.
  const showHome = !p.map_ready || p.map_ready.map_id === DEMO_HOME_MAP_ID
  // Once they step outside, positions fall off this floor plan — LiveTrack takes over.
  const inside = (x: number, y: number) => x >= 0 && x <= bounds.width && y >= 0 && y <= bounds.height

  return (
    <div className="card-slate !p-5">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <h2>Home map</h2>
        <div className="flex flex-wrap gap-3 text-[12px] text-[var(--color-ink-2)]">
          {zonesOn ? (
            (['safe', 'watch', 'exit'] as const).map((c) => (
              <span key={c} className="inline-flex items-center gap-1.5">
                <span className="h-2.5 w-2.5 rounded-full" style={{ background: PAINT_STROKE[c] }} />
                {PAINT_LABEL[c]}
              </span>
            ))
          ) : (
            <span>Night Watch off · zones hidden</span>
          )}
          {live && <span className="pill !py-1">Live tracking</span>}
        </div>
      </div>

      <div className="mb-4 flex flex-wrap gap-x-4 gap-y-2 text-[12px] text-[var(--color-ink-2)]" aria-label="Map markers">
        <span className="inline-flex items-center gap-1.5">
          <span className="h-2.5 w-2.5 rounded-full bg-[#f0883e]" />
          Lantern · robot position
        </span>
        <span className="inline-flex items-center gap-1.5">
          <span className="h-2.5 w-2.5 rounded-full bg-[#e5626a]" />
          {patientName} · active watch only
        </span>
        {showHome && (
          <span className="inline-flex items-center gap-1.5">
            <span className="h-2.5 w-3 rounded-[2px] bg-[#153a3b]" />
            Lantern dock · fixed
          </span>
        )}
      </div>

      <div className="mb-4 flex gap-2" role="tablist" aria-label="Map views">
        <button type="button" role="tab" aria-selected={view === 'map'} className={`pill !py-2 ${view === 'map' ? 'bg-[var(--color-ink)] text-[var(--color-surface)]' : ''}`} onClick={() => setView('map')}>2D zones</button>
        <button type="button" role="tab" aria-selected={view === '3d'} className={`pill !py-2 ${view === '3d' ? 'bg-[var(--color-ink)] text-[var(--color-surface)]' : ''}`} onClick={() => setView('3d')}>3D scan</button>
      </div>

      {view === '3d' && <Map3D url={p.map_ready?.artifact_url} />}

      {view === 'map' && <svg
        viewBox={`0 0 ${SVG.width} ${SVG.height}`}
        className="h-auto w-full rounded-[14px] bg-[var(--color-surface)]"
      >
        {showHome ? (
          <HomeFloor bounds={bounds} />
        ) : (
          <>
            <rect
              x={SVG.pad}
              y={SVG.pad}
              width={SVG.width - SVG.pad * 2}
              height={SVG.height - SVG.pad * 2}
              fill={PAINT_FILL.safe}
              opacity={0.35}
            />
            {p.map_ready?.rooms?.map((r) => (
              <polygon
                key={r.id}
                points={polygonToPoints(r.polygon, bounds)}
                fill="none"
                stroke="#153a3b"
                strokeWidth={1}
                strokeDasharray="4 3"
              />
            ))}
          </>
        )}
        {zones.map((z: Zone) => (
          <polygon
            key={z.id}
            points={polygonToPoints(z.polygon, bounds)}
            fill={PAINT_FILL[z.class] || 'rgba(255,255,255,0.08)'}
            stroke={showHome ? undefined : PAINT_STROKE[z.class] || '#153a3b'}
            strokeWidth={z.class === 'safe' || showHome ? 0 : 1.5}
            shapeRendering="crispEdges"
            opacity={z.class === 'safe' ? 0.5 : 1}
          />
        ))}

        {showHome && <HomeStructures bounds={bounds} />}
        {zoneLabels(zones, bounds).map((l) => (
          <text
            key={l.key}
            x={l.cx}
            y={l.cy + 4}
            textAnchor="middle"
            fill="#153a3b"
            fontSize={11}
            fontWeight={600}
            fontFamily="Inter, sans-serif"
            stroke="#ffffff"
            strokeWidth={3}
            paintOrder="stroke"
            pointerEvents="none"
          >
            {l.text}
          </text>
        ))}

        {live && p.person_trail.filter((t) => inside(t.x, t.y)).length > 1 && (
          <polyline
            fill="none"
            stroke="#f0883e"
            strokeWidth={2.5}
            strokeLinecap="round"
            strokeLinejoin="round"
            opacity={0.9}
            points={p.person_trail
              .filter((t) => inside(t.x, t.y))
              .map(({ x, y }) => {
                const { cx, cy } = worldToSvg(x, y, bounds)
                return `${cx},${cy}`
              })
              .join(' ')}
          />
        )}

        {p.pose &&
          inside(p.pose.x, p.pose.y) &&
          (() => {
            const { cx, cy } = worldToSvg(p.pose.x, p.pose.y, bounds)
            return (
              <g>
                <circle cx={cx} cy={cy} r={17} fill="#f0883e" opacity={0.16} />
                <circle cx={cx} cy={cy} r={9} fill="#f0883e" stroke="#ffffff" strokeWidth={2} />
                <text x={cx + 14} y={cy + 4} fill="#153a3b" fontSize={11} fontWeight={600} fontFamily="Inter, sans-serif">
                  Lantern
                </text>
              </g>
            )
          })()}

        {patientTrackingActive &&
          p.person_track &&
          inside(p.person_track.x, p.person_track.y) &&
          (() => {
            const { cx, cy } = worldToSvg(p.person_track.x, p.person_track.y, bounds)
            return (
              <g>
                <circle cx={cx} cy={cy} r={12} fill="#e5626a" stroke="#ffffff" strokeWidth={2} />
                <text x={cx + 14} y={cy + 4} fill="#153a3b" fontSize={12} fontWeight={600} fontFamily="Inter, sans-serif">
                  {patientName}
                </text>
              </g>
            )
          })()}

        {showHome && (() => {
          const { cx, cy } = worldToSvg(DEMO_HOME_PIN.x, DEMO_HOME_PIN.y, bounds)
          return (
            <g>
              <title>Lantern's fixed charging dock</title>
              <rect x={cx - 8} y={cy - 6} width={16} height={12} rx={3} fill="#153a3b" stroke="#ffffff" strokeWidth={2} />
              <text x={cx + 13} y={cy + 4} fill="#153a3b" fontSize={10} fontWeight={600} fontFamily="Inter, sans-serif">
                Lantern dock
              </text>
            </g>
          )
        })()}
      </svg>}

      {view === 'map' && !patientTrackingActive && (
        <p className="mt-3 text-[12px] text-[var(--color-ink-2)]">
          {patientName}'s location is hidden while Night Watch is off. Run the demo walk or turn on Night Watch to show active location reports.
        </p>
      )}
      {view === 'map' && patientTrackingActive && !p.person_track && (
        <p className="mt-3 text-[12px] text-[var(--color-ink-2)]">
          Waiting for {patientName}'s first location report. Lantern and {patientName} appear only when their devices publish positions.
        </p>
      )}
    </div>
  )
}
