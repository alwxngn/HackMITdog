import { useCallback, useEffect, useRef, useState } from 'react'
import type { MapReadyPayload } from '../../lib/demoFloorplan'
import { DEMO_HOME_MAP_ID, DEMO_PRESETS } from '../../lib/demoHome'
import { SVG, polygonToPoints, svgToWorld, worldToSvg, type MapBounds } from '../../lib/frame'
import {
  PAINT_FILL,
  PAINT_LABEL,
  PAINT_STROKE,
  emptyGrid,
  gridToZones,
  paintCell,
  zonesToGrid,
  type PaintClass,
} from '../../lib/zonePaint'
import type { Zone } from '../../lib/types'
import { HomeFloor, HomeStructures } from '../HomeScene'

const COLS = 40
const ROWS = 40
const BRUSHES = [
  { label: 'S', size: 2 },
  { label: 'M', size: 4 },
  { label: 'L', size: 8 },
]

type Tool = PaintClass | 'home'

interface Props {
  map: MapReadyPayload
  home: { x: number; y: number }
  /** zones already saved, so re-editing starts from what's there */
  initialZones?: Zone[]
  onHomeChange: (h: { x: number; y: number }) => void
  onZonesChange: (zones: Zone[]) => void
}

export function ZonePainter({ map, home, initialZones, onHomeChange, onZonesChange }: Props) {
  const bounds: MapBounds = { width: map.width_m, height: map.height_m }
  const showHome = map.map_id === DEMO_HOME_MAP_ID
  const [tool, setTool] = useState<Tool>('exit')
  const [brush, setBrush] = useState(4)
  const [grid, setGrid] = useState(() =>
    initialZones?.length
      ? zonesToGrid(initialZones, COLS, ROWS, map.width_m, map.height_m)
      : emptyGrid(COLS, ROWS),
  )
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
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []) // publish the starting zones once

  function commit(next: Uint8Array) {
    gridRef.current = next
    setGrid(next)
    emitZones(next)
  }

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
    paintCell(next, COLS, ROWS, col, row, tool, brush)
    commit(next)
  }

  function applyPreset(cls: 'watch' | 'exit', [x0, y0, x1, y1]: [number, number, number, number]) {
    const next = new Uint8Array(gridRef.current)
    for (let r = 0; r < ROWS; r++) {
      const cy = ((r + 0.5) / ROWS) * bounds.height
      if (cy < y0 || cy > y1) continue
      for (let c = 0; c < COLS; c++) {
        const cx = ((c + 0.5) / COLS) * bounds.width
        if (cx >= x0 && cx <= x1) next[r * COLS + c] = cls === 'watch' ? 1 : 2
      }
    }
    commit(next)
  }

  const cellW = (SVG.width - SVG.pad * 2) / COLS
  const cellH = (SVG.height - SVG.pad * 2) / ROWS

  const on = 'bg-[var(--color-ink)] !text-[var(--color-surface)]'

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap gap-2">
        {(['exit', 'watch', 'safe'] as PaintClass[]).map((c) => (
          <button
            key={c}
            type="button"
            className={`pill min-h-10 cursor-pointer px-4 shadow-[var(--shadow-card)] ${tool === c ? on : ''}`}
            onClick={() => setTool(c)}
          >
            <span
              className="mr-2 inline-block h-2.5 w-2.5 rounded-full"
              style={{ background: PAINT_STROKE[c] }}
            />
            {c === 'safe' ? 'Erase (Safe)' : PAINT_LABEL[c]}
          </button>
        ))}
        <button
          type="button"
          className={`pill min-h-10 cursor-pointer px-4 shadow-[var(--shadow-card)] ${tool === 'home' ? on : ''}`}
          onClick={() => setTool('home')}
        >
          Place home
        </button>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        {showHome &&
          DEMO_PRESETS.map((pr) => (
            <button
              key={pr.label}
              type="button"
              className="btn-ghost !min-h-9 !px-3 !py-1 !text-[13px]"
              onClick={() => applyPreset(pr.cls, pr.rect)}
            >
              <span
                className="inline-block h-2 w-2 rounded-full"
                style={{ background: PAINT_STROKE[pr.cls] }}
              />
              {pr.label}
            </button>
          ))}
        <button
          type="button"
          className="btn-ghost !min-h-9 !px-3 !py-1 !text-[13px]"
          onClick={() => commit(emptyGrid(COLS, ROWS))}
        >
          Clear all
        </button>
        <span className="ml-auto inline-flex items-center gap-1 text-[12px]">
          Brush
          {BRUSHES.map((b) => (
            <button
              key={b.label}
              type="button"
              aria-label={`Brush ${b.label}`}
              className={`h-8 w-8 cursor-pointer rounded-full text-[12px] font-medium ${
                brush === b.size
                  ? 'bg-[var(--color-ink)] text-[var(--color-surface)]'
                  : 'bg-[var(--color-panel)] text-[var(--color-ink)]'
              }`}
              onClick={() => setBrush(b.size)}
            >
              {b.label}
            </button>
          ))}
        </span>
      </div>

      <p className="text-[13px] text-[var(--color-ink-2)]">
        Drag on the floor plan to paint. Everything starts Safe. Paint{' '}
        <strong className="font-medium text-[var(--color-ink)]">Danger</strong> across a door
        to block it off, or <strong className="font-medium text-[var(--color-ink)]">Warning</strong> for
        caution areas.
        {tool === 'home' ? ' Tap to drop the home pin.' : ''}
      </p>

      <svg
        viewBox={`0 0 ${SVG.width} ${SVG.height}`}
        className="mx-auto w-full max-w-[560px] touch-none cursor-crosshair rounded-[14px] bg-[var(--color-surface)] ring-1 ring-[var(--color-line)]"
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
        {showHome && <HomeFloor bounds={bounds} />}
        {/* base safe wash */}
        <rect
          x={SVG.pad}
          y={SVG.pad}
          width={SVG.width - SVG.pad * 2}
          height={SVG.height - SVG.pad * 2}
          fill={PAINT_FILL.safe}
          opacity={showHome ? 0.35 : 0.45}
        />
        {/* painted warning / danger cells */}
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
        {showHome ? (
          <HomeStructures bounds={bounds} />
        ) : (
          <>
            {map.rooms.map((r) => (
              <polygon
                key={r.id}
                points={polygonToPoints(r.polygon, bounds)}
                fill="none"
                stroke="#0e1116"
                strokeWidth={1.5}
                strokeDasharray="4 3"
              />
            ))}
            <polygon
              points={polygonToPoints(map.outline, bounds)}
              fill="none"
              stroke="#0e1116"
              strokeWidth={2}
            />
          </>
        )}
        {/* home pin */}
        {(() => {
          const { cx, cy } = worldToSvg(home.x, home.y, bounds)
          return (
            <g pointerEvents="none">
              <circle cx={cx} cy={cy} r={8} fill="#0e1116" stroke="#ffffff" strokeWidth={2} />
              <text
                x={cx + 12}
                y={cy + 4}
                fill="#0e1116"
                fontSize={10}
                fontWeight={600}
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
