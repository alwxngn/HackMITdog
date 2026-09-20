import { useState } from 'react'
import { useProjection } from '../hooks/useProjection'

const M_PER_DEG = 111_320
const W = 480
const H = 360
const PAD = 40

type Pt = { e: number; n: number }

/** Metres east / north of a reference point. */
function offset(lat: number, lon: number, ref: { lat: number; lon: number }): Pt {
  return {
    e: (lon - ref.lon) * M_PER_DEG * Math.cos((ref.lat * Math.PI) / 180),
    n: (lat - ref.lat) * M_PER_DEG,
  }
}

/** A round distance for the scale bar. */
function niceLength(m: number): number {
  const pow = 10 ** Math.floor(Math.log10(m))
  const f = m / pow
  return (f >= 5 ? 5 : f >= 2 ? 2 : 1) * pow
}

type Props = {
  open: boolean
  onToggle: () => void
  onCallHelp: () => void
}

export function LiveTrack({ open, onToggle, onCallHelp }: Props) {
  const p = useProjection()
  const [copied, setCopied] = useState(false)
  const name = (p.config.patient as { preferred_name?: string; name?: string } | undefined)?.preferred_name
  const who = name || 'They'

  const track = p.person_trail.filter((t): t is typeof t & { lat: number; lon: number } => t.lat != null && t.lon != null)
  const now = p.person_track
  if (track.length === 0 || now?.lat == null || now.lon == null) return null

  const ref = { lat: track[0].lat, lon: track[0].lon }
  const path = track.map((t) => offset(t.lat, t.lon, ref))
  const person = offset(now.lat, now.lon, ref)
  const dog = p.pose?.lat != null && p.pose.lon != null ? offset(p.pose.lat, p.pose.lon, ref) : null

  const homeDist = Math.round(Math.hypot(person.e, person.n))
  const dogGap = dog ? Math.round(Math.hypot(person.e - dog.e, person.n - dog.n)) : null
  const updated = new Date((track[track.length - 1].ts || 0) * 1000).toLocaleTimeString([], {
    hour: 'numeric',
    minute: '2-digit',
    second: '2-digit',
  })
  const coords = `${now.lat.toFixed(5)}, ${now.lon.toFixed(5)}`
  const mapsUrl = `https://www.google.com/maps/search/?api=1&query=${now.lat},${now.lon}`

  // Fit everything into the frame with one uniform scale.
  const all = [{ e: 0, n: 0 }, ...path, ...(dog ? [dog] : [])]
  const minE = Math.min(...all.map((q) => q.e))
  const maxE = Math.max(...all.map((q) => q.e))
  const minN = Math.min(...all.map((q) => q.n))
  const maxN = Math.max(...all.map((q) => q.n))
  const scale = Math.min((W - PAD * 2) / Math.max(maxE - minE, 20), (H - PAD * 2) / Math.max(maxN - minN, 20))
  const offX = (W - (maxE - minE) * scale) / 2
  const offY = (H - (maxN - minN) * scale) / 2
  const sv = (q: Pt) => ({ x: offX + (q.e - minE) * scale, y: H - offY - (q.n - minN) * scale })

  const home = sv({ e: 0, n: 0 })
  const me = sv(person)
  const pup = dog ? sv(dog) : null
  const barM = niceLength(80 / scale)

  async function copy() {
    try {
      await navigator.clipboard.writeText(coords)
      setCopied(true)
      setTimeout(() => setCopied(false), 1500)
    } catch {
      /* clipboard can be blocked on plain http */
    }
  }

  return (
    <section id="live-track" className="card-slate !p-5">
      <div className="mb-4 flex items-start justify-between gap-3">
        <div>
          <p className="eyebrow mb-2 inline-flex items-center gap-2">
            <span className="h-2 w-2 animate-pulse rounded-full bg-[var(--color-danger)]" />
            Live location
          </p>
          <h2>{who} is outside</h2>
        </div>
        <button type="button" className={open ? 'btn-ghost !min-h-10 !py-2' : 'btn-primary !min-h-10 !py-2'} onClick={onToggle}>
          {open ? 'Hide map' : 'Track live location'}
        </button>
      </div>

      {!open && (
        <p className="text-[14px] text-[var(--color-ink-2)]">
          About {homeDist} m from home. Open the map to follow them and find where they are.
        </p>
      )}

      {open && (
        <>
          <svg viewBox={`0 0 ${W} ${H}`} className="h-auto w-full rounded-[14px] bg-[var(--color-surface)]">
            {Array.from({ length: 7 }, (_, i) => (
              <line key={`v${i}`} x1={(W / 6) * i} y1={0} x2={(W / 6) * i} y2={H} stroke="#eef1f4" strokeWidth={1} />
            ))}
            {Array.from({ length: 6 }, (_, i) => (
              <line key={`h${i}`} x1={0} y1={(H / 5) * i} x2={W} y2={(H / 5) * i} stroke="#eef1f4" strokeWidth={1} />
            ))}

            <polyline
              fill="none"
              stroke="#2563ff"
              strokeWidth={3}
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeDasharray="1 7"
              points={path.map((q) => `${sv(q).x},${sv(q).y}`).join(' ')}
            />

            <g>
              <circle cx={home.x} cy={home.y} r={8} fill="#0e1116" stroke="#fff" strokeWidth={2} />
              <text x={home.x + 12} y={home.y + 4} fontSize={11} fontWeight={600} fill="#0e1116" fontFamily="Inter, sans-serif">
                home
              </text>
            </g>

            {pup && (
              <g>
                <circle cx={pup.x} cy={pup.y} r={7} fill="#2563ff" stroke="#fff" strokeWidth={2} />
                <text x={pup.x - 12} y={pup.y + 4} textAnchor="end" fontSize={11} fontWeight={600} fill="#0e1116" fontFamily="Inter, sans-serif">
                  Lantern
                </text>
              </g>
            )}

            <g>
              <circle cx={me.x} cy={me.y} r={10} fill="#e5484d" opacity={0.25}>
                <animate attributeName="r" values="10;22;10" dur="1.6s" repeatCount="indefinite" />
                <animate attributeName="opacity" values="0.3;0;0.3" dur="1.6s" repeatCount="indefinite" />
              </circle>
              <circle cx={me.x} cy={me.y} r={9} fill="#e5484d" stroke="#fff" strokeWidth={2.5} />
              <text x={me.x - 14} y={me.y - 14} textAnchor="end" fontSize={12} fontWeight={600} fill="#0e1116" fontFamily="Inter, sans-serif" stroke="#fff" strokeWidth={3} paintOrder="stroke">
                {who}
              </text>
            </g>

            <g>
              <line x1={PAD} y1={H - 18} x2={PAD + barM * scale} y2={H - 18} stroke="#0e1116" strokeWidth={2} />
              <text x={PAD} y={H - 24} fontSize={10} fill="#4a5560" fontFamily="Inter, sans-serif">
                {barM} m
              </text>
            </g>
          </svg>

          <dl className="mt-4 grid grid-cols-2 gap-x-4 gap-y-3 text-[13px]">
            <div>
              <dt className="eyebrow mb-0.5">From home</dt>
              <dd className="text-[15px] text-[var(--color-ink)]">{homeDist} m</dd>
            </div>
            <div>
              <dt className="eyebrow mb-0.5">Lantern is</dt>
              <dd className="text-[15px] text-[var(--color-ink)]">{dogGap != null ? `${dogGap} m behind` : 'nearby'}</dd>
            </div>
            <div>
              <dt className="eyebrow mb-0.5">Location</dt>
              <dd className="text-[15px] text-[var(--color-ink)]">{coords}</dd>
            </div>
            <div>
              <dt className="eyebrow mb-0.5">Updated</dt>
              <dd className="text-[15px] text-[var(--color-ink)]">{updated}</dd>
            </div>
          </dl>

          <div className="mt-4 flex flex-wrap gap-3">
            <a href={mapsUrl} target="_blank" rel="noreferrer" className="btn-primary !min-h-10 !py-2">
              Open in Maps
            </a>
            <button type="button" className="btn-ghost !min-h-10 !py-2" onClick={copy}>
              {copied ? 'Copied' : 'Copy location'}
            </button>
            <button type="button" className="btn-ghost !min-h-10 !py-2" onClick={onCallHelp}>
              Call for help
            </button>
          </div>
        </>
      )}
    </section>
  )
}
