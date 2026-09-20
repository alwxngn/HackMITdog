/** Soft wave that sits under a solid block of the same colour. */
export function Wave({ className, color = 'var(--color-brand)' }: { className?: string; color?: string }) {
  return (
    <svg
      viewBox="0 0 400 40"
      preserveAspectRatio="none"
      aria-hidden
      className={className ?? 'block h-[34px] w-full'}
    >
      <path fill={color} d="M0 0H400V10C340 36 270 4 200 14C130 24 70 38 0 12Z" />
    </svg>
  )
}
