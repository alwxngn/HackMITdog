/** Metres → SVG. Bounds come from map_ready (or demo 2×2). */

export type MapBounds = { width: number; height: number }

export const DEFAULT_BOUNDS: MapBounds = { width: 2.0, height: 2.0 }
export const SVG = { width: 480, height: 480, pad: 24 }

/** @deprecated prefer passing bounds — kept for call sites during migration */
export const MAP_METRES = DEFAULT_BOUNDS

export function worldToSvg(
  x: number,
  y: number,
  bounds: MapBounds = DEFAULT_BOUNDS,
): { cx: number; cy: number } {
  const { width, height, pad } = SVG
  const usableW = width - pad * 2
  const usableH = height - pad * 2
  const cx = pad + (x / bounds.width) * usableW
  const cy = pad + (1 - y / bounds.height) * usableH
  return { cx, cy }
}

export function svgToWorld(
  cx: number,
  cy: number,
  bounds: MapBounds = DEFAULT_BOUNDS,
): { x: number; y: number } {
  const { width, height, pad } = SVG
  const usableW = width - pad * 2
  const usableH = height - pad * 2
  const x = ((cx - pad) / usableW) * bounds.width
  const y = (1 - (cy - pad) / usableH) * bounds.height
  return { x, y }
}

export function polygonToPoints(
  poly: [number, number][],
  bounds: MapBounds = DEFAULT_BOUNDS,
): string {
  return poly
    .map(([x, y]) => {
      const { cx, cy } = worldToSvg(x, y, bounds)
      return `${cx},${cy}`
    })
    .join(' ')
}
