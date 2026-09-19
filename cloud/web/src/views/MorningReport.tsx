import { useEffect, useState } from 'react'
import type { MorningReport as Report } from '../lib/types'

export function MorningReport() {
  const [report, setReport] = useState<Report | null>(null)

  async function load() {
    const r = await fetch('/api/report')
    setReport(await r.json())
  }

  useEffect(() => {
    load()
    const id = setInterval(load, 5000)
    return () => clearInterval(id)
  }, [])

  if (!report) return null

  return (
    <div className="rounded-lg bg-[var(--panel)] p-4">
      <div className="mb-2 flex items-baseline justify-between">
        <h2 className="text-lg">Morning report</h2>
        <button className="text-xs text-[var(--muted)] underline" onClick={load}>
          refresh
        </button>
      </div>
      <p className="text-[var(--accent)]">{report.summary}</p>
      <ul className="mt-3 space-y-2 text-sm text-[var(--muted)]">
        {report.episodes.map((e, i) => (
          <li key={i}>
            {e.peak_state} · {e.duration_s}s · {e.resolution || 'open'}
            {e.reason ? ` — ${e.reason}` : ''}
          </li>
        ))}
      </ul>
    </div>
  )
}
