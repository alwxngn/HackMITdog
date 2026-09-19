import { useEffect, useMemo } from 'react'

type SplitBy = 'words' | 'characters' | 'lines'
type Direction = 'up' | 'down' | 'left' | 'right'
type StaggerFrom = 'start' | 'end' | 'center' | 'edges' | 'random' | number

interface Props {
  text: string
  splitBy?: SplitBy
  direction?: Direction
  distance?: number
  stagger?: number
  staggerFrom?: StaggerFrom
  blur?: boolean
  autoPlay?: boolean
  delay?: number
  className?: string
  segmentClassName?: string
  onRevealStart?: () => void
  onRevealComplete?: () => void
}

function segmentsOf(text: string, splitBy: SplitBy): string[] {
  if (splitBy === 'characters') return Array.from(text)
  if (splitBy === 'lines') return text.split('\n')
  return text.split(/(\s+)/)
}

function offset(direction: Direction, distance: number) {
  if (direction === 'up') return { kx: '0px', ky: `${distance}px` }
  if (direction === 'down') return { kx: '0px', ky: `${-distance}px` }
  if (direction === 'left') return { kx: `${distance}px`, ky: '0px' }
  return { kx: `${-distance}px`, ky: '0px' }
}

function staggerIndex(i: number, n: number, from: StaggerFrom): number {
  if (typeof from === 'number') return Math.abs(i - from)
  if (from === 'end') return n - 1 - i
  if (from === 'center') return Math.abs(i - (n - 1) / 2)
  if (from === 'edges') return Math.min(i, n - 1 - i)
  if (from === 'random') return Math.random() * n
  return i
}

export function KineticTextReveal({
  text,
  splitBy = 'words',
  direction = 'up',
  distance = 20,
  stagger = 0.075,
  staggerFrom = 'start',
  blur = true,
  autoPlay = true,
  delay = 0,
  className,
  segmentClassName,
  onRevealStart,
  onRevealComplete,
}: Props) {
  const parts = useMemo(() => segmentsOf(text, splitBy), [text, splitBy])
  const { kx, ky } = offset(direction, distance)

  useEffect(() => {
    if (!autoPlay) return
    onRevealStart?.()
    const last = Math.max(...parts.map((_, i) => staggerIndex(i, parts.length, staggerFrom)))
    const t = window.setTimeout(
      () => onRevealComplete?.(),
      (delay + last * stagger + 0.72) * 1000,
    )
    return () => window.clearTimeout(t)
  }, [autoPlay, delay, parts, stagger, staggerFrom, onRevealComplete, onRevealStart])

  return (
    <span className={className}>
      {parts.map((part, i) => {
        if (/^\s+$/.test(part)) return <span key={`s-${i}`}>{part}</span>
        const d = delay + staggerIndex(i, parts.length, staggerFrom) * stagger
        return (
          <span key={`${part}-${i}`} className="kinetic-mask">
            <span
              className={`kinetic-seg ${segmentClassName ?? ''}`}
              style={{
                animationDelay: `${d}s`,
                ['--kx' as string]: kx,
                ['--ky' as string]: ky,
                filter: blur ? undefined : 'none',
              }}
            >
              {part}
            </span>
          </span>
        )
      })}
    </span>
  )
}
