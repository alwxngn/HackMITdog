import { polygonToPoints, SVG, worldToSvg } from '../lib/frame'
import type { Zone } from '../lib/types'
import { useProjection } from '../hooks/useProjection'

const ZONE_FILL: Record<string, string> = {
  safe: 'rgba(0,255,170,0.22)',
  watch: 'rgba(0,177,255,0.22)',
  exit: 'rgba(177,166,246,0.35)',
}

const ZONE_STROKE: Record<string, string> = {
  safe: '#00ffaa',
  watch: '#00b1ff',
  exit: '#b1a6f6',
}

export function MapView() {
  const p = useProjection()
  const live = p.live_tracking || Boolean(p.open_alert?.live_tracking)

  return (
    <div className="card">
      <div className="mb-3 flex items-baseline justify-between gap-2">
        <h2 className="text-[18px] tracking-[-0.03em] text-[var(--color-cloud-white)]">Floor</h2>
        <span className="text-[12px] tracking-[0.02em] text-[var(--color-lilac-mist)]">
          {live ? 'live tracking' : 'map'} · metres
        </span>
      </div>
      <svg
        viewBox={`0 0 ${SVG.width} ${SVG.height}`}
        className="h-auto w-full max-w-full rounded-[16px] border border-[var(--color-iris-border)] bg-[var(--color-deep-iris)]"
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
        {p.zones.map((z: Zone) => (
          <g key={z.id}>
            <polygon
              points={polygonToPoints(z.polygon)}
              fill={ZONE_FILL[z.class] || 'rgba(255,255,255,0.08)'}
              stroke={ZONE_STROKE[z.class] || '#b1a6f6'}
              strokeWidth={1.5}
            />
            {z.polygon[0] && (
              <text
                x={worldToSvg(z.polygon[0][0], z.polygon[0][1]).cx + 4}
                y={worldToSvg(z.polygon[0][0], z.polygon[0][1]).cy + 14}
                fill="#f4f4f6"
                fontSize={11}
                fontFamily="Manrope, sans-serif"
              >
                {z.label || z.id}
              </text>
            )}
          </g>
        ))}

        {live && p.person_trail.length > 1 && (
          <polyline
            fill="none"
            stroke="#00b1ff"
            strokeWidth={2}
            opacity={0.85}
            points={p.person_trail
              .map(({ x, y }) => {
                const { cx, cy } = worldToSvg(x, y)
                return `${cx},${cy}`
              })
              .join(' ')}
          />
        )}

        {p.pose &&
          (() => {
            const { cx, cy } = worldToSvg(p.pose.x, p.pose.y)
            return (
              <g>
                <circle cx={cx} cy={cy} r={10} fill="#b1a6f6" stroke="#ffffff" strokeWidth={1.5} />
                <text x={cx + 12} y={cy + 4} fill="#b1a6f6" fontSize={11} fontFamily="Manrope, sans-serif">
                  robot
                </text>
              </g>
            )
          })()}

        {p.person_track &&
          (() => {
            const { cx, cy } = worldToSvg(p.person_track.x, p.person_track.y)
            return (
              <g>
                <circle cx={cx} cy={cy} r={12} fill="#00b1ff" stroke="#ffffff" strokeWidth={2} />
                <text x={cx + 14} y={cy + 4} fill="#ffffff" fontSize={12} fontFamily="Manrope, sans-serif">
                  person
                </text>
              </g>
            )
          })()}

        {(() => {
          const home = (p.config.patient as { home?: { x: number; y: number } } | undefined)?.home
          if (!home) return null
          const { cx, cy } = worldToSvg(home.x, home.y)
          return (
            <g>
              <rect x={cx - 4} y={cy - 4} width={8} height={8} rx={2} fill="#00ffaa" />
              <text x={cx + 8} y={cy + 4} fill="#d8d8e3" fontSize={10} fontFamily="Manrope, sans-serif">
                home
              </text>
            </g>
          )
        })()}
      </svg>
    </div>
  )
}
