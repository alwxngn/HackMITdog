/**
 * Hard-coded demo home (2 × 2 m, matches DEMO_MAP / DEFAULT_CONFIG zones).
 * Everything is in world metres (origin SW, y up). `z` / `z0` are heights in SVG px.
 * In live mode the robot's own map_ready replaces this.
 */

export const DEMO_HOME_MAP_ID = 'demo_home_v1'

export type Tone = 'wall' | 'wood' | 'soft' | 'water' | 'plant' | 'ink'

export interface Block {
  x: number
  y: number
  w: number
  d: number
  /** height of the block in px */
  z: number
  /** elevation of the block's base in px (things resting on other things) */
  z0?: number
  /** corner radius in metres */
  r?: number
  round?: boolean
  tone: Tone
  /** drawn right after the parent, so they sit on top of it */
  kids?: Block[]
}

export interface Rug {
  x: number
  y: number
  w: number
  d: number
  r?: number
  fill: string
}

export interface Door {
  hx: number
  hy: number
  len: number
  /** degrees, world space (0 = +x, 90 = +y) */
  closed: number
  open: number
}

export const TONES: Record<Tone, { top: string; front: string }> = {
  wall: { top: '#ffffff', front: '#2b5f60' },
  wood: { top: '#d9e8e4', front: '#9fc6bf' },
  soft: { top: '#f7f3ea', front: '#ded6c4' },
  water: { top: '#d3e8ef', front: '#9cc3cf' },
  plant: { top: '#7ccaa6', front: '#3f8f73' },
  ink: { top: '#4c7f80', front: '#2b5f60' },
}

const T = 0.055
const WALL_Z = 14

const hWall = (y: number, x0: number, x1: number, kids?: Block[]): Block => ({
  x: x0 - T / 2,
  y: y - T / 2,
  w: x1 - x0 + T,
  d: T,
  z: WALL_Z,
  tone: 'wall',
  kids,
})

const vWall = (x: number, y0: number, y1: number, kids?: Block[]): Block => ({
  x: x - T / 2,
  y: y0 - T / 2,
  w: T,
  d: y1 - y0 + T,
  z: WALL_Z,
  tone: 'wall',
  kids,
})

/** Flat glass inlay on top of a wall. */
const windowH = (x: number, y: number, w: number): Block => ({
  x,
  y: y - 0.015,
  w,
  d: 0.03,
  z: 0,
  z0: WALL_Z,
  tone: 'water',
})
const windowV = (x: number, y: number, d: number): Block => ({
  x: x - 0.015,
  y,
  w: 0.03,
  d,
  z: 0,
  z0: WALL_Z,
  tone: 'water',
})

export const DEMO_WALLS: Block[] = [
  hWall(0, 0, 2),
  hWall(2, 0, 2, [windowH(0.3, 2, 0.45)]),
  vWall(0, 0, 2, [windowV(0, 0.5, 0.42), windowV(0, 1.45, 0.35)]),
  vWall(2, 0.4, 2, [windowV(2, 1.3, 0.4)]),
  vWall(2, 0, 0.1),
  // bedroom | hall (door gap 0.5 – 0.85)
  vWall(1, 0, 0.5),
  vWall(1, 0.85, 1.45),
  // bath | living (door gap 1.45 – 1.7)
  vWall(1, 1.7, 2),
  hWall(1.2, 0, 1),
]

