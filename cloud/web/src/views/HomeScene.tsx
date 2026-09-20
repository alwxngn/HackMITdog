import { SVG, worldToSvg, type MapBounds } from '../lib/frame'
import {
  DEMO_DOORS,
  DEMO_FURNITURE,
  DEMO_RUGS,
  DEMO_TILE_ROOM,
  DEMO_WALLS,
  TONES,
  type Block,
} from '../lib/demoHome'

/**
 * Dollhouse view: camera is above and slightly south, so anything with height is
 * shifted up the screen by its height and shows its south-facing side. Each block
 * is a front face (body) plus a lighter top face.
 */

const pxPerMetre = (bounds: MapBounds) => (SVG.width - SVG.pad * 2) / bounds.width

function rectOf(b: Block, bounds: MapBounds) {
  const sw = worldToSvg(b.x, b.y, bounds)
  const ne = worldToSvg(b.x + b.w, b.y + b.d, bounds)
  return { x: sw.cx, y: ne.cy, w: ne.cx - sw.cx, d: sw.cy - ne.cy }
}

function flatten(blocks: Block[]): Block[] {
  return blocks.flatMap((b) => [b, ...flatten(b.kids ?? [])])
}

/** Far (north) things first so nearer things overlap them. Kids stay right after their parent. */
function paintOrder(blocks: Block[]): Block[] {
  return [...blocks].sort((a, b) => b.y - a.y).flatMap((b) => [b, ...paintOrder(b.kids ?? [])])
}

function BlockShape({ b, bounds }: { b: Block; bounds: MapBounds }) {
  const tone = TONES[b.tone]
  const { x, y, w, d } = rectOf(b, bounds)
  const rx = (b.r ?? 0) * pxPerMetre(bounds)
  const lift = b.z0 ?? 0
  const top = y - lift - b.z
  const stroke = 'rgba(21,58,59,0.5)'

  if (b.round) {
    const cx = x + w / 2
    const baseY = y + d / 2 - lift
    const topY = baseY - b.z
    return (
      <g>
        <ellipse cx={cx} cy={baseY} rx={w / 2} ry={d / 2} fill={tone.front} stroke={stroke} strokeWidth={1} />
        {b.z > 0 && <rect x={x} y={topY} width={w} height={b.z} fill={tone.front} />}
        {b.z > 0 && (
          <path
            d={`M${x} ${topY}V${baseY}M${x + w} ${topY}V${baseY}`}
            stroke={stroke}
            strokeWidth={1}
          />
        )}
        <ellipse cx={cx} cy={topY} rx={w / 2} ry={d / 2} fill={tone.top} stroke={stroke} strokeWidth={1} />
      </g>
    )
  }

  return (
    <g>
      {b.z > 0 && (
        <rect
          x={x}
          y={top}
          width={w}
          height={d + b.z}
          rx={rx}
          fill={tone.front}
          stroke={stroke}
          strokeWidth={1}
        />
      )}
      <rect
        x={x}
        y={top}
        width={w}
        height={d}
        rx={rx}
        fill={tone.top}
        stroke={b.z > 0 ? undefined : stroke}
        strokeWidth={1}
      />
    </g>
  )
}

function ShadowShape({ b, bounds }: { b: Block; bounds: MapBounds }) {
  const { x, y, w, d } = rectOf(b, bounds)
  const dx = b.z * 0.4 + 1
  const dy = b.z * 0.5 + 2
  const rx = (b.r ?? 0) * pxPerMetre(bounds)
  if (b.round) {
    return <ellipse cx={x + w / 2 + dx} cy={y + d / 2 + dy} rx={w / 2} ry={d / 2} />
  }
  return <rect x={x + dx} y={y + dy} width={w} height={d} rx={rx} />
}

