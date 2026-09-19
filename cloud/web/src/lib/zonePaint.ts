import type { Zone } from './types'

export type PaintClass = 'safe' | 'watch' | 'exit'

export const PAINT_LABEL: Record<PaintClass, string> = {
  safe: 'Safe',
  watch: 'Watch',
  exit: "Don't go",
}

export const PAINT_FILL: Record<PaintClass, string> = {
  safe: 'rgba(177,219,184,0.7)',
  watch: 'rgba(182,206,213,0.9)',
  exit: 'rgba(15,62,23,0.18)',
}

export const PAINT_STROKE: Record<PaintClass, string> = {
  safe: '#0f3e17',
  watch: '#0f3e17',
  exit: '#0c2f10',
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

/** Merge contiguous same-class cells into axis-aligned rectangle polygons (metres). */
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
    // flood fill bounding box
    const stack = [i]
    visited[i] = 1
    let minC = i % cols
    let maxC = minC
    let minR = Math.floor(i / cols)
    let maxR = minR
    while (stack.length) {
      const cur = stack.pop()!
      const c = cur % cols
      const r = Math.floor(cur / cols)
      minC = Math.min(minC, c)
      maxC = Math.max(maxC, c)
      minR = Math.min(minR, r)
      maxR = Math.max(maxR, r)
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
    const x0 = minC * cellW
    const x1 = (maxC + 1) * cellW
    const y0 = minR * cellH
    const y1 = (maxR + 1) * cellH
    zones.push({
      id: `${cls}_${minC}_${minR}`,
      class: cls,
      label: PAINT_LABEL[cls],
      kind: cls === 'exit' ? 'door' : 'door',
      polygon: [
        [x0, y0],
        [x1, y0],
        [x1, y1],
        [x0, y1],
      ],
    })
  }

  return zones
}
