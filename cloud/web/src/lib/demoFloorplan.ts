/** Demo / table floorplan — same shape as E2 map_ready payload. */

export interface MapReadyPayload {
  request_id: string
  map_id: string
  origin: { x: number; y: number }
  width_m: number
  height_m: number
  outline: [number, number][]
  rooms: { id: string; polygon: [number, number][] }[]
}

export const DEMO_MAP: MapReadyPayload = {
  request_id: 'ms_demo',
  map_id: 'demo_home_v1',
  origin: { x: 0, y: 0 },
  width_m: 2,
  height_m: 2,
  outline: [
    [0, 0],
    [2, 0],
    [2, 2],
    [0, 2],
  ],
  rooms: [
    { id: 'bedroom', polygon: [[0, 0], [1, 0], [1, 1.2], [0, 1.2]] },
    { id: 'hallway', polygon: [[1, 0.3], [1.8, 0.3], [1.8, 1], [1, 1]] },
    { id: 'front_door', polygon: [[1.6, 0], [2, 0], [2, 0.5], [1.6, 0.5]] },
  ],
}
