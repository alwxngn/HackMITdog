import type { ReactNode } from 'react'
import { DogMascot } from './DogMascot'
import { Wave } from './Wave'

interface Props {
  /** row above the title (logo, toggles) */
  top?: ReactNode
  children: ReactNode
  mood?: 'happy' | 'sleepy' | 'alert'
  avatar?: number
  /** show a red "!" above the mascot: Lantern is on alert */
  alert?: boolean
  /** inner container width, e.g. for wide pages */
  inner?: string
}

/** Navy header block with the mascot in a peach bubble and a dripping bottom edge. */
export function Hero({ top, children, mood = 'happy', avatar = 92, alert = false, inner = '' }: Props) {
  return (
    <header className="relative text-[#d5e7e4]">
      <div className="bg-[var(--color-brand)] px-7 pb-1 pt-7">
       <div className={`mx-auto ${inner}`}>
        {top}
        <div className={`${top ? 'mt-6' : ''} flex items-end justify-between gap-3`}>
          <div className="min-w-0 flex-1 pb-3">{children}</div>
          <div
            className="relative z-10 grid shrink-0 translate-y-7 place-items-center rounded-full border-4 border-[var(--color-bg)] bg-white shadow-[var(--shadow-card)]"
            style={{ width: avatar, height: avatar }}
          >
            <DogMascot mood={mood} className="h-[84%] w-[84%]" />
            {alert && (
              <span
                role="img"
                aria-label="Night Watch is on. Lantern is alert."
                className="absolute -top-3 left-1/2 -ml-[15px] grid h-[30px] w-[30px] place-items-center rounded-full border-[3px] border-white bg-[var(--color-danger)] text-[17px] font-bold leading-none text-white shadow-[0_4px_10px_-2px_rgba(229,98,106,0.7)]"
                style={{ animation: 'alert-pop 1.8s ease-in-out infinite' }}
              >
                !
              </span>
            )}
          </div>
        </div>
       </div>
      </div>
      <Wave className="-mt-px block h-[34px] w-full" />
    </header>
  )
}