/** Floor, rugs and door swings — sits under the zone overlay. */
export function HomeFloor({ bounds }: { bounds: MapBounds }) {
  const floor = rectOf({ x: 0, y: 0, w: bounds.width, d: bounds.height, z: 0, tone: 'wall' }, bounds)
  const tile = rectOf({ ...DEMO_TILE_ROOM, z: 0, tone: 'wall' }, bounds)
  const k = pxPerMetre(bounds)

  return (
    <g>
      <defs>
        <pattern id="home-plank" width="96" height="24" patternUnits="userSpaceOnUse">
          <rect width="30" height="12" fill="#f8efe3" />
          <rect x="30" width="66" height="12" fill="#fbf4ea" />
          <rect y="12" width="78" height="12" fill="#f9f1e6" />
          <rect x="78" y="12" width="18" height="12" fill="#f4e9dc" />
          <path
            d="M0 12H96M0 24H96M30 0V12M78 12V24"
            stroke="rgba(21,58,59,0.09)"
            strokeWidth="0.8"
            fill="none"
          />
        </pattern>
        <pattern id="home-tile" width="16" height="16" patternUnits="userSpaceOnUse">
          <rect width="16" height="16" fill="#e3eef1" />
          <path d="M0 0H16M0 0V16" stroke="rgba(21,58,59,0.1)" strokeWidth="0.8" fill="none" />
        </pattern>
        <filter id="home-blur" x="-10%" y="-10%" width="120%" height="120%">
          <feGaussianBlur stdDeviation="2.2" />
        </filter>
      </defs>

      <rect x={floor.x} y={floor.y} width={floor.w} height={floor.d} fill="url(#home-plank)" />
      <rect x={tile.x} y={tile.y} width={tile.w} height={tile.d} fill="url(#home-tile)" />

      {DEMO_RUGS.map((r, i) => {
        const p = rectOf({ ...r, z: 0, tone: 'wall' }, bounds)
        return (
          <g key={i}>
            <rect x={p.x} y={p.y} width={p.w} height={p.d} rx={(r.r ?? 0) * k} fill={r.fill} />
            <rect
              x={p.x + 3}
              y={p.y + 3}
              width={p.w - 6}
              height={p.d - 6}
              rx={Math.max(0, (r.r ?? 0) * k - 2)}
              fill="none"
              stroke="rgba(21,58,59,0.2)"
              strokeWidth={0.8}
              strokeDasharray="3 2"
            />
          </g>
        )
      })}

      {DEMO_DOORS.map((dr, i) => {
        const rad = (deg: number) => (deg * Math.PI) / 180
        const hinge = worldToSvg(dr.hx, dr.hy, bounds)
        const at = (deg: number) =>
          worldToSvg(dr.hx + dr.len * Math.cos(rad(deg)), dr.hy + dr.len * Math.sin(rad(deg)), bounds)
        const open = at(dr.open)
        const closed = at(dr.closed)
        const sweep = dr.open - dr.closed < 0 ? 1 : 0
        return (
          <g key={i}>
            <path
              d={`M${closed.cx} ${closed.cy}A${dr.len * k} ${dr.len * k} 0 0 ${sweep} ${open.cx} ${open.cy}`}
              fill="none"
              stroke="rgba(21,58,59,0.35)"
              strokeWidth={0.8}
              strokeDasharray="2 2"
            />
            <line x1={hinge.cx} y1={hinge.cy} x2={open.cx} y2={open.cy} stroke="#153a3b" strokeWidth={5} strokeLinecap="round" />
            <line x1={hinge.cx} y1={hinge.cy} x2={open.cx} y2={open.cy} stroke="#ffffff" strokeWidth={2.6} strokeLinecap="round" />
          </g>
        )
      })}
    </g>
  )
}

const SHADOWED = flatten([...DEMO_WALLS, ...DEMO_FURNITURE]).filter((b) => !b.z0 && b.z > 0)
const DRAW_ORDER = paintOrder([...DEMO_WALLS, ...DEMO_FURNITURE])

/** Walls + furniture silhouettes with cast shadows — sits above the zone overlay. */
export function HomeStructures({ bounds }: { bounds: MapBounds }) {
  return (
    <g>
      <g filter="url(#home-blur)" fill="rgba(21,58,59,0.22)">
        {SHADOWED.map((b, i) => (
          <ShadowShape key={i} b={b} bounds={bounds} />
        ))}
      </g>
      {DRAW_ORDER.map((b, i) => (
        <BlockShape key={i} b={b} bounds={bounds} />
      ))}
    </g>
  )
}
