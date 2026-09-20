import type { Zone } from './types'

export type PaintClass = 'safe' | 'watch' | 'exit'

export const PAINT_LABEL: Record<PaintClass, string> = {
  safe: 'Safe',
  watch: 'Watch',
  exit: "Don't go",
}

export const PAINT_FILL: Record<PaintClass, string> = {
  safe: 'rgba(22,160,107,0.30)',
  watch: 'rgba(217,154,11,0.38)',
  exit: 'rgba(229,72,77,0.34)',
}

export const PAINT_STROKE: Record<PaintClass, string> = {
  safe: '#16a06b',
  watch: '#c78a08',
  exit: '#d63b41',
}

const CLASS_CODE: Record<PaintClass, number> = { safe: 0, watch: 1, exit: 2 }
const CODE_CLASS: PaintClass[] = ['safe', 'watch', 'exit']

export function emptyGrid(cols: number, rows: number): Uint8Array {
  return new Uint8Array(cols * rows) // 0 = safe
}

export function paintCell(
  grid: Uint8Array,
  cols: number,
  rows: number,
  col: number,
  row: number,
  cls: PaintClass,
  brush = 1,
): void {
  const r0 = Math.max(0, row - Math.floor(brush / 2))
  const c0 = Math.max(0, col - Math.floor(brush / 2))
  for (let r = r0; r < Math.min(rows, r0 + brush); r++) {
    for (let c = c0; c < Math.min(cols, c0 + brush); c++) {
      grid[r * cols + c] = CLASS_CODE[cls]
    }
  }
}

/** Restore painted cells from saved zones (axis-aligned rectangles). */
export function zonesToGrid(
  zones: Zone[],
  cols: number,
  rows: number,
  widthM: number,
  heightM: number,
): Uint8Array {
  const grid = emptyGrid(cols, rows)
  for (const z of zones) {
    if (z.class === 'safe' || z.polygon.length === 0) continue
    const xs = z.polygon.map(([x]) => x)
    const ys = z.polygon.map(([, y]) => y)
    const x0 = Math.min(...xs)
    const x1 = Math.max(...xs)
    const y0 = Math.min(...ys)
    const y1 = Math.max(...ys)
    for (let r = 0; r < rows; r++) {
      const cy = ((r + 0.5) / rows) * heightM
      if (cy < y0 || cy > y1) continue
      for (let c = 0; c < cols; c++) {
        const cx = ((c + 0.5) / cols) * widthM
        if (cx >= x0 && cx <= x1) grid[r * cols + c] = CLASS_CODE[z.class]
      }
    }
  }
  return grid
}

/**
 * Turn painted cells into zones (metres). Each connected painted region becomes
 * exact axis-aligned rectangles (row runs merged vertically), so a zone covers
 * only what was painted — not the bounding box of the stroke.
 */
export function gridToZones(
  grid: Uint8Array,
  cols: number,
  rows: number,
  widthM: number,
  heightM: number,
): Zone[] {
  const cellW = widthM / cols
  const cellH = heightM / rows
  const zones: Zone[] = [
    {
      id: 'whole_safe',
      class: 'safe',
      label: 'Safe',
      kind: 'door',
      polygon: [
        [0, 0],
        [widthM, 0],
        [widthM, heightM],
        [0, heightM],
      ],
    },
  ]

  const visited = new Uint8Array(cols * rows)

  for (let i = 0; i < grid.length; i++) {
    const code = grid[i]
    if (code === 0 || visited[i]) continue
    const cls = CODE_CLASS[code]

    // flood fill one region
    const cells: number[] = []
    const stack = [i]
    visited[i] = 1
    while (stack.length) {
      const cur = stack.pop()!
      cells.push(cur)
      const c = cur % cols
      const r = Math.floor(cur / cols)
      const neighbors = [
        r > 0 ? cur - cols : -1,
        r < rows - 1 ? cur + cols : -1,
        c > 0 ? cur - 1 : -1,
        c < cols - 1 ? cur + 1 : -1,
      ]
      for (const n of neighbors) {
        if (n < 0 || visited[n] || grid[n] !== code) continue
        visited[n] = 1
        stack.push(n)
      }
    }

    const inRegion = new Set(cells)
    const minR = Math.min(...cells.map((k) => Math.floor(k / cols)))
    const maxR = Math.max(...cells.map((k) => Math.floor(k / cols)))
    const minC = Math.min(...cells.map((k) => k % cols))
    const region = `${cls}_${minC}_${minR}`

    // row runs, merged into rectangles while consecutive rows share the same span
    const rects: { c0: number; c1: number; r0: number; r1: number }[] = []
    let open = new Map<string, { c0: number; c1: number; r0: number; r1: number }>()
    for (let r = minR; r <= maxR + 1; r++) {
      const next = new Map<string, { c0: number; c1: number; r0: number; r1: number }>()
      let c = 0
      while (r <= maxR && c < cols) {
        if (!inRegion.has(r * cols + c)) {
          c++
          continue
        }
        const c0 = c
        while (c < cols && inRegion.has(r * cols + c)) c++
        const key = `${c0}-${c - 1}`
        const prev = open.get(key)
        if (prev) {
          prev.r1 = r
          next.set(key, prev)
          open.delete(key)
        } else {
          next.set(key, { c0, c1: c - 1, r0: r, r1: r })
        }
      }
      rects.push(...open.values())
      open = next
    }

    rects.forEach((rc, k) => {
      const x0 = rc.c0 * cellW
      const x1 = (rc.c1 + 1) * cellW
      const y0 = rc.r0 * cellH
      const y1 = (rc.r1 + 1) * cellH
      zones.push({
        id: rects.length > 1 ? `${region}_${k}` : region,
        region,
        class: cls,
        label: PAINT_LABEL[cls],
        kind: 'door',
        polygon: [
          [x0, y0],
          [x1, y0],
          [x1, y1],
          [x0, y1],
        ],
      })
    })
  }

  return zones
}
