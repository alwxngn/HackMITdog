import { useState } from 'react'
import { Switch } from '../components/Switch'
import {
  DAY_LABELS,
  DAY_NAMES,
  KIND_META,
  SUGGESTIONS,
  byTime,
  describeDays,
  formatTime,
  makeItem,
  type RoutineItem,
  type RoutineKind,
} from '../lib/routine'

const KINDS = Object.keys(KIND_META) as RoutineKind[]

export function DayChips({ days, onChange }: { days: boolean[]; onChange: (d: boolean[]) => void }) {
  return (
    <div className="flex gap-1.5">
      {DAY_LABELS.map((l, i) => (
        <button
          key={i}
          type="button"
          aria-label={DAY_NAMES[i]}
          aria-pressed={days[i]}
          onClick={() => onChange(days.map((d, j) => (j === i ? !d : d)))}
          className={`grid h-9 w-9 cursor-pointer place-items-center rounded-full border border-[var(--color-line)] text-[13px] font-semibold transition-colors ${
            days[i]
              ? 'bg-[var(--color-ink)] text-[var(--color-surface)]'
              : 'bg-[var(--color-surface)] text-[var(--color-ink)]'
          }`}
        >
          {l}
        </button>
      ))}
    </div>
  )
}

function KindChips({ kind, onChange }: { kind: RoutineKind; onChange: (k: RoutineKind) => void }) {
  return (
    <div className="flex flex-wrap gap-1.5">
      {KINDS.map((k) => (
        <button
          key={k}
          type="button"
          aria-pressed={kind === k}
          onClick={() => onChange(k)}
          className={`inline-flex cursor-pointer items-center gap-1 rounded-full border border-[var(--color-line)] px-2.5 py-1 text-[12px] font-semibold text-[var(--color-ink)] ${
            kind === k ? 'bg-[var(--color-accent)]' : 'bg-[var(--color-surface)]'
          }`}
        >
          <span aria-hidden>{KIND_META[k].emoji}</span>
          {KIND_META[k].label}
        </button>
      ))}
    </div>
  )
}

function ItemCard({
  item,
  onChange,
  onDelete,
}: {
  item: RoutineItem
  onChange: (next: RoutineItem) => void
  onDelete: () => void
}) {
  const [open, setOpen] = useState(false)
  const meta = KIND_META[item.kind]
  return (
    <li className="rounded-[20px] border border-[var(--color-line)] bg-[var(--color-surface)]">
      <div className="flex items-center gap-3 p-3">
        <button
          type="button"
          onClick={() => setOpen((o) => !o)}
          aria-expanded={open}
          className="flex min-w-0 flex-1 cursor-pointer items-center gap-3 text-left"
        >
          <span
            aria-hidden
            className="grid h-11 w-11 shrink-0 place-items-center rounded-[14px] border border-[var(--color-line)] text-[20px]"
            style={{ background: meta.bg, opacity: item.enabled ? 1 : 0.5 }}
          >
            {meta.emoji}
          </span>
          <span className={`min-w-0 ${item.enabled ? '' : 'opacity-50'}`}>
            <span className="block truncate text-[15px] font-semibold text-[var(--color-ink)]">{item.title || 'Untitled'}</span>
            <span className="block truncate text-[12px] font-semibold">
              {formatTime(item.time)} · {describeDays(item.days)}
            </span>
          </span>
        </button>
        <Switch on={item.enabled} onChange={(enabled) => onChange({ ...item, enabled })} label={`${item.title} on`} />
      </div>

      {open && (
        <div className="space-y-3 border-t-2 border-dashed border-[var(--color-line)] p-3">
          <div className="flex gap-2">
            <input
              className="input-field !py-2"
              value={item.title}
              onChange={(e) => onChange({ ...item, title: e.target.value })}
              aria-label="Title"
              maxLength={40}
            />
            <input
              className="input-field !w-[152px] !px-3 !py-2"
              type="time"
              value={item.time}
              onChange={(e) => onChange({ ...item, time: e.target.value })}
              aria-label="Time"
            />
          </div>
          <KindChips kind={item.kind} onChange={(kind) => onChange({ ...item, kind })} />
          <DayChips days={item.days} onChange={(days) => onChange({ ...item, days })} />
          <button
            type="button"
            className="cursor-pointer text-[13px] font-semibold text-[var(--color-danger)] underline underline-offset-4"
            onClick={onDelete}
          >
            Remove from routine
          </button>
        </div>
      )}
    </li>
  )
}

interface Props {
  items: RoutineItem[]
  onChange: (next: RoutineItem[]) => void
  /** one-tap starter chips (used in onboarding) */
  suggestions?: boolean
}

/** Edit the daily routine: existing items (time, days, on/off) plus an add form. */
export function RoutineEditor({ items, onChange, suggestions }: Props) {
  const [time, setTime] = useState('09:00')
  const [title, setTitle] = useState('')
  const [kind, setKind] = useState<RoutineKind>('other')
  const [days, setDays] = useState<boolean[]>([true, true, true, true, true, true, true])

  const sorted = [...items].sort(byTime)

  function add() {
    if (!title.trim()) return
    onChange([...items, makeItem(time, title.trim(), kind, days)])
    setTitle('')
  }

  return (
    <div className="space-y-4">
      {suggestions && (
        <div>
          <p className="eyebrow mb-2">Quick add</p>
          <div className="flex flex-wrap gap-1.5">
            {SUGGESTIONS.map((s) => {
              const taken = items.some((i) => i.title === s.title)
              return (
                <button
                  key={s.title}
                  type="button"
                  disabled={taken}
                  onClick={() => onChange([...items, makeItem(s.time, s.title, s.kind)])}
                  className="inline-flex cursor-pointer items-center gap-1 rounded-full border border-[var(--color-line)] bg-[var(--color-surface)] px-3 py-1.5 text-[12px] font-semibold text-[var(--color-ink)] enabled:hover:bg-[var(--color-accent-soft)] disabled:cursor-default disabled:opacity-40"
                >
                  <span aria-hidden>{KIND_META[s.kind].emoji}</span>
                  {s.title}
                </button>
              )
            })}
          </div>
        </div>
      )}

      {sorted.length > 0 && (
        <ul className="space-y-2.5">
          {sorted.map((it) => (
            <ItemCard
              key={it.id}
              item={it}
              onChange={(next) => onChange(items.map((x) => (x.id === it.id ? next : x)))}
              onDelete={() => onChange(items.filter((x) => x.id !== it.id))}
            />
          ))}
        </ul>
      )}

      <div className="space-y-3 rounded-[20px] border-2 border-dashed border-[var(--color-tint)] bg-[var(--color-panel)] p-4">
        <p className="text-[15px] font-semibold text-[var(--color-ink)]">Add to routine</p>
        <div className="flex gap-2">
          <input
            className="input-field !py-2"
            placeholder="e.g. Water the plants"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && add()}
            aria-label="New routine item"
            maxLength={40}
          />
          <input
            className="input-field !w-[152px] !px-3 !py-2"
            type="time"
            value={time}
            onChange={(e) => setTime(e.target.value)}
            aria-label="Time"
          />
        </div>
        <KindChips kind={kind} onChange={setKind} />
        <DayChips days={days} onChange={setDays} />
        <button type="button" className="btn-primary !min-h-11" disabled={!title.trim()} onClick={add}>
          Add
        </button>
      </div>
    </div>
  )
}
