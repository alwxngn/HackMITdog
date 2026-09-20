import { useState } from 'react'
import { useRoutine } from '../hooks/useRoutine'
import {
  DAY_LABELS,
  DAY_NAMES,
  KIND_META,
  MOCK_ROUTINE,
  byTime,
  formatTime,
  todayIndex,
} from '../lib/routine'
import { RoutineEditor } from './RoutineEditor'

function nowHHMM() {
  const d = new Date()
  return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}

export function RoutineTab({ name }: { name?: string }) {
  const { items, hasSaved, save } = useRoutine(MOCK_ROUTINE)
  const today = todayIndex()
  const [day, setDay] = useState(today)
  const [done, setDone] = useState<Record<string, boolean>>({})
  const [view, setView] = useState<'day' | 'edit'>('day')

  const list = items.filter((i) => i.enabled && i.days[day]).sort(byTime)
  const key = (id: string) => `${id}:${day}`
  const doneCount = list.filter((i) => done[key(i.id)]).length
  const pct = list.length ? Math.round((doneCount / list.length) * 100) : 0
  const nextId = day === today ? list.find((i) => !done[key(i.id)] && i.time >= nowHHMM())?.id : undefined

  return (
    <div className="flex flex-col gap-4">
      {/* Today | Edit */}
      <div role="tablist" aria-label="Routine views" className="grid grid-cols-2 gap-1 rounded-full border border-[var(--color-line)] bg-[var(--color-surface)] p-1">
        {(
          [
            ['day', 'Today'],
            ['edit', 'Edit routine'],
          ] as const
        ).map(([id, label]) => (
          <button
            key={id}
            type="button"
            role="tab"
            aria-selected={view === id}
            onClick={() => setView(id)}
            className={`h-10 cursor-pointer rounded-full text-[14px] font-semibold transition-colors ${
              view === id ? 'bg-[var(--color-brand)] text-white' : 'text-[var(--color-ink-2)] hover:bg-[var(--color-panel)]'
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {view === 'day' && (
        <>
      {/* week strip */}
      <div className="flex justify-between gap-1.5">
        {DAY_LABELS.map((l, i) => (
          <button
            key={i}
            type="button"
            aria-label={DAY_NAMES[i]}
            aria-pressed={day === i}
            onClick={() => setDay(i)}
            className={`flex h-[62px] flex-1 cursor-pointer flex-col items-center justify-center rounded-[18px] border border-[var(--color-line)] transition-colors ${
              day === i
                ? 'bg-[var(--color-accent)] text-[var(--color-ink)] shadow-[var(--shadow-lift)]'
                : 'bg-[var(--color-surface)] text-[var(--color-ink)]'
            }`}
          >
            <span className="text-[11px] font-semibold uppercase opacity-70">{DAY_NAMES[i]}</span>
            <span className="text-[17px] font-bold leading-none">{l}</span>
            {i === today && <span className="mt-1 h-1.5 w-1.5 rounded-full bg-[var(--color-ink)]" />}
          </button>
        ))}
      </div>

      {/* progress */}
      <div className="card-mint !p-4">
        <div className="mb-2 flex items-baseline justify-between">
          <p className="text-[15px] font-semibold text-[var(--color-ink)]">
            {day === today ? 'Today' : DAY_NAMES[day]}
            <span className="ml-2 text-[13px] font-bold text-[var(--color-ink-2)]">
              {doneCount} of {list.length} done
            </span>
          </p>
          <span className="text-[13px] font-semibold text-[var(--color-ink)]">{pct}%</span>
        </div>
        <div className="h-3 overflow-hidden rounded-full border border-[var(--color-line)] bg-[var(--color-surface)]">
          <div
            className="h-full rounded-full bg-[var(--color-ink)] transition-all duration-500"
            style={{ width: `${pct}%` }}
          />
        </div>
      </div>

      {!hasSaved && (
        <p className="rounded-[16px] border-2 border-dashed border-[var(--color-tint)] bg-[var(--color-surface)] px-4 py-3 text-[13px] font-semibold">
          This is a sample day. Open Edit routine and change anything to make it {name ? `${name}’s` : 'the'} routine.
        </p>
      )}

      {/* the day */}
      {list.length === 0 ? (
        <div className="card text-center">
          <p className="text-[15px] font-semibold text-[var(--color-ink)]">Nothing planned for {DAY_NAMES[day]}</p>
          <p className="mt-1 text-[13px]">Add something below, or switch a day on for an existing item.</p>
        </div>
      ) : (
        <ul className="space-y-2.5">
          {list.map((it) => {
            const meta = KIND_META[it.kind]
            const isDone = !!done[key(it.id)]
            const isNext = it.id === nextId
            return (
              <li key={it.id} className="flex items-stretch gap-3">
                <span className="w-[62px] shrink-0 pt-4 text-right text-[12px] font-semibold text-[var(--color-ink-2)]">
                  {formatTime(it.time)}
                </span>
                <button
                  type="button"
                  onClick={() => setDone({ ...done, [key(it.id)]: !isDone })}
                  aria-pressed={isDone}
                  className={`flex flex-1 cursor-pointer items-center gap-3 rounded-[20px] border border-[var(--color-line)] p-3 text-left transition-colors ${
                    isNext ? 'bg-[var(--color-accent-soft)] shadow-[var(--shadow-lift)]' : 'bg-[var(--color-surface)]'
                  }`}
                >
                  <span
                    aria-hidden
                    className="grid h-10 w-10 shrink-0 place-items-center rounded-[13px] border border-[var(--color-line)] text-[18px]"
                    style={{ background: meta.bg }}
                  >
                    {meta.emoji}
                  </span>
                  <span className="min-w-0 flex-1">
                    <span
                      className={`block truncate text-[15px] font-semibold text-[var(--color-ink)] ${
                        isDone ? 'line-through opacity-50' : ''
                      }`}
                    >
                      {it.title}
                    </span>
                    <span className="block text-[12px] font-semibold">
                      {isNext ? 'Up next' : meta.label}
                    </span>
                  </span>
                  <span
                    aria-hidden
                    className={`grid h-7 w-7 shrink-0 place-items-center rounded-full border border-[var(--color-line)] ${
                      isDone ? 'bg-[var(--color-ink)]' : 'bg-[var(--color-surface)]'
                    }`}
                  >
                    {isDone && (
                      <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="#fff" strokeWidth="3.2" strokeLinecap="round" strokeLinejoin="round">
                        <path d="m5 12.5 4.5 4.5L19 7.5" />
                      </svg>
                    )}
                  </span>
                </button>
              </li>
            )
          })}
        </ul>
      )}
        </>
      )}

      {view === 'edit' && (
        <div>
          <h2 className="mb-1 text-[22px]">Edit routine</h2>
          <p className="mb-3 text-[13px]">
            Tap an item to change its time or days. A steady daily rhythm helps with memory.
          </p>
          <RoutineEditor items={items} onChange={save} />
        </div>
      )}
    </div>
  )
}
