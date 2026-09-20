import type { ReactNode } from 'react'

export type TabId = 'home' | 'checkin' | 'activity' | 'settings'

const stroke = {
  fill: 'none',
  stroke: 'currentColor',
  strokeWidth: 1.7,
  strokeLinecap: 'round' as const,
  strokeLinejoin: 'round' as const,
}

const TABS: { id: TabId; label: string; icon: ReactNode }[] = [
  {
    id: 'home',
    label: 'Home',
    icon: (
      <svg viewBox="0 0 24 24" className="h-[22px] w-[22px]" {...stroke}>
        <path d="M4 11.2 12 4l8 7.2" />
        <path d="M6 9.8V19a1 1 0 0 0 1 1h3.5v-5.5h3V20H17a1 1 0 0 0 1-1V9.8" />
      </svg>
    ),
  },
  {
    id: 'checkin',
    label: 'Check in',
    icon: (
      <svg viewBox="0 0 24 24" className="h-[22px] w-[22px]" {...stroke}>
        <path d="M5 5h14a1 1 0 0 1 1 1v9a1 1 0 0 1-1 1h-7l-4.5 3.5V16H5a1 1 0 0 1-1-1V6a1 1 0 0 1 1-1Z" />
        <path d="M8.5 9.5h7M8.5 12.5h4" />
      </svg>
    ),
  },
  {
    id: 'activity',
    label: 'Activity',
    icon: (
      <svg viewBox="0 0 24 24" className="h-[22px] w-[22px]" {...stroke}>
        <circle cx="12" cy="12" r="8" />
        <path d="M12 7.5V12l3 2" />
      </svg>
    ),
  },
  {
    id: 'settings',
    label: 'Settings',
    icon: (
      <svg viewBox="0 0 24 24" className="h-[22px] w-[22px]" {...stroke}>
        <path d="M5 8h9M18 8h1M5 16h1M10 16h9" />
        <circle cx="16" cy="8" r="2" />
        <circle cx="8" cy="16" r="2" />
      </svg>
    ),
  },
]

interface Props {
  active: TabId
  onChange: (t: TabId) => void
  /** small dot on a tab, e.g. unread check-in reply */
  badge?: TabId | null
}

/** Floating pill nav. The active tab expands to show its label. */
export function TabIsland({ active, onChange, badge }: Props) {
  return (
    <nav
      aria-label="Sections"
      className="fixed inset-x-0 bottom-0 z-40 flex justify-center px-4 pointer-events-none"
      style={{ paddingBottom: 'calc(env(safe-area-inset-bottom, 0px) + 16px)' }}
    >
      <div className="pointer-events-auto flex items-center gap-1 rounded-full bg-[var(--color-ink)] p-1.5 shadow-[0_14px_34px_-10px_rgba(5,7,10,0.55)]">
        {TABS.map((t) => {
          const on = t.id === active
          return (
            <button
              key={t.id}
              type="button"
              aria-label={t.label}
              aria-current={on ? 'page' : undefined}
              onClick={() => onChange(t.id)}
              className={`relative flex h-11 cursor-pointer items-center justify-center gap-2 rounded-full transition-all duration-300 ease-out ${
                on
                  ? 'bg-[var(--color-surface)] px-4 text-[var(--color-ink)]'
                  : 'w-11 text-[var(--color-tint)] hover:text-[var(--color-surface)]'
              }`}
            >
              {t.icon}
              {on && <span className="text-[13px] font-medium whitespace-nowrap">{t.label}</span>}
              {badge === t.id && !on && (
                <span className="absolute right-2 top-2 h-2 w-2 rounded-full bg-[var(--color-tint)] ring-2 ring-[var(--color-ink)]" />
              )}
            </button>
          )
        })}
      </div>
    </nav>
  )
}
