export function Switch({
  on,
  onChange,
  label,
}: {
  on: boolean
  onChange: (next: boolean) => void
  label: string
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={on}
      aria-label={label}
      onClick={() => onChange(!on)}
      className={`relative h-7 w-12 shrink-0 cursor-pointer rounded-full border border-[var(--color-line)] transition-colors ${
        on ? 'bg-[var(--color-accent)]' : 'bg-[var(--color-panel)]'
      }`}
    >
      <span
        className={`absolute top-[3px] h-4 w-4 rounded-full border border-[var(--color-line)] bg-[var(--color-surface)] transition-all ${
          on ? 'left-[23px]' : 'left-[3px]'
        }`}
      />
    </button>
  )
}
