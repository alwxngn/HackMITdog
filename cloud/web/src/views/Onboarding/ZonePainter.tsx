import { useCallback, useEffect, useRef, useState } from 'react'
import type { MapReadyPayload } from '../../lib/demoFloorplan'
import { SVG, polygonToPoints, svgToWorld, worldToSvg, type MapBounds } from '../../lib/frame'
import {
  PAINT_FILL,
  PAINT_LABEL,
  PAINT_STROKE,
  emptyGrid,
  gridToZones,
  paintCell,
  type PaintClass,
} from '../../lib/zonePaint'
import type { Zone } from '../../lib/types'

const COLS = 40
const ROWS = 40

type Tool = PaintClass | 'home'

interface Props {
  map: MapReadyPayload
  home: { x: number; y: number }
  onHomeChange: (h: { x: number; y: number }) => void
  onZonesChange: (zones: Zone[]) => void
}

export function ZonePainter({ map, home, onHomeChange, onZonesChange }: Props) {
  const bounds: MapBounds = { width: map.width_m, height: map.height_m }
  const [tool, setTool] = useState<Tool>('exit')
  const [grid, setGrid] = useState(() => emptyGrid(COLS, ROWS))
  const painting = useRef(false)
  const gridRef = useRef(grid)
  gridRef.current = grid

  const emitZones = useCallback(
    (g: Uint8Array) => {
      onZonesChange(gridToZones(g, COLS, ROWS, map.width_m, map.height_m))
    },
    [map.height_m, map.width_m, onZonesChange],
  )

  useEffect(() => {
    emitZones(grid)
  }, []) // initial safe whole-map

  function pointerToCell(e: React.PointerEvent<SVGSVGElement>) {
    const rect = e.currentTarget.getBoundingClientRect()
    const cx = ((e.clientX - rect.left) / rect.width) * SVG.width
    const cy = ((e.clientY - rect.top) / rect.height) * SVG.height
    const { x, y } = svgToWorld(cx, cy, bounds)
    const col = Math.min(COLS - 1, Math.max(0, Math.floor((x / bounds.width) * COLS)))
    const row = Math.min(ROWS - 1, Math.max(0, Math.floor((y / bounds.height) * ROWS)))
    return { col, row, x, y }
  }

  function applyPaint(e: React.PointerEvent<SVGSVGElement>) {
    const { col, row, x, y } = pointerToCell(e)
    if (tool === 'home') {
      onHomeChange({
        x: Math.round(x * 100) / 100,
        y: Math.round(y * 100) / 100,
      })
      return
    }
    const next = new Uint8Array(gridRef.current)
    paintCell(next, COLS, ROWS, col, row, tool, 2)
    gridRef.current = next
    setGrid(next)
    emitZones(next)
  }

  const cellW = (SVG.width - SVG.pad * 2) / COLS
  const cellH = (SVG.height - SVG.pad * 2) / ROWS

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap gap-2">
        {(['safe', 'watch', 'exit'] as PaintClass[]).map((c) => (
          <button
            key={c}
            type="button"
            className={`pill min-h-10 px-4 ${tool === c ? 'bg-[var(--color-forest-ink)] text-[var(--color-cream-paper)]' : ''}`}
            onClick={() => setTool(c)}
          >
            <span
              className="mr-2 inline-block h-2.5 w-2.5 rounded-full"
              style={{ background: PAINT_STROKE[c] }}
            />
            {PAINT_LABEL[c]}
          </button>
        ))}
        <button
          type="button"
          className={`pill min-h-10 px-4 ${tool === 'home' ? 'bg-[var(--color-forest-ink)] text-[var(--color-cream-paper)]' : ''}`}
          onClick={() => setTool('home')}
        >
          Place home
        </button>
      </div>
      <p className="text-[13px] text-[var(--color-charcoal)]">
        Drag to paint. Whole home starts Safe (green). Watch = caution, Don&apos;t go = exit risk.
        {tool === 'home' ? ' Tap to drop the home pin.' : ''}
      </p>
      <svg
        viewBox={`0 0 ${SVG.width} ${SVG.height}`}
        className="w-full touch-none cursor-crosshair rounded-[14px] bg-[var(--color-cream-paper)]"
        onPointerDown={(e) => {
          painting.current = true
          e.currentTarget.setPointerCapture(e.pointerId)
          applyPaint(e)
        }}
        onPointerMove={(e) => {
          if (!painting.current) return
          applyPaint(e)
        }}
        onPointerUp={() => {
          painting.current = false
        }}
        onPointerCancel={() => {
          painting.current = false
        }}
      >
        {/* base safe wash */}
        <rect
          x={SVG.pad}
          y={SVG.pad}
          width={SVG.width - SVG.pad * 2}
          height={SVG.height - SVG.pad * 2}
          fill={PAINT_FILL.safe}
          opacity={0.45}
        />
        {/* painted watch / don't-go cells */}
        {Array.from(grid).map((code, i) => {
          if (code === 0) return null
          const col = i % COLS
          const row = Math.floor(i / COLS)
          const cls = code === 1 ? 'watch' : 'exit'
          return (
            <rect
              key={i}
              x={SVG.pad + col * cellW}
              y={SVG.pad + (ROWS - 1 - row) * cellH}
              width={cellW + 0.5}
              height={cellH + 0.5}
              fill={PAINT_FILL[cls]}
            />
          )
        })}
        {/* room outlines from scan */}
        {map.rooms.map((r) => (
          <polygon
            key={r.id}
            points={polygonToPoints(r.polygon, bounds)}
            fill="none"
            stroke="#0f3e17"
            strokeWidth={1.5}
            strokeDasharray="4 3"
          />
        ))}
        <polygon
          points={polygonToPoints(map.outline, bounds)}
          fill="none"
          stroke="#0f3e17"
          strokeWidth={2}
        />
        {/* home pin */}
        {(() => {
          const { cx, cy } = worldToSvg(home.x, home.y, bounds)
          return (
            <g>
              <circle cx={cx} cy={cy} r={10} fill="#0f3e17" stroke="#fffefc" strokeWidth={2} />
              <text
                x={cx}
                y={cy - 14}
                textAnchor="middle"
                fill="#0f3e17"
                fontSize={11}
                fontFamily="Inter, sans-serif"
              >
                home
              </text>
            </g>
          )
        })()}
      </svg>
    </div>
  )
}
