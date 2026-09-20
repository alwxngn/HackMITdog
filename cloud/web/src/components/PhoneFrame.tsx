import type { ReactNode } from 'react'

/**
 * Centered, phone-width column shared by every screen. On real phones it fills the screen;
 * on wider screens it floats in the middle as a rounded card.
 */
export function PhoneFrame({ children, className = '' }: { children: ReactNode; className?: string }) {
  return (
    <div className="min-h-full sm:bg-[var(--color-panel-2)] sm:py-6">
      <div
        className={`relative mx-auto flex min-h-full w-full max-w-[460px] flex-col overflow-hidden sm:min-h-[calc(100dvh-3rem)] sm:rounded-[40px] sm:shadow-[0_30px_60px_-24px_rgba(21,58,59,0.5)] ${className}`}
      >
        {children}
      </div>
    </div>
  )
}
