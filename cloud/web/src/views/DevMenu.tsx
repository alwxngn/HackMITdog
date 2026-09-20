import { useState, type ReactNode } from 'react'
import { Switch } from '../components/Switch'
import { useProjection } from '../hooks/useProjection'
import { setNightWatch } from '../lib/nightWatch'
import { DemoWalk } from './DemoWalk'

/**
 * Presenter/dev tools live beside the phone, not inside it. Shown only on wide screens
 * where there is room next to the phone-width column; hidden on a real phone.
 */
export function DevMenuShell({ children }: { children: ReactNode }) {
  return (
    <aside
      aria-label="Developer menu"
      className="fixed top-6 z-20 hidden w-[280px] flex-col gap-3 min-[1120px]:flex"
      style={{ left: 'calc(50% + 254px)' }}
    >
      <p className="eyebrow px-1">Developer menu</p>
      {children}
    </aside>
  )
}

export function DevMenu() {
  const p = useProjection()
  const [error, setError] = useState('')
  const on = (p.config.night_watch_enabled as boolean | undefined) ?? false

  return (
    <DevMenuShell>
      <section className="card !p-5">
        <div className="flex items-center justify-between gap-4">
          <div>
            <p className="text-[15px] font-semibold text-[var(--color-ink)]">Night Watch</p>
            <p className="text-[12px] text-[var(--color-ink-2)]">
              {on ? 'Warning and danger zones are on' : 'Zones are hidden and ignored'}
            </p>
          </div>
          <Switch on={on} onChange={async (next) => setError((await setNightWatch(next)) ?? '')} label="Night Watch" />
        </div>
        {error && (
          <p role="alert" className="mt-3 text-[12px] text-[var(--color-danger)]">
            {error}
          </p>
        )}
      </section>

      <DemoWalk />
    </DevMenuShell>
  )
}
