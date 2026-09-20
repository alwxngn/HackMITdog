import { polygonToPoints, SVG, worldToSvg, type MapBounds } from '../lib/frame'
import { PAINT_FILL, PAINT_LABEL, PAINT_STROKE } from '../lib/zonePaint'
import type { Zone } from '../lib/types'
import { useProjection } from '../hooks/useProjection'
import { DEMO_HOME_MAP_ID } from '../lib/demoHome'
import { HomeFloor, HomeStructures } from './HomeScene'

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
    return { key, text: zs[0].label || zs[0].id, ...mid }
  })
}

export function MapView() {
  const p = useProjection()
  const live = p.live_tracking || Boolean(p.open_alert?.live_tracking)
  const bounds: MapBounds = {
    width: p.map_ready?.width_m ?? 2,
    height: p.map_ready?.height_m ?? 2,
  }
  // Demo table-top home is hard-coded; a real robot scan falls back to plain room outlines.
  const showHome = !p.map_ready || p.map_ready.map_id === DEMO_HOME_MAP_ID

  return (
    <div className="card-slate !p-5">
      <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="eyebrow mb-2">Home</p>
          <h2>Where they are</h2>
        </div>
        <div className="flex flex-wrap gap-3 text-[12px] text-[var(--color-ink-2)]">
          {(['safe', 'watch', 'exit'] as const).map((c) => (
            <span key={c} className="inline-flex items-center gap-1.5">
              <span className="h-2.5 w-2.5 rounded-full" style={{ background: PAINT_STROKE[c] }} />
              {PAINT_LABEL[c]}
            </span>
          ))}
          {live && <span className="pill !py-1">Live tracking</span>}
        </div>
      </div>

      <svg
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
                stroke="#0e1116"
                strokeWidth={1}
                strokeDasharray="4 3"
              />
            ))}
          </>
        )}
        {p.zones.map((z: Zone) => (
          <polygon
            key={z.id}
            points={polygonToPoints(z.polygon, bounds)}
            fill={PAINT_FILL[z.class] || 'rgba(255,255,255,0.08)'}
            stroke={showHome ? undefined : PAINT_STROKE[z.class] || '#0e1116'}
            strokeWidth={z.class === 'safe' || showHome ? 0 : 1.5}
            shapeRendering="crispEdges"
            opacity={z.class === 'safe' ? 0.5 : 1}
          />
        ))}

        {showHome && <HomeStructures bounds={bounds} />}
        {zoneLabels(p.zones, bounds).map((l) => (
          <text
            key={l.key}
            x={l.cx}
            y={l.cy + 4}
            textAnchor="middle"
            fill="#0e1116"
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

        {live && p.person_trail.length > 1 && (
          <polyline
            fill="none"
            stroke="#2563ff"
            strokeWidth={2.5}
            strokeLinecap="round"
            strokeLinejoin="round"
            opacity={0.9}
            points={p.person_trail
              .map(({ x, y }) => {
                const { cx, cy } = worldToSvg(x, y, bounds)
                return `${cx},${cy}`
              })
              .join(' ')}
          />
        )}

        {p.pose &&
          (() => {
            const { cx, cy } = worldToSvg(p.pose.x, p.pose.y, bounds)
            return (
              <g>
                <circle cx={cx} cy={cy} r={17} fill="#2563ff" opacity={0.16} />
                <circle cx={cx} cy={cy} r={9} fill="#2563ff" stroke="#ffffff" strokeWidth={2} />
                <text x={cx + 14} y={cy + 4} fill="#0e1116" fontSize={11} fontWeight={600} fontFamily="Inter, sans-serif">
                  Lantern
                </text>
              </g>
            )
          })()}

        {p.person_track &&
          (() => {
            const { cx, cy } = worldToSvg(p.person_track.x, p.person_track.y, bounds)
            return (
              <g>
                <circle cx={cx} cy={cy} r={12} fill="#e5484d" stroke="#ffffff" strokeWidth={2} />
                <text x={cx + 14} y={cy + 4} fill="#0e1116" fontSize={12} fontWeight={600} fontFamily="Inter, sans-serif">
                  person
                </text>
              </g>
            )
          })()}

        {(() => {
          const home = (p.config.patient as { home?: { x: number; y: number } } | undefined)?.home
          if (!home) return null
          const { cx, cy } = worldToSvg(home.x, home.y, bounds)
          return (
            <g>
              <circle cx={cx} cy={cy} r={8} fill="#0e1116" stroke="#ffffff" strokeWidth={2} />
              <text x={cx + 12} y={cy + 4} fill="#0e1116" fontSize={10} fontWeight={600} fontFamily="Inter, sans-serif">
                home
              </text>
            </g>
          )
        })()}
      </svg>
    </div>
  )
}
