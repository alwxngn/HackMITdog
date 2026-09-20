/** Faint paw prints scattered over a coloured background. Place inside a `relative` parent. */
export function PawBackdrop({ opacity = 0.09 }: { opacity?: number }) {
  return (
    <svg aria-hidden className="pointer-events-none absolute inset-0 h-full w-full">
      <defs>
        <g id="lantern-paw">
          <path d="M0 10c-12 0-21 10-15 20 4 7 10 6 15 6s11 1 15-6c6-10-3-20-15-20z" />
          <ellipse cx="-20" cy="-2" rx="5.5" ry="8" transform="rotate(-22 -20 -2)" />
          <ellipse cx="-7" cy="-14" rx="5.5" ry="8.5" />
          <ellipse cx="7" cy="-14" rx="5.5" ry="8.5" />
          <ellipse cx="20" cy="-2" rx="5.5" ry="8" transform="rotate(22 20 -2)" />
        </g>
        <pattern id="lantern-paws" width="260" height="260" patternUnits="userSpaceOnUse" patternTransform="rotate(-14)">
          <g fill="#fff" opacity={opacity}>
            <use href="#lantern-paw" transform="translate(56 64) scale(1.1)" />
            <use href="#lantern-paw" transform="translate(190 150) scale(1.9) rotate(22)" />
            <use href="#lantern-paw" transform="translate(70 214) scale(0.8) rotate(-12)" />
          </g>
        </pattern>
      </defs>
      <rect width="100%" height="100%" fill="url(#lantern-paws)" />
    </svg>
  )
}
