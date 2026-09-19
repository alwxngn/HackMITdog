import { polygonToPoints, SVG, worldToSvg } from '../lib/frame'
import type { Zone } from '../lib/types'
import { useProjection } from '../hooks/useProjection'

const ZONE_FILL: Record<string, string> = {
  safe: 'rgba(61,122,95,0.35)',
  watch: 'rgba(184,137,61,0.35)',
  exit: 'rgba(181,74,74,0.45)',
}

export function MapView() {
  const p = useProjection()
  const live = p.live_tracking || Boolean(p.open_alert?.live_tracking)

  return (
    <div className="rounded-lg bg-[var(--panel)] p-3">
      <div className="mb-2 flex items-baseline justify-between">
        <h2 className="text-lg">Floor</h2>
        <span className="text-xs uppercase tracking-wide text-[var(--muted)]">
          {live ? 'live tracking' : 'map'} · metres
        </span>
      </div>
      <svg
        viewBox={`0 0 ${SVG.width} ${SVG.height}`}
        className="h-auto w-full max-w-full rounded border border-white/10 bg-[#0b1016]"
      >
        {/* tape boundary */}
        <rect
          x={SVG.pad}
          y={SVG.pad}
          width={SVG.width - SVG.pad * 2}
          height={SVG.height - SVG.pad * 2}
          fill="none"
          stroke="rgba(255,255,255,0.15)"
          strokeDasharray="4 4"
        />
        {p.zones.map((z: Zone) => (
          <g key={z.id}>
            <polygon
              points={polygonToPoints(z.polygon)}
              fill={ZONE_FILL[z.class] || 'rgba(255,255,255,0.1)'}
              stroke="rgba(255,255,255,0.35)"
              strokeWidth={1}
            />
            {z.polygon[0] && (
              <text
                x={worldToSvg(z.polygon[0][0], z.polygon[0][1]).cx + 4}
                y={worldToSvg(z.polygon[0][0], z.polygon[0][1]).cy + 14}
                fill="rgba(255,255,255,0.7)"
                fontSize={11}
              >
                {z.label || z.id}
              </text>
            )}
          </g>
        ))}

        {/* trail when live tracking */}
        {live && p.person_trail.length > 1 && (
          <polyline
            fill="none"
            stroke="var(--accent)"
            strokeWidth={2}
            opacity={0.7}
            points={p.person_trail
              .map(({ x, y }) => {
                const { cx, cy } = worldToSvg(x, y)
                return `${cx},${cy}`
              })
              .join(' ')}
          />
        )}

        {p.pose && (() => {
          const { cx, cy } = worldToSvg(p.pose.x, p.pose.y)
          return (
            <g>
              <circle cx={cx} cy={cy} r={10} fill="#6b8cae" stroke="#fff" strokeWidth={1.5} />
              <text x={cx + 12} y={cy + 4} fill="#9bb4cc" fontSize={11}>
                robot
              </text>
            </g>
          )
        })()}

        {p.person_track && (() => {
          const { cx, cy } = worldToSvg(p.person_track.x, p.person_track.y)
          return (
            <g>
              <circle cx={cx} cy={cy} r={12} fill="var(--accent)" stroke="#fff" strokeWidth={2} />
              <text x={cx + 14} y={cy + 4} fill="var(--ink)" fontSize={12}>
                person
              </text>
            </g>
          )
        })()}

        {/* home anchor */}
        {(() => {
          const home = (p.config.patient as { home?: { x: number; y: number } } | undefined)?.home
          if (!home) return null
          const { cx, cy } = worldToSvg(home.x, home.y)
          return (
            <g>
              <rect x={cx - 4} y={cy - 4} width={8} height={8} fill="var(--safe)" />
              <text x={cx + 8} y={cy + 4} fill="var(--muted)" fontSize={10}>
                home
              </text>
            </g>
          )
        })()}
      </svg>
    </div>
  )
}
