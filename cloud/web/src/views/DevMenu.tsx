import { DemoWalk } from './DemoWalk'

/**
 * Presenter/dev tools that live beside the phone, not inside it. Shown only on wide
 * screens where there is room next to the phone-width column; hidden on a real phone.
 */
export function DevMenu() {
  return (
    <aside
      aria-label="Dev menu"
      className="fixed top-6 z-20 hidden w-[280px] flex-col gap-3 min-[1120px]:flex"
      style={{ left: 'calc(50% + 254px)' }}
    >
      <p className="eyebrow inline-flex items-center gap-2 px-1">
        <span className="rounded-full bg-[var(--color-ink)] px-2 py-0.5 text-[10px] font-semibold tracking-[0.08em] text-white">
          DEV
        </span>
        Dev menu
      </p>
      <DemoWalk />
    </aside>
  )
}
