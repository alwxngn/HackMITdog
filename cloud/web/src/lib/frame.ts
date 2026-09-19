/** Metres → SVG pixels. Origin = SW corner of taped area (docs/16-e3-portal.md). */

export const MAP_METRES = { width: 2.0, height: 2.0 }
export const SVG = { width: 480, height: 480, pad: 24 }

export function worldToSvg(x: number, y: number): { cx: number; cy: number } {
  const { width, height, pad } = { width: SVG.width, height: SVG.height, pad: SVG.pad }
  const usableW = width - pad * 2
  const usableH = height - pad * 2
  // y increases north; SVG y increases down — flip
  const cx = pad + (x / MAP_METRES.width) * usableW
  const cy = pad + (1 - y / MAP_METRES.height) * usableH
  return { cx, cy }
}

export function svgToWorld(cx: number, cy: number): { x: number; y: number } {
  const { width, height, pad } = SVG
  const usableW = width - pad * 2
  const usableH = height - pad * 2
  const x = ((cx - pad) / usableW) * MAP_METRES.width
  const y = (1 - (cy - pad) / usableH) * MAP_METRES.height
  return { x, y }
}

export function polygonToPoints(poly: [number, number][]): string {
  return poly
    .map(([x, y]) => {
      const { cx, cy } = worldToSvg(x, y)
      return `${cx},${cy}`
    })
    .join(' ')
}
