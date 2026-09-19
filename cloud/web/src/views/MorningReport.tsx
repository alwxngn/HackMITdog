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
    <div className="card">
      <div className="mb-3 flex items-baseline justify-between">
        <h2 className="text-[18px] tracking-[-0.03em]">Morning report</h2>
        <button
          type="button"
          className="text-[13px] text-[var(--color-forest-ink)] underline"
          onClick={load}
        >
          refresh
        </button>
      </div>
      <p className="text-[18px] text-[var(--color-forest-ink)]">
        {report.summary}
      </p>
      <ul className="mt-4 space-y-2 text-[14px] text-[var(--color-charcoal)]">
        {report.episodes.map((e, i) => (
          <li key={i} className="flex gap-2">
            <span className="mt-1 h-2 w-2 shrink-0 rounded-full bg-[var(--color-forest-ink)]" />
            <span>
              {e.peak_state} · {e.duration_s}s · {e.resolution || 'open'}
              {e.reason ? ` — ${e.reason}` : ''}
            </span>
          </li>
        ))}
      </ul>
    </div>
  )
}
