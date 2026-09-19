import { polygonToPoints, SVG, worldToSvg, type MapBounds } from '../lib/frame'
import { PAINT_FILL, PAINT_LABEL, PAINT_STROKE } from '../lib/zonePaint'
import type { Zone } from '../lib/types'
import { useProjection } from '../hooks/useProjection'

export function MapView() {
  const p = useProjection()
  const live = p.live_tracking || Boolean(p.open_alert?.live_tracking)
  const bounds: MapBounds = {
    width: p.map_ready?.width_m ?? 2,
    height: p.map_ready?.height_m ?? 2,
  }

  return (
    <div className="card-slate h-full">
      <div className="mb-3 flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="text-[18px]">Floor</h2>
        <span className="text-[13px] text-[var(--color-charcoal)]">
          {live ? 'live tracking' : 'map'} · metres
          {p.map_ready?.map_id ? ` · ${p.map_ready.map_id}` : ''}
        </span>
      </div>

      <div className="mb-3 flex flex-wrap gap-3 text-[12px]">
        {(['safe', 'watch', 'exit'] as const).map((c) => (
          <span key={c} className="inline-flex items-center gap-1.5 text-[var(--color-charcoal)]">
            <span
              className="h-2.5 w-2.5 rounded-full"
              style={{ background: PAINT_STROKE[c] }}
            />
            {PAINT_LABEL[c]}
          </span>
        ))}
      </div>

      <svg
        viewBox={`0 0 ${SVG.width} ${SVG.height}`}
        className="h-auto w-full max-w-full rounded-[14px] bg-[var(--color-cream-paper)]"
      >
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
            stroke="#0f3e17"
            strokeWidth={1}
            strokeDasharray="4 3"
          />
        ))}
        {p.zones.map((z: Zone) => (
          <g key={z.id}>
            <polygon
              points={polygonToPoints(z.polygon, bounds)}
              fill={PAINT_FILL[z.class] || 'rgba(255,255,255,0.08)'}
              stroke={PAINT_STROKE[z.class] || '#0f3e17'}
              strokeWidth={z.class === 'safe' ? 0 : 1.5}
              opacity={z.class === 'safe' ? 0.25 : 0.85}
            />
            {z.class !== 'safe' && z.polygon[0] && (
              <text
                x={worldToSvg(z.polygon[0][0], z.polygon[0][1], bounds).cx + 4}
                y={worldToSvg(z.polygon[0][0], z.polygon[0][1], bounds).cy + 14}
                fill="#0f3e17"
                fontSize={11}
                fontFamily="Inter, sans-serif"
              >
                {z.label || z.id}
              </text>
            )}
          </g>
        ))}

        {live && p.person_trail.length > 1 && (
          <polyline
            fill="none"
            stroke="#0f3e17"
            strokeWidth={2}
            opacity={0.85}
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
                <circle cx={cx} cy={cy} r={10} fill="#0f3e17" stroke="#fffefc" strokeWidth={1.5} />
                <text x={cx + 12} y={cy + 4} fill="#0f3e17" fontSize={11} fontFamily="Inter, sans-serif">
                  robot
                </text>
              </g>
            )
          })()}

        {p.person_track &&
          (() => {
            const { cx, cy } = worldToSvg(p.person_track.x, p.person_track.y, bounds)
            return (
              <g>
                <circle cx={cx} cy={cy} r={12} fill="#0c2f10" stroke="#fffefc" strokeWidth={2} />
                <text x={cx + 14} y={cy + 4} fill="#0f3e17" fontSize={12} fontFamily="Inter, sans-serif">
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
              <circle cx={cx} cy={cy} r={9} fill="#0f3e17" stroke="#fffefc" strokeWidth={2} />
              <text x={cx + 12} y={cy + 4} fill="#0f3e17" fontSize={10} fontFamily="Inter, sans-serif">
                home
              </text>
            </g>
          )
        })()}
      </svg>
    </div>
  )
}