export const DEMO_FURNITURE: Block[] = [
  // — bedroom —
  {
    x: 0.2, y: 0.42, w: 0.5, d: 0.72, z: 6, r: 0.02, tone: 'wood',
    kids: [
      {
        x: 0.22, y: 0.42, w: 0.46, d: 0.62, z: 5, z0: 6, r: 0.02, tone: 'soft',
        kids: [
          { x: 0.245, y: 0.93, w: 0.18, d: 0.09, z: 3, z0: 11, r: 0.03, tone: 'wall' },
          { x: 0.475, y: 0.93, w: 0.18, d: 0.09, z: 3, z0: 11, r: 0.03, tone: 'wall' },
          { x: 0.22, y: 0.42, w: 0.46, d: 0.36, z: 1.5, z0: 11, r: 0.015, tone: 'water' },
        ],
      },
    ],
  },
  { x: 0.08, y: 1.03, w: 0.1, d: 0.1, z: 6, r: 0.01, tone: 'wood' },
  { x: 0.72, y: 1.03, w: 0.1, d: 0.1, z: 6, r: 0.01, tone: 'wood' },
  { x: 0.55, y: 0.06, w: 0.38, d: 0.14, z: 9, r: 0.01, tone: 'wood' },
  { x: 0.06, y: 0.08, w: 0.12, d: 0.12, z: 10, round: true, tone: 'plant' },

  // — bathroom —
  {
    x: 0.05, y: 1.35, w: 0.26, d: 0.6, z: 8, r: 0.04, tone: 'wall',
    kids: [{ x: 0.07, y: 1.38, w: 0.22, d: 0.54, z: 0, z0: 8, r: 0.035, tone: 'water' }],
  },
  { x: 0.44, y: 1.88, w: 0.14, d: 0.07, z: 9, r: 0.01, tone: 'wall' },
  { x: 0.45, y: 1.75, w: 0.12, d: 0.13, z: 6, round: true, tone: 'wall' },
  {
    x: 0.62, y: 1.83, w: 0.32, d: 0.14, z: 9, r: 0.01, tone: 'wood',
    kids: [{ x: 0.72, y: 1.855, w: 0.12, d: 0.09, z: 0, z0: 9, round: true, tone: 'water' }],
  },

  // — kitchen / living —
  { x: 1.05, y: 1.8, w: 0.17, d: 0.17, z: 13, r: 0.01, tone: 'wood' },
  {
    x: 1.25, y: 1.85, w: 0.72, d: 0.13, z: 8, r: 0.01, tone: 'wood',
    kids: [
      { x: 1.5, y: 1.875, w: 0.14, d: 0.08, z: 0, z0: 8, r: 0.01, tone: 'water' },
      { x: 1.75, y: 1.87, w: 0.12, d: 0.09, z: 0, z0: 8, r: 0.01, tone: 'ink' },
    ],
  },
  { x: 1.85, y: 1.4, w: 0.12, d: 0.45, z: 8, r: 0.01, tone: 'wood' },
  { x: 1.3, y: 1.6, w: 0.4, d: 0.13, z: 8, r: 0.01, tone: 'soft' },
  { x: 1.38, y: 1.5, w: 0.07, d: 0.07, z: 5, round: true, tone: 'wood' },
  { x: 1.55, y: 1.5, w: 0.07, d: 0.07, z: 5, round: true, tone: 'wood' },
  {
    x: 1.08, y: 1.08, w: 0.55, d: 0.2, z: 5, r: 0.03, tone: 'wood',
    kids: [
      { x: 1.08, y: 1.08, w: 0.55, d: 0.06, z: 5, z0: 5, r: 0.02, tone: 'wood' },
      { x: 1.11, y: 1.15, w: 0.49, d: 0.12, z: 2, z0: 5, r: 0.015, tone: 'soft' },
    ],
  },
  { x: 1.25, y: 1.3, w: 0.22, d: 0.14, z: 4, round: true, tone: 'wood' },
  { x: 1.7, y: 1.1, w: 0.1, d: 0.1, z: 10, round: true, tone: 'plant' },

  // — hall —
  { x: 1.1, y: 0.12, w: 0.2, d: 0.2, z: 4, round: true, tone: 'soft',
    kids: [{ x: 1.13, y: 0.15, w: 0.14, d: 0.14, z: 0, z0: 4, round: true, tone: 'wood' }],
  },
  { x: 1.85, y: 0.5, w: 0.11, d: 0.3, z: 6, r: 0.01, tone: 'wood' },
]

export const DEMO_RUGS: Rug[] = [
  { x: 0.1, y: 0.25, w: 0.72, d: 0.72, r: 0.03, fill: '#e2efec' },
  { x: 0.4, y: 1.42, w: 0.32, d: 0.16, r: 0.02, fill: '#d5e7e4' },
  { x: 1.05, y: 1.2, w: 0.57, d: 0.28, r: 0.03, fill: '#e2efec' },
  { x: 1.3, y: 0.4, w: 0.35, d: 0.45, r: 0.03, fill: '#e2efec' },
  { x: 1.78, y: 0.12, w: 0.2, d: 0.26, r: 0.02, fill: '#c9e0dc' },
]

export const DEMO_DOORS: Door[] = [
  { hx: 1, hy: 0.52, len: 0.3, closed: 90, open: 0 },
  { hx: 1, hy: 1.47, len: 0.22, closed: 90, open: 180 },
  { hx: 2, hy: 0.38, len: 0.26, closed: 270, open: 180 },
]

/** Bathroom floor gets tile instead of planks. */
export const DEMO_TILE_ROOM = { x: 0, y: 1.2, w: 1, d: 0.8 }

/** One-tap zones for the demo home, in metres [x0, y0, x1, y1]. Matches DEFAULT_CONFIG. */
export const DEMO_PRESETS: { label: string; cls: 'watch' | 'exit'; rect: [number, number, number, number] }[] = [
  { label: 'Block front door', cls: 'exit', rect: [1.6, 0, 2, 0.5] },
  { label: 'Watch hallway', cls: 'watch', rect: [1, 0.3, 1.8, 0.9] },
]

/** Where the dog sleeps / docks. */
export const DEMO_HOME_PIN = { x: 1.2, y: 0.22 }
