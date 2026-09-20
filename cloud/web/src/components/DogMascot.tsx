type Mood = 'happy' | 'sleepy' | 'alert'

interface Props {
  mood?: Mood
  className?: string
  /** gentle bob + blink */
  animate?: boolean
  title?: string
  /** any CSS colour; defaults to the brand teal */
  color?: string
}

/**
 * Lantern's mascot: a flat, one-colour pup. Two leaf ears, dot eyes, a half-moon nose
 * and a bone for a smile — the negative space above the bone is the mouth.
 */
export function DogMascot({
  mood = 'happy',
  className,
  animate = true,
  title = 'Lantern the dog',
  color = 'var(--color-brand)',
}: Props) {
  const eye = mood === 'alert' ? 9 : 7.4

  return (
    <svg
      viewBox="12 8 176 140"
      role="img"
      aria-label={title}
      className={className}
      fill={color}
      style={animate ? { animation: 'dog-bob 3.6s ease-in-out infinite' } : undefined}
    >
      {/* ears */}
      <polygon points="33,34 62,26 40,52" stroke={color} strokeWidth="14" strokeLinejoin="round" />
      <polygon points="147,46 170,60 156,75" stroke={color} strokeWidth="14" strokeLinejoin="round" />

      {/* eyes */}
      {mood === 'sleepy' ? (
        <g fill="none" stroke={color} strokeWidth="3.6" strokeLinecap="round">
          <path d="M62 62 q7 6.5 14 0" />
          <path d="M117 74 q7 6.5 14 0" />
        </g>
      ) : (
        <g style={animate ? { transformOrigin: '96px 68px', animation: 'dog-blink 5s ease-in-out infinite' } : undefined}>
          <circle cx="69" cy="62" r={eye} />
          <circle cx="124" cy="74" r={eye} />
        </g>
      )}

      {/* nose */}
      <path d="M81 88 H103 A11 11 0 0 1 81 88 Z" transform="rotate(8 92 90)" />

      {/* whisker dots */}
      <g>
        <circle cx="66" cy="105" r="1.4" />
        <circle cx="72" cy="102" r="1.4" />
        <circle cx="76" cy="108" r="1.4" />
        <circle cx="107" cy="103" r="1.4" />
        <circle cx="110" cy="108" r="1.4" />
        <circle cx="115" cy="107" r="1.4" />
        <circle cx="104" cy="111" r="1.4" />
      </g>

      {/* bone smile */}
      <path d="M40 106 Q90 128 142 106 L146 130 L36 132 Z" />
      <circle cx="34" cy="102" r="15" />
      <circle cx="28" cy="127" r="12" />
      <circle cx="141" cy="103" r="13" />
      <circle cx="148" cy="131" r="11" />
    </svg>
  )
}
