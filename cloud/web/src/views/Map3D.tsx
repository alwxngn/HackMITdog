import { useEffect, useRef, useState, type PointerEvent as ReactPointerEvent } from 'react'

type Point = [number, number, number, number?, number?, number?]
type ProjectedPoint = [number, number, number, number?, number?, number?]

function parsePly(text: string): Point[] {
  const lines = text.split(/\r?\n/)
  const end = lines.indexOf('end_header')
  if (end < 0) throw new Error('PLY header is missing')
  const countLine = lines.find((line) => line.startsWith('element vertex '))
  const count = Number(countLine?.split(' ')[2])
  if (!Number.isFinite(count)) throw new Error('PLY vertex count is missing')
  const points: Point[] = []
  for (const line of lines.slice(end + 1, end + 1 + count)) {
    const values = line.trim().split(/\s+/).map(Number)
    if (values.length >= 3 && values.slice(0, 3).every(Number.isFinite)) {
      points.push([values[0], values[1], values[2], values[3], values[4], values[5]])
    }
  }
  return points
}

export function Map3D({ url }: { url: string | null | undefined }) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const [points, setPoints] = useState<Point[]>([])
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [rotation, setRotation] = useState({ yaw: 0.65, pitch: -0.72 })
  const dragging = useRef(false)
  const dragStart = useRef({ x: 0, y: 0, yaw: 0.65, pitch: -0.72 })

  useEffect(() => {
    let cancelled = false
    setPoints([])
    setError('')
    if (!url) return
    setLoading(true)
    fetch(url)
      .then((response) => {
        if (!response.ok) throw new Error(`Could not load map (${response.status})`)
        return response.text()
      })
      .then((text) => {
        if (!cancelled) setPoints(parsePly(text))
      })
      .catch((reason: unknown) => {
        if (!cancelled) setError(reason instanceof Error ? reason.message : 'Could not load 3-D map')
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [url])

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas || points.length === 0) return
    const context = canvas.getContext('2d')
    if (!context) return
    const ratio = window.devicePixelRatio || 1
    const width = canvas.clientWidth
    const height = canvas.clientHeight
    canvas.width = width * ratio
    canvas.height = height * ratio
    context.setTransform(ratio, 0, 0, ratio, 0, 0)
    context.fillStyle = '#eef1f5'
    context.fillRect(0, 0, width, height)

    // Keep the artifact full resolution, but render a bounded sample so a
    // large household scan remains responsive on phones and laptops.
    const renderPoints = points.length > 45_000
      ? points.filter((_, index) => index % Math.ceil(points.length / 45_000) === 0)
      : points
    let totals: [number, number, number] = [0, 0, 0]
    let sourceMinZ = Infinity
    for (const point of renderPoints) {
      totals = [totals[0] + point[0], totals[1] + point[1], totals[2] + point[2]]
      sourceMinZ = Math.min(sourceMinZ, point[2])
    }
    const center: [number, number, number] = [totals[0] / renderPoints.length, totals[1] / renderPoints.length, totals[2] / renderPoints.length]
    const minZ = sourceMinZ
    const cosYaw = Math.cos(rotation.yaw)
    const sinYaw = Math.sin(rotation.yaw)
    const cosPitch = Math.cos(rotation.pitch)
    const sinPitch = Math.sin(rotation.pitch)
    const project = (x: number, y: number, z: number): [number, number, number] => {
      const dx = x - center[0]
      const dy = y - center[1]
      const dz = z - center[2]
      const side = dx * cosYaw - dy * sinYaw
      const depth = dx * sinYaw + dy * cosYaw
      return [side, depth * cosPitch - dz * sinPitch, depth * sinPitch + dz * cosPitch]
    }
    const rotated: ProjectedPoint[] = renderPoints.map(([x, y, z, r, g, b]) => {
      const [px, py, pz] = project(x, y, z)
      return [px, py, pz, r, g, b]
    })
    let extent = 0.1
    let rotatedMinZ = Infinity
    let rotatedMaxZ = -Infinity
    for (const [x, y, z] of rotated) {
      extent = Math.max(extent, Math.abs(x), Math.abs(y))
      rotatedMinZ = Math.min(rotatedMinZ, z)
      rotatedMaxZ = Math.max(rotatedMaxZ, z)
    }
    const scale = (Math.min(width, height) * 0.42) / extent
    const screen = (point: Point) => [width / 2 + point[0] * scale, height / 2 - point[1] * scale]

    // A subtle floor grid provides scale and makes the robot's map frame
    // legible even when the LiDAR has no camera color data.
    const gridExtent = extent * 1.25
    const floorCorners = [
      screen(project(-gridExtent, -gridExtent, minZ)),
      screen(project(gridExtent, -gridExtent, minZ)),
      screen(project(gridExtent, gridExtent, minZ)),
      screen(project(-gridExtent, gridExtent, minZ)),
    ]
    context.beginPath()
    context.moveTo(floorCorners[0][0], floorCorners[0][1])
    for (const [x, y] of floorCorners.slice(1)) context.lineTo(x, y)
    context.closePath()
    context.fillStyle = '#dfe6ef'
    context.globalAlpha = 0.72
    context.fill()
    context.globalAlpha = 1

    context.lineWidth = 1
    context.strokeStyle = '#d6dce5'
    for (let i = -5; i <= 5; i += 1) {
      const a = screen(project((i / 5) * gridExtent, -gridExtent, minZ))
      const b = screen(project((i / 5) * gridExtent, gridExtent, minZ))
      const c = screen(project(-gridExtent, (i / 5) * gridExtent, minZ))
      const d = screen(project(gridExtent, (i / 5) * gridExtent, minZ))
      context.beginPath()
      context.moveTo(a[0], a[1])
      context.lineTo(b[0], b[1])
      context.moveTo(c[0], c[1])
      context.lineTo(d[0], d[1])
      context.stroke()
    }

    for (const [x, y, z, r, g, b] of rotated) {
      const px = width / 2 + x * scale
      const py = height / 2 - y * scale
      const depth = Math.max(0.8, Math.min(2.8, 1.25 + z * 0.025))
      const heightRatio = (z - rotatedMinZ) / Math.max(0.001, rotatedMaxZ - rotatedMinZ)
      if (r !== undefined && g !== undefined && b !== undefined) {
        context.fillStyle = `rgb(${r}, ${g}, ${b})`
      } else {
        // Height shading: floor is slate blue, walls are blue, ceiling is warm.
        const red = Math.round(45 + heightRatio * 190)
        const green = Math.round(105 + heightRatio * 75)
        const blue = Math.round(210 - heightRatio * 100)
        context.fillStyle = `rgb(${red}, ${green}, ${blue})`
      }
      context.globalAlpha = Math.max(0.25, Math.min(0.92, 0.62 + z * 0.018))
      context.fillRect(px, py, depth, depth)
    }
    context.globalAlpha = 1
  }, [points, rotation])

  function dragStartHandler(event: ReactPointerEvent<HTMLCanvasElement>) {
    if (event.button !== 0) return
    dragging.current = true
    dragStart.current = { x: event.clientX, y: event.clientY, ...rotation }
    event.currentTarget.setPointerCapture(event.pointerId)
  }

  function dragMoveHandler(event: ReactPointerEvent<HTMLCanvasElement>) {
    if (!dragging.current) return
    setRotation({
      yaw: dragStart.current.yaw + (event.clientX - dragStart.current.x) * 0.01,
      pitch: Math.max(-1.45, Math.min(-0.05, dragStart.current.pitch + (event.clientY - dragStart.current.y) * 0.01)),
    })
  }

  function dragEndHandler(event: ReactPointerEvent<HTMLCanvasElement>) {
    dragging.current = false
    if (event.currentTarget.hasPointerCapture(event.pointerId)) event.currentTarget.releasePointerCapture(event.pointerId)
  }

  return (
    <div className="space-y-3">
      {!url && <p className="rounded-[12px] bg-[var(--color-panel-2)] p-4 text-[13px]">The robot has not supplied a web-accessible 3-D map yet. Run <code>map_room</code> with <code>artifact_url</code> to make the scan available here.</p>}
      {loading && <p className="text-[13px] text-[var(--color-ink-2)]">Loading 3-D scan…</p>}
      {error && <p className="rounded-[12px] bg-[#fff1f0] p-4 text-[13px] text-[#a22]">{error}</p>}
      <div className="relative">
        <canvas
          ref={canvasRef}
          onPointerDown={dragStartHandler}
          onPointerMove={dragMoveHandler}
          onPointerUp={dragEndHandler}
          onPointerCancel={dragEndHandler}
          className="h-[420px] w-full cursor-grab touch-none rounded-[14px] bg-[#eef1f5] active:cursor-grabbing"
          aria-label="3-D robot map. Click and drag to rotate."
        />
        <button type="button" className="absolute right-3 top-3 rounded-full bg-white/85 px-3 py-1.5 text-[12px] shadow" onClick={() => setRotation({ yaw: 0.65, pitch: -0.72 })}>Reset view</button>
      </div>
      {points.length > 0 && <p className="text-[12px] text-[var(--color-ink-2)]">{points.length.toLocaleString()} points · drag to rotate</p>}
    </div>
  )
}
