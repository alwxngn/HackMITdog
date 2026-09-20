import { useEffect, useState } from 'react'
import { episodeLine } from '../lib/copy'
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
    <div className="card-cream">
      <div className="mb-3 flex items-baseline justify-between">
        <div>
          <p className="eyebrow mb-2">Overnight</p>
          <h2>Last night</h2>
        </div>
        <button type="button" className="text-[13px] text-[var(--color-ink)] underline" onClick={load}>
          Refresh
        </button>
      </div>
      <p className="text-[16px] text-[var(--color-ink)]">{report.summary}</p>
      {report.episodes.length === 0 ? (
        <p className="mt-3 text-[14px] text-[var(--color-ink-2)]">A peaceful night. Nothing to worry about.</p>
      ) : (
        <ul className="mt-4 space-y-2 text-[14px] text-[var(--color-ink-2)]">
          {report.episodes.map((e, i) => (
            <li key={i} className="flex gap-2">
              <span className="mt-1.5 h-2 w-2 shrink-0 rounded-full bg-[var(--color-ink)]" />
              <span>{episodeLine(e)}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
